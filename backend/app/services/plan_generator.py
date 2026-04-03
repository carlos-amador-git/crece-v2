from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.benchmark import Competidor, CompetidorSocialProfile
from app.models.dirigente import Dirigente
from app.models.plan_ia import PlanIA, TipoPlan
from app.models.social import SentimentLabel, SocialPost, SocialProfile
from app.models.user import User

logger = logging.getLogger(__name__)


async def _gather_context(db: AsyncSession, dirigente: Dirigente) -> dict:
    """Collect real metrics to feed the AI prompt. Never invent data."""
    thirty_days_ago = datetime.now(UTC) - timedelta(days=30)

    # Social profiles summary
    profiles_result = await db.execute(
        select(SocialProfile).where(SocialProfile.dirigente_id == dirigente.id)
    )
    profiles = list(profiles_result.scalars().all())

    profiles_data = []
    for p in profiles:
        # Recent post stats
        stats_result = await db.execute(
            select(
                func.count(SocialPost.id),
                func.avg(SocialPost.engagement_rate),
                func.avg(SocialPost.sentiment_score),
            ).where(
                SocialPost.profile_id == p.id,
                SocialPost.published_at >= thirty_days_ago,
            )
        )
        row = stats_result.one()
        profiles_data.append({
            "platform": p.platform.value,
            "handle": p.handle,
            "followers": p.followers_count,
            "posts_30d": int(row[0]),
            "avg_engagement_30d": round(float(row[1]), 4) if row[1] else 0.0,
            "avg_sentiment_30d": round(float(row[2]), 4) if row[2] else None,
        })

    # Sentiment distribution
    sent_result = await db.execute(
        select(SocialPost.sentiment_label, func.count(SocialPost.id))
        .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
        .where(
            SocialProfile.dirigente_id == dirigente.id,
            SocialPost.published_at >= thirty_days_ago,
            SocialPost.sentiment_label.is_not(None),
        )
        .group_by(SocialPost.sentiment_label)
    )
    sentiment_dist = {row[0].value: int(row[1]) for row in sent_result.all()}

    # Top competitors
    comp_result = await db.execute(
        select(Competidor, func.sum(CompetidorSocialProfile.followers_count))
        .join(CompetidorSocialProfile)
        .where(Competidor.es_rival.is_(True))
        .group_by(Competidor.id)
        .order_by(func.sum(CompetidorSocialProfile.followers_count).desc())
        .limit(5)
    )
    competitors = [
        {
            "nombre": row[0].nombre,
            "partido": row[0].partido,
            "total_followers": int(row[1]) if row[1] else 0,
        }
        for row in comp_result.all()
    ]

    return {
        "dirigente": {
            "nombre": dirigente.full_name,
            "cargo": dirigente.cargo,
            "partido": dirigente.partido,
            "estado": dirigente.estado,
            "municipio": dirigente.municipio,
        },
        "social_profiles": profiles_data,
        "sentiment_30d": sentiment_dist,
        "top_competitors": competitors,
        "analysis_date": datetime.now(UTC).isoformat(),
    }


def _build_prompt(tipo: TipoPlan, context: dict, extra: str | None = None) -> str:
    """Build a structured prompt from real data for Claude."""
    context_json = json.dumps(context, indent=2, ensure_ascii=False, default=str)

    tipo_instructions = {
        TipoPlan.DIAGNOSTICO: (
            "Genera un DIAGNOSTICO COMPLETO de la presencia digital del dirigente. "
            "Analiza fortalezas, debilidades, oportunidades y amenazas. "
            "Incluye metricas especificas y comparativas."
        ),
        TipoPlan.CONSOLIDACION: (
            "Genera un PLAN DE CONSOLIDACION a 90 dias. "
            "Estructura en 3 fases mensuales con objetivos SMART, KPIs, "
            "acciones concretas por plataforma, y calendario de contenido."
        ),
        TipoPlan.CRISIS: (
            "Genera un PLAN DE MANEJO DE CRISIS digital. "
            "Incluye protocolos de respuesta rapida, escalamiento, "
            "narrativas alternativas, y plan de recuperacion reputacional."
        ),
        TipoPlan.CONTENIDO: (
            "Genera un PLAN DE CONTENIDO detallado para 30 dias. "
            "Incluye pilares tematicos, formatos por plataforma, "
            "horarios optimos de publicacion, y ejemplos de posts."
        ),
    }

    instruction = tipo_instructions[tipo]

    prompt = f"""Eres un estratega de comunicacion politica digital experto en el contexto
mexicano. Tu cliente es un dirigente del partido Movimiento Ciudadano (MC).

{instruction}

## DATOS REALES DEL DIRIGENTE (NO inventes datos adicionales):

{context_json}

## REGLAS:
1. Basa tu analisis EXCLUSIVAMENTE en los datos proporcionados.
2. Si faltan datos, indica que se necesitan y NO inventes sustitutos.
3. Responde en espanol.
4. Usa formato Markdown con secciones claras.
5. Se especifico: numeros, fechas, plataformas, metricas.
6. Considera el contexto politico mexicano actual.
"""

    if extra:
        prompt += f"\n## CONTEXTO ADICIONAL DEL USUARIO:\n{extra}\n"

    return prompt


async def generate_plan(
    db: AsyncSession,
    dirigente: Dirigente,
    tipo: TipoPlan,
    user: User,
    contexto_adicional: str | None = None,
) -> PlanIA:
    """Generate an AI plan using Claude and persist it."""
    import anthropic

    context = await _gather_context(db, dirigente)
    prompt = _build_prompt(tipo, context, contexto_adicional)

    client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)

    message = client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    contenido = message.content[0].text

    plan = PlanIA(
        dirigente_id=dirigente.id,
        tipo=tipo,
        contenido=contenido,
        modelo_ia=settings.CLAUDE_MODEL,
        prompt_usado=prompt,
        datos_entrada=context,
        generado_por_id=user.id,
    )
    db.add(plan)
    await db.flush()
    await db.refresh(plan)
    return plan


async def generate_plan_stream(
    db: AsyncSession,
    dirigente: Dirigente,
    tipo: TipoPlan,
    user: User,
    contexto_adicional: str | None = None,
) -> AsyncGenerator[str, None]:
    """Stream plan generation via SSE-compatible chunks."""
    import anthropic

    context = await _gather_context(db, dirigente)
    prompt = _build_prompt(tipo, context, contexto_adicional)

    client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)

    collected_text = ""

    with client.messages.stream(
        model=settings.CLAUDE_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            collected_text += text
            yield f"data: {json.dumps({'text': text})}\n\n"

    # Persist the completed plan
    plan = PlanIA(
        dirigente_id=dirigente.id,
        tipo=tipo,
        contenido=collected_text,
        modelo_ia=settings.CLAUDE_MODEL,
        prompt_usado=prompt,
        datos_entrada=context,
        generado_por_id=user.id,
    )
    db.add(plan)
    await db.flush()
    await db.refresh(plan)

    yield f"data: {json.dumps({'done': True, 'plan_id': plan.id})}\n\n"
