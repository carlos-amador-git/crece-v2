"""extract_topics_saymi_cc.py · 2026-05-21

Topic extraction via CC subprocess para posts Saymi FB con texto.
Adaptado de backfill_nlp_saymi.py · patrón idéntico, prompt distinto.

Desbloquea B08 SoV (Share of Voice) que está en insufficient_data por
social_posts.topics_extracted vacío (98.8% NULL).

Stack: claude --print --effort medium (más rápido que high · clasificación
es menos crítica que comments NLP). Batch de 10 posts por llamada.

Uso (HOST · claude CLI vive en /Users/marxchavez/.local/bin/claude):
    python3 backend/scripts/extract_topics_saymi_cc.py --limit 50  # smoke
    nohup python3 backend/scripts/extract_topics_saymi_cc.py --limit 500 \\
        > backend/.context/topic_extract_$(date +%Y%m%d_%H%M).log 2>&1 &
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

CLAUDE_BIN = "/Users/marxchavez/.local/bin/claude"
CC_EFFORT = os.environ.get("CC_EFFORT", "medium")
DEFAULT_TIMEOUT_CC = int(os.environ.get("CC_TIMEOUT", "600"))
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "10"))
MODEL_VERSION = "cc-topics-v1-2026-05-21"

DB_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://crece:crece_dev@localhost:5438/crece",
)


def build_prompt(posts: list[dict], dirigente_desc: str) -> str:
    items = "\n".join(
        f'{i+1}. [id={p["id"]}] "{(p["content"] or "")[:500].replace(chr(34), chr(39))}"'
        for i, p in enumerate(posts)
    )
    return f"""Eres un analista político mexicano. Extrae los temas centrales de cada post de {dirigente_desc}.

Posts:
{items}

Para CADA post devuelve un objeto JSON. Responde con un ARRAY JSON en el MISMO ORDEN.

Cada objeto debe tener:
- "id": entero (id del post)
- "topics": array de 1-4 strings (temas centrales del post, en español, lowercase, sin puntuación). Ejemplos válidos: "turismo oaxaca", "gestion publica", "mundial 2026", "tianguis turistico", "alebrijes ixcotel", "dia del nino", "infraestructura turistica", "promocion cultural", "cooperacion internacional", "deporte juvenil", "felicitacion politica", "evento institucional"
- "tematica_principal": string · el tema MÁS dominante del post (puede repetirse en topics o no)

Reglas:
- Sé específico: prefiere "tianguis turistico 2026" sobre solo "turismo".
- Si el post es felicitación a persona, usa "felicitacion <rol>" (ej "felicitacion politico", "felicitacion deportista").
- Si el post es promoción de evento, usa "promocion <evento>".
- Si NO puedes identificar tema (post muy corto, solo emojis, fragmento incompleto), usa topics=["sin_tema_claro"] y tematica_principal="sin_tema_claro".

