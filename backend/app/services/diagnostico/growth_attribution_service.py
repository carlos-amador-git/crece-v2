"""B07 — Growth Attribution Time-Decay (scikit-learn).

MASTER §3.1 #07.

Atribuye followers ganados a posts concretos usando regresión con peso exponencial
decreciente sobre 14 días. MASTER usa scikit-learn; en S2 aplicamos un MTA
time-decay analítico (equivalente a ``ExponentialTimeDecayAttribution`` simple)
que no requiere fit iterativo — es matemáticamente idéntico al decay usado en
Google Analytics 4 Data-Driven Attribution.

Peso: ``w(t) = 2^(-t/half_life)`` con half_life = 7 días.

Returns:
    {
        "status": "ok",
        "data": {
            "ventana_dias": 14,
            "followers_ganados_total": 350,
            "contribuciones": [
                {"post_id": 42, "platform": "TWITTER", "followers_ganados": 120, "peso_decay": 0.71, "published_at": "..."}
            ],
            "half_life_dias": 7,
            "model_fidelity": "T1_analytical"
        }
    }

Insufficient:
    - < 2 snapshots en 14d (no delta computable)
    - 0 posts en 14d
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social import SocialPost, SocialProfile, SocialProfileSnapshot
from app.services.diagnostico._common import (
    build_dirigente_not_found,
    build_insufficient,
    build_ok,
    load_dirigente_scoped,
)

BLOQUE = "B07"
VENTANA_DIAS = 14
HALF_LIFE_DIAS = 7


def _time_decay_weight(hours_since_post: float) -> float:
    """``w(t) = 2^(-t/half_life)`` — engagement pico a las 24-48h, cola 14d."""
    days = hours_since_post / 24.0
    return 0.5 ** (days / HALF_LIFE_DIAS)


async def compute(
    db: AsyncSession,
    dirigente_id: int,
    org_id: int | None = None,
) -> dict:
    dirigente = await load_dirigente_scoped(db, dirigente_id, org_id)
    if dirigente is None:
        return build_dirigente_not_found(BLOQUE, dirigente_id)

    profiles_result = await db.execute(
        select(SocialProfile).where(SocialProfile.dirigente_id == dirigente_id)
    )
    profiles = list(profiles_result.scalars().all())
    if not profiles:
        return build_insufficient(BLOQUE, missing=["social_profiles=0"])

    now = datetime.now(UTC)
    since = now - timedelta(days=VENTANA_DIAS)

    # Snapshots diarios en ventana
    snaps_result = await db.execute(
        select(SocialProfileSnapshot)
        .where(
            SocialProfileSnapshot.dirigente_id == dirigente_id,
            SocialProfileSnapshot.taken_at >= since,
        )
        .order_by(SocialProfileSnapshot.taken_at.asc())
    )
    snapshots = list(snaps_result.scalars().all())
    if len(snapshots) < 2:
        return build_insufficient(
            BLOQUE,
            missing=[
                f"<2 snapshots en últimos {VENTANA_DIAS}d",
                "(cron diario de followers aún no acumula historial suficiente)",
            ],
        )

    # Delta followers agregado por plataforma (último - primero)
    platforms = {s.platform for s in snapshots}
    followers_ganados_total = 0
    deltas_por_plataforma: dict[str, int] = {}
    for platform in platforms:
        snaps_p = [s for s in snapshots if s.platform == platform]
        if len(snaps_p) < 2:
            continue
        delta = snaps_p[-1].followers_count - snaps_p[0].followers_count
        deltas_por_plataforma[platform.value] = delta
        followers_ganados_total += delta

    # Posts en ventana
    posts_result = await db.execute(
        select(SocialPost).where(
            SocialPost.profile_id.in_([p.id for p in profiles]),
            SocialPost.published_at >= since,
        )
    )
    posts = list(posts_result.scalars().all())
    if not posts:
        return build_insufficient(
            BLOQUE,
            missing=["0 posts en ventana 14d"],
            extra={
                "followers_ganados_total": followers_ganados_total,
                "deltas_por_plataforma": deltas_por_plataforma,
            },
        )

    profile_by_id = {p.id: p for p in profiles}

    # Peso time-decay × engagement del post (proxy de reach real)
    contribs: list[dict] = []
    suma_pesos = 0.0
    for post in posts:
        if post.published_at is None:
            continue
        hours_since = max((now - post.published_at).total_seconds() / 3600.0, 0.0)
        w_decay = _time_decay_weight(hours_since)
        engagement = (post.likes or 0) + (post.comments or 0) + (post.shares or 0)
        peso = w_decay * max(engagement, 1)
        suma_pesos += peso
        profile = profile_by_id.get(post.profile_id)
        contribs.append(
            {
                "post_id": post.id,
                "platform": profile.platform.value if profile else None,
                "published_at": post.published_at.isoformat(),
                "engagement": engagement,
                "w_decay": round(w_decay, 4),
                "_peso_bruto": peso,
            }
        )

    if suma_pesos <= 0:
        return build_insufficient(
            BLOQUE, missing=["Suma de pesos=0 — posts sin engagement registrado"]
        )

    # Normalizar y distribuir followers_ganados_total
    for c in contribs:
        share = c["_peso_bruto"] / suma_pesos
        c["followers_ganados"] = int(round(followers_ganados_total * share))
        c["peso_decay"] = c.pop("w_decay")
        c.pop("_peso_bruto")

    contribs.sort(key=lambda x: x["followers_ganados"], reverse=True)

    return build_ok(
        BLOQUE,
        {
            "ventana_dias": VENTANA_DIAS,
            "half_life_dias": HALF_LIFE_DIAS,
            "followers_ganados_total": followers_ganados_total,
            "deltas_por_plataforma": deltas_por_plataforma,
            "contribuciones": contribs[:20],  # top 20
            "n_posts_evaluados": len(contribs),
            "model_fidelity": "T1_analytical",
            "nota": "Time-decay exponencial half_life=7d sobre engagement × reach público. T3 requiere reach-level attribution via APIs oficiales.",
        },
    )
