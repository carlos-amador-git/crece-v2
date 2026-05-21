"""regen_contenido_v2.py · 2026-05-21

Genera Plan de Contenido (Calendario Editorial) con shape de 10 bloques
aprobados por CEO 2026-05-21. Ventana default 4 semanas.

Input: posts top historicos + efemérides próximas + diagnóstico vigente.
Output: estructura_json con ventana, cadencia, pilares, posts sugeridos.

Stack: CC effort=high + fallback gemini-clean.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg2 as psycopg
import requests

CLAUDE_BIN = "/Users/marxchavez/.local/bin/claude"
GEMINI_BIN = "/Users/marxchavez/.claude/bin/gemini-clean"
CC_EFFORT = os.environ.get("CC_EFFORT", "high")
DEFAULT_TIMEOUT_CC = int(os.environ.get("CC_TIMEOUT", "900"))
MODEL_VERSION = "cc-contenido-v2-2026-05-21"

DB_URL = os.environ.get("DATABASE_URL_SYNC", "postgresql://crece:crece_dev@localhost:5438/crece")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8002")


PROMPT_TEMPLATE = """Eres community manager senior de campañas políticas mexicanas.

CONTEXTO DEL DIRIGENTE:
- Nombre: {nombre}
- Cargo: {cargo}
- Partido: {partido}

DIAGNÓSTICO VIGENTE:
{diagnostico_md}

POSTS TOP RECIENTES (referencia de qué funciona):
{top_posts_md}

EFEMÉRIDES PRÓXIMAS (próximas 4 semanas {ventana_inicio} → {ventana_fin}):
{efemerides_md}

CADENCIA HISTÓRICA (últimos 30d):
{cadencia_md}

TU TAREA: producir un Calendario Editorial de 4 semanas en JSON con shape exacto:

{{
  "ventana": {{"inicio": "{ventana_inicio}", "fin": "{ventana_fin}", "semanas": 4}},
  "cadencia_recomendada": {{
    "facebook": "Ej: 3-5 posts/dia",
    "instagram": "Ej: 1-2 posts/dia",
    "twitter": "Ej: 5-8 posts/dia",
    "tiktok": "Ej: 3-4 videos/sem",
    "youtube": "Ej: 1 video/sem"
  }},
  "pilares_editoriales": [
    {{"titulo": "Nombre corto pilar", "descripcion": "1 frase del enfoque", "frecuencia_semanal_pct": 30}}
  ],
  "posts_sugeridos": [
    {{
      "fecha_sugerida": "YYYY-MM-DD",
      "hora_optima": "HH:MM",
      "plataforma": "facebook|instagram|twitter|tiktok|youtube",
      "tipo": "foto|video|carrusel|reel|texto|live",
      "pilar": "Título del pilar al que pertenece",
      "copy": "Texto completo del post (max 280 chars facebook, hilo o caption para otros)",
      "hashtags": ["#OaxacaTurismo", "#PAZ"],
      "tono": "celebratorio|informativo|propositivo|institucional|cercano",
      "rationale": "Por qué este post este día (efeméride, evento, debilidad a atacar)",
      "cta_label": "Texto botón si aplica · ej 'Agendar' · 'Crear Reel' · 'Programar'"
    }}
  ],
  "veda_warnings": [
    {{"fecha_inicio": "YYYY-MM-DD", "fecha_fin": "YYYY-MM-DD", "descripcion": "Veda electoral · qué se permite y qué no"}}
  ]
}}

