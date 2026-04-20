"""B14 — Topic Drift Detector (MASTER §3.2 #14).

Compara los topics que el POST discute (caption + topics_extracted) contra
los topics de los COMMENTS (nlp_target + content). Un drift alto significa
que el post habla de X pero los comments discuten Y (malentendido,
captura de la conversación por trolls, o viralidad por razón equivocada).

Metodología:
    - Token set del caption = bigrams de palabras (>=3 chars, sin stopwords)
    - Token set de comments agregados = bigrams de los comments bajo el post
    - Jaccard similarity. drift_score = 1 - jaccard (0=alineado, 1=total drift).

Returns:
    {
        "posts_con_drift": [
            {"post_id", "drift_score", "caption_tokens_top5", "comments_tokens_top5", "n_comments"},
            ...
        ],
        "drift_score_promedio": 0.42,
        "n_posts_analizados": 45,
        "posts_drift_alto": 7,  # score > 0.75
    }

Insufficient:
    - 0 posts con al menos 3 comments (no se puede medir drift)
"""
from __future__ import annotations

import re
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
UMBRAL_DRIFT_ALTO = 0.75

STOPWORDS_ES = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del",
    "al", "a", "en", "y", "o", "u", "que", "qué", "por", "para", "con",
    "sin", "sobre", "como", "cómo", "pero", "si", "sí", "no", "es", "son",
    "era", "ser", "estar", "este", "esta", "esto", "ese", "esa", "eso",
    "me", "te", "se", "le", "les", "mi", "tu", "su", "yo", "nos", "nosotros",
    "más", "mas", "muy", "ya", "hay", "fue", "está", "están", "ha", "han",
    "he", "su", "sus", "lo", "las", "https", "http", "www", "rt", "ft",
    "jajaja", "jaja", "jaj", "jeje", "hola", "gracias",
}


def _tokenize(text: str | None) -> list[str]:
    if not text:
        return []
    text = re.sub(r"http\S+", " ", text.lower())
    text = re.sub(r"[^\wáéíóúñü ]", " ", text)
    tokens = [t for t in text.split() if len(t) >= 3 and t not in STOPWORDS_ES]
    return tokens


def _bigrams(tokens: list[str]) -> set[str]:
    if len(tokens) < 2:
        return set(tokens)
    return {f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)} | set(tokens)


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


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
            SocialPost.content.is_not(None),
        )
    )
    posts = list(posts_res.scalars().all())
    if not posts:
        return build_insufficient(BLOQUE, missing=["0 posts con content en ventana"])

    comments = await load_comments_for_dirigente(db, dirigente_id, VENTANA_DIAS)
    if not comments:
        return build_insufficient(BLOQUE, missing=["0 comments en ventana"])

    comments_por_post: dict[int, list[dict]] = defaultdict(list)
    for c in comments:
        comments_por_post[c["post_id"]].append(c)

    resultados: list[dict] = []
    for post in posts:
        post_comments = comments_por_post.get(post.id, [])
        if len(post_comments) < MIN_COMMENTS_POR_POST:
            continue
        caption_tokens = _tokenize(post.content)
        caption_bg = _bigrams(caption_tokens)
        comments_text = " ".join(c.get("content") or "" for c in post_comments)
        comments_tokens = _tokenize(comments_text)
        comments_bg = _bigrams(comments_tokens)
        sim = _jaccard(caption_bg, comments_bg)
        drift = round(1.0 - sim, 3)

        # top 5 tokens (no bigrams) para UI
        caption_top = [t for t, _ in Counter(caption_tokens).most_common(5)]
        comments_top = [t for t, _ in Counter(comments_tokens).most_common(5)]

        resultados.append(
            {
                "post_id": post.id,
                "drift_score": drift,
                "caption_tokens_top5": caption_top,
                "comments_tokens_top5": comments_top,
                "n_comments": len(post_comments),
                "published_at": post.published_at.isoformat() if post.published_at else None,
            }
        )

    if not resultados:
        return build_insufficient(
            BLOQUE,
            missing=[
                f"0 posts con ≥{MIN_COMMENTS_POR_POST} comments en ventana "
                "— necesario para medir drift estadísticamente",
            ],
        )

    resultados.sort(key=lambda x: x["drift_score"], reverse=True)
    drift_avg = round(sum(r["drift_score"] for r in resultados) / len(resultados), 3)
    drift_alto = sum(1 for r in resultados if r["drift_score"] >= UMBRAL_DRIFT_ALTO)

    return build_ok(
        BLOQUE,
        {
            "posts_con_drift": resultados[:20],
            "drift_score_promedio": drift_avg,
            "n_posts_analizados": len(resultados),
            "posts_drift_alto": drift_alto,
            "umbral_drift_alto": UMBRAL_DRIFT_ALTO,
            "ventana_dias": VENTANA_DIAS,
            "metodologia": "bigram_jaccard_v1",
        },
    )
