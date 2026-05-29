"""regen_plan_dirigente.py — Sprint F PLAN-2026-05-17-fans-dashboard.md

Genera un Plan IA para un dirigente, OFFLINE, vía subprocess Claude Code CLI
(`claude --print --effort high`) con fallback a `gemini-clean --mode plan`.

Persiste el plan en `planes_ia` + las recomendaciones individuales en
`recomendaciones_plan_ia` (estado='propuesta'). El usuario `crece-cli`
(user_id=1 por convención) queda como `generado_por_id`.

Decisiones cerradas que respeta:
- D-1 (CEO 2026-05-17): NO toca Ollama ni `llm_pipeline.py`. Endpoint
  `/plan-ia/generate` sigue en 503. La generación es 100% offline.
- D-2: stack runtime = CC subprocess + Gemini CLI fallback.

Diferencia con el pipeline async original (`app/services/plan_ia/llm_pipeline.py`):
ese pipeline carga los 18 bloques del diagnóstico (B01-B18) vía servicios async.
Este script standalone usa el contexto curado de `dirigente_context_builder`
(Sprint E ya añadió `performance_posts`). Es una entrada más compacta y rica
en señal cualitativa de redes sociales, en vez de los 18 KPIs cuantitativos.

IMPORTANTE — corre en HOST (Mac Mini), NO en container:
- `claude` CLI vive en /Users/marxchavez/.local/bin/claude
- `gemini-clean` vive en /Users/marxchavez/.claude/bin/gemini-clean
- DB_URL apunta a host postgres :5438 (asyncpg driver)

Uso:
  python backend/scripts/regen_plan_dirigente.py --dirigente-id 3  # Saymi
  python backend/scripts/regen_plan_dirigente.py --dirigente-id 3 --dry-run
  python backend/scripts/regen_plan_dirigente.py --dirigente-id 3 --skip-cc  # solo Gemini

  nohup python backend/scripts/regen_plan_dirigente.py --dirigente-id 3 \\
    > backend/.context/plan_regen_saymi_$(date +%Y%m%d_%H%M).log 2>&1 &
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Asegurar import de app.* (script vive en backend/scripts/)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.services.dirigente_context_builder import (
    build_context,
    format_context_for_prompt,
)

# ----- Config ------------------------------------------------------------

DEFAULT_DB_URL = "postgresql+asyncpg://crece:crece_dev@localhost:5438/crece"
DB_URL = os.environ.get("DATABASE_URL", DEFAULT_DB_URL)
# El builder usa asyncpg; si DATABASE_URL viene con +psycopg, lo reemplazamos.
if DB_URL.startswith("postgresql://"):
    DB_URL = DB_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif "+psycopg" in DB_URL:
    DB_URL = DB_URL.replace("+psycopg", "+asyncpg")

CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "/Users/marxchavez/.local/bin/claude")
GEMINI_BIN = os.environ.get("GEMINI_BIN", "/Users/marxchavez/.claude/bin/gemini-clean")

DEFAULT_TIMEOUT_CC = int(os.environ.get("CC_TIMEOUT", "900"))   # 15 min
DEFAULT_TIMEOUT_GEMINI = int(os.environ.get("GEMINI_TIMEOUT", "600"))  # 10 min
CC_EFFORT = os.environ.get("CC_EFFORT", "high")

MODEL_VERSION_CC = "cc-subprocess-plan-v1-2026-05-19"
MODEL_VERSION_GEMINI = "gemini-cli-plan-v1-2026-05-19"

GENERADO_POR_ID = int(os.environ.get("PLAN_GENERADO_POR_ID", "1"))  # admin/root


# ----- Prompt ------------------------------------------------------------

PROMPT_TEMPLATE = """Eres analista de estrategia política digital. Tu tarea: generar entre 3 y 5
recomendaciones accionables para el dirigente abajo descrito, basadas
exclusivamente en el contexto de redes sociales provisto.

CONTEXTO DEL DIRIGENTE:
{ctx_md}

REGLAS DURAS (no negociables):
1. Cada recomendación debe ser ACCIONABLE en los próximos 14-30 días.
2. NO recomendaciones genéricas de vanidad ("aumentar engagement",
   "publicar más", "interactuar con seguidores"). Cita SIEMPRE un dato
   concreto del contexto (un post, un tono, una crítica, una promesa).
3. NO inventes datos: si una métrica no está en el contexto, no la cites.
4. Si el contexto incluye `Posts que generaron crítica`, AL MENOS UNA
   recomendación debe atacar esa narrativa (responder, corregir, pivotar).
5. Si el contexto incluye `Posts de mejor desempeño`, AL MENOS UNA
   recomendación debe replicar/escalar ese patrón.
