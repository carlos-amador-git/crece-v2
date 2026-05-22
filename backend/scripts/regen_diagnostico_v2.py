"""regen_diagnostico_v2.py · 2026-05-21

Genera Plan Diagnóstico que sintetiza los 18 cards B01-B18 reales (Tier 1 + Tier 2)
en lugar de inventar dimensiones.

Refactor 2026-05-21 (D-DIAGNOSTICO-V2-B01B18) · CEO aprobó concepto · LLM
sintetiza datos REALES ya calculados por los servicios diagnóstico.

Stack: CC subprocess effort=high + fallback gemini-clean.

Output JSON shape (guardado en planes_ia.estructura_json):
{
  "ipd_score": 6.0,
  "ipd_bucket": "MEDIO",
  "delta_vs_anterior": null,
  "insight_bala": "...",
  "fortalezas": [{"card": "B05", "titulo": "...", "evidencia": "..."}],
  "debilidades": [...],
  "riesgos": [...],
  "acciones_top3": [{"orden": 1, "texto": "...", "card_origen": "B10", "cta_label": "...", "cta_href": "..."}]
}

Uso (HOST):
    python3 backend/scripts/regen_diagnostico_v2.py --dirigente-id 3
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
DEFAULT_TIMEOUT_GEMINI = int(os.environ.get("GEMINI_TIMEOUT", "600"))
MODEL_VERSION = "cc-diagnostico-v2-2026-05-21"

DB_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://crece:crece_dev@localhost:5438/crece",
)
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8002")

PROMPT_TEMPLATE = """Eres analista político senior especializado en presencia digital política mexicana.

CONTEXTO DEL DIRIGENTE: {nombre} · {cargo} · partido {partido} · rol {rol}.

IMPORTANTE: este diagnóstico es EXCLUSIVAMENTE sobre {nombre}. NO menciones otros dirigentes en el insight ni en fortalezas/debilidades/riesgos. Usa SIEMPRE el nombre "{nombre}" (o "tu/tus" referido a {nombre}) cuando narres.

DATOS REALES (computados ahora mismo desde la BD):

# Tier 1 · Recepción y Tono (B01-B10)
{tier1_md}

# Tier 2 · Autenticidad, Narrativa y Riesgo (B11-B18)
{tier2_md}

# IPD Score actual: {ipd_score} / 10 · bucket: {ipd_bucket}

TU TAREA: producir un Diagnóstico Estratégico en JSON con la estructura EXACTA:

{{
  "ipd_score": {ipd_score},
  "ipd_bucket": "{ipd_bucket}",
  "delta_vs_anterior": null,
  "insight_bala": "1 frase narrativa que sintetiza el diagnóstico completo. Debe ser MEMORABLE, accionable, no genérica. Ej: 'Tu volumen es alto (B01 sobresaliente) y la audiencia te aprueba 655x a 1 (B05), pero la coordinación artificial (B12) y la veda activa (B17) son los riesgos del trimestre.'",
  "fortalezas": [
    {{"card": "B0X", "titulo": "Nombre corto", "evidencia": "Dato concreto del contexto que la respalda"}}
  ],
  "debilidades": [
    {{"card": "B0X", "titulo": "Nombre corto", "evidencia": "Dato concreto"}}
  ],
  "oportunidades": [
    {{"card": "B1X o contextual", "titulo": "Nombre corto", "evidencia": "Factor EXTERNO que el dirigente puede aprovechar (ej. efeméride próxima, vacío de oposición en tema, tendencia favorable detectada)"}}
  ],
  "amenazas": [
    {{"card": "B1X", "titulo": "Nombre corto", "evidencia": "Factor EXTERNO de riesgo (ej. veda activa B17, violencia política B18, crisis B06, coordinación artificial detectada B12)"}}
  ],
  "acciones_top3": [
    {{
      "orden": 1,
      "texto": "Acción concreta y ejecutable en 14-30 días (1-2 oraciones)",
      "card_origen": "B0X o B1X que motiva la acción",
      "cta_label": "Texto corto del botón (ej. 'Ver comentarios', 'Configurar IG', 'Generar plan')",
      "cta_href": "URL relativa CRECE (ej. '/dashboard/hub?tab=comentarios', '/dashboard/sistema/onboarding')"
    }}
  ]
}}

REGLAS DURAS:
- 2-4 fortalezas (INTERNA positiva). 2-4 debilidades (INTERNA negativa). 1-3 oportunidades (EXTERNA positiva). 1-3 amenazas (EXTERNA negativa). EXACTAMENTE 3 acciones.
- Diferencia INTERNA vs EXTERNA: Fortalezas/Debilidades son sobre el dirigente y su contenido. Oportunidades/Amenazas son del CONTEXTO (calendario electoral, efemérides, oposición, regulación, audiencia). NO mezcles.
- Cada item DEBE citar la card de origen (B01..B18). NUNCA inventes una card.
- Insight_bala MÁXIMO 240 caracteres. Narrativa, no listado.
- Acciones: PROHIBIDO genéricos ("aumentar engagement", "publicar más"). Cada acción debe ser específica + citar evidencia del contexto.
- CTAs deben ir a rutas que existen en CRECE: /dashboard/hub, /dashboard/aceptacion/fans-y-perfiles, /dashboard/diagnostico, /dashboard/social/clima, /dashboard/sistema/metodologia, /dashboard/sistema/onboarding, /dashboard/recomendaciones.

