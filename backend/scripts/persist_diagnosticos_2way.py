"""Persist 6 diagnosticos enriquecidos Claude+Gemini 2-way a planes_ia.

Lee 6 archivos markdown del host en rutas conocidas + ingiere también
las 6 versiones Gemini archivadas para referencia.

Usage (desde host):
  cp script al container y correr, o ejecutar inline.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, "/app")
from app.models.plan_ia import PlanIA, TipoPlan  # noqa: E402

DATABASE_URL = os.environ["DATABASE_URL"]

# (dirigente_id, claude_path, gemini_path, ctx_path)
TARGETS = [
    (1, "/app/diagnosticos_2way/pina-claude.md",      "/app/diagnosticos_2way/pina-gemini.md",     "/app/diagnosticos_2way/ctx_1.json"),
    (2, "/app/diagnosticos_2way/solano-claude.md",    "/app/diagnosticos_2way/solano-gemini.md",   "/app/diagnosticos_2way/ctx_2.json"),
    (3, "/app/diagnosticos_2way/pineda-claude.md",    "/app/diagnosticos_2way/pineda-gemini.md",   "/app/diagnosticos_2way/ctx_3.json"),
    (4, "/app/diagnosticos_2way/nolasco-claude.md",   "/app/diagnosticos_2way/nolasco-gemini.md",  "/app/diagnosticos_2way/ctx_4.json"),
    (5, "/app/diagnosticos_2way/jimenez-claude.md",   "/app/diagnosticos_2way/jimenez-gemini.md",  "/app/diagnosticos_2way/ctx_5.json"),
    (6, "/app/diagnosticos_2way/cravioto-claude.md",  "/app/diagnosticos_2way/cravioto-gemini.md", "/app/diagnosticos_2way/ctx_6.json"),
]

CLAUDE_MODEL_ID = "claude-2way-enriched-2026-05-10"
GEMINI_MODEL_ID = "gemini-cli-2way-enriched-2026-05-10"


async def main() -> int:
    eng = create_async_engine(DATABASE_URL, echo=False)
    Session = async_sessionmaker(eng, expire_on_commit=False)

    async with Session() as db:
        for did, claude_p, gemini_p, ctx_p in TARGETS:
            ctx = json.loads(Path(ctx_p).read_text(encoding="utf-8")) if Path(ctx_p).exists() else None
            claude_md = Path(claude_p).read_text(encoding="utf-8") if Path(claude_p).exists() else None
            gemini_md = Path(gemini_p).read_text(encoding="utf-8") if Path(gemini_p).exists() else None

            now = datetime.now(UTC)

            if gemini_md and len(gemini_md) > 1000:
                plan_g = PlanIA(
                    dirigente_id=did,
                    tipo=TipoPlan.DIAGNOSTICO,
                    contenido=gemini_md,
                    modelo_ia=GEMINI_MODEL_ID,
                    prompt_usado="(prompt enriquecido FODA 8-10 items/cuadrante v1 — see /tmp/diag_prompt_template.md)",
                    datos_entrada=ctx,
                    generado_por_id=1,
                    aprobado=False,
                    created_at=now,
                )
                db.add(plan_g)
                print(f"  [+] dirigente {did} GEMINI persisted ({len(gemini_md)} chars)", file=sys.stderr)

            if claude_md and len(claude_md) > 1000:
                plan_c = PlanIA(
                    dirigente_id=did,
                    tipo=TipoPlan.DIAGNOSTICO,
                    contenido=claude_md,
                    modelo_ia=CLAUDE_MODEL_ID,
                    prompt_usado="(prompt enriquecido FODA 8-10 items/cuadrante v1 — see /tmp/diag_prompt_template.md)",
                    datos_entrada=ctx,
                    generado_por_id=1,
                    aprobado=False,
                    # Claude se persiste DESPUES (created_at > gemini) para que sea el latest
                    created_at=datetime.now(UTC),
                )
                db.add(plan_c)
                print(f"  [+] dirigente {did} CLAUDE persisted ({len(claude_md)} chars)", file=sys.stderr)

        await db.commit()
        print("\n[OK] Commit completo", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
