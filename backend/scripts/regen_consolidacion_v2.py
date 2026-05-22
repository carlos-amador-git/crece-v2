"""regen_consolidacion_v2.py · 2026-05-21

Genera Plan ESTRATÉGICO (Consolidación) trimestre con shape de 10 bloques
aprobados por CEO 2026-05-21.

Input: Diagnóstico vigente + overview aceptación + competidores.
Output: estructura_json con shape PlanEstrategia90Dias.

Stack: CC effort=high + fallback gemini-clean.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import psycopg2 as psycopg
import requests

CLAUDE_BIN = "/Users/marxchavez/.local/bin/claude"
GEMINI_BIN = "/Users/marxchavez/.claude/bin/gemini-clean"
CC_EFFORT = os.environ.get("CC_EFFORT", "high")
DEFAULT_TIMEOUT_CC = int(os.environ.get("CC_TIMEOUT", "900"))
MODEL_VERSION = "cc-consolidacion-v2-2026-05-21"

DB_URL = os.environ.get("DATABASE_URL_SYNC", "postgresql://crece:crece_dev@localhost:5438/crece")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8002")


PROMPT_TEMPLATE = """Eres consultor político senior especializado en estrategia digital trimestral.

CONTEXTO DEL DIRIGENTE:
- Nombre: {nombre}
- Cargo: {cargo}
- Partido: {partido}
- Rol: {rol}

DIAGNÓSTICO VIGENTE (síntesis de los 18 indicadores B01-B18):
{diagnostico_md}

KPIs BASELINE actuales:
- IPD: {ipd_score} / 10 ({ipd_bucket})
- Activación: {pct_activacion}% ({comentaristas_unicos} comentaristas / {total_followers} followers)
- Aprobación promedio: {pct_aprobacion}%
- Rechazo promedio: {pct_rechazo}%
- Comments analizados (corpus): {total_comments}

TU TAREA: producir un Plan Estratégico de 90 días (1 trimestre) en JSON con shape exacto:

{{
  "resumen_ejecutivo": "1-2 frases que sintetizan situación + ambición trimestre (max 240 chars)",
  "objetivo_90d": {{
    "narrativa": "1 frase del estado deseado al final del trimestre",
    "kpis_target": [
      {{"metrica": "ej. IPD", "valor_baseline": {ipd_score}, "valor_target": 7.5, "unidad": "/ 10"}}
    ]
  }},
  "narrativa_central": "Mensaje principal del trimestre · 1-2 frases · postura política implícita",
  "pilares": [
    {{
      "titulo": "Nombre corto del pilar (ej. 'Cercanía territorial')",
      "descripcion": "1-2 frases del por qué y el cómo",
      "tacticas": ["tactica 1 concreta", "tactica 2 concreta", "tactica 3 concreta"]
    }}
  ],
  "audiencias_prioritarias": [
    {{"nombre": "Segmento", "rationale": "Por qué priorizar a este segmento ahora", "tactica_clave": "1 acción específica"}}
  ],
  "mitigaciones_debilidades": [
    {{"debilidad_origen": "B0X o B1X del Diagnóstico", "accion_mitigacion": "Acción concreta 14-30 días"}}
  ],
  "roadmap_3_hitos": [
    {{"mes": 1, "hito": "Qué se logra en los primeros 30 días", "kpi_control": "Cómo se mide"}},
    {{"mes": 2, "hito": "Qué se logra en los siguientes 30 días", "kpi_control": "..."}},
    {{"mes": 3, "hito": "Cómo cierra el trimestre", "kpi_control": "..."}}
  ],
  "riesgos": [
    {{"tipo": "compliance|crisis|oposicion|operativo", "descripcion": "...", "mitigacion": "..."}}
  ]
}}

