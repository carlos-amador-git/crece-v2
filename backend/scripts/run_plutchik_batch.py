"""Batch Plutchik-6 — Sprint S2 T3.

Carga posts de ``social_posts`` cuya fila en ``sentiment_analyses`` NO tiene
``emotions.plutchik_6`` poblado, los clasifica con Gemma 3:12b (prompt S0 T0.4
validado Kappa=0.810) y persiste la distribución 6-emociones en
``sentiment_analyses.emotions['plutchik_6']``.

Uso::

    python backend/scripts/run_plutchik_batch.py --limit 200
    python backend/scripts/run_plutchik_batch.py --limit 50 --ollama-url http://host.docker.internal:11434

Si el post no tiene ``sentiment_analyses`` aún, se crea una fila mínima con
``model_used='gemma3:12b-plutchik'`` y ``sentiment_score=0.0`` (neutral) para
poder persistir el ``emotions`` JSONB. Las columnas legacy de sentiment
(pysentimiento) quedan intactas y deben llenarse en un pipeline separado.

Principios MD:
- NO mockear. Si Ollama no responde, reporta blocker y exit code 2.
- Commit por item. Si se interrumpe, no se pierde progreso.
- Output JSON sample del primer post exitoso, progress cada 20.

Desbloquea: #05 Sentiment Plutchik + #04 Benchmark + #06 Crisis Spike + #08 SoV.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import and_, select, text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.database import async_session_factory  # noqa: E402
from app.models.social import (  # noqa: E402
    Platform,
    SentimentAnalysis,
    SentimentLabel,
    SocialPost,
    SocialProfile,
)
from app.services.sentiment_service import classify_plutchik_6  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("run_plutchik_batch")

MODEL_NAME = "gemma3:12b-plutchik"


async def _fetch_pending(
    session: AsyncSession,
    *,
    limit: int,
    platform: Platform | None,
) -> list[tuple[SocialPost, Platform, SentimentAnalysis | None]]:
    """Devuelve (post, platform, sentiment_analysis_or_None) listos para procesar.

    Selecciona posts cuya ``SentimentAnalysis`` más reciente NO tenga
    ``emotions->'plutchik_6'`` populado. Si el post no tiene sentiment_analyses,
    también entra en la cola y se crea una fila mínima.
    """
    # Una sola query: post + plataforma + sentiment_analysis existente (si hay).
    # Excluye posts cuyo sentiment_analysis YA tiene plutchik_6.
    plat_filter = ""
    params: dict[str, object] = {"limit": limit}
    if platform is not None:
        plat_filter = "AND sp2.platform = :platform"
        params["platform"] = platform.value

    sql = text(
        f"""
        SELECT post.id AS post_id,
               sp2.platform AS platform,
               sa.id AS sa_id
        FROM social_posts post
        JOIN social_profiles sp2 ON post.profile_id = sp2.id
        LEFT JOIN LATERAL (
            SELECT id, emotions FROM sentiment_analyses
            WHERE post_id = post.id
            ORDER BY analyzed_at DESC
            LIMIT 1
        ) sa ON TRUE
        WHERE post.content IS NOT NULL
          AND (sa.id IS NULL OR NOT (sa.emotions ? 'plutchik_6'))
          {plat_filter}
        ORDER BY post.id ASC
        LIMIT :limit
        """
    )
    res = await session.execute(sql, params)
    rows = res.all()

    if not rows:
        return []

    post_ids = [r.post_id for r in rows]
    sa_ids = [r.sa_id for r in rows if r.sa_id is not None]

    post_map = {
        p.id: p
        for p in (
            await session.execute(
                select(SocialPost).where(SocialPost.id.in_(post_ids))
            )
        )
        .scalars()
        .all()
    }
    sa_map: dict[int, SentimentAnalysis] = {}
    if sa_ids:
        sa_map = {
            sa.id: sa
            for sa in (
                await session.execute(
                    select(SentimentAnalysis).where(SentimentAnalysis.id.in_(sa_ids))
                )
            )
            .scalars()
            .all()
        }

    pending: list[tuple[SocialPost, Platform, SentimentAnalysis | None]] = []
    for r in rows:
        post = post_map.get(r.post_id)
        if post is None:
            continue
        plat = Platform(r.platform)
        sa = sa_map.get(r.sa_id) if r.sa_id else None
        pending.append((post, plat, sa))

    return pending


async def _process_one(
    session: AsyncSession,
    post: SocialPost,
    platform: Platform,
    sa: SentimentAnalysis | None,
    *,
    ollama_url: str | None,
) -> tuple[bool, dict]:
    """Clasifica un post y persiste en sentiment_analyses.emotions.plutchik_6."""
    text = post.content or ""
    plutchik = await classify_plutchik_6(
        text,
        post_text=None,
        plataforma=platform.value,
        base_url=ollama_url,
    )

    if sa is None:
        # Crear fila mínima. No pisamos campos de pipeline pysentimiento.
        sa = SentimentAnalysis(
            post_id=post.id,
            model_used=MODEL_NAME,
            sentiment_score=0.0,
            sentiment_label=SentimentLabel.NEUTRAL,
            emotions={"plutchik_6": plutchik},
            is_toxic=False,
            toxicity_score=0.0,
        )
        session.add(sa)
    else:
        # Merge preservando keys previos (ej. pysentimiento emotions)
        existing = dict(sa.emotions) if sa.emotions else {}
        existing["plutchik_6"] = plutchik
        sa.emotions = existing

    ok = "_err" not in plutchik
    return ok, plutchik


async def run(
    *,
    limit: int,
    platform: Platform | None,
    ollama_url: str | None,
) -> tuple[int, int, float]:
    """Ejecuta el batch. Devuelve (procesados_ok, errores, duración_segundos)."""
    logger.info(
        "Plutchik batch S2 T3 | limit=%d platform=%s ollama=%s",
        limit,
        platform.value if platform else "ALL",
        ollama_url or "default (settings.OLLAMA_BASE_URL)",
    )

    processed = 0
    errors = 0
    start = time.perf_counter()
    first_sample_printed = False

    async with async_session_factory() as session:
        pending = await _fetch_pending(session, limit=limit, platform=platform)
        total = len(pending)
        logger.info("Posts pendientes plutchik_6: %d", total)

        if total == 0:
            logger.warning("Nada por procesar. Todos los posts ya tienen plutchik_6 o no hay contenido.")
            return 0, 0, 0.0

        for idx, (post, plat, sa) in enumerate(pending, start=1):
            t0 = time.perf_counter()
            ok, plutchik = await _process_one(
                session, post, plat, sa, ollama_url=ollama_url
            )
            await session.commit()
            elapsed = time.perf_counter() - t0

            if ok:
                processed += 1
            else:
                errors += 1
                logger.warning(
                    "post_id=%d _err=%s (%.1fs)",
                    post.id,
                    plutchik.get("_err"),
                    elapsed,
                )

            if not first_sample_printed and ok:
                logger.info(
                    "SAMPLE post_id=%d platform=%s elapsed=%.1fs plutchik_6=%s",
                    post.id,
                    plat.value,
                    elapsed,
                    plutchik,
                )
                first_sample_printed = True

            if idx % 20 == 0 or idx == total:
                dur = time.perf_counter() - start
                rate = idx / dur if dur > 0 else 0
                logger.info(
                    "Progreso %d/%d (ok=%d err=%d) %.2f posts/s acum=%.1fs",
                    idx,
                    total,
                    processed,
                    errors,
                    rate,
                    dur,
                )

    total_elapsed = time.perf_counter() - start
    logger.info(
        "Cierre: ok=%d err=%d tiempo=%.1fs avg=%.2fs/post",
        processed,
        errors,
        total_elapsed,
        total_elapsed / max(processed + errors, 1),
    )
    return processed, errors, total_elapsed


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Plutchik-6 batch (Gemma 3:12b) — Sprint S2 T3")
    p.add_argument("--limit", type=int, default=200, help="Max posts a procesar")
    p.add_argument("--platform", type=str, default=None, help="TWITTER|INSTAGRAM|...")
    p.add_argument(
        "--ollama-url",
        type=str,
        default=None,
        help="Override Ollama base URL (default settings.OLLAMA_BASE_URL)",
    )
    return p


def main() -> None:
    args = _build_parser().parse_args()
    platform_enum: Platform | None = None
    if args.platform:
        platform_enum = Platform(args.platform.upper())

    try:
        ok, err, dur = asyncio.run(
            run(
                limit=args.limit,
                platform=platform_enum,
                ollama_url=args.ollama_url,
            )
        )
    except KeyboardInterrupt:
        logger.warning("Interrumpido por usuario")
        sys.exit(130)

    # exit 0 si al menos 1 exitoso, 2 si todos fallaron (blocker)
    sys.exit(0 if ok > 0 else 2)


if __name__ == "__main__":
    main()