6. Anti-redundancia intra-batch: cada recomendación debe distinguirse de
   las otras por AL MENOS DOS de estos ejes: tipo (start/stop/continue),
   principio_conductual, plataforma_destino, evidencia citada.

OUTPUT: ÚNICAMENTE un objeto JSON con esta forma EXACTA (sin markdown,
sin comentarios, sin texto adicional):

{{
  "resumen_diagnostico": "1-2 oraciones que sintetizan el contexto",
  "recomendaciones": [
    {{
      "tipo": "start" | "stop" | "continue",
      "accion_texto": "qué hacer concretamente, 1-2 oraciones",
      "ventana_duracion_dias": 14,
      "principio_conductual": "nombre corto del principio (ej. reciprocidad, prueba_social, autoridad, escasez)",
      "evidencia_respaldo": {{
        "tipo_dato": "post_ganador" | "post_perdedor" | "tono_dominante" | "promesa_pendiente" | "efemeride" | "otro",
        "cita_textual": "fragmento del contexto que justifica esta recomendación"
      }},
      "criterio_exito": {{
        "metrica": "ej. n_comments_positivos, response_rate, posts_publicados",
        "objetivo": "valor o rango medible en la ventana"
      }},
      "plataforma_destino": "FB" | "IG" | "X" | "TikTok" | "YouTube" | "all"
    }}
  ]
}}
"""


# ----- LLM callers -------------------------------------------------------

def _call_claude_code(prompt: str, timeout: int = DEFAULT_TIMEOUT_CC) -> str | None:
    """Invoca Claude Code CLI. Retorna stdout o None si falla."""
    if not Path(CLAUDE_BIN).exists():
        print(f"  [CC] binary not found at {CLAUDE_BIN}", file=sys.stderr)
        return None
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "--print", "--effort", CC_EFFORT, prompt],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            print(f"  [CC] exit={result.returncode} stderr={result.stderr[:200]}",
                  file=sys.stderr)
            return None
        return result.stdout
    except subprocess.TimeoutExpired:
        print(f"  [CC] timeout {timeout}s", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  [CC] exception {type(e).__name__}: {e}", file=sys.stderr)
        return None


def _call_gemini_cli(prompt: str, timeout: int = DEFAULT_TIMEOUT_GEMINI) -> str | None:
    """Invoca gemini-clean. Retorna stdout o None si falla."""
    if not Path(GEMINI_BIN).exists():
        print(f"  [GEMINI] binary not found at {GEMINI_BIN}", file=sys.stderr)
        return None
    try:
        result = subprocess.run(
            [GEMINI_BIN, "--mode", "plan", "-p", prompt],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            # gemini-clean a veces emite warnings a stderr pero rc=0
            print(f"  [GEMINI] exit={result.returncode} stderr={result.stderr[:200]}",
                  file=sys.stderr)
            return None
        return result.stdout
    except subprocess.TimeoutExpired:
        print(f"  [GEMINI] timeout {timeout}s", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  [GEMINI] exception {type(e).__name__}: {e}", file=sys.stderr)
        return None


# ----- Parse -------------------------------------------------------------

def parse_llm_json(raw: str) -> dict | None:
    """Parser robusto: limpia fence, busca primer objeto balanceado."""
    cleaned = (raw or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    depth = 0
    start = None
    for i, ch in enumerate(cleaned):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                candidate = cleaned[start:i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    start = None
    return None


def validate_shape(parsed: dict) -> tuple[bool, str]:
    """Verifica la estructura mínima esperada del JSON. Retorna (ok, reason)."""
    if not isinstance(parsed, dict):
        return False, "no es dict"
    recs = parsed.get("recomendaciones")
    if not isinstance(recs, list) or not recs:
        return False, "falta 'recomendaciones' o vacío"
    if len(recs) < 3 or len(recs) > 8:
        return False, f"recomendaciones={len(recs)} fuera de [3,8]"
    for i, r in enumerate(recs):
        if not isinstance(r, dict):
            return False, f"rec[{i}] no es dict"
        if not r.get("accion_texto") or not isinstance(r["accion_texto"], str):
            return False, f"rec[{i}] sin accion_texto"
        if r.get("tipo") not in ("start", "stop", "continue"):
            return False, f"rec[{i}] tipo inválido: {r.get('tipo')}"
    return True, "ok"


# ----- DB ----------------------------------------------------------------

async def fetch_dirigente_metadata(session, dirigente_id: int) -> dict | None:
    row = (await session.execute(text("""
        SELECT id, full_name, cargo, partido, org_id
        FROM dirigentes WHERE id = :did
    """), {"did": dirigente_id})).first()
    if not row:
        return None
    return {
        "id": row[0],
        "full_name": row[1],
        "cargo": row[2],
        "partido": row[3],
        "org_id": row[4],
    }


async def insert_plan_and_recomendaciones(
    session, *, dirigente_id: int, org_id: int, modelo_ia: str,
    prompt_usado: str, contexto_ctx: dict, parsed: dict,
) -> tuple[int, list[int]]:
    """INSERT en planes_ia (header) + recomendaciones_plan_ia (detail).

    Retorna (plan_id, [rec_ids]).
    """
    now = datetime.now(UTC)
    # planes_ia header
    plan_row = (await session.execute(text("""
        INSERT INTO planes_ia (
            dirigente_id, tipo, contenido, modelo_ia, prompt_usado,
            datos_entrada, generado_por_id, aprobado, created_at, estructura_json
        ) VALUES (
            :did, :tipo, :contenido, :modelo, :prompt,
            :datos, :gen_by, false, :created, :estructura
        ) RETURNING id
    """), {
        "did": dirigente_id,
        "tipo": "CONTENIDO",  # tipo_plan_enum: DIAGNOSTICO/CONSOLIDACION/CRISIS/CONTENIDO
        "contenido": parsed.get("resumen_diagnostico") or "(sin resumen)",
        "modelo": modelo_ia,
        "prompt": prompt_usado,
        "datos": json.dumps(contexto_ctx, ensure_ascii=False, default=str),
        "gen_by": GENERADO_POR_ID,
        "created": now,
        "estructura": json.dumps(parsed, ensure_ascii=False, default=str),
    })).first()
    plan_id = plan_row[0]

    # Mapping plataforma del prompt LLM al enum del response schema
    # (el endpoint /planes/{id}/tareas valida con PlataformaEnum normalizado)
    PLATAFORMA_ENUM_MAP = {
        "IG": "INSTAGRAM", "FB": "FACEBOOK", "X": "TWITTER",
        "TikTok": "TIKTOK", "YouTube": "YOUTUBE", "all": "CROSS",
    }

    rec_ids: list[int] = []
    for orden_idx, rec in enumerate(parsed.get("recomendaciones") or []):
        ventana_dias = int(rec.get("ventana_duracion_dias") or 14)
        plataforma_raw = rec.get("plataforma_destino") or "all"
        plataforma_enum = PLATAFORMA_ENUM_MAP.get(plataforma_raw, "CROSS")
        plataformas_json = (
            json.dumps([plataforma_enum]) if plataforma_enum != "CROSS"
            else json.dumps(["INSTAGRAM", "FACEBOOK", "TWITTER", "TIKTOK", "YOUTUBE"])
        )
        accion = (rec.get("accion_texto") or "").strip()
        crit_exito = rec.get("criterio_exito") or {}

        # Insert recomendaciones_plan_ia (formato canónico Tier 2 / antivanity)
        rec_row = (await session.execute(text("""
            INSERT INTO recomendaciones_plan_ia (
                plan_ia_id, dirigente_id, org_id, tipo, accion_texto,
                ventana_inicio, ventana_fin, ventana_duracion_dias,
                criterio_exito, principio_conductual, evidencia_respaldo,
                estado, plataformas_destino, created_at, updated_at
            ) VALUES (
                :plan_id, :did, :org_id, :tipo, :accion,
                :vi, :vf, :vd,
                :crit, :princ, :evid,
                'propuesta', :plats, :created, :created
            ) RETURNING id
        """), {
            "plan_id": plan_id,
            "did": dirigente_id,
            "org_id": org_id,
            "tipo": rec.get("tipo", "start"),
            "accion": accion[:5000],
            "vi": now,
            "vf": now + timedelta(days=ventana_dias),
            "vd": ventana_dias,
            "crit": json.dumps(crit_exito, ensure_ascii=False),
            "princ": (rec.get("principio_conductual") or "")[:100] or None,
            "evid": json.dumps(rec.get("evidencia_respaldo") or {}, ensure_ascii=False),
            "plats": plataformas_json,
            "created": now,
        })).first()
        rec_ids.append(rec_row[0])

        # Insert paralelo en plan_tareas para que aparezca en /dashboard/planes/[id]
        # (la UI lee plan_tareas, no recomendaciones_plan_ia)
        titulo = accion[:200] if len(accion) <= 200 else accion[:197] + "..."
        await session.execute(text("""
            INSERT INTO plan_tareas (
                plan_id, orden, titulo, descripcion,
                plataforma, metrica_objetivo,
                estado, created_at, updated_at
            ) VALUES (
                :plan_id, :orden, :titulo, :desc,
                :plat, :metr,
                'TODO', :created, :created
            )
        """), {
            "plan_id": plan_id,
            "orden": orden_idx,
            "titulo": titulo,
            "desc": accion,
            "plat": plataforma_enum if plataforma_enum != "CROSS" else None,
            "metr": (crit_exito.get("metrica") or "")[:200] or None,
            "created": now,
        })

    await session.commit()
    return plan_id, rec_ids


# ----- Orchestration -----------------------------------------------------

async def main_async(args: argparse.Namespace) -> int:
    engine = create_async_engine(DB_URL, pool_pre_ping=True)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        meta = await fetch_dirigente_metadata(session, args.dirigente_id)
        if not meta:
            print(f"ERROR: dirigente_id={args.dirigente_id} no existe en BD",
                  file=sys.stderr)
            return 2
        print(f"Dirigente: {meta['full_name']} (id={meta['id']}, "
              f"cargo={meta['cargo']}, org_id={meta['org_id']})")

        print("Construyendo contexto via dirigente_context_builder…")
        ctx = await build_context(session, args.dirigente_id)
        ctx_md = format_context_for_prompt(ctx)
        if not ctx_md.strip():
            print("ERROR: contexto vacío — dirigente sin datos suficientes",
                  file=sys.stderr)
            return 3

        prompt = PROMPT_TEMPLATE.format(ctx_md=ctx_md)
        print(f"Prompt construido: {len(prompt)} chars · "
              f"{len(ctx.get('performance_posts', {}).get('winners') or [])} winners · "
              f"{len(ctx.get('performance_posts', {}).get('losers') or [])} losers")

        if args.dry_run:
            print("\n--- DRY RUN: prompt formateado ---")
            print(prompt)
            print("--- END DRY RUN ---")
            return 0

        # Intento 1: Claude Code
        modelo_usado = None
        raw = None
        if not args.skip_cc:
            print(f"\n[1/2] Claude Code (effort={CC_EFFORT}, timeout={DEFAULT_TIMEOUT_CC}s)…")
            t0 = time.time()
            raw = _call_claude_code(prompt)
            elapsed = time.time() - t0
            print(f"  CC elapsed={elapsed:.1f}s · output_chars={len(raw or '')}")
            if raw:
                modelo_usado = MODEL_VERSION_CC
        else:
            print("\n[1/2] Claude Code SKIPPED (--skip-cc)")

        # Validar shape de CC; si falla, fallback
        parsed = parse_llm_json(raw) if raw else None
        ok, reason = (False, "no raw") if parsed is None else validate_shape(parsed)
        if not ok:
            print(f"  CC parse/validate failed: {reason}")
            print(f"\n[2/2] Fallback Gemini CLI (timeout={DEFAULT_TIMEOUT_GEMINI}s)…")
            t0 = time.time()
            raw = _call_gemini_cli(prompt)
            elapsed = time.time() - t0
            print(f"  Gemini elapsed={elapsed:.1f}s · output_chars={len(raw or '')}")
            if raw:
                parsed = parse_llm_json(raw)
                ok, reason = (False, "no raw") if parsed is None else validate_shape(parsed)
                if ok:
                    modelo_usado = MODEL_VERSION_GEMINI

        if not ok or parsed is None:
            print(f"\nERROR: ambos LLMs fallaron · ultimo reason={reason}",
                  file=sys.stderr)
            tail = (raw or "")[-500:] if raw else "(no raw)"
            print(f"  raw_tail: {tail}", file=sys.stderr)
            return 4

        print(f"\nValidación OK con modelo={modelo_usado} · "
              f"{len(parsed.get('recomendaciones', []))} recomendaciones")

        plan_id, rec_ids = await insert_plan_and_recomendaciones(
            session,
            dirigente_id=args.dirigente_id,
            org_id=meta["org_id"] or 1,
            modelo_ia=modelo_usado,
            prompt_usado=prompt,
            contexto_ctx=ctx,
            parsed=parsed,
        )
        print(f"\nPersistido: planes_ia.id={plan_id} · "
              f"recomendaciones_plan_ia ids={rec_ids}")
        print(f"\n--- Resumen recomendaciones ---")
        for i, rec in enumerate(parsed.get("recomendaciones", []), 1):
            print(f"  {i}. [{rec.get('tipo'):<8}] {(rec.get('accion_texto') or '')[:180]}")

    await engine.dispose()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument("--dirigente-id", type=int, default=3,
                        help="ID del dirigente (default: 3 = Saymi)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Imprime el prompt formateado pero NO llama LLMs ni BD")
    parser.add_argument("--skip-cc", action="store_true",
                        help="Salta Claude Code, va directo a Gemini CLI")
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
