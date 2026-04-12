from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.gasto_electoral import (
    AlertaCompliance,
    CategoriaGastoINE,
    GastoElectoral,
    SeveridadAlerta,
    TipoAlertaCompliance,
)
from app.models.plan_ia import PlanIA
from app.models.social import SocialPost, SocialProfile
from app.schemas.blindaje import BotAnalysisResult, ComplianceReportResponse

# ── Thresholds ───────────────────────────────────────────────

FACTURA_REQUIRED_THRESHOLD_MXN = 5_000.0
TOPE_WARNING_PERCENT = 0.80


class BlindajeService:
    """Electoral compliance and legal protection service.

    Implements INE regulation checks including spending compliance,
    bot detection, content labeling verification, and veda enforcement.
    """

    # ── Bot detection ────────────────────────────────────────

    @staticmethod
    async def check_bot_indicators(
        db: AsyncSession,
        post: SocialPost,
    ) -> BotAnalysisResult:
        """Detect bot-like behavior on a social post's author profile.

        Indicators checked:
        - follower/following ratio > 10
        - engagement_rate < 0.01% with >10K followers
        - >50 posts/day from the same profile
        - Account age < 30 days with >1K followers (approximated via
          earliest post date in the system)
        """
        indicators: list[str] = []

        # Fetch the profile that owns this post
        profile_result = await db.execute(
            select(SocialProfile).where(SocialProfile.id == post.profile_id)
        )
        profile = profile_result.scalar_one_or_none()

        if profile is None:
            return BotAnalysisResult(
                post_id=post.id,
                is_suspicious=False,
                indicators=["Profile not found — cannot evaluate"],
                confidence=0.0,
            )

        # Indicator 1: follower/following ratio
        if profile.following_count > 0:
            ratio = profile.followers_count / profile.following_count
            if ratio > 10.0:
                indicators.append(f"Follower/following ratio is {ratio:.1f} (threshold: 10)")

        # Indicator 2: very low engagement with high follower count
        if profile.followers_count > 10_000 and post.engagement_rate < 0.0001:
            indicators.append(
                f"Engagement rate {post.engagement_rate:.6f} with "
                f"{profile.followers_count:,} followers (threshold: 0.01%)"
            )

        # Indicator 3: excessive posting frequency (>50 posts/day)
        one_day_ago = datetime.now(UTC) - timedelta(days=1)
        count_result = await db.execute(
            select(func.count(SocialPost.id)).where(
                SocialPost.profile_id == profile.id,
                SocialPost.published_at >= one_day_ago,
            )
        )
        daily_posts = count_result.scalar_one()
        if daily_posts > 50:
            indicators.append(f"Published {daily_posts} posts in the last 24h (threshold: 50)")

        # Indicator 4: new account with high follower count
        # Approximate account age using the earliest post we have on record
        earliest_result = await db.execute(
            select(func.min(SocialPost.published_at)).where(SocialPost.profile_id == profile.id)
        )
        earliest_post_date = earliest_result.scalar_one()
        if earliest_post_date is not None:
            account_age_days = (datetime.now(UTC) - earliest_post_date).days
            if account_age_days < 30 and profile.followers_count > 1_000:
                indicators.append(
                    f"Account age ~{account_age_days} days with "
                    f"{profile.followers_count:,} followers (threshold: 30 days / 1K)"
                )

        # Calculate confidence score based on number of indicators triggered
        confidence = min(len(indicators) * 0.30, 1.0)

        return BotAnalysisResult(
            post_id=post.id,
            is_suspicious=len(indicators) > 0,
            indicators=indicators,
            confidence=round(confidence, 2),
        )

    # ── Gastos compliance ────────────────────────────────────

    @staticmethod
    async def check_gastos_compliance(
        db: AsyncSession,
        org_id: int,
    ) -> list[AlertaCompliance]:
        """Check spending records for compliance violations.

        Rules:
        - Gastos > $5,000 MXN without factura_uuid
        - Individual gasto exceeding campaign tope
        - Accumulated spending approaching tope (>80%)
        """
        alertas: list[AlertaCompliance] = []
        tope = settings.TOPE_CAMPANA_MXN

        # 1. Gastos without factura above threshold
        gastos_sin_factura_result = await db.execute(
            select(GastoElectoral).where(
                GastoElectoral.org_id == org_id,
                GastoElectoral.monto > FACTURA_REQUIRED_THRESHOLD_MXN,
                GastoElectoral.factura_uuid.is_(None),
            )
        )
        for gasto in gastos_sin_factura_result.scalars().all():
            alertas.append(
                AlertaCompliance(
                    org_id=org_id,
                    tipo=TipoAlertaCompliance.GASTO_SIN_FACTURA,
                    severidad=SeveridadAlerta.ALTA,
                    titulo=f"Gasto sin factura: ${gasto.monto:,.2f}",
                    descripcion=(
                        f'El gasto "{gasto.concepto}" por ${gasto.monto:,.2f} '
                        f"del {gasto.fecha_gasto} no tiene CFDI asociado. "
                        f"Todo gasto mayor a ${FACTURA_REQUIRED_THRESHOLD_MXN:,.0f} "
                        f"requiere comprobante fiscal."
                    ),
                    referencia_tipo="gasto",
                    referencia_id=gasto.id,
                )
            )

        # 2. Individual gasto exceeding tope
        gastos_excede_result = await db.execute(
            select(GastoElectoral).where(
                GastoElectoral.org_id == org_id,
                GastoElectoral.monto > tope,
            )
        )
        for gasto in gastos_excede_result.scalars().all():
            alertas.append(
                AlertaCompliance(
                    org_id=org_id,
                    tipo=TipoAlertaCompliance.GASTO_EXCEDE_TOPE,
                    severidad=SeveridadAlerta.CRITICA,
                    titulo=f"Gasto excede tope de campana: ${gasto.monto:,.2f}",
                    descripcion=(
                        f'El gasto "{gasto.concepto}" por ${gasto.monto:,.2f} '
                        f"excede el tope de campana de ${tope:,.2f}."
                    ),
                    referencia_tipo="gasto",
                    referencia_id=gasto.id,
                )
            )

        # 3. Accumulated spending approaching tope
        total_result = await db.execute(
            select(func.coalesce(func.sum(GastoElectoral.monto), 0.0)).where(
                GastoElectoral.org_id == org_id,
            )
        )
        total_gastado = float(total_result.scalar_one())
        porcentaje = total_gastado / tope if tope > 0 else 0.0

        if porcentaje >= TOPE_WARNING_PERCENT and porcentaje < 1.0:
            alertas.append(
                AlertaCompliance(
                    org_id=org_id,
                    tipo=TipoAlertaCompliance.TOPE_CAMPANA_PROXIMO,
                    severidad=SeveridadAlerta.ALTA,
                    titulo=f"Gasto acumulado al {porcentaje:.0%} del tope",
                    descripcion=(
                        f"El gasto acumulado de ${total_gastado:,.2f} representa "
                        f"el {porcentaje:.1%} del tope de campana de ${tope:,.2f}. "
                        f"Quedan ${tope - total_gastado:,.2f} disponibles."
                    ),
                    referencia_tipo="organizacion",
                    referencia_id=None,
                )
            )
        elif porcentaje >= 1.0:
            alertas.append(
                AlertaCompliance(
                    org_id=org_id,
                    tipo=TipoAlertaCompliance.GASTO_EXCEDE_TOPE,
                    severidad=SeveridadAlerta.CRITICA,
                    titulo=f"Tope de campana excedido: {porcentaje:.0%}",
                    descripcion=(
                        f"El gasto acumulado de ${total_gastado:,.2f} excede "
                        f"el tope de campana de ${tope:,.2f} "
                        f"por ${total_gastado - tope:,.2f}."
                    ),
                    referencia_tipo="organizacion",
                    referencia_id=None,
                )
            )

        return alertas

    # ── Content compliance ───────────────────────────────────

    @staticmethod
    async def check_contenido_compliance(
        db: AsyncSession,
        org_id: int,
    ) -> list[AlertaCompliance]:
        """Check AI-generated content for compliance violations.

        Rules:
        - PlanIA records without modelo_ia populated
        - Content published during veda electoral period
        """
        alertas: list[AlertaCompliance] = []

        # 1. AI-generated content without modelo_ia label
        planes_sin_etiqueta_result = await db.execute(
            select(PlanIA)
            .join(
                PlanIA.dirigente,
            )
            .where(
                PlanIA.modelo_ia.is_(None) | (PlanIA.modelo_ia == ""),
            )
        )
        for plan in planes_sin_etiqueta_result.scalars().all():
            alertas.append(
                AlertaCompliance(
                    org_id=org_id,
                    tipo=TipoAlertaCompliance.CONTENIDO_SIN_ETIQUETA_IA,
                    severidad=SeveridadAlerta.CRITICA,
                    titulo="Contenido IA sin etiqueta de modelo",
                    descripcion=(
                        f"El plan IA #{plan.id} (tipo: {plan.tipo}) "
                        f"no tiene campo modelo_ia poblado. "
                        f"Todo contenido generado con IA debe identificar "
                        f"el modelo utilizado."
                    ),
                    referencia_tipo="contenido",
                    referencia_id=plan.id,
                )
            )

        # 2. Content published during veda electoral
        if (
            settings.VEDA_ELECTORAL_ACTIVE
            and settings.VEDA_ELECTORAL_INICIO
            and settings.VEDA_ELECTORAL_FIN
        ):
            try:
                veda_inicio = datetime.fromisoformat(settings.VEDA_ELECTORAL_INICIO)
                veda_fin = datetime.fromisoformat(settings.VEDA_ELECTORAL_FIN)
            except ValueError:
                # If dates are malformed, skip veda check rather than crash
                return alertas

            # Check social posts published during veda
            posts_en_veda_result = await db.execute(
                select(SocialPost)
                .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
                .where(
                    SocialPost.published_at >= veda_inicio,
                    SocialPost.published_at <= veda_fin,
                    SocialPost.is_political.is_(True),
                )
            )
            for post in posts_en_veda_result.scalars().all():
                alertas.append(
                    AlertaCompliance(
                        org_id=org_id,
                        tipo=TipoAlertaCompliance.VEDA_VIOLACION,
                        severidad=SeveridadAlerta.CRITICA,
                        titulo="Contenido politico publicado durante veda",
                        descripcion=(
                            f"El post #{post.id} (plataforma post ID: "
                            f"{post.platform_post_id}) fue publicado el "
                            f"{post.published_at.isoformat()} durante el periodo "
                            f"de veda electoral "
                            f"({settings.VEDA_ELECTORAL_INICIO} a "
                            f"{settings.VEDA_ELECTORAL_FIN})."
                        ),
                        referencia_tipo="post",
                        referencia_id=post.id,
                    )
                )

        return alertas

    # ── Compliance report ────────────────────────────────────

    @staticmethod
    async def generate_compliance_report(
        db: AsyncSession,
        org_id: int,
        periodo_inicio: date | None = None,
        periodo_fin: date | None = None,
    ) -> ComplianceReportResponse:
        """Generate a compliance report with spending by SIF category,
        active alerts summary, and bot detection stats."""
        tope = settings.TOPE_CAMPANA_MXN

        # Build date filter for gastos
        gasto_filters = [GastoElectoral.org_id == org_id]
        if periodo_inicio is not None:
            gasto_filters.append(GastoElectoral.fecha_gasto >= periodo_inicio)
        if periodo_fin is not None:
            gasto_filters.append(GastoElectoral.fecha_gasto <= periodo_fin)

        # Gastos by category (SIF format)
        cat_result = await db.execute(
            select(
                GastoElectoral.categoria,
                func.coalesce(func.sum(GastoElectoral.monto), 0.0),
            )
            .where(and_(*gasto_filters))
            .group_by(GastoElectoral.categoria)
        )
        gastos_por_categoria: dict[str, float] = {}
        total_gastos = 0.0
        for cat, amount in cat_result.all():
            amount_float = float(amount)
            gastos_por_categoria[cat.value] = round(amount_float, 2)
            total_gastos += amount_float

        # Fill missing categories with 0
        for cat in CategoriaGastoINE:
            if cat.value not in gastos_por_categoria:
                gastos_por_categoria[cat.value] = 0.0

        porcentaje_tope = round((total_gastos / tope) * 100, 2) if tope > 0 else 0.0

        # Active alerts by severity
        alertas_result = await db.execute(
            select(
                AlertaCompliance.severidad,
                func.count(AlertaCompliance.id),
            )
            .where(
                AlertaCompliance.org_id == org_id,
                AlertaCompliance.resuelta.is_(False),
            )
            .group_by(AlertaCompliance.severidad)
        )
        alertas_activas: dict[str, int] = {}
        for sev, count in alertas_result.all():
            alertas_activas[sev.value] = int(count)
        for sev in SeveridadAlerta:
            if sev.value not in alertas_activas:
                alertas_activas[sev.value] = 0

        # Bot detection count
        bot_result = await db.execute(
            select(func.count(AlertaCompliance.id)).where(
                AlertaCompliance.org_id == org_id,
                AlertaCompliance.tipo == TipoAlertaCompliance.BOT_DETECTADO,
                AlertaCompliance.resuelta.is_(False),
            )
        )
        bot_posts_detectados = bot_result.scalar_one()

        return ComplianceReportResponse(
            gastos_por_categoria=gastos_por_categoria,
            total_gastos=round(total_gastos, 2),
            tope_campana=tope,
            porcentaje_tope=porcentaje_tope,
            alertas_activas=alertas_activas,
            bot_posts_detectados=int(bot_posts_detectados),
        )

    # ── Full audit ───────────────────────────────────────────

    @staticmethod
    async def run_full_audit(
        db: AsyncSession,
        org_id: int,
    ) -> list[AlertaCompliance]:
        """Run all compliance checks and persist alert records.

        Returns the list of newly created AlertaCompliance records.
        """
        all_alertas: list[AlertaCompliance] = []

        # Run each check
        gastos_alertas = await BlindajeService.check_gastos_compliance(db, org_id)
        contenido_alertas = await BlindajeService.check_contenido_compliance(db, org_id)

        all_alertas.extend(gastos_alertas)
        all_alertas.extend(contenido_alertas)

        # Persist all new alerts
        for alerta in all_alertas:
            db.add(alerta)

        if all_alertas:
            await db.flush()
            # Refresh all to get generated IDs
            for alerta in all_alertas:
                await db.refresh(alerta)

        return all_alertas
