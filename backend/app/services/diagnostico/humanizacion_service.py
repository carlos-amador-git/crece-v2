"""B10 — Humanización Score (0-100).

MASTER §3.1 #10.

Heurística léxica sobre ``social_posts.content`` (últimos 90d) con 4 factores:

    1. primera_persona_pct   — uso de "yo/nosotros/mi/nuestro" en el corpus
    2. emojis_pct             — fracción de posts con al menos 1 emoji
    3. keywords_personales_pct — "familia/hijos/gracias/abrazo/vecino/..." etc.
    4. institucional_pct      — "gobierno/institucional/comunicado/oficial/..."
                                (factor negativo)

Score final:
    score = 100 * (0.30*p1 + 0.20*p2 + 0.30*p3 - 0.20*p4)
    clamp [0, 100]

Returns:
    {
        "status": "ok",
        "data": {
            "score_0_100": 62.5,
            "factores": {"primera_persona_pct": 45, "emojis_pct": 30, ...},
            "interpretacion": "Humanizado" | "Equilibrado" | "Institucional",
            "n_posts": 50
        }
    }

Insufficient:
    - 0 posts con content en 90d
"""
from __future__ import annotations

import re
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

BLOQUE = "B10"
VENTANA_DIAS = 90

PRIMERA_PERSONA_RX = re.compile(
    r"\b(yo|mi|m[ií]a|m[ií]o|conmigo|nosotr[oa]s|nuestr[oa]s?|nuestra|nuestros|nuestras)\b",
    re.IGNORECASE,
)
# Unicode emoji range basic + extended
EMOJI_RX = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U0001F700-\U0001F77F"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\u2600-\u27BF"
    "]+",
    flags=re.UNICODE,
)
KEYWORDS_PERSONALES = [
    "familia", "hijos", "hija", "hijo", "esposa", "esposo",
    "gracias", "abrazo", "vecin", "barrio", "colonia",
    "madre", "padre", "mamá", "papá", "mama", "papa",
    "amigos", "personal", "comunidad",
]
KEYWORDS_INSTITUCIONALES = [
    "gobierno", "institucion", "institucional", "comunicado",
    "oficial", "autoridad", "secretar", "subsecretar",
    "dependencia", "oficio", "acuerdo", "decreto", "dictamen",
    "reglament", "normativ",
]


def _count_matches(text: str, keywords: list[str]) -> int:
    text_lower = text.lower()
    return sum(1 for k in keywords if k in text_lower)


def _interpretar(score: float) -> str:
    if score >= 60:
        return "Humanizado"
    if score >= 35:
        return "Equilibrado"
    return "Institucional"


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

    since = datetime.now(UTC) - timedelta(days=VENTANA_DIAS)
    posts_result = await db.execute(
        select(SocialPost).where(
            SocialPost.profile_id.in_([p.id for p in profiles]),
            SocialPost.published_at >= since,
            SocialPost.content.is_not(None),
        )
    )
    posts = list(posts_result.scalars().all())
    posts = [p for p in posts if p.content and p.content.strip()]
    if not posts:
        return build_insufficient(BLOQUE, missing=["0 posts con content en 90d"])

    n = len(posts)
    n_primera = sum(1 for p in posts if PRIMERA_PERSONA_RX.search(p.content or ""))
    n_emoji = sum(1 for p in posts if EMOJI_RX.search(p.content or ""))
    n_personal = sum(1 for p in posts if _count_matches(p.content or "", KEYWORDS_PERSONALES) > 0)
    n_institucional = sum(
        1 for p in posts if _count_matches(p.content or "", KEYWORDS_INSTITUCIONALES) > 0
    )

    p1 = n_primera / n
    p2 = n_emoji / n
    p3 = n_personal / n
    p4 = n_institucional / n

    raw = 100.0 * (0.30 * p1 + 0.20 * p2 + 0.30 * p3 - 0.20 * p4)
    score = max(0.0, min(raw, 100.0))

    return build_ok(
        BLOQUE,
        {
            "score_0_100": round(score, 2),
            "factores": {
                "primera_persona_pct": round(p1 * 100, 2),
                "emojis_pct": round(p2 * 100, 2),
                "keywords_personales_pct": round(p3 * 100, 2),
                "institucional_pct": round(p4 * 100, 2),
            },
            "interpretacion": _interpretar(score),
            "n_posts": n,
            "ventana_dias": VENTANA_DIAS,
            "pesos_formula": {"p1": 0.30, "p2": 0.20, "p3": 0.30, "p4_negativo": -0.20},
        },
    )
