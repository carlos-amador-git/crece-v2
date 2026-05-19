"""CLI batch processor — Sprint S1 T5.

Procesa posts de `social_posts`, llama a TopicExtractor (Gemma 3:12b vía Ollama)
y persiste el resultado en el campo JSONB `topics_extracted`. También actualiza
`scraped_at` NO tocado (es inmutable); no hay `updated_at` en el modelo, por lo
que se deja constancia con el `extracted_at` dentro del JSON y se guarda el JSON
completo en el campo.

Uso:
    python backend/scripts/run_topic_extraction.py --limit 50 --where-null

Args:
    --limit N         cuántos posts procesar como máximo (default 50)
    --where-null      solo posts cuyo `topics_extracted` sea NULL (default True)
    --post-id ID      procesar un solo post por ID (ignora --limit / --where-null)
    --platform P      filtra por plataforma (TWITTER, INSTAGRAM, FACEBOOK, ...)

Principios MD:
- NO mockear. Si Ollama no está accesible, reporta blocker y sale con exit!=0.
- Un commit por funcionalidad verificada. Correr el script es la verificación.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

# Permite ejecutar el script sin instalar el paquete (`python scripts/...`)
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select, update  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.database import async_session_factory  # noqa: E402
from app.models.social import Platform, SocialPost, SocialProfile  # noqa: E402
from app.nlp.topic_extractor import TopicExtractor  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("run_topic_extraction")


async def _fetch_posts(
    session: AsyncSession,
    *,
    limit: int,
    where_null: bool,
    post_id: int | None,
    platform: Platform | None,
) -> list[tuple[SocialPost, Platform]]:
    """Devuelve lista de (post, plataforma) lista para extraer.

    Hace JOIN con social_profiles para leer la plataforma (requerida por el
    prompt). Retorna los posts ordenados por id asc para reproducibilidad.
    """
    stmt = (
        select(SocialPost, SocialProfile.platform)
        .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
        .order_by(SocialPost.id.asc())
    )
    if post_id is not None:
        stmt = stmt.where(SocialPost.id == post_id)
    else:
        if where_null:
            stmt = stmt.where(SocialPost.topics_extracted.is_(None))
        if platform is not None:
            stmt = stmt.where(SocialProfile.platform == platform)
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


async def _process_one(
    session: AsyncSession,
    extractor: TopicExtractor,
    post: SocialPost,
    platform: Platform,
) -> tuple[bool, dict]:
    """Procesa un post. Devuelve (éxito, payload persistido)."""
    text = post.content or ""
    payload = await extractor.extract(
        text=text,
        post_text=None,  # para posts del dirigente, no hay "post original"
        plataforma=platform.value,
    )
    await session.execute(
        update(SocialPost)
        .where(SocialPost.id == post.id)
        .values(topics_extracted=payload)
    )
    return ("_err" not in payload, payload)


async def run(
    *,
    limit: int,
    where_null: bool,
    post_id: int | None,
    platform: Platform | None,
) -> int:
    """Ejecuta el batch. Devuelve el número de posts procesados con éxito."""
    extractor = TopicExtractor()
    logger.info(
        "TopicExtractor configurado: base_url=%s model=%s",
        extractor.base_url,
        extractor.model,
    )

    start_total = time.perf_counter()
    processed = 0
    errors = 0

    async with async_session_factory() as session:
        posts = await _fetch_posts(
            session,
            limit=limit,
            where_null=where_null,
            post_id=post_id,
            platform=platform,
        )
        total = len(posts)
        logger.info("Posts a procesar: %d", total)

        if total == 0:
            logger.warning(
                "No hay posts que cumplan el filtro. "
                "Revisa --where-null / --platform / --post-id."
            )
            return 0

        first_shown = False
        for idx, (post, plat) in enumerate(posts, start=1):
            t0 = time.perf_counter()
            ok, payload = await _process_one(session, extractor, post, plat)
            elapsed = time.perf_counter() - t0

            if ok:
                processed += 1
            else:
                errors += 1

            # commit por item: si el proceso se interrumpe, no se pierde progreso
            await session.commit()

            if not first_shown:
                # muestra verbose del primer resultado exitoso
                logger.info(
                    "SAMPLE post_id=%d platform=%s elapsed=%.1fs payload=%s",
                    post.id,
                    plat.value,
                    elapsed,
                    payload,
                )
                first_shown = True

            if idx % 10 == 0 or idx == total:
                logger.info(
                    "Progreso %d/%d (ok=%d err=%d) last_elapsed=%.1fs",
                    idx,
                    total,
                    processed,
                    errors,
                    elapsed,
                )

    total_elapsed = time.perf_counter() - start_total
    logger.info(
        "Cierre: procesados=%d errores=%d tiempo_total=%.1fs promedio=%.1fs/post",
        processed,
        errors,
        total_elapsed,
        (total_elapsed / max(processed + errors, 1)),
    )
    return processed


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Topic extraction batch (Gemma 3:12b)")
    p.add_argument("--limit", type=int, default=50, help="Máximo de posts a procesar")
    p.add_argument(
        "--where-null",
        action="store_true",
        default=True,
        help="Solo posts con topics_extracted NULL (default True)",
    )
    p.add_argument(
        "--no-where-null",
        dest="where_null",
        action="store_false",
        help="Procesar incluso posts que ya tienen topics_extracted",
    )
    p.add_argument("--post-id", type=int, default=None, help="ID específico")
    p.add_argument("--platform", type=str, default=None, help="TWITTER|INSTAGRAM|...")
    return p


def main() -> None:
    args = _build_parser().parse_args()
    platform_enum: Platform | None = None
    if args.platform:
        platform_enum = Platform(args.platform.upper())

    try:
        processed = asyncio.run(
            run(
                limit=args.limit,
                where_null=args.where_null,
                post_id=args.post_id,
                platform=platform_enum,
            )
        )
    except KeyboardInterrupt:
        logger.warning("Interrumpido por usuario")
        sys.exit(130)

    # exit 0 si al menos 1 exitoso, 2 si ninguno (blocker operativo)
    sys.exit(0 if processed > 0 else 2)


if __name__ == "__main__":
    main()
