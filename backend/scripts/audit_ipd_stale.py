"""Detector de IPD stale · S9 Sprint dedicado 2026-05-15.

Audit hallazgo A4 (.context/AUDIT-INFO-LOGIC-2026-05-15.md): el IPD se
calcula en runtime sobre social_profiles + social_posts. Si los profiles
tienen >7 días sin scrape, el IPD mostrado en UI puede estar basado en
data vieja y el dirigente no lo sabe.

Este script NO recalcula nada — solo lista quién está stale para que el
CEO decida triggers de re-scrape (riesgo de side effects: rate limits,
quota Apify).

Uso:
    docker exec crece-backend python -m scripts.audit_ipd_stale
    docker exec crece-backend python -m scripts.audit_ipd_stale --days 14
    docker exec crece-backend python -m scripts.audit_ipd_stale --json

Salida default: tabla legible. Con --json: stdout JSON parseable.
"""
from __future__ import annotations

import argparse
import asyncio
import json as json_lib
import os
import sys
from datetime import datetime, timedelta, UTC

sys.path.insert(0, "/app")

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


async def find_stale_dirigentes(
    session: AsyncSession,
    *,
    threshold_days: int = 7,
) -> list[dict]:
    """Devuelve dirigentes cuyo profile más reciente fue scrapeado hace
    más de ``threshold_days`` días.

    Si un dirigente NO tiene profiles, también lo reporta (`reason="no_profiles"`).
    Si un dirigente tiene profiles pero ninguno con last_scraped_at, lo
    reporta como `reason="never_scraped"`.
    """
    cutoff = datetime.now(UTC) - timedelta(days=threshold_days)

    sql = text(
        """
        WITH profile_stats AS (
            SELECT
                d.id AS dirigente_id,
                d.full_name,
                d.org_id,
                COUNT(sp.id) AS profile_count,
                MAX(sp.last_scraped_at) AS most_recent_scrape,
                MIN(sp.last_scraped_at) AS least_recent_scrape,
                COUNT(sp.id) FILTER (WHERE sp.last_scraped_at IS NULL) AS never_scraped_profiles
            FROM dirigentes d
            LEFT JOIN social_profiles sp ON sp.dirigente_id = d.id
            GROUP BY d.id, d.full_name, d.org_id
        )
        SELECT
            dirigente_id,
            full_name,
            org_id,
            profile_count,
            most_recent_scrape,
            least_recent_scrape,
            never_scraped_profiles,
            CASE
                WHEN profile_count = 0 THEN 'no_profiles'
                WHEN most_recent_scrape IS NULL THEN 'never_scraped'
                WHEN most_recent_scrape < :cutoff THEN 'stale'
                ELSE 'fresh'
            END AS staleness_state
        FROM profile_stats
        WHERE
            profile_count = 0
            OR most_recent_scrape IS NULL
            OR most_recent_scrape < :cutoff
        ORDER BY most_recent_scrape ASC NULLS FIRST
        """
    )
    rows = (await session.execute(sql, {"cutoff": cutoff})).mappings().all()
    out = []
    now = datetime.now(UTC)
    for r in rows:
        r_dict = dict(r)
        if r_dict["most_recent_scrape"]:
            r_dict["days_since_scrape"] = (now - r_dict["most_recent_scrape"]).days
            r_dict["most_recent_scrape"] = r_dict["most_recent_scrape"].isoformat()
        else:
            r_dict["days_since_scrape"] = None
        if r_dict["least_recent_scrape"]:
            r_dict["least_recent_scrape"] = r_dict["least_recent_scrape"].isoformat()
        out.append(r_dict)
    return out


async def main(args) -> int:
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

    async with SessionLocal() as session:
        stale = await find_stale_dirigentes(session, threshold_days=args.days)

    await engine.dispose()

    if args.json:
        print(json_lib.dumps(stale, default=str, indent=2))
        return 0

    if not stale:
        print(f"✓ Sin dirigentes stale (umbral: {args.days} días).")
        return 0

    # Tabla legible
    print(f"\nDirigentes con IPD stale (umbral: {args.days} días):\n")
    print(f"{'ID':>4} {'Estado':<14} {'Días':>5} {'Perfiles':>9} {'Nombre':<40}")
    print("-" * 75)
    for r in stale:
        days = r["days_since_scrape"]
        days_str = f"{days}" if days is not None else "—"
        print(
            f"{r['dirigente_id']:>4} {r['staleness_state']:<14} {days_str:>5} "
            f"{r['profile_count']:>9} {r['full_name'][:40]:<40}"
        )
    print(f"\nTotal: {len(stale)} dirigentes stale.")
    print(
        "\nEste script NO recalcula. Decisión CEO sobre re-scrape selectivo "
        "(rate limits + presupuesto Apify aplican)."
    )
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--days",
        type=int,
        default=7,
        help="Umbral en días para considerar IPD stale (default 7)",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Salida JSON parseable (default tabla legible)",
    )
    sys.exit(asyncio.run(main(ap.parse_args())))
