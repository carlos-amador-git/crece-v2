"""Backfill plataformas_destino para todas las recomendaciones_plan_ia.

Usa los mismos PLATFORM_PATTERNS del frontend (detectPlataformas) pero en Python
con re. Aplica a accion_texto, criterio_exito, principio_conductual y evidencia.
"""
from __future__ import annotations

import asyncio
import json
import re

from sqlalchemy import text

from app.core.database import async_session_factory


PATTERNS = {
    "INSTAGRAM": re.compile(r"\b(IG|Instagram)\b", re.IGNORECASE),
    "FACEBOOK": re.compile(r"\b(FB|Facebook)\b", re.IGNORECASE),
    "TIKTOK": re.compile(r"\b(TT|TikTok)\b", re.IGNORECASE),
    "YOUTUBE": re.compile(r"\b(YT|YouTube)\b", re.IGNORECASE),
    "TWITTER": re.compile(r"\b(Twitter|X/Twitter|\bX\b)\b", re.IGNORECASE),
}


def detect(text_blob: str) -> list[str]:
    if not text_blob:
        return []
    found = []
    for plat, rgx in PATTERNS.items():
        if rgx.search(text_blob):
            found.append(plat)
    return found


async def main():
    async with async_session_factory() as session:
        # Cache de plataformas top-3 por dirigente (fallback)
        prof_rows = (await session.execute(text("""
            SELECT dirigente_id, platform::text AS plat, followers_count
            FROM social_profiles
            ORDER BY dirigente_id, followers_count DESC NULLS LAST
        """))).all()
        top_plat = {}
        for r in prof_rows:
            top_plat.setdefault(r.dirigente_id, []).append(r.plat)
        # Top-3
        top_plat = {did: plats[:3] for did, plats in top_plat.items()}

        rows = (await session.execute(text("""
            SELECT id, dirigente_id, accion_texto, principio_conductual,
                   criterio_exito::text AS crit_text,
                   evidencia_respaldo::text AS evid_text
            FROM recomendaciones_plan_ia
        """))).all()

        total = 0
        with_fallback = 0
        for r in rows:
            blob = " ".join([
                r.accion_texto or "",
                r.principio_conductual or "",
                r.crit_text or "",
                r.evid_text or "",
            ])
            plats = detect(blob)
            if not plats:
                # Fallback: top-3 plataformas del dirigente
                plats = top_plat.get(r.dirigente_id, [])
                with_fallback += 1
            await session.execute(
                text("""
                    UPDATE recomendaciones_plan_ia
                    SET plataformas_destino = CAST(:plats AS JSONB)
                    WHERE id = :rid
                """),
                {"rid": r.id, "plats": json.dumps(plats)},
            )
            total += 1
        await session.commit()
        print(f"Backfilled {total} rows · {with_fallback} usaron fallback top-3 dirigente")


if __name__ == "__main__":
    asyncio.run(main())