REGLAS DURAS:
- Pilares: EXACTAMENTE 3.
- Audiencias prioritarias: 2-4.
- Mitigaciones: 2-4 (debe referenciar debilidades del diagnóstico).
- Roadmap: EXACTAMENTE 3 hitos (mes 1, 2, 3).
- Riesgos: 2-4.
- Las tacticas y kpis_target deben ser MEDIBLES, no genéricos.
- Si el diagnóstico cita una card (B0X), las mitigaciones DEBEN referenciar esa card.

OUTPUT: ÚNICAMENTE JSON. Sin markdown, sin comentarios."""


def fetch_context(dirigente_id: int, dirigente_email: str) -> dict:
    r = requests.post(
        f"{BACKEND_URL}/api/v1/auth/login",
        data={"username": dirigente_email, "password": "demo2026!"},
        timeout=10,
    )
    r.raise_for_status()
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Overview
    ov = requests.get(f"{BACKEND_URL}/api/v1/aceptacion/overview", headers=headers, timeout=10).json()
    diri = next((d for d in ov.get("dirigentes", []) if d.get("dirigente_id") == dirigente_id), None)

    # Diagnóstico vigente (último plan tipo DIAGNOSTICO)
    planes = requests.get(
        f"{BACKEND_URL}/api/v1/planes/?dirigente_id={dirigente_id}&tipo=DIAGNOSTICO&page=1",
        headers=headers, timeout=10,
    ).json()
    last_diag = (planes.get("items") or [{}])[0]
    diag_estr = last_diag.get("estructura_json") or {}

    # Dirigente metadata
    conn = psycopg.connect(DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT full_name, cargo, partido FROM dirigentes WHERE id = %s",
            (dirigente_id,),
        )
        r = cur.fetchone()
    conn.close()

    return {
        "nombre": r[0] if r else "Dirigente",
        "cargo": r[1] if r else "",
        "partido": r[2] if r else "",
        "rol": diri.get("rol_politico") if diri else "n/a",
        "ipd_score": diag_estr.get("ipd_score", 6.0),
        "ipd_bucket": diag_estr.get("ipd_bucket", "MEDIO"),
        "pct_activacion": round(diri.get("pct_activados", 0), 2) if diri else 0,
        "comentaristas_unicos": diri.get("unique_commenters", 0) if diri else 0,
        "total_followers": diri.get("total_followers", 0) if diri else 0,
        "pct_aprobacion": round(diri.get("pct_aprobacion", 0), 1) if diri else 0,
        "pct_rechazo": round(diri.get("pct_rechazo", 0), 1) if diri else 0,
        "total_comments": diri.get("total_comments", 0) if diri else 0,
        "diagnostico_estr": diag_estr,
    }


def diagnostico_to_md(estr: dict) -> str:
    if not estr:
        return "_(Sin diagnóstico vigente · regenerar primero)_"
    lines = [f"- **Insight**: {estr.get('insight_bala', 'n/a')}"]
    for k in ("fortalezas", "debilidades", "riesgos"):
        items = estr.get(k, [])
        if items:
            lines.append(f"- **{k.capitalize()}**:")
            for it in items[:4]:
                lines.append(f"  - {it.get('card', '?')} {it.get('titulo', '')}: {it.get('evidencia', '')}")
    return "\n".join(lines)


def call_llm(prompt: str) -> tuple[str | None, str]:
    """CC effort=high → fallback gemini. Returns (raw, modelo)."""
    if Path(CLAUDE_BIN).exists():
        try:
            r = subprocess.run(
                [CLAUDE_BIN, "--print", "--effort", CC_EFFORT, prompt],
                capture_output=True, text=True, timeout=DEFAULT_TIMEOUT_CC,
                stdin=subprocess.DEVNULL,
            )
            if r.returncode == 0 and r.stdout:
                return r.stdout, MODEL_VERSION
        except Exception as e:
            print(f"  [CC] {type(e).__name__}: {e}", file=sys.stderr)
    if Path(GEMINI_BIN).exists():
        try:
            r = subprocess.run(
                [GEMINI_BIN, "--mode", "plan", "--prompt", prompt],
                capture_output=True, text=True, timeout=600,
                stdin=subprocess.DEVNULL,
            )
            if r.returncode == 0 and r.stdout:
                return r.stdout, "gemini-cli-fallback-v1"
        except Exception:
            pass
    return None, "none"


def parse_json(raw: str) -> dict | None:
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
                cand = cleaned[start:i + 1]
                try:
                    return json.loads(cand)
                except json.JSONDecodeError:
                    start = None
    return None


def validate(parsed: dict) -> tuple[bool, str]:
    if not isinstance(parsed, dict):
        return False, "no dict"
    required = ["resumen_ejecutivo", "objetivo_90d", "narrativa_central", "pilares", "roadmap_3_hitos"]
    for k in required:
        if k not in parsed:
            return False, f"falta {k}"
    if not isinstance(parsed["pilares"], list) or len(parsed["pilares"]) != 3:
        return False, "pilares debe ser 3"
    if not isinstance(parsed["roadmap_3_hitos"], list) or len(parsed["roadmap_3_hitos"]) != 3:
        return False, "roadmap debe ser 3"
    return True, "ok"


def insert_plan(conn, dirigente_id: int, contenido: str, estr: dict, modelo: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO planes_ia (
                dirigente_id, tipo, contenido, modelo_ia, prompt_usado,
                datos_entrada, generado_por_id, aprobado, created_at, estructura_json
            )
            VALUES (%s, 'CONSOLIDACION', %s, %s, %s, %s, 1, false, NOW(), %s)
            RETURNING id
            """,
            (
                dirigente_id, contenido, modelo, "v2",
                json.dumps({"source": "regen_consolidacion_v2", "ts": datetime.now(UTC).isoformat()}),
                json.dumps(estr, ensure_ascii=False),
            ),
        )
        new_id = cur.fetchone()[0]
    conn.commit()
    return new_id


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dirigente-id", type=int, required=True)
    p.add_argument("--dirigente-email", required=True)
    args = p.parse_args()

    print(f"[1/4] Fetch context dirigente_id={args.dirigente_id}…", flush=True)
    ctx = fetch_context(args.dirigente_id, args.dirigente_email)
    print(f"  IPD={ctx['ipd_score']} · pct_activacion={ctx['pct_activacion']}% · followers={ctx['total_followers']}", flush=True)

    prompt = PROMPT_TEMPLATE.format(
        **{
            k: v for k, v in ctx.items() if k != "diagnostico_estr"
        },
        diagnostico_md=diagnostico_to_md(ctx["diagnostico_estr"]),
    )

    print(f"[2/4] LLM (effort={CC_EFFORT})…", flush=True)
    raw, modelo = call_llm(prompt)
    if not raw:
        print("  Ambos LLMs fallaron", file=sys.stderr)
        return 1

    parsed = parse_json(raw)
    if not parsed:
        print(f"  parse fail · raw[:200]={raw[:200]}", file=sys.stderr)
        return 2
    ok, reason = validate(parsed)
    if not ok:
        print(f"  validate fail: {reason}", file=sys.stderr)
        return 3

    contenido_md = (
        f"# Plan Estratégico 90 días\n\n"
        f"## Resumen ejecutivo\n{parsed['resumen_ejecutivo']}\n\n"
        f"## Objetivo del trimestre\n{parsed['objetivo_90d'].get('narrativa', '')}\n\n"
        f"## Narrativa central\n{parsed['narrativa_central']}\n\n"
        f"## Pilares\n" + "\n".join(f"- **{p['titulo']}**: {p['descripcion']}" for p in parsed["pilares"]) + "\n\n"
        f"## Roadmap\n" + "\n".join(f"- **Mes {h['mes']}**: {h['hito']}" for h in parsed["roadmap_3_hitos"])
    )
    conn = psycopg.connect(DB_URL)
    plan_id = insert_plan(conn, args.dirigente_id, contenido_md, parsed, modelo)
    conn.close()
    print(f"\nDONE · plan_id={plan_id}")
    print(f"\nResumen: {parsed['resumen_ejecutivo']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