Responde ÚNICAMENTE el array JSON. Sin texto adicional, sin markdown, sin backticks."""


def call_cc(prompt: str, timeout: int = DEFAULT_TIMEOUT_CC) -> str | None:
    # 1. Claude
    if Path(CLAUDE_BIN).exists():
        try:
            result = subprocess.run(
                [CLAUDE_BIN, "--print", "--effort", CC_EFFORT, prompt],
                capture_output=True, text=True, timeout=timeout,
                stdin=subprocess.DEVNULL,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout
        except subprocess.TimeoutExpired:
            print(f"  [CC] timeout {timeout}s", file=sys.stderr)

    # 2. Gemini fallback
    GEMINI_CMD = "/opt/homebrew/bin/gemini"
    if Path(GEMINI_CMD).exists():
        try:
            result = subprocess.run(
                [GEMINI_CMD, "--sandbox", "--approval-mode", "plan", "-p", prompt],
                capture_output=True, text=True, timeout=180,
                stdin=subprocess.DEVNULL,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout
        except subprocess.TimeoutExpired:
            print("  [Gemini] timeout", file=sys.stderr)

    return None


def call_cc_with_retry(prompt: str) -> str | None:
    backoff = [2, 5, 15]
    for attempt, wait in enumerate([0] + backoff, 1):
        if wait:
            time.sleep(wait)
        raw = call_cc(prompt)
        if raw:
            return raw
        print(f"  [retry {attempt}] CC failed, waiting…", file=sys.stderr)
    return None


def parse_array_response(raw: str) -> list[dict] | None:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else None
    except json.JSONDecodeError:
        return None


def validate_item(item: dict, expected_id: int) -> dict | None:
    if not isinstance(item, dict):
        return None
    if item.get("id") != expected_id:
        return None
    topics = item.get("topics")
    tematica = item.get("tematica_principal")
    if not isinstance(topics, list) or not topics:
        return None
    if not isinstance(tematica, str):
        return None
    # normalize
    topics_norm = [t.lower().strip() for t in topics if isinstance(t, str) and t.strip()]
    if not topics_norm:
        return None
    return {
        "id": expected_id,
        "topics": topics_norm[:4],
        "tematica_principal": tematica.lower().strip(),
    }


def process_batch(conn, batch: list[dict], dry_run: bool, dirigente_desc: str) -> tuple[int, int]:
    prompt = build_prompt(batch, dirigente_desc)
    raw = call_cc_with_retry(prompt)
    if not raw:
        return (0, len(batch))
    parsed = parse_array_response(raw)
    if not parsed:
        print(f"  [parse] not array · raw[:200]={raw[:200]}", file=sys.stderr)
        return (0, len(batch))

    ok = 0
    fail = 0
    extracted_at = datetime.now(UTC).isoformat()
    for i, post in enumerate(batch):
        item = parsed[i] if i < len(parsed) else None
        if not item:
            fail += 1
            continue
        validated = validate_item(item, post["id"])
        if not validated:
            fail += 1
            continue
        jsonb_value = {
            "topics": validated["topics"],
            "tematica_principal": validated["tematica_principal"],
            "extracted_at": extracted_at,
            "model_version": MODEL_VERSION,
        }
        if not dry_run:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE social_posts SET topics_extracted = %s WHERE id = %s",
                    (json.dumps(jsonb_value), post["id"]),
                )
        ok += 1
    if not dry_run:
        conn.commit()
    return (ok, fail)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--dirigente-id", type=int, default=3)
    args = p.parse_args()

    print(
        f"Sprint topic extract · dirigente={args.dirigente_id} limit={args.limit} batch={BATCH_SIZE} effort={CC_EFFORT} dry={args.dry_run}",
        flush=True,
    )

    conn = psycopg.connect(DB_URL)
    # Identidad del dirigente para el prompt (genérico, no hardcode Saymi)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT full_name, cargo, partido FROM dirigentes WHERE id = %s",
            (args.dirigente_id,),
        )
        drow = cur.fetchone()
    if not drow:
        print(f"dirigente {args.dirigente_id} no existe", file=sys.stderr)
        return 1
    _nombre, _cargo, _partido = drow
    dirigente_desc = _nombre + (f" ({_cargo}" if _cargo else "")
    if _partido:
        dirigente_desc += f", {_partido}" if _cargo else f" ({_partido}"
    if _cargo or _partido:
        dirigente_desc += ")"
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT sp.id, sp.content
            FROM social_posts sp
            JOIN social_profiles sps ON sps.id = sp.profile_id
            WHERE sps.dirigente_id = %s
              AND LENGTH(TRIM(COALESCE(sp.content, ''))) > 10
              AND sp.topics_extracted IS NULL
            ORDER BY sp.published_at DESC
            LIMIT %s
            """,
            (args.dirigente_id, args.limit),
        )
        rows = [{"id": r[0], "content": r[1]} for r in cur.fetchall()]

    if not rows:
        print("Nada que procesar.")
        return 0

    print(f"Procesando {len(rows)} posts en batches de {BATCH_SIZE}…", flush=True)
    total_ok = 0
    total_fail = 0
    t0 = time.monotonic()
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        ok, fail = process_batch(conn, batch, args.dry_run, dirigente_desc)
        total_ok += ok
        total_fail += fail
        elapsed = time.monotonic() - t0
        rate = (total_ok + total_fail) / max(elapsed, 1)
        print(
            f"  batch {i // BATCH_SIZE + 1} · ok={ok} fail={fail} · acum ok={total_ok} fail={total_fail} · rate {rate:.2f}/s",
            flush=True,
        )

    conn.close()
    print(f"\nDONE · ok={total_ok} fail={total_fail} elapsed={time.monotonic()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
