"""migrate_tono_v1_to_v2_saymi.py · 2026-05-25

Migra posts Saymi (dirigente_id=3) de vocab v1 legacy (neutral/positivo/negativo)
a vocab v2 (celebratorio/informativo/propositivo/personal/solidario/critico/
defensivo) usando Claude subprocess.

Conservador con RAM (CEO 2026-05-25):
- batch_size=5 (vs 10 default de extract_topics_saymi_cc)
- CC_EFFORT=low (clasificación categórica simple, no requiere razonamiento)
- pause 2s entre batches
- memory_pressure check cada 20 batches · ABORT si <30% free
- checkpoint commit cada 10 batches (50 posts) por seguridad

Patrón derivado de extract_topics_saymi_cc.py.

Uso:
    backend/.venv/bin/python backend/scripts/migrate_tono_v1_to_v2_saymi.py \\
        --limit 1200 > backend/.context/migrate_tono_$(date +%H%M).log 2>&1
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import psycopg2 as psycopg

CLAUDE_BIN = "/Users/marxchavez/.local/bin/claude"
CC_EFFORT = os.environ.get("CC_EFFORT", "low")
DEFAULT_TIMEOUT_CC = int(os.environ.get("CC_TIMEOUT", "300"))
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "5"))
PAUSE_BETWEEN_BATCHES_S = float(os.environ.get("PAUSE_S", "2.0"))
RAM_CHECK_EVERY_N_BATCHES = 20
RAM_FREE_PCT_MIN = 30
MODEL_VERSION = "tono-migration-v1-to-v2-2026-05-25"

DB_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://crece:crece_dev@localhost:5438/crece",
)

V2_VOCAB = [
    "celebratorio",
    "informativo",
    "propositivo",
    "personal",
    "solidario",
    "critico",
    "defensivo",
]


def check_ram_or_abort() -> None:
    """ABORTar si memoria libre < RAM_FREE_PCT_MIN (default 30%)."""
    try:
        result = subprocess.run(
            ["memory_pressure"], capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if "System-wide memory free percentage" in line:
                m = re.search(r"(\d+)", line)
                if m:
                    free = int(m.group(1))
                    if free < RAM_FREE_PCT_MIN:
                        print(
                            f"ABORT: memory_free {free}% < {RAM_FREE_PCT_MIN}% min",
                            file=sys.stderr,
                            flush=True,
                        )
                        sys.exit(2)
                    print(f"  [RAM] free={free}%", flush=True)
                    return
    except Exception as e:
        print(f"  [RAM check failed: {e}]", file=sys.stderr, flush=True)


def build_prompt(posts: list[dict]) -> str:
    items = "\n".join(
        f'{i+1}. [id={p["id"]}] tono_v1="{p["tono_v1"]}" content="{(p["content"] or "")[:300].replace(chr(34), chr(39))}"'
        for i, p in enumerate(posts)
    )
    vocab_str = ", ".join(V2_VOCAB)
    return f"""Reclasifica el tono de cada post de Saymi Pineda Velasco (Sec. Turismo Oaxaca, MORENA) del vocabulario v1 legacy (neutral/positivo/negativo) al vocabulario v2.

Vocabulario v2 permitido (elige UNO por post): {vocab_str}

Reglas de mapeo:
- celebratorio: felicitaciones, agradecimientos, conmemoraciones, logros
- informativo: anuncios, datos, agenda, comunicación de hechos sin valoración
- propositivo: anuncia/propone iniciativas, proyectos, planes futuros
- personal: experiencias propias, reflexiones, anécdotas, identidad
- solidario: apoyo a víctimas, expresión de empatía, condolencias
- critico: señala problemas, denuncia, expone fallos
- defensivo: aclara, responde a críticas, justifica acciones

Posts:
{items}

Para CADA post devuelve un objeto JSON. Responde con un ARRAY JSON en el MISMO ORDEN.

Cada objeto: {{"id": <int>, "tono_v2": "<uno de v2>"}}

