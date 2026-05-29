"""Sprint S1 T10 — Generador idempotente del bundle Zenodo v1.

Consume DB CRECE v2 (social_posts + social_profile_snapshots + dirigentes.estrato_politico)
y produce `benchmarks_er_politicos_mx_v1.csv` con 25 celdas estrato × plataforma.

Uso:
    python backend/scripts/generate_zenodo_bundle.py \
        --window-days 90 \
        --output backend/data/zenodo/v1/ \
        --bootstrap-samples 1000

Idempotente: sobrescribe el CSV y registra metadata en `_calibration_log.json`.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import statistics
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.dirigente import Dirigente
from app.models.social import Platform, SocialPost, SocialProfile

ESTRATOS = ("Nano", "Micro", "Mid", "Macro", "Mega")
PLATAFORMAS = ("X", "Instagram", "Facebook", "TikTok", "YouTube")

# Mapeo plataforma del Enum a nombre canónico del CSV
PLATFORM_TO_LABEL = {
    Platform.TWITTER: "X",
    Platform.INSTAGRAM: "Instagram",
    Platform.FACEBOOK: "Facebook",
    Platform.TIKTOK: "TikTok",
    Platform.YOUTUBE: "YouTube",
}


def bootstrap_ci95_median(values: list[float], samples: int = 1000, seed: int = 42) -> tuple[float, float]:
    """Intervalo de confianza 95% del percentil 50 vía bootstrap."""
    import random

    rng = random.Random(seed)
    n = len(values)
    if n < 2:
        return (float("nan"), float("nan"))
    medians = []
    for _ in range(samples):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        medians.append(statistics.median(sample))
    medians.sort()
    low_idx = int(samples * 0.025)
    high_idx = int(samples * 0.975) - 1
    return (medians[low_idx], medians[high_idx])


async def collect_er_values(
    session: AsyncSession, window_start: datetime, window_end: datetime
) -> dict[tuple[str, str], list[float]]:
    """Retorna dict[(estrato, plataforma_label)] -> lista de ER_post en la ventana."""
    stmt = (
        select(SocialPost, SocialProfile, Dirigente)
        .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
        .join(Dirigente, SocialProfile.dirigente_id == Dirigente.id)
        .where(SocialPost.published_at >= window_start)
        .where(SocialPost.published_at <= window_end)
        .where(Dirigente.estrato_politico.isnot(None))
    )
    result = await session.execute(stmt)
    rows = result.all()

    bucket: dict[tuple[str, str], list[float]] = {
        (e, p): [] for e in ESTRATOS for p in PLATAFORMAS
    }

    for post, profile, dirigente in rows:
        followers = profile.followers_count or 0
        if followers <= 0:
            continue
        interactions = (post.likes or 0) + (post.comments or 0) + (post.shares or 0)
        er = (interactions / followers) * 100.0
        platform_label = PLATFORM_TO_LABEL.get(profile.platform)
        if not platform_label:
            continue
        key = (dirigente.estrato_politico, platform_label)
        if key in bucket:
            bucket[key].append(er)

    return bucket


def calibrate_cell(values: list[float], bootstrap_samples: int) -> dict[str, Any]:
    """Calcula métricas para una celda (estrato, plataforma)."""
    n = len(values)
    if n == 0:
        return {
            "n_observaciones": 0,
            "er_p25": None,
            "er_p50": None,
            "er_p75": None,
            "ic95_low": None,
            "ic95_high": None,
            "status": "TBD",
        }

    sorted_values = sorted(values)
    p25_idx = max(0, int(n * 0.25) - 1)
    p50_idx = max(0, int(n * 0.50) - 1)
    p75_idx = max(0, int(n * 0.75) - 1)
    er_p25 = sorted_values[p25_idx] if n >= 4 else None
    er_p50 = statistics.median(sorted_values)
    er_p75 = sorted_values[p75_idx] if n >= 4 else None

    ic_low, ic_high = bootstrap_ci95_median(values, samples=bootstrap_samples)

    status = "VALIDATED" if n >= 30 else "TBD"

    return {
        "n_observaciones": n,
        "er_p25": round(er_p25, 4) if er_p25 is not None else None,
        "er_p50": round(er_p50, 4) if er_p50 is not None else None,
        "er_p75": round(er_p75, 4) if er_p75 is not None else None,
        "ic95_low": round(ic_low, 4) if ic_low == ic_low else None,  # NaN check
        "ic95_high": round(ic_high, 4) if ic_high == ic_high else None,
        "status": status,
    }


async def main(args: argparse.Namespace) -> None:
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "benchmarks_er_politicos_mx_v1.csv"
    log_path = output_dir / "_calibration_log.json"

    window_end = datetime.now(UTC)
    window_start = window_end - timedelta(days=args.window_days)

    print(
        f"=== Generando bundle Zenodo v1 · ventana {window_start.date()} → {window_end.date()} ({args.window_days}d) ==="
    )

    async with async_session_factory() as session:
        bucket = await collect_er_values(session, window_start, window_end)

    total_obs = sum(len(v) for v in bucket.values())
    print(f"Total observaciones en ventana: {total_obs}")

    rows_out: list[dict[str, Any]] = []
    validated = 0
    for estrato in ESTRATOS:
        for plataforma in PLATAFORMAS:
            values = bucket.get((estrato, plataforma), [])
            cell = calibrate_cell(values, args.bootstrap_samples)
            cell["estrato"] = estrato
            cell["plataforma"] = plataforma
            cell["ventana_inicio"] = window_start.date().isoformat()
            cell["ventana_fin"] = window_end.date().isoformat()
            rows_out.append(cell)
            if cell["status"] == "VALIDATED":
                validated += 1

    fieldnames = [
        "estrato", "plataforma", "n_observaciones",
        "er_p25", "er_p50", "er_p75",
        "ic95_low", "ic95_high",
        "ventana_inicio", "ventana_fin", "status",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows_out:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    log_entry = {
        "run_at": datetime.now(UTC).isoformat(),
        "window_days": args.window_days,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "total_observaciones": total_obs,
        "cells_total": len(rows_out),
        "cells_validated": validated,
        "cells_tbd": len(rows_out) - validated,
        "bootstrap_samples": args.bootstrap_samples,
        "csv_path": str(csv_path),
    }
    log_path.write_text(json.dumps(log_entry, indent=2, ensure_ascii=False))

    print("\n=== Bundle generado ===")
    print(f"  CSV: {csv_path}")
    print(f"  Log: {log_path}")
    print(f"  Celdas VALIDATED: {validated}/25")
    print(f"  Celdas TBD: {len(rows_out) - validated}/25")
    print(f"  Status: v1 {'preliminar (muestra insuficiente)' if validated < 10 else 'usable con ' + str(validated) + ' celdas'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Zenodo bundle v1 for CRECE v2 ER benchmarks")
    parser.add_argument("--window-days", type=int, default=90, help="Rolling window in days")
    parser.add_argument("--output", default="backend/data/zenodo/v1/", help="Output directory")
    parser.add_argument("--bootstrap-samples", type=int, default=1000, help="Bootstrap replications for IC95")
    args = parser.parse_args()
    asyncio.run(main(args))
