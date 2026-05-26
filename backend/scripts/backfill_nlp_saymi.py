"""backfill_nlp_saymi.py — Sprint D PLAN-2026-05-17-fans-dashboard.md

Clasifica los comments de Saymi (dirigente_id=3) que NO tienen `nlp_tono`.

Stack: subprocess `claude` (Claude Code CLI) con --print --effort high (default
post audit 2026-05-18: effort=low subestimaba criticas y sobre-clasificaba
como "personal/+0"). Retry exponencial 3 intentos (2s/5s/15s). Si CC falla
los 3 intentos, el batch queda pendiente para la proxima corrida. NO usa Ollama (D-1 plan) ni Groq API ni
API key de Anthropic.

Gemini NO se usa como fallback aqui. Su rol es cross-audit independiente
(ver `backend/scripts/cross_audit_nlp_gemini.py`).

IMPORTANTE — debe correr en HOST (Mac Mini), NO dentro del container:
- claude CLI vive en /Users/marxchavez/.local/bin/claude (host)
- DB_URL por defecto apunta a host postgres en :5438

Mapping tono → polaridad (heurística observada en BD existente):
- celebratorio, solidario, propositivo → +1
- personal, informativo → 0
- critico, ataque → -1

Uso (desde HOST):
  python backend/scripts/backfill_nlp_saymi.py --dry-run --limit 5  # smoke
  python backend/scripts/backfill_nlp_saymi.py --limit 508          # full
  nohup python backend/scripts/backfill_nlp_saymi.py --limit 508 \
      > backend/.context/nlp_backfill_saymi_$(date +%Y%m%d_%H%M).log 2>&1 &
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

# Host por defecto (postgres expuesto en :5438 del Mac Mini)
DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://crece:crece_dev@localhost:5438/crece",
)
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "/Users/marxchavez/.local/bin/claude")
DIRIGENTE_ID = 3
MODEL_VERSION_CC = "cc-subprocess-v1-2026-05-17"
# Plan R-5: timeout 600s para plan regen, 300s suficiente para batch de 5-20 comments
DEFAULT_TIMEOUT_CC = int(os.environ.get("CC_TIMEOUT", "600"))
CC_EFFORT = os.environ.get("CC_EFFORT", "high")

TONO_POLARIDAD = {
    "celebratorio": 1,
    "solidario": 1,
    "propositivo": 1,
    "personal": 0,
    "informativo": 0,
    "critico": -1,
    "ataque": -1,
}

VALID_TONOS = set(TONO_POLARIDAD.keys())
VALID_TARGETS = {"gobierno", "oposicion", "ciudadania", "medios", "autopromocion", "tema_especifico", "otro", "dirigente"}


def build_batch_prompt(comments: list[dict], dirigente_nombre: str = "Saymi Pineda Velasco", rol: str = "oficialismo") -> str:
    """Prompt para clasificar un batch en una sola invocación."""
    items = "\n".join(
        f'{i+1}. [id={c["id"]}] "{c["content"][:500].replace(chr(34), chr(39))}"'
        for i, c in enumerate(comments)
    )
    return f"""Clasifica cada uno de los siguientes comments dirigidos a un post de "{dirigente_nombre}" (rol: {rol}).

Comments:
{items}

Para CADA comment, responde con un objeto JSON. Devuelve un ARRAY JSON con un objeto por comment, en el MISMO ORDEN.

Cada objeto debe tener:
- "id": entero (el id del comment)
- "tono": uno de: critico, propositivo, celebratorio, informativo, solidario, ataque, personal
- "target": uno de: dirigente, gobierno, oposicion, ciudadania, medios, autopromocion, tema_especifico, otro

Tono guidance:
- critico: cuestiona, denuncia, señala fallas
- propositivo: propone soluciones
- celebratorio: celebra logros, apoya, felicita
- informativo: hechos sin postura
- solidario: condolencias, apoyo emocional
- ataque: ataque directo a persona/institución
- personal: contenido sin carga política (saludos, felicitaciones genéricas)

Target dirigente = respuesta directa a {dirigente_nombre}.

