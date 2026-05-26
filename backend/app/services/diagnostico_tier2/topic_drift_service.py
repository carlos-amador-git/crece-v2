"""B14 — Composición de la conversación de la audiencia (MASTER §3.2 #14).

Mide **a qué responde** la audiencia en los comments de cada post, usando la
señal NLP ya disponible (`social_comments.nlp_target`, 98% poblado) y los
`social_posts.topics_extracted` (temas del post):

    - "tema"    → el comment habla del tema del post (nlp_target=tema_especifico)
    - "persona" → reacciona al dirigente (nlp_target=dirigente) · engagement
                  genérico sano (felicidades, bonita, emojis)
    - "otro"    → se desvía a gobierno/oposición/otro asunto

Reemplaza el drift léxico bigram-Jaccard v1, que estaba SATURADO: daba ~1.0 a
casi todo porque los elogios genéricos no repiten las palabras del caption.
0.966 de desvío "promedio" no significaba audiencia desconectada — significaba
"los comentarios son reacciones cortas", que es lo normal.

Returns:
    {
        "composicion": {"persona": 55.7, "tema": 28.0, "otro": 16.3},  # % sobre comments clasificados
        "posts": [  # 1 por publicación → alimenta el heatmap
            {"post_id", "n_comments", "dominante", "pct_tema", "pct_persona",
             "pct_otro", "published_at"},
            ...
        ],
        "temas_top": [{"tema": "turismo oaxaca", "n_comments": 42}, ...],
        "n_posts_analizados": 45,
        "n_comments_analizados": 1200,
    }

Insufficient:
    - 0 posts con ≥3 comments clasificados (no se puede medir composición)
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social import SocialPost
from app.services.diagnostico_tier2._common import (
    build_dirigente_not_found,
    build_insufficient,
    build_ok,
    load_comments_for_dirigente,
    load_dirigente_scoped,
    load_profile_ids,
)

BLOQUE = "B14"
VENTANA_DIAS = 90
MIN_COMMENTS_POR_POST = 3

# nlp_target → bucket de composición
_TARGET_TEMA = "tema_especifico"
_TARGET_PERSONA = "dirigente"
# topics ruido que no nombran un tema real
_TOPICS_RUIDO = {"otro", "institucional", "ninguno", "general", "sin_tema_claro"}


def _extract_topics(raw: object) -> list[str]:
    """topics_extracted llega como {"topics": [...]} o lista directa."""
    if not raw:
        return []
    if isinstance(raw, dict):
        topics = raw.get("topics", [])
    elif isinstance(raw, list):
        topics = raw
    else:
        return []
    out: list[str] = []
    for t in topics:
        s = str(t).strip().lower()
        if s and s not in _TOPICS_RUIDO:
            out.append(s)
    return out


async def compute(
    db: AsyncSession,
    dirigente_id: int,
    org_id: int | None = None,
) -> dict:
    dirigente = await load_dirigente_scoped(db, dirigente_id, org_id)
    if dirigente is None:
        return build_dirigente_not_found(BLOQUE, dirigente_id)

    profile_ids = await load_profile_ids(db, dirigente_id)
    if not profile_ids:
        return build_insufficient(BLOQUE, missing=["social_profiles=0"])

    since = datetime.now(UTC) - timedelta(days=VENTANA_DIAS)
    posts_res = await db.execute(
        select(SocialPost).where(
            SocialPost.profile_id.in_(profile_ids),
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

    agg = Counter()  # persona / tema / otro (agregado)
    tema_counter: Counter[str] = Counter()  # tema → n comments temáticos
    posts_out: list[dict] = []

    for post in posts:
        post_comments = comments_por_post.get(post.id, [])
        if len(post_comments) < MIN_COMMENTS_POR_POST:
            continue
        post_topics = _extract_topics(post.topics_extracted)
        pb = Counter()  # bucket por-post
        for c in post_comments:
            tgt = (c.get("nlp_target") or "").strip().lower()
            if not tgt:
                continue  # sin clasificar → no cuenta
            if tgt == _TARGET_PERSONA:
                pb["persona"] += 1
            elif tgt == _TARGET_TEMA:
                pb["tema"] += 1
                for t in post_topics:
                    tema_counter[t] += 1
            else:
                pb["otro"] += 1

        total_pb = pb["persona"] + pb["tema"] + pb["otro"]
        if total_pb == 0:
            continue

        agg.update(pb)
        dominante = pb.most_common(1)[0][0]
        posts_out.append(
            {
                "post_id": post.id,
                "n_comments": total_pb,
                "dominante": dominante,
                "pct_tema": round(100.0 * pb["tema"] / total_pb, 1),
                "pct_persona": round(100.0 * pb["persona"] / total_pb, 1),
                "pct_otro": round(100.0 * pb["otro"] / total_pb, 1),
                "published_at": (
                    post.published_at.isoformat() if post.published_at else None
                ),
            }
        )

    n_clasificados = agg["persona"] + agg["tema"] + agg["otro"]
    if not posts_out or n_clasificados == 0:
        return build_insufficient(
            BLOQUE,
            missing=[
                f"0 posts con ≥{MIN_COMMENTS_POR_POST} comments clasificados "
                "(nlp_target) en ventana — necesario para medir composición",
            ],
        )

    # Más reciente primero (el heatmap rotula "más reciente →")
    posts_out.sort(key=lambda p: p["published_at"] or "", reverse=True)

    composicion = {
        "persona": round(100.0 * agg["persona"] / n_clasificados, 1),
        "tema": round(100.0 * agg["tema"] / n_clasificados, 1),
        "otro": round(100.0 * agg["otro"] / n_clasificados, 1),
    }
    temas_top = [
        {"tema": t, "n_comments": n} for t, n in tema_counter.most_common(8)
    ]

    return build_ok(
        BLOQUE,
        {
            "composicion": composicion,
            "posts": posts_out[:60],
            "temas_top": temas_top,
            "n_posts_analizados": len(posts_out),
            "n_comments_analizados": n_clasificados,
            "ventana_dias": VENTANA_DIAS,
            "metodologia": "nlp_target_composition_v2",
        },
    )
