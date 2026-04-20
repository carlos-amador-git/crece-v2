"""B15 — Rage Click Flag (MASTER §3.2 #15).

Detecta posts donde el engagement viene de indignación (no de conversión).
Heurística combinada:

    1. Alta carga de keywords hostiles en comments (RAGE_KEYWORDS)
    2. Sentiment agregado negativo de comments (nlp_polaridad < -0.3 o
       nlp_tono='hostil'/'indignacion')
    3. Velocidad de engagement spike: posts con ER actual > baseline × 3

Un post es "rage" cuando >=2 de 3 señales disparan.

Returns:
    {
        "rage_clicks_detectados": 12,
        "pct_engagement_rage": 18.5,
        "top_posts_rage": [
            {post_id, score_rage, n_comments_hostiles, er, signals: [...]},
            ...
        ],
        "n_posts_analizados": 80,
    }

Insufficient:
    - 0 posts en ventana o 0 comments
"""
from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social import SocialPost, SocialProfile
from app.services.diagnostico_tier2._common import (
    RAGE_KEYWORDS,
    build_dirigente_not_found,
    build_insufficient,
    build_ok,
    load_comments_for_dirigente,
    load_dirigente_scoped,
)

BLOQUE = "B15"
VENTANA_DIAS = 90
UMBRAL_HOSTIL_PCT = 0.25  # >=25% de comments con keyword hostil
UMBRAL_SENTIMENT_NEG = -0.3
ER_SPIKE_MULT = 3.0


def _comment_es_hostil(content: str | None) -> bool:
    if not content:
        return False
    t = content.lower()
    return any(k in t for k in RAGE_KEYWORDS)


async def compute(
    db: AsyncSession,
    dirigente_id: int,
    org_id: int | None = None,
) -> dict:
    dirigente = await load_dirigente_scoped(db, dirigente_id, org_id)
    if dirigente is None:
        return build_dirigente_not_found(BLOQUE, dirigente_id)

    profiles_res = await db.execute(
        select(SocialProfile).where(SocialProfile.dirigente_id == dirigente_id)
    )
    profiles = list(profiles_res.scalars().all())
    if not profiles:
        return build_insufficient(BLOQUE, missing=["social_profiles=0"])

    since = datetime.now(UTC) - timedelta(days=VENTANA_DIAS)
    posts_res = await db.execute(
        select(SocialPost).where(
            SocialPost.profile_id.in_([p.id for p in profiles]),
            SocialPost.published_at >= since,
        )
    )
    posts = list(posts_res.scalars().all())
    if not posts:
        return build_insufficient(BLOQUE, missing=["0 posts en ventana"])

    comments = await load_comments_for_dirigente(db, dirigente_id, VENTANA_DIAS)
    if not comments:
        return build_insufficient(BLOQUE, missing=["0 comments en ventana"])

    comments_por_post: dict[int, list[dict]] = defaultdict(list)
    for c in comments:
        comments_por_post[c["post_id"]].append(c)

    # Baseline ER para spike detection
    ers = [p.engagement_rate for p in posts if p.engagement_rate and p.engagement_rate > 0]
    er_mediano = sorted(ers)[len(ers) // 2] if ers else 0.0
    er_umbral_spike = er_mediano * ER_SPIKE_MULT if er_mediano > 0 else 0.0

    rage_posts: list[dict] = []
    for post in posts:
        pc = comments_por_post.get(post.id, [])
        if not pc:
            continue
        n_hostiles = sum(1 for c in pc if _comment_es_hostil(c.get("content")))
        pct_hostil = n_hostiles / len(pc)

        # Sentiment: preferir nlp_polaridad, fallback nlp_tono
        polaridades = [
            c["nlp_polaridad"]
            for c in pc
            if c.get("nlp_polaridad") is not None
        ]
        pol_avg = (
            sum(polaridades) / len(polaridades) if polaridades else None
        )
        tonos_hostiles = sum(
            1 for c in pc if (c.get("nlp_tono") or "").lower() in {"hostil", "indignacion", "furia"}
        )

        signals: list[str] = []
        if pct_hostil >= UMBRAL_HOSTIL_PCT:
            signals.append(f"keywords_hostiles:{pct_hostil:.0%}")
        if pol_avg is not None and pol_avg <= UMBRAL_SENTIMENT_NEG:
            signals.append(f"sentiment_neg:{pol_avg:.2f}")
        elif tonos_hostiles / len(pc) >= 0.3:
            signals.append(f"tonos_hostiles:{tonos_hostiles}/{len(pc)}")
        if er_umbral_spike > 0 and (post.engagement_rate or 0) > er_umbral_spike:
            signals.append(f"er_spike:{post.engagement_rate:.3f}")

        score_rage = round(len(signals) / 3.0, 2)
        if len(signals) >= 2:
            rage_posts.append(
                {
                    "post_id": post.id,
                    "score_rage": score_rage,
                    "n_comments_hostiles": n_hostiles,
                    "n_comments_total": len(pc),
                    "pct_hostil": round(pct_hostil * 100, 1),
                    "er": round(post.engagement_rate or 0, 4),
                    "signals": signals,
                    "published_at": post.published_at.isoformat() if post.published_at else None,
                }
            )

    rage_posts.sort(key=lambda x: x["score_rage"], reverse=True)
    pct_engagement_rage = round(
        (len(rage_posts) / len(posts)) * 100.0, 2
    ) if posts else 0.0

    return build_ok(
        BLOQUE,
        {
            "rage_clicks_detectados": len(rage_posts),
            "pct_engagement_rage": pct_engagement_rage,
            "top_posts_rage": rage_posts[:10],
            "n_posts_analizados": len(posts),
            "er_mediano_baseline": round(er_mediano, 4),
            "er_umbral_spike": round(er_umbral_spike, 4),
            "umbrales": {
                "hostil_pct": UMBRAL_HOSTIL_PCT,
                "sentiment_neg": UMBRAL_SENTIMENT_NEG,
                "er_spike_mult": ER_SPIKE_MULT,
            },
            "ventana_dias": VENTANA_DIAS,
        },
    )