REGLAS DURAS:
- Pilares editoriales: 3-4 (la suma de frecuencia_semanal_pct = 100).
- Posts sugeridos: 8-12 (no más · es muestra representativa · no inundar).
- Cada post sugerido DEBE tener fecha dentro de la ventana.
- Hora_optima debe respaldarse en la cadencia histórica si está disponible.
- Si hay efemérides relevantes, AL MENOS 2 posts sugeridos deben aprovecharlas.
- veda_warnings: 0-2 según si la ventana cae en periodo de veda activa.
- CTAs útiles: "Agendar a calendario" para posts normales · "Crear Reel" para reels · "Programar" para video largo · "Editar borrador" si es un copy de partida.

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

    # Diagnóstico vigente
    planes = requests.get(
        f"{BACKEND_URL}/api/v1/planes/?dirigente_id={dirigente_id}&tipo=DIAGNOSTICO&page=1",
        headers=headers, timeout=10,
    ).json()
    last_diag = (planes.get("items") or [{}])[0]
    diag_estr = last_diag.get("estructura_json") or {}

    # Dirigente meta + cadencia + top posts via SQL directo
    conn = psycopg.connect(DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT full_name, cargo, partido FROM dirigentes WHERE id = %s", (dirigente_id,)
        )
        r = cur.fetchone()
        nombre = r[0] if r else "Dirigente"
        cargo = r[1] if r else ""
        partido = r[2] if r else ""

        # Top 5 posts por engagement reciente (últimos 30d)
        cur.execute(
            """
            SELECT sp.platform_post_id, sps.platform, LEFT(sp.content, 120),
                   sp.likes, sp.comments, sp.published_at
            FROM social_posts sp
            JOIN social_profiles sps ON sps.id = sp.profile_id
            WHERE sps.dirigente_id = %s
              AND sp.published_at >= NOW() - INTERVAL '30 days'
              AND LENGTH(TRIM(COALESCE(sp.content, ''))) > 10
            ORDER BY (sp.likes + sp.comments * 3 + sp.shares * 5) DESC NULLS LAST
            LIMIT 5
            """,
            (dirigente_id,),
        )
        top_posts = cur.fetchall()

        # Cadencia 30d por plataforma
        cur.execute(
            """
            SELECT sps.platform, COUNT(*) AS n_posts,
                   ROUND(COUNT(*)::numeric / 30, 2) AS por_dia
            FROM social_posts sp
            JOIN social_profiles sps ON sps.id = sp.profile_id
            WHERE sps.dirigente_id = %s
              AND sp.published_at >= NOW() - INTERVAL '30 days'
            GROUP BY sps.platform
            ORDER BY n_posts DESC
            """,
            (dirigente_id,),
        )
        cadencia = cur.fetchall()

        # Efemérides próximas 28 días (cruza mes/día con CURRENT_DATE)
        cur.execute(
            """
            WITH d AS (SELECT generate_series(CURRENT_DATE, CURRENT_DATE + INTERVAL '28 days', '1 day') AS day),
                 e AS (
                   SELECT d.day, e.titulo, e.viralidad, e.tipo
                   FROM d
                   JOIN efemerides e
                     ON EXTRACT(MONTH FROM d.day) = e.mes
                    AND EXTRACT(DAY FROM d.day) = e.dia
                   WHERE e.is_active = true
                 )
            SELECT titulo, day, viralidad, tipo FROM e ORDER BY day ASC LIMIT 10
            """
        )
        efs = cur.fetchall()
    conn.close()

    return {
        "nombre": nombre, "cargo": cargo, "partido": partido,
        "diag_estr": diag_estr,
        "top_posts": top_posts, "cadencia": cadencia, "efs": efs,
    }


def diagnostico_to_md(estr: dict) -> str:
    if not estr:
        return "_(Sin diagnóstico vigente)_"
    return f"- **Insight**: {estr.get('insight_bala', 'n/a')}"


def top_posts_md(top: list) -> str:
    if not top:
        return "_(Sin posts recientes con texto)_"
    lines = []
    for pid, plat, content, likes, comments, pub in top:
        lines.append(f"- **{plat}** ({pub.date() if pub else '?'}) · likes={likes} comments={comments}\n  «{content[:100]}»")
    return "\n".join(lines)


def cadencia_to_md(cad: list) -> str:
    if not cad:
        return "_(Sin actividad reciente)_"
    return "\n".join(f"- **{p[0]}**: {p[1]} posts/30d ({p[2]} posts/día)" for p in cad)