Responde ÚNICAMENTE el array JSON. Sin texto adicional, sin markdown."""


def call_cc(prompt: str, timeout: int = DEFAULT_TIMEOUT_CC) -> str | None:
    """Invoca Claude Code CLI con --print --effort `CC_EFFORT`. Retorna stdout o None.

    Default effort=high (post audit 2026-05-18: low subestimaba criticas).
    Timeout default 600s (effort=high tarda mas que low). Override via env
    `CC_TIMEOUT` y `CC_EFFORT`.
    """
    if not Path(CLAUDE_BIN).exists():
        print(f"  [CC] binary not found at {CLAUDE_BIN} (¿corriendo en container?)", file=sys.stderr)
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
    except subprocess.TimeoutExpired:
        print(f"  [CC] timeout {timeout}s", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  [CC] error: {e}", file=sys.stderr)
        return None


def call_cc_with_retry(prompt: str, timeout: int = DEFAULT_TIMEOUT_CC) -> str | None:
    """Llama a CC con retry exponencial (3 intentos, backoff 2s/5s/15s).

    Gemini NO se usa como fallback aqui. Su rol es cross-audit independiente
    (ver `cross_audit_nlp_gemini.py`). Si CC falla los 3 intentos, el batch
    se reporta como failed y queda pendiente para la proxima corrida.
    """
    backoffs = [2, 5, 15]
    for attempt, sleep_secs in enumerate(backoffs, start=1):
        raw = call_cc(prompt, timeout=timeout)
        if raw is not None:
            if attempt > 1:
                print(f"  [CC] exito en intento {attempt}/3")
            return raw
        if attempt < len(backoffs):
            print(f"  [CC] intento {attempt}/3 fallo, retry en {sleep_secs}s")
            time.sleep(sleep_secs)
    print("  [CC] los 3 intentos fallaron, batch sera reintentado en la proxima corrida")
    return None


def parse_array_response(raw: str) -> list[dict] | None:
    """Extrae array JSON tolerante a markdown / prefijos."""
    # Strip markdown
    m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", raw, re.DOTALL)
    if m:
        raw = m.group(1)
    else:
        start = raw.find("[")
        end = raw.rfind("]")
        if start >= 0 and end > start:
            raw = raw[start:end + 1]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list):
        return None
    return data


def validate_item(item: dict, expected_id: int) -> dict | None:
    """Valida un item parseado y aplica mapping polaridad."""
    if not isinstance(item, dict):
        return None
    tono = item.get("tono")
    target = item.get("target")
    if tono not in VALID_TONOS or target not in VALID_TARGETS:
        return None
    return {
        "id": expected_id,
        "tono": tono,
        "target": target,
        "polaridad": TONO_POLARIDAD[tono],
    }


def process_batch(conn, batch: list[dict], dry_run: bool, dirigente_nombre: str = "Saymi Pineda Velasco", rol: str = "oficialismo") -> tuple[int, int]:
    """Procesa un batch via CC con retry. Retorna (n_updated, n_failed).

    Si CC falla los 3 intentos, batch se reporta failed (no escribe BD) y
    queda para la proxima corrida. Gemini NO sustituye a CC aqui.
    """
    prompt = build_batch_prompt(batch, dirigente_nombre, rol)
    raw = call_cc_with_retry(prompt)
    if raw is None:
        return 0, len(batch)
    model_version = MODEL_VERSION_CC

    parsed = parse_array_response(raw)
    if not parsed:
        print(f"  [batch] parse failed. Raw: {raw[:200]}")
        return 0, len(batch)

    # Empareja por orden (el LLM podría reorderar pero el orden es ground truth)
    updates: list[dict] = []
    for i, comment in enumerate(batch):
        if i >= len(parsed):
            continue
        # Acepta match por id o por posición
        item = parsed[i]
        if isinstance(item, dict) and item.get("id") != comment["id"]:
            # Intenta buscar por id
            matching = [x for x in parsed if isinstance(x, dict) and x.get("id") == comment["id"]]
            if matching:
                item = matching[0]
        validated = validate_item(item, comment["id"])
        if validated:
            updates.append(validated)

    if not updates:
        return 0, len(batch)

    if dry_run:
        print(f"  [batch] dry-run, no UPDATE. Sample: {updates[:2]}")
        return len(updates), len(batch) - len(updates)

    with conn.cursor() as cur:
        for u in updates:
            cur.execute(
                """
                UPDATE social_comments
                SET nlp_tono = %s,
                    nlp_target = %s,
                    nlp_polaridad = %s,
                    nlp_model_version = %s,
                    updated_at = NOW()
                WHERE id = %s AND nlp_tono IS NULL
                """,
                (u["tono"], u["target"], u["polaridad"], model_version, u["id"]),
            )
        conn.commit()
    return len(updates), len(batch) - len(updates)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=508, help="máx comments a procesar")
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--dirigente-id", type=int, default=DIRIGENTE_ID)
    args = parser.parse_args()

    print(f"Sprint D backfill NLP — dirigente_id={args.dirigente_id}, limit={args.limit}, batch={args.batch_size}, dry_run={args.dry_run}")

    with psycopg.connect(DB_URL) as conn:
        # Identidad real del dirigente para el prompt (genérico, no hardcode Saymi)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT full_name, partido FROM dirigentes WHERE id = %s",
                (args.dirigente_id,),
            )
            drow = cur.fetchone()
        dirigente_nombre = drow[0] if drow else "el dirigente"
        rol = (drow[1] or "político") if drow else "político"
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT sc.id, sc.content
                FROM social_comments sc
                JOIN social_posts sp ON sc.parent_post_id = sp.id
                JOIN social_profiles sps ON sp.profile_id = sps.id
                WHERE sps.dirigente_id = %s
                  AND sc.nlp_tono IS NULL
                  AND sc.content IS NOT NULL
                  AND LENGTH(sc.content) > 3
                ORDER BY sc.id
                LIMIT %s
                """,
                (args.dirigente_id, args.limit),
            )
            comments = [{"id": r[0], "content": r[1]} for r in cur.fetchall()]

        total = len(comments)
        if total == 0:
            print("Nada que procesar. Salgo.")
            return

        print(f"Pull: {total} comments pendientes")

        total_updated = 0
        total_failed = 0
        t0 = time.time()
        for i in range(0, total, args.batch_size):
            batch = comments[i:i + args.batch_size]
            batch_num = i // args.batch_size + 1
            n_batches = (total + args.batch_size - 1) // args.batch_size
            elapsed = time.time() - t0
            rate = (i / elapsed) if elapsed > 0 else 0
            eta = (total - i) / rate if rate > 0 else 0
            print(f"\n[batch {batch_num}/{n_batches}] ids={[c['id'] for c in batch]} · "
                  f"elapsed={elapsed:.0f}s · eta={eta:.0f}s")
            n_u, n_f = process_batch(conn, batch, args.dry_run, dirigente_nombre, rol)
            total_updated += n_u
            total_failed += n_f
            print(f"  → updated={n_u}, failed={n_f} (cum: {total_updated}/{total})")

        print(f"\nDONE — updated={total_updated}, failed={total_failed}, total={total}, elapsed={time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
