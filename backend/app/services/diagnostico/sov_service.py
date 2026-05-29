"""B08 — Share of Voice (SoV) por tema clave.

MASTER §3.1 #08.

Calcula % de menciones del dirigente vs competidores (proxies D-22) en topics
extraídos por Sprint S1 T5 (topic extractor Gemma 3:12b sobre ``social_posts.
topics_extracted``).

Para cada topic del corpus:
    sov_propio = n_posts_propio_mencionando_topic / total_posts_corpus_mencionando_topic

Returns:
    {
        "status": "ok",
        "data": {
            "self_pct_global": 35.2,        # % menciones totales en topics cubiertos
            "topics_cubiertos": [
                {
                    "topic": "seguridad",
                    "self_n_posts": 8,
                    "self_pct": 32.0,
                    "rivales": [{"dirigente_id": 2, "n_posts": 5, "pct": 20.0}, ...],
                    "total_posts": 25
                }
            ],
            "n_topics_totales": 7,
            "gap_alert": ["seguridad: SoV propio 12% <20% umbral"]
        }
    }

Insufficient:
    - 0 posts propios con ``topics_extracted`` (Sprint S1 T5 pendiente)
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social import SocialPost, SocialProfile
from app.services.diagnostico._common import (
    build_dirigente_not_found,
    build_insufficient,
    build_ok,
    load_dirigente_scoped,
)
from app.services.diagnostico.benchmark_service import PROXIES_S2_DESARROLLO

BLOQUE = "B08"
VENTANA_DIAS = 28
UMBRAL_GAP_SOV_PCT = 20.0


def _extract_topics(raw: dict | None) -> list[str]:
    """Topic extractor Sprint S1 T5 formato: {"topics": ["seguridad", ...]} o lista plana."""
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(t).lower() for t in raw if t]
    if isinstance(raw, dict):
        for key in ("topics", "topic", "categorias"):
            val = raw.get(key)
            if isinstance(val, list):
                return [str(t).lower() for t in val if t]
            if isinstance(val, str):
                return [val.lower()]
    return []


async def _topics_por_dirigente(
    db: AsyncSession, dirigente_id: int, since: datetime
) -> dict[str, int]:
    """Count posts por topic para un dirigente."""
    profiles_result = await db.execute(
        select(SocialProfile.id).where(SocialProfile.dirigente_id == dirigente_id)
    )
    profile_ids = [row[0] for row in profiles_result.all()]
    if not profile_ids:
        return {}
    posts_result = await db.execute(
        select(SocialPost).where(
            SocialPost.profile_id.in_(profile_ids),
            SocialPost.published_at >= since,
            SocialPost.topics_extracted.is_not(None),
        )
    )
    counts: dict[str, int] = {}
    for post in posts_result.scalars().all():
        for topic in _extract_topics(post.topics_extracted):
            counts[topic] = counts.get(topic, 0) + 1
    return counts


async def compute(
    db: AsyncSession,
    dirigente_id: int,
    org_id: int | None = None,
    topics: list[str] | None = None,
) -> dict:
    dirigente = await load_dirigente_scoped(db, dirigente_id, org_id)
    if dirigente is None:
        return build_dirigente_not_found(BLOQUE, dirigente_id)

    since = datetime.now(UTC) - timedelta(days=VENTANA_DIAS)
    self_counts = await _topics_por_dirigente(db, dirigente_id, since)
    if not self_counts:
        return build_insufficient(
            BLOQUE,
            missing=[
                "0 posts propios con topics_extracted en 28d",
                "(Sprint S1 T5 topic extractor no ha corrido sobre este dirigente)",
            ],
        )

    # Rivales: competidor_directo_ids o proxies S2
    rivales_ids = list(dirigente.competidor_directo_ids or [])
    if not rivales_ids:
        rivales_ids = PROXIES_S2_DESARROLLO.get(dirigente_id, [])

    rivales_counts: dict[int, dict[str, int]] = {}
    rivales_nombres: dict[int, str] = {}
    for rid in rivales_ids:
        rd = await load_dirigente_scoped(db, rid, org_id)
        if rd is None:
            continue
        rivales_nombres[rid] = rd.full_name
        rivales_counts[rid] = await _topics_por_dirigente(db, rid, since)

    # Set de topics a analizar (filtrado si ``topics`` arg)
    all_topics = set(self_counts.keys())
    for rc in rivales_counts.values():
        all_topics.update(rc.keys())
    if topics:
        all_topics = {t.lower() for t in topics if t.lower() in all_topics}

    topics_cubiertos: list[dict] = []
    total_menciones_global = 0
    total_menciones_propio = 0
    gap_alerts: list[str] = []
    for topic in sorted(all_topics):
        self_n = self_counts.get(topic, 0)
        rivales_breakdown = []
        total = self_n
        for rid, rc in rivales_counts.items():
            n = rc.get(topic, 0)
            total += n
            rivales_breakdown.append({
                "dirigente_id": rid,
                "full_name": rivales_nombres.get(rid),
                "n_posts": n,
            })
        if total == 0:
            continue
        self_pct = round(self_n / total * 100.0, 2)
        for r in rivales_breakdown:
            r["pct"] = round(r["n_posts"] / total * 100.0, 2)
        topics_cubiertos.append(
            {
                "topic": topic,
                "self_n_posts": self_n,
                "self_pct": self_pct,
                "rivales": rivales_breakdown,
                "total_posts": total,
            }
        )
        total_menciones_global += total
        total_menciones_propio += self_n
        if self_pct < UMBRAL_GAP_SOV_PCT:
            gap_alerts.append(f"{topic}: SoV propio {self_pct}% <{UMBRAL_GAP_SOV_PCT}% umbral")

    self_pct_global = round(
        total_menciones_propio / total_menciones_global * 100.0, 2
    ) if total_menciones_global > 0 else 0.0

    return build_ok(
        BLOQUE,
        {
            "self_pct_global": self_pct_global,
            "topics_cubiertos": topics_cubiertos,
            "n_topics_totales": len(topics_cubiertos),
            "gap_alert": gap_alerts,
            "ventana_dias": VENTANA_DIAS,
            "origen_competidores": "dirigente.competidor_directo_ids"
            if dirigente.competidor_directo_ids else "proxies_s2" if rivales_ids else "ninguno",
        },
    )