Si dudas, prefiere "informativo". Responde ÚNICAMENTE el array JSON. Sin markdown, sin backticks, sin texto adicional."""


def call_cc(prompt: str, timeout: int = DEFAULT_TIMEOUT_CC) -> str | None:
    if not Path(CLAUDE_BIN).exists():
        print(f"  [CC] binary not found: {CLAUDE_BIN}", file=sys.stderr)
        return None
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
    return None


def call_cc_with_retry(prompt: str) -> str | None:
    for attempt, wait in enumerate([0, 3, 8], 1):
        if wait:
            time.sleep(wait)
        raw = call_cc(prompt)
        if raw:
            return raw
        print(f"  [retry {attempt}] CC failed", file=sys.stderr)
    return None


def parse_array(raw: str) -> list[dict] | None:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else None
    except json.JSONDecodeError:
        return None


def process_batch(conn, batch: list[dict]) -> tuple[int, int]:
    prompt = build_prompt(batch)
    raw = call_cc_with_retry(prompt)
    if not raw:
        return (0, len(batch))
    parsed = parse_array(raw)
    if not parsed:
        print(f"  [parse fail] raw[:200]={raw[:200]}", file=sys.stderr)
        return (0, len(batch))

    ok = 0
    fail = 0
    for i, post in enumerate(batch):
        item = parsed[i] if i < len(parsed) else None
        if not isinstance(item, dict) or item.get("id") != post["id"]:
            fail += 1
            continue
        tono_v2 = item.get("tono_v2")
        if not isinstance(tono_v2, str) or tono_v2.lower().strip() not in V2_VOCAB:
            fail += 1
            continue
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE social_posts SET tono_discurso = %s, nlp_model_version = %s WHERE id = %s",
                (tono_v2.lower().strip(), MODEL_VERSION, post["id"]),
            )
        ok += 1
    return (ok, fail)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=1200)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    print(
        f"Tono migration v1→v2 · limit={args.limit} batch={BATCH_SIZE} "
        f"effort={CC_EFFORT} pause={PAUSE_BETWEEN_BATCHES_S}s ram_min={RAM_FREE_PCT_MIN}% "
        f"dry={args.dry_run}",
        flush=True,
    )

    conn = psycopg.connect(DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT sp.id, sp.content, sp.tono_discurso
            FROM social_posts sp
            JOIN social_profiles spr ON spr.id = sp.profile_id
            WHERE spr.dirigente_id = 3
              AND sp.tono_discurso IN ('neutral', 'positivo', 'negativo')
              AND LENGTH(TRIM(COALESCE(sp.content, ''))) > 10
            ORDER BY sp.published_at DESC
            LIMIT %s
            """,
            (args.limit,),
        )
        rows = [
            {"id": r[0], "content": r[1], "tono_v1": r[2]}
            for r in cur.fetchall()
        ]

    if not rows:
        print("Nada que migrar.")
        return 0

    print(f"Procesando {len(rows)} posts en batches de {BATCH_SIZE}…", flush=True)
    total_ok = total_fail = 0
    t0 = time.monotonic()
    n_batches = 0

    try:
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            n_batches += 1

            if n_batches % RAM_CHECK_EVERY_N_BATCHES == 1:
                check_ram_or_abort()

            if args.dry_run:
                ok, fail = (len(batch), 0)
                print(f"  [dry] batch {n_batches} would process {len(batch)} posts")
            else:
                ok, fail = process_batch(conn, batch)
            total_ok += ok
            total_fail += fail
            elapsed = time.monotonic() - t0
            rate = (total_ok + total_fail) / max(elapsed, 1)
            print(
                f"  batch {n_batches} · ok={ok} fail={fail} · acum ok={total_ok} fail={total_fail} · rate {rate:.2f}/s",
                flush=True,
            )

            # Checkpoint commit cada 10 batches
            if not args.dry_run and n_batches % 10 == 0:
                conn.commit()
                print(f"  [checkpoint] commit at batch {n_batches}", flush=True)

            time.sleep(PAUSE_BETWEEN_BATCHES_S)

        if not args.dry_run:
            conn.commit()
    finally:
        conn.close()

    print(
        f"\nDONE · ok={total_ok} fail={total_fail} elapsed={time.monotonic()-t0:.1f}s",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
