"""Backfill: pseudonimiza author_hash crudos (PII en texto plano) — LFPDPPP.

CONTEXTO (revisión CEO 2026-05-26 · cards B12/B13):
Algunas filas tienen el NOMBRE REAL en `author_hash` en vez de un hash (la ruta
RADAR FB Playwright lo guardó sin hashear). Eso es PII en texto plano + rompe la
deduplicación de autores + genera falsos "coordinación" en B12.

Tablas afectadas: social_comments (242) + watched_profiles (15).

Hashea cada valor crudo con el esquema canónico (ensure_author_hash). Determinista:
el mismo nombre → mismo hash en ambas tablas, preservando el join. Idempotente
(solo toca valores que NO son hash).

Uso:
    docker exec crece-backend python scripts/backfill_author_hash_pii.py --dry-run
    docker exec crece-backend python scripts/backfill_author_hash_pii.py --apply
"""
from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import text

from app.core.database import async_session_factory
from app.services.author_hash import ensure_author_hash, is_hashed

# Filtro de crudos idéntico al usado en el diagnóstico.
_CRUDO_WHERE = "(author_hash ~ '[[:space:]]' OR author_hash !~ '^[0-9a-f]{8,}')"


async def _process_table(db, table: str, has_platform: bool, apply: bool) -> tuple[int, int]:
    cols = "id, author_hash" + (", platform" if has_platform else "")
    rows = (
        await db.execute(text(f"SELECT {cols} FROM {table} WHERE {_CRUDO_WHERE}"))
    ).mappings().all()

    cambios: list[tuple] = []
    for r in rows:
        if is_hashed(r["author_hash"]):
            continue  # defensa extra
        platform = (r.get("platform") if has_platform else None) or "FACEBOOK"
        platform = str(platform).upper()
        new_hash = ensure_author_hash(r["author_hash"], platform)
        if new_hash and new_hash != r["author_hash"]:
            cambios.append((r["id"], new_hash, r["author_hash"]))

    print(f"\n[{table}] crudos: {len(rows)} · a pseudonimizar: {len(cambios)}")
    for _id, nh, old in cambios[:5]:
        print(f"   '{old[:30]}' → {nh[:16]}…")

    if apply and cambios:
        for _id, nh, _old in cambios:
            await db.execute(
                text(f"UPDATE {table} SET author_hash = :h WHERE id = :id"),
                {"h": nh, "id": _id},
            )
    return len(rows), len(cambios)


async def main(apply: bool) -> None:
    async with async_session_factory() as db:
        await _process_table(db, "social_comments", has_platform=False, apply=apply)
        await _process_table(db, "watched_profiles", has_platform=True, apply=apply)
        if apply:
            await db.commit()
            print("\n[APPLY] commit OK")
        else:
            print("\n[DRY-RUN] nada escrito. Corre con --apply.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(apply=args.apply))