OUTPUT: ÚNICAMENTE el objeto JSON. Sin markdown, sin comentarios, sin texto adicional."""


def fetch_dirigente_meta(dirigente_id: int) -> dict:
    """Lee nombre/cargo/partido directo de BD para parametrizar prompt."""
    import psycopg2 as psycopg
    conn = psycopg.connect(DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT full_name, cargo, partido FROM dirigentes WHERE id = %s",
            (dirigente_id,),
        )
        r = cur.fetchone()
    conn.close()
    if not r:
        return {"nombre": f"Dirigente #{dirigente_id}", "cargo": "n/a", "partido": "n/a"}
    return {"nombre": r[0] or f"Dirigente #{dirigente_id}", "cargo": r[1] or "n/a", "partido": r[2] or "n/a"}


def fetch_diagnostico(dirigente_id: int, dirigente_email: str = "pineda@crece.mx") -> tuple[dict, dict, float, str]:
    """Llama /diagnostico/{id} y /diagnostico_tier2/{id} y retorna (tier1, tier2, ipd, bucket).

    Auth via login del propio dirigente (viewer · solo ve su data).
    """
    # Login
    r = requests.post(
        f"{BACKEND_URL}/api/v1/auth/login",
        data={"username": dirigente_email, "password": "demo2026!"},
        timeout=10,
    )
    r.raise_for_status()
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    t1 = requests.get(f"{BACKEND_URL}/api/v1/diagnostico/{dirigente_id}", headers=headers, timeout=30).json()
    t2 = requests.get(f"{BACKEND_URL}/api/v1/diagnostico_tier2/{dirigente_id}", headers=headers, timeout=30).json()

    # IPD: viene del overview de aceptación (calculate_ipd ya lo tiene)
    ov = requests.get(f"{BACKEND_URL}/api/v1/aceptacion/overview", headers=headers, timeout=10).json()
    diri = next((d for d in ov.get("dirigentes", []) if d.get("dirigente_id") == dirigente_id), None)
    rol = (diri.get("rol_politico") if diri else None) or "n/a"
    # Adjuntar rol al return (sin romper tuple existente)
    fetch_diagnostico._last_rol = rol  # type: ignore[attr-defined]
    # placeholder IPD: si no hay, usar bucket por pct_aprobacion como aproximación
    ipd = 6.0
    if diri:
        # IPD aproximado del bucket aprobación/rechazo
        apr = diri.get("pct_aprobacion") or 0
        ipd = round(min(10.0, max(0.0, apr / 10 + 2.0)), 1)
    bucket = "ALTO" if ipd >= 7 else "MEDIO" if ipd >= 4 else "BAJO"

    return t1, t2, ipd, bucket


def bloques_to_md(bloques: dict) -> str:
    lines = []
    for key, b in (bloques or {}).items():
        status = b.get("status", "n/a")
        if status == "insufficient_data":
            lines.append(f"- **{key}**: insufficient_data (no procesar)")
            continue
        # extraer datos clave (varía por bloque)
        relevant = {k: v for k, v in b.items() if k not in ("status", "computed_at", "config") and not isinstance(v, dict) and v is not None}
        if relevant:
            data_str = ", ".join(f"{k}={v}" for k, v in list(relevant.items())[:6])
            lines.append(f"- **{key}**: {data_str}")
        else:
            sub = {k: v for k, v in b.items() if isinstance(v, dict)}
            if sub:
                lines.append(f"- **{key}**: {json.dumps(sub, default=str, ensure_ascii=False)[:300]}")
    return "\n".join(lines)


def call_cc(prompt: str, timeout: int = DEFAULT_TIMEOUT_CC) -> str | None:
    if not Path(CLAUDE_BIN).exists():
        print(f"  [CC] binary not found", file=sys.stderr)
        return None
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "--print", "--effort", CC_EFFORT, prompt],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            print(f"  [CC] stderr: {result.stderr[:200]}", file=sys.stderr)
            return None
        return result.stdout
    except Exception as e:
        print(f"  [CC] {type(e).__name__}: {e}", file=sys.stderr)
        return None


def call_gemini(prompt: str, timeout: int = DEFAULT_TIMEOUT_GEMINI) -> str | None:
    if not Path(GEMINI_BIN).exists():
        return None
    try:
        result = subprocess.run(
            [GEMINI_BIN, "--mode", "plan", "-p", prompt],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            return None
        return result.stdout
    except Exception:
        return None


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
    required = ["ipd_score", "ipd_bucket", "insight_bala", "fortalezas", "debilidades", "oportunidades", "amenazas", "acciones_top3"]
    for k in required:
        if k not in parsed:
            return False, f"falta {k}"
    if not isinstance(parsed["insight_bala"], str) or len(parsed["insight_bala"]) > 280:
        return False, "insight_bala inválido"
    if not isinstance(parsed["acciones_top3"], list) or len(parsed["acciones_top3"]) != 3:
        return False, "acciones_top3 debe ser exactly 3"
    # FODA back-compat: el frontend viejo lee 'riesgos' · agregamos alias.
    if "riesgos" not in parsed:
        parsed["riesgos"] = parsed["amenazas"]
    return True, "ok"


def insert_plan(conn, dirigente_id: int, contenido: str, estructura: dict, prompt_hash: str, modelo: str):
    titulo = f"Diagnóstico · {datetime.now(UTC).date().isoformat()}"
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO planes_ia (
                dirigente_id, tipo, contenido, modelo_ia, prompt_usado,
                datos_entrada, generado_por_id, aprobado, created_at, estructura_json
            )
            VALUES (%s, 'DIAGNOSTICO', %s, %s, %s, %s, 1, false, NOW(), %s)
            RETURNING id
            """,
            (
                dirigente_id,
                contenido,
                modelo,
                prompt_hash,
                json.dumps({"source": "regen_diagnostico_v2", "ts": datetime.now(UTC).isoformat()}),
                json.dumps(estructura, ensure_ascii=False),
            ),
        )
        new_id = cur.fetchone()[0]
    conn.commit()
    return new_id


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dirigente-id", type=int, required=True)
    p.add_argument("--dirigente-email", default="pineda@crece.mx")
    args = p.parse_args()

    print(f"[1/4] Fetch B01-B18 dirigente_id={args.dirigente_id}…", flush=True)
    t0 = time.monotonic()
    t1, t2, ipd, bucket = fetch_diagnostico(args.dirigente_id, args.dirigente_email)
    print(f"  Tier 1: {t1.get('resumen')}", flush=True)
    print(f"  Tier 2: {t2.get('resumen')}", flush=True)
    print(f"  IPD: {ipd} ({bucket})", flush=True)

    tier1_md = bloques_to_md(t1.get("bloques", {}))
    tier2_md = bloques_to_md(t2.get("bloques", {}))
    # D-DIAGNOSTICO-V2-FIX-2026-05-21 · prompt parametrizado por dirigente real.
    meta = fetch_dirigente_meta(args.dirigente_id)
    rol = getattr(fetch_diagnostico, "_last_rol", "n/a")
    prompt = PROMPT_TEMPLATE.format(
        tier1_md=tier1_md, tier2_md=tier2_md, ipd_score=ipd, ipd_bucket=bucket,
        nombre=meta["nombre"], cargo=meta["cargo"], partido=meta["partido"], rol=rol,
    )

    print(f"[2/4] LLM (effort={CC_EFFORT})…", flush=True)
    raw = call_cc(prompt)
    modelo = MODEL_VERSION
    if not raw:
        print("  [CC] fail · fallback gemini", flush=True)
        raw = call_gemini(prompt)
        modelo = "gemini-cli-fallback-v1"
    if not raw:
        print("  Ambos LLMs fallaron · ABORT", file=sys.stderr)
        return 1

    print(f"[3/4] Parse + validate…", flush=True)
    parsed = parse_json(raw)
    if not parsed:
        print(f"  parse fail · raw[:200]={raw[:200]}", file=sys.stderr)
        return 2
    ok, reason = validate(parsed)
    if not ok:
        print(f"  validate fail: {reason}", file=sys.stderr)
        print(f"  raw[:500]={raw[:500]}", file=sys.stderr)
        return 3

    print(f"[4/4] Insert plan…", flush=True)
    conn = psycopg.connect(DB_URL)
    contenido_md = (
        f"# Diagnóstico Estratégico\n\n"
        f"**IPD:** {parsed['ipd_score']} / 10 · {parsed['ipd_bucket']}\n\n"
        f"## Insight\n{parsed['insight_bala']}\n\n"
        f"## Fortalezas\n" + "\n".join(f"- **{f['card']}** {f['titulo']}: {f['evidencia']}" for f in parsed["fortalezas"]) + "\n\n"
        f"## Debilidades\n" + "\n".join(f"- **{d['card']}** {d['titulo']}: {d['evidencia']}" for d in parsed["debilidades"]) + "\n\n"
        f"## Riesgos\n" + "\n".join(f"- **{r['card']}** {r['titulo']}: {r['evidencia']}" for r in parsed["riesgos"]) + "\n\n"
        f"## Acciones prioritarias\n" + "\n".join(
            f"{a['orden']}. {a['texto']} · ({a['card_origen']}) [{a['cta_label']}]({a['cta_href']})"
            for a in parsed["acciones_top3"]
        )
    )
    plan_id = insert_plan(conn, args.dirigente_id, contenido_md, parsed, "v2", modelo)
    conn.close()

    elapsed = time.monotonic() - t0
    print(f"\nDONE · plan_id={plan_id} · elapsed={elapsed:.1f}s")
    print(f"\nInsight Bala: {parsed['insight_bala']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