def efs_to_md(efs: list) -> str:
    if not efs:
        return "_(Sin efemérides relevantes próximas)_"
    return "\n".join(f"- {e[1]} · **{e[0]}** · viralidad={e[2]} · {e[3]}" for e in efs)


def call_llm(prompt: str) -> tuple[str | None, str]:
    if Path(CLAUDE_BIN).exists():
        try:
            r = subprocess.run(
                [CLAUDE_BIN, "--print", "--effort", CC_EFFORT, prompt],
                capture_output=True, text=True, timeout=DEFAULT_TIMEOUT_CC,
            )
            if r.returncode == 0 and r.stdout:
                return r.stdout, MODEL_VERSION
        except Exception as e:
            print(f"  [CC] {type(e).__name__}: {e}", file=sys.stderr)
    if Path(GEMINI_BIN).exists():
        try:
            r = subprocess.run(
                [GEMINI_BIN, "--mode", "plan", "-p", prompt],
                capture_output=True, text=True, timeout=600,
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
    required = ["ventana", "cadencia_recomendada", "pilares_editoriales", "posts_sugeridos"]
    for k in required:
        if k not in parsed:
            return False, f"falta {k}"
    if not isinstance(parsed["pilares_editoriales"], list) or len(parsed["pilares_editoriales"]) < 2:
        return False, "pilares deben ser 2-4"
    if not isinstance(parsed["posts_sugeridos"], list) or len(parsed["posts_sugeridos"]) < 4:
        return False, "posts_sugeridos minimo 4"
    return True, "ok"


def insert_plan(conn, dirigente_id: int, contenido: str, estr: dict, modelo: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO planes_ia (
                dirigente_id, tipo, contenido, modelo_ia, prompt_usado,
                datos_entrada, generado_por_id, aprobado, created_at, estructura_json
            )
            VALUES (%s, 'CONTENIDO', %s, %s, %s, %s, 1, false, NOW(), %s)
            RETURNING id
            """,
            (
                dirigente_id, contenido, modelo, "v2",
                json.dumps({"source": "regen_contenido_v2", "ts": datetime.now(UTC).isoformat()}),
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
    ventana_inicio = datetime.now().date().isoformat()
    ventana_fin = (datetime.now().date() + timedelta(days=28)).isoformat()
    print(f"  top_posts={len(ctx['top_posts'])} cadencia={len(ctx['cadencia'])} efs={len(ctx['efs'])}", flush=True)

    prompt = PROMPT_TEMPLATE.format(
        nombre=ctx["nombre"], cargo=ctx["cargo"], partido=ctx["partido"],
        diagnostico_md=diagnostico_to_md(ctx["diag_estr"]),
        top_posts_md=top_posts_md(ctx["top_posts"]),
        efemerides_md=efs_to_md(ctx["efs"]),
        cadencia_md=cadencia_to_md(ctx["cadencia"]),
        ventana_inicio=ventana_inicio, ventana_fin=ventana_fin,
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
        f"# Calendario Editorial · {ventana_inicio} → {ventana_fin}\n\n"
        f"## Cadencia recomendada\n"
        + "\n".join(f"- **{k}**: {v}" for k, v in parsed["cadencia_recomendada"].items())
        + "\n\n## Pilares editoriales\n"
        + "\n".join(f"- **{p['titulo']}** ({p.get('frecuencia_semanal_pct', 0)}%): {p.get('descripcion', '')}" for p in parsed["pilares_editoriales"])
        + f"\n\n## {len(parsed['posts_sugeridos'])} posts sugeridos"
    )
    conn = psycopg.connect(DB_URL)
    plan_id = insert_plan(conn, args.dirigente_id, contenido_md, parsed, modelo)
    conn.close()
    print(f"\nDONE · plan_id={plan_id}")
    print(f"  posts_sugeridos: {len(parsed['posts_sugeridos'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
