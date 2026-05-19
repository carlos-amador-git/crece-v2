"""Scraper light de competidores via Apify · W2 fallback.

Usa `apify/facebook-pages-scraper` (specifically para metadata de páginas FB)
para obtener followers + posts count. Cost esperado: ~$0.02 por página.

W2-gratis falló porque FB ya no expone followers en HTML estático y
Selenium/ChromeDriver no funciona en el container Docker. Esta versión
usa Apify INICIAL como fallback ratificado por CEO 2026-05-14.

Uso:
    docker exec -e APIFY_TOKEN=apify_api_xxx crece-backend \\
      python scripts/scrape_competitors_light_apify.py --dirigente-id 3
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from datetime import date, datetime, UTC

sys.path.insert(0, "/app")

import psycopg2
from apify_client import ApifyClient
import requests as http

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("scrape_light")

ACTOR_FB_PAGES = "apify/facebook-pages-scraper"


def _first_of_month(d: date) -> date:
    return d.replace(day=1)


def _apify_usage(token: str) -> float:
    r = http.get(f"https://api.apify.com/v2/users/me/limits?token={token}", timeout=10)
    r.raise_for_status()
    return float(r.json()["data"]["current"].get("monthlyUsageUsd", 0.0))


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
        SELECT id, display_name, platform, profile_external_id, profile_handle, profile_url
        FROM competitor_profiles
        WHERE {' AND '.join(where)} AND platform = 'FACEBOOK'
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
    # Mantener competitor_profiles.last_scraped_at en sync para que UI sepa
    # cuándo fue la última medición sin tener que hacer JOIN con metrics.
    await session.execute(
        text("UPDATE competitor_profiles SET last_scraped_at = NOW() WHERE id = :cid"),
        {"cid": competitor_id},
    )


async def main(args) -> int:
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        log.error("APIFY_TOKEN no configurado en env")
        return 1

    # Pre-flight budget
    used_before = _apify_usage(token)
    log.info(f"Apify MTD before: ${used_before:.4f} · cap budget run: ${args.budget:.2f}")
    if used_before >= 4.95:
        log.error("Cuenta agotada (cap $5). Abort.")
        return 2

    # DB
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("ASYNC_DATABASE_URL")
    if not db_url:
        from app.core.config import settings
        db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql+psycopg2://"):
        db_url = db_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url, echo=False)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    month_start = _first_of_month(datetime.now(UTC).date())

    async with SessionLocal() as session:
        competitors = await fetch_competitors(
            session,
            dirigente_id=args.dirigente_id,
            competitor_id=args.competitor_id,
        )
        if not competitors:
            log.warning("Sin competidores FB activos para procesar.")
            return 0

        log.info(f"Procesando {len(competitors)} competidores FB · mes {month_start}")

        # Dedupe handles (Taboada está 2 veces con FB+IG, aquí solo FB)
        handles_seen = set()
        urls = []
        comp_by_handle = {}
        for c in competitors:
            h = c["profile_handle"] or c["profile_external_id"]
            if h.startswith("legacy_") or h.startswith("wizard:"):
                log.warning(f"[{c['id']}] handle no real ({h!r}) · skip")
                continue
            if h in handles_seen:
                continue
            handles_seen.add(h)
            url = c.get("profile_url") or f"https://www.facebook.com/{h}"
            urls.append({"url": url})
            comp_by_handle[h] = c

        if not urls:
            log.warning("Ningún handle FB válido para scrape.")
            return 0

        log.info(f"URLs únicas a llamar: {len(urls)}")
        for u in urls:
            log.info(f"  - {u['url']}")

        # Llamada Apify
        apify = ApifyClient(token)
        run_input = {"startUrls": urls}
        t0 = time.time()
        log.info(f"Llamando {ACTOR_FB_PAGES} ...")
        run = apify.actor(ACTOR_FB_PAGES).call(run_input=run_input, timeout_secs=180)
        cost_sdk = float(run.get("usageTotalUsd") or 0.0)
        elapsed = time.time() - t0
        log.info(f"Run done in {elapsed:.1f}s · cost (SDK)=${cost_sdk:.4f} · status={run['status']}")

        items = list(apify.dataset(run["defaultDatasetId"]).iterate_items())
        log.info(f"Items received: {len(items)}")

        for raw in items:
            # facebook-pages-scraper retorna: pageName, pageUrl, likes, followers, posts...
            url = raw.get("pageUrl") or raw.get("url") or ""
            handle = url.rstrip("/").rsplit("/", 1)[-1]
            comp = comp_by_handle.get(handle)
            if not comp:
                # Try fuzzy match (case-insensitive)
                comp = next(
                    (c for h, c in comp_by_handle.items() if h.lower() == handle.lower()),
                    None,
                )
            if not comp:
                log.warning(f"  raw handle '{handle}' no matchea ningún competitor · skip")
                continue

            followers = int(raw.get("followers") or raw.get("likes") or raw.get("fanCount") or 0)
            posts = int(raw.get("posts") or raw.get("postsCount") or 0)
            log.info(
                f"  ✓ [{comp['id']}] {comp['display_name']}: followers={followers:,} · posts={posts}"
            )

            await upsert_metrics(
                session,
                competitor_id=comp["id"],
                month_start=month_start,
                followers_total=followers,
                posts_count=posts,
            )
            await session.commit()

    await engine.dispose()

    used_after = _apify_usage(token)
    log.info(f"Apify MTD after: ${used_after:.4f} · gastado en run: ${used_after - used_before:.4f}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirigente-id", type=int)
    ap.add_argument("--competitor-id", type=int)
    ap.add_argument("--budget", type=float, default=0.15, help="Cap USD para este run")
    sys.exit(asyncio.run(main(ap.parse_args())))
