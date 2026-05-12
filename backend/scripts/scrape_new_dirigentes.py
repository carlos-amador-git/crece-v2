"""
Scrape real posts for dirigentes. Uses the project's existing scraper infrastructure
(profile_id based). Optionally runs NLP via reprocess_nlp.

Usage:
    # Legacy mode — 4 shadow MORENA dirigentes
    python -m scripts.scrape_new_dirigentes

    # Single dirigente by ID (2026-04-24 onboarding · e.g. Máynez id=7)
    python -m scripts.scrape_new_dirigentes --dirigente-id 7 --skip-nlp

Flags:
    --dirigente-id INT  · scrape solo ese dirigente (por id, no por nombre)
    --skip-nlp          · NO correr reprocess_nlp al final

WARNING post-3d6fe3f (2026-04-18): reprocess_nlp depende de columnas dropeadas
(tono_discurso, target_politico, sentimiento_politico_ajustado, nlp_model_version).
Fallará hasta que F1.1 Schema restauración se ejecute.
Ver: .context/PLAN-recuperacion-post-incidente-2026-04-21.md
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.dirigente import Dirigente
from app.models.social import SocialProfile

TARGET_DIRIGENTES_LEGACY = [
    "Saymi Adriana Pineda Velasco",
    "Yesenia Nolasco Ramírez",
    "Gabriela Jiménez Godoy",
    "César Cravioto Romero",
]


async def main(dirigente_id: int | None = None, skip_nlp: bool = False):
    engine = create_async_engine(str(settings.DATABASE_URL), echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Collect profile IDs to scrape
    profiles_to_scrape: list[tuple[int, str, str]] = []  # (profile_id, platform, handle)
    target_ids: list[int] = []

    async with async_session() as session:
        if dirigente_id is not None:
            # Single-dirigente mode (2026-04-24+)
            dirigente = (await session.execute(
                select(Dirigente).where(Dirigente.id == dirigente_id)
            )).scalar_one_or_none()
            if not dirigente:
                logger.error(f"Dirigente id={dirigente_id} not found")
                await engine.dispose()
                return
            target_ids.append(dirigente.id)
            profiles = (await session.execute(
                select(SocialProfile).where(SocialProfile.dirigente_id == dirigente.id)
            )).scalars().all()
            for p in profiles:
                profiles_to_scrape.append((p.id, p.platform.value.lower(), p.handle))
                logger.info(f"  Queued: {dirigente.full_name} — {p.platform.value} @{p.handle} (profile_id={p.id})")
        else:
            # Legacy mode — 4 shadow MORENA dirigentes by name
            for name in TARGET_DIRIGENTES_LEGACY:
                result = await session.execute(
                    select(Dirigente).where(Dirigente.full_name == name)
                )
                dirigente = result.scalar_one_or_none()
                if not dirigente:
                    logger.warning(f"Dirigente not found: {name}")
                    continue
                target_ids.append(dirigente.id)
                profiles = (await session.execute(
                    select(SocialProfile).where(SocialProfile.dirigente_id == dirigente.id)
                )).scalars().all()
                for p in profiles:
                    profiles_to_scrape.append((p.id, p.platform.value.lower(), p.handle))
                    logger.info(f"  Queued: {name} — {p.platform.value} @{p.handle} (profile_id={p.id})")

    await engine.dispose()

    # Run scrapers (synchronous — they create their own DB sessions)
    from app.scrapers.base import get_scraper

    for profile_id, platform, handle in profiles_to_scrape:
        logger.info(f"Scraping {platform} @{handle} (profile_id={profile_id})...")
        try:
            scraper = get_scraper(platform)
            result = scraper.scrape(profile_id=profile_id)
            new_posts = result.get("new_posts", 0)
            errors = result.get("errors", [])
            logger.info(f"  OK: {new_posts} new posts" + (f", errors: {errors}" if errors else ""))
        except Exception as e:
            logger.error(f"  FAIL: {platform} @{handle} — {type(e).__name__}: {e}")

    # Run NLP on new posts (salvo --skip-nlp)
    # TODO post-F1.1: reactivar reprocess_nlp cuando F1.1 Schema restauración
    #       (PLAN-recuperacion-post-incidente-2026-04-21.md) haya restaurado las
    #       columnas dropeadas por 3d6fe3f (tono_discurso, target_politico,
    #       sentimiento_politico_ajustado, nlp_model_version).
    if skip_nlp:
        logger.info("\nNLP step skipped (--skip-nlp). Schema post-3d6fe3f requires F1.1 first.")
    else:
        logger.info("\nRunning NLP on new posts...")
        try:
            from scripts.reprocess_nlp import reprocess_nlp
            updated = await reprocess_nlp()
            logger.info(f"  NLP processed {updated} posts")
        except Exception as e:
            logger.error(f"  NLP failed: {type(e).__name__}: {e}")

    # Summary — per-platform counts + <20 flag (insuficiente FODA)
    engine2 = create_async_engine(str(settings.DATABASE_URL), echo=False)
    async_session2 = sessionmaker(engine2, class_=AsyncSession, expire_on_commit=False)
    FODA_MIN_THRESHOLD = 20
    async with async_session2() as session:
        for did in target_ids:
            d = (await session.execute(
                select(Dirigente).where(Dirigente.id == did)
            )).scalar_one_or_none()
            if not d:
                continue
            total = (await session.execute(
                text("""
                    SELECT count(*) FROM social_posts sp
                    JOIN social_profiles p ON sp.profile_id = p.id
                    WHERE p.dirigente_id = :did
                """),
                {"did": did},
            )).scalar()
            logger.info(f"\n  {d.full_name}: {total} posts total")
            per_plat = (await session.execute(
                text("""
                    SELECT p.platform::text, COUNT(sp.id)
                    FROM social_profiles p
                    LEFT JOIN social_posts sp ON sp.profile_id = p.id
                    WHERE p.dirigente_id = :did
                    GROUP BY p.platform
                    ORDER BY p.platform
                """),
                {"did": did},
            )).fetchall()
            for platform, count in per_plat:
                flag = "  ⚠️ INSUFICIENTE FODA (<20)" if count < FODA_MIN_THRESHOLD else ""
                logger.info(f"    {platform}: {count} posts{flag}")

    await engine2.dispose()
    logger.info("\nDone.")


def _parse_args():
    parser = argparse.ArgumentParser(description="Scrape posts for dirigentes.")
    parser.add_argument(
        "--dirigente-id",
        type=int,
        default=None,
        help="Scrape single dirigente by id (overrides legacy TARGET_DIRIGENTES list).",
    )
    parser.add_argument(
        "--skip-nlp",
        action="store_true",
        help="Skip reprocess_nlp step (required post-3d6fe3f until F1.1).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(main(dirigente_id=args.dirigente_id, skip_nlp=args.skip_nlp))
