"""Generate benchmark test cases from real DB data.

Reuses `plan_generator._gather_context` so the JSON reflects exactly what the
production pipeline sends to the LLM. Run once per data refresh; the resulting
JSON files become immutable fixtures for the benchmark loop.

Usage:
    python -m benchmarks.ai.build_test_cases

Writes one JSON per dirigente at `benchmarks/ai/test_cases/{slug}_{tipo}.json`.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.dirigente import Dirigente
from app.models.plan_ia import TipoPlan
from app.services.plan_generator import _build_prompt, _gather_context

OUT_DIR = Path(__file__).parent / "test_cases"


def _slug(name: str) -> str:
    return name.lower().replace(" ", "_").replace(".", "").replace(",", "")


async def build() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    async with async_session_factory() as db:
        result = await db.execute(select(Dirigente))
        dirigentes = list(result.scalars().all())

        if not dirigentes:
            raise SystemExit("No dirigentes en DB. Corre seed primero.")

        for d in dirigentes:
            ctx = await _gather_context(db, d)
            for tipo in (TipoPlan.DIAGNOSTICO, TipoPlan.CONSOLIDACION):
                prompt = _build_prompt(tipo, ctx)
                payload = {
                    "dirigente_id": d.id,
                    "dirigente_nombre": d.full_name,
                    "tipo_plan": tipo.value,
                    "context": ctx,
                    "rendered_prompt": prompt,
                }
                path = OUT_DIR / f"{_slug(d.full_name)}_{tipo.value.lower()}.json"
                path.write_text(
                    json.dumps(payload, indent=2, ensure_ascii=False, default=str),
                    encoding="utf-8",
                )
                print(f"wrote {path.relative_to(Path.cwd())}")


if __name__ == "__main__":
    asyncio.run(build())
