"""Scraper light de competidores · W2-gratis (sin Apify).

Plan war-room-personal · W2 alternativo. CEO confirmó 2026-05-14:
"tal vez no necesitamos Apify · tenemos skills que usamos antes que para
el proposito general podrían servir".

Reusa los scrapers nativos `backend/app/scrapers/{platform}.py` que ya
implementan `update_profile_stats(handle) -> {followers_count, following_count,
posts_count}` con estrategias en cascada (curl-cffi → page-info-scraper →
Playwright). Cero costo Apify.

Para cada competitor_profile activo:
1. Llama scraper nativo según platform.
2. UPSERT en competitor_metrics_monthly (month_start = primer día mes actual).
3. Engagement_rate queda None — requiere posts data más profunda.

Uso:
    docker exec crece-backend python scripts/scrape_competitors_light.py
    docker exec crece-backend python scripts/scrape_competitors_light.py --dirigente-id 3
    docker exec crece-backend python scripts/scrape_competitors_light.py --competitor-id 1
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import date, datetime, UTC
from pathlib import Path

# Cargar settings desde .env raíz
sys.path.insert(0, "/app")

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _first_of_month(d: date) -> date:
    return d.replace(day=1)


def _scraper_for(platform: str):
    """Lazy import del scraper nativo."""
    platform = platform.upper()
    if platform == "FACEBOOK":
        from app.scrapers.facebook import FacebookScraper
        return FacebookScraper()
    if platform == "INSTAGRAM":
        from app.scrapers.instagram import InstagramScraper
        return InstagramScraper()
    if platform == "TWITTER":
        from app.scrapers.twitter import TwitterScraper
        return TwitterScraper()
    if platform == "TIKTOK":
        from app.scrapers.tiktok import TikTokScraper
        return TikTokScraper()
    if platform == "YOUTUBE":
        from app.scrapers.youtube import YouTubeScraper
        return YouTubeScraper()
    return None


async def fetch_competitors(
    session: AsyncSession,
    *,
    dirigente_id: int | None = None,
    competitor_id: int | None = None,
) -> list[dict]:
    where = ["is_active = TRUE"]
    params: dict = {}
    if dirigente_id is not None:
        where.append("dirigente_objetivo_id = :did")
        params["did"] = dirigente_id
    if competitor_id is not None:
        where.append("id = :cid")
        params["cid"] = competitor_id
    sql = f"""
        SELECT id, dirigente_objetivo_id, display_name, platform,
               profile_external_id, profile_handle
        FROM competitor_profiles
        WHERE {' AND '.join(where)}
        ORDER BY id
    """
    rows = (await session.execute(text(sql), params)).mappings().all()
    return [dict(r) for r in rows]


async def upsert_metrics(
    session: AsyncSession,
    *,
    competitor_id: int,
    month_start: date,
    followers_total: int,
    posts_count: int,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO competitor_metrics_monthly
              (competitor_id, month_start, followers_total, posts_count,
               total_reactions, total_comments, total_shares, computed_at)
            VALUES (:cid, :ms, :ft, :pc, 0, 0, 0, NOW())
            ON CONFLICT (competitor_id, month_start) DO UPDATE SET
              followers_total = EXCLUDED.followers_total,
              posts_count = EXCLUDED.posts_count,
              computed_at = NOW()
            """
        ),
        {"cid": competitor_id, "ms": month_start, "ft": followers_total, "pc": posts_count},
    )
    await session.execute(
        text("UPDATE competitor_profiles SET last_scraped_at = NOW() WHERE id = :cid"),
        {"cid": competitor_id},
    )


async def scrape_one(
    session: AsyncSession,
    competitor: dict,
    month_start: date,
) -> dict:
    cid = competitor["id"]
    name = competitor["display_name"]
    platform = competitor["platform"]
    handle = competitor["profile_handle"] or competitor["profile_external_id"]

    if not handle or handle.startswith("legacy_") or handle.startswith("wizard:"):
        logger.warning(f"[{cid}] {name} ({platform}) handle no real ({handle!r}) — skip")
        return {"competitor_id": cid, "status": "skipped_handle", "name": name, "platform": platform}

    scraper = _scraper_for(platform)
    if scraper is None:
        logger.warning(f"[{cid}] platform {platform} sin scraper nativo — skip")
        return {"competitor_id": cid, "status": "skipped_platform", "name": name, "platform": platform}

    logger.info(f"[{cid}] scrape {name} · {platform} · @{handle}")
    try:
        stats = scraper.update_profile_stats(handle)
    except Exception as e:
        logger.exception(f"[{cid}] exception: {e}")
        return {"competitor_id": cid, "status": "error", "error": str(e), "name": name, "platform": platform}

    followers = int(stats.get("followers_count") or 0)
    posts = int(stats.get("posts_count") or 0)

    if followers == 0 and posts == 0:
        logger.warning(f"[{cid}] {name} {platform} retornó 0/0 — no UPSERT")
        return {"competitor_id": cid, "status": "no_data", "name": name, "platform": platform}

    await upsert_metrics(
        session,
        competitor_id=cid,
        month_start=month_start,
        followers_total=followers,
        posts_count=posts,
    )

    logger.info(f"[{cid}] OK · followers={followers:,} · posts={posts}")
    return {
        "competitor_id": cid,
        "status": "ok",
        "name": name,
        "platform": platform,
        "followers": followers,
        "posts": posts,
    }


async def main(args) -> int:
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("ASYNC_DATABASE_URL")
    if not db_url:
        from app.core.config import settings
        db_url = settings.DATABASE_URL
    # normalize async dialect
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql+psycopg2://"):
        db_url = db_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url, echo=False)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    month_start = _first_of_month(datetime.now(UTC).date())
    logger.info(f"=== scrape_competitors_light · mes {month_start} ===")

    async with SessionLocal() as session:
        competitors = await fetch_competitors(
            session,
            dirigente_id=args.dirigente_id,
            competitor_id=args.competitor_id,
        )
        if not competitors:
            logger.warning("No hay competidores activos para procesar.")
            return 0

        logger.info(f"Procesando {len(competitors)} competidores")
        results = []
        for c in competitors:
            r = await scrape_one(session, c, month_start)
            results.append(r)
            await session.commit()

    await engine.dispose()

    # Summary
    ok = [r for r in results if r["status"] == "ok"]
    no_data = [r for r in results if r["status"] == "no_data"]
    skipped = [r for r in results if r["status"].startswith("skipped")]
    errors = [r for r in results if r["status"] == "error"]
    logger.info("=== RESUMEN ===")
    logger.info(f"OK:        {len(ok)}")
    logger.info(f"No-data:   {len(no_data)}")
    logger.info(f"Skipped:   {len(skipped)}")
    logger.info(f"Errors:    {len(errors)}")
    for r in ok:
        logger.info(f"  ✓ {r['name']} ({r['platform']}): {r['followers']:,} followers · {r['posts']} posts")
    for r in no_data + skipped + errors:
        logger.info(f"  · {r['name']} ({r['platform']}): {r['status']}")

    return 0 if not errors else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirigente-id", type=int, help="Filtrar por dirigente_objetivo_id")
    ap.add_argument("--competitor-id", type=int, help="Procesar UN competitor_profile.id")
    sys.exit(asyncio.run(main(ap.parse_args())))
