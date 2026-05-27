"""backfill_nlp_posts.py — Sprint post-ingest Hugo 2026-05-20 · Fase 3a/3b

Clasifica POSTS (no comments) sin `tono_discurso` para un dirigente dado.
Adaptación de `backfill_nlp_saymi.py` (que opera sobre social_comments).

Stack:
- subprocess `claude` (Claude Code CLI) `--print --effort high` (D-PLAN-IA-CC-GEMINI-CLI-1).
- Retry exponencial 3 intentos (2s/5s/15s). Si CC falla los 3, batch queda
  pendiente para próxima corrida.
- Idempotente: WHERE tono_discurso IS NULL en el UPDATE (re-run = no-op para los ya clasificados).

Vocabulario v2 (matriz polaridad v2):
- tono: critico | propositivo | celebratorio | informativo | solidario | ataque | personal
- target: gobierno | oposicion | ciudadania | medios | autopromocion | tema_especifico | dirigente | otro
- polaridad mapping: critico/ataque=-1, personal/informativo=0, celebratorio/solidario/propositivo=+1

Uso (desde HOST Mac Mini, NO container):
  python backend/scripts/backfill_nlp_posts.py --dirigente-id 57 --dry-run --limit 5
  python backend/scripts/backfill_nlp_posts.py --dirigente-id 57 --limit 200
  nohup python backend/scripts/backfill_nlp_posts.py --dirigente-id 57 --limit 200 \
      > backend/.context/nlp_backfill_posts_pepe_$(date +%Y%m%d_%H%M).log 2>&1 &

Output BD:
- UPDATE social_posts SET tono_discurso, target_politico,
                          sentimiento_politico_ajustado, nlp_model_version, llm_modelo,
                          llm_processed_at, clasificacion_origen='ai_suggested'
  WHERE id=? AND tono_discurso IS NULL
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

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://crece:crece_dev@localhost:5438/crece",
)
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "/Users/marxchavez/.local/bin/claude")
MODEL_VERSION_CC = "cc-posts-subprocess-v1-2026-05-20"
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

# DB constraint `ck_social_posts_target_politico` permite:
# oficialismo, oposicion, propio, personal, no_determinado, gobierno,
# ciudadania, medios, autopromocion, tema_especifico, dirigente.
VALID_TARGETS = {
    "gobierno", "oposicion", "ciudadania", "medios",
    "autopromocion", "tema_especifico", "dirigente",
    "oficialismo", "propio", "personal", "no_determinado",
}

# LLM puede devolver "otro" → mapeamos al valor canónico permitido por BD.
TARGET_ALIASES = {
    "otro": "no_determinado",
}


def build_batch_prompt(posts: list[dict], dirigente_nombre: str, rol: str) -> str:
    items = "\n".join(
        f'{i+1}. [id={p["id"]}] plataforma={p["platform"]} '
        f'"{(p["content"] or "")[:600].replace(chr(34), chr(39))}"'
        for i, p in enumerate(posts)
    )
    return f"""Clasifica cada uno de los siguientes POSTS publicados por "{dirigente_nombre}" (rol: {rol}).

Posts:
{items}

Para CADA post, responde con un objeto JSON. Devuelve un ARRAY JSON con un objeto por post, en el MISMO ORDEN.

Cada objeto debe tener:
- "id": entero (el id del post)
- "tono": uno de: critico, propositivo, celebratorio, informativo, solidario, ataque, personal
- "target": uno de: dirigente, gobierno, oposicion, ciudadania, medios, autopromocion, tema_especifico, otro

Tono guidance (CRÍTICO: post es del dirigente, no de un comentarista):
- critico: el dirigente cuestiona/denuncia/señala fallas (típico de oposición, también oficialismo crítico interno)
- propositivo: el dirigente propone solución/iniciativa concreta
- celebratorio: el dirigente celebra logros, anuncia éxitos, felicita
- informativo: el dirigente informa hechos sin postura política fuerte (agenda, ruedas de prensa, datos)
- solidario: el dirigente expresa condolencias / apoyo / acompañamiento
- ataque: ataque directo a persona / institución
- personal: contenido personal/familiar sin agenda política (cumpleaños, fechas íntimas, mensajes generales)
- autopromocion: post promocional puro del dirigente sin tono crítico/propositivo (usa tono="celebratorio" con target="autopromocion")

Target guidance:
- gobierno: post dirigido a oficialismo / autoridades en turno (federal, estatal, municipal)
- oposicion: post dirigido a partidos opositores
- ciudadania: post dirigido al ciudadano común
- medios: post dirigido a prensa / medios de comunicación
- autopromocion: dirigente habla de sus propias acciones/logros
- tema_especifico: post sobre un tema (educación, salud, seguridad) sin atacar a otro actor
- dirigente: post sobre otro dirigente (par o competencia)
- otro: ninguna de las anteriores

Si el post está vacío o solo contiene URL/menciones: tono="personal", target="otro".

Responde ÚNICAMENTE el array JSON. Sin texto adicional, sin markdown."""


def call_cc(prompt: str, timeout: int = DEFAULT_TIMEOUT_CC) -> str | None:
    # 1. Claude
    if Path(CLAUDE_BIN).exists():
        try:
            result = subprocess.run(
                [CLAUDE_BIN, "--print", "--strict-mcp-config", "--effort", CC_EFFORT, *(["--model", os.environ["CC_MODEL"]] if os.environ.get("CC_MODEL") else []), prompt],
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


def call_cc_with_retry(prompt: str, timeout: int = DEFAULT_TIMEOUT_CC) -> str | None:
    backoffs = [2, 5, 15]
    for attempt, sleep_secs in enumerate(backoffs, start=1):
        raw = call_cc(prompt, timeout=timeout)
        if raw is not None:
            if attempt > 1:
                print(f"  [CC] éxito en intento {attempt}/3")
            return raw
        if attempt < len(backoffs):
            print(f"  [CC] intento {attempt}/3 falló, retry en {sleep_secs}s")
            time.sleep(sleep_secs)
    print("  [CC] los 3 intentos fallaron, batch será reintentado en la próxima corrida")
    return None


def parse_array_response(raw: str) -> list[dict] | None:
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
    if not isinstance(item, dict):
        return None
    tono = item.get("tono")
    target = item.get("target")
    target = TARGET_ALIASES.get(target, target)
    if tono not in VALID_TONOS or target not in VALID_TARGETS:
        return None
    return {
        "id": expected_id,
        "tono": tono,
        "target": target,
        "polaridad": TONO_POLARIDAD[tono],
    }


def process_batch(conn, batch: list[dict], dirigente_nombre: str, rol: str,
                  dry_run: bool, include_legacy: bool = False) -> tuple[int, int]:
    prompt = build_batch_prompt(batch, dirigente_nombre, rol)
    raw = call_cc_with_retry(prompt)
    if raw is None:
        return 0, len(batch)

    parsed = parse_array_response(raw)
    if not parsed:
        print(f"  [batch] parse failed. Raw: {raw[:200]}")
        return 0, len(batch)

    updates: list[dict] = []
    for i, post in enumerate(batch):
        if i >= len(parsed):
            continue
        item = parsed[i]
        if isinstance(item, dict) and item.get("id") != post["id"]:
            matching = [x for x in parsed if isinstance(x, dict) and x.get("id") == post["id"]]
            if matching:
                item = matching[0]
        validated = validate_item(item, post["id"])
        if validated:
            updates.append(validated)

    if not updates:
        return 0, len(batch)

    if dry_run:
        print(f"  [batch] dry-run, no UPDATE. Sample: {updates[:2]}")
        return len(updates), len(batch) - len(updates)

    where_legacy = "OR nlp_model_version IS NULL" if include_legacy else ""
    with conn.cursor() as cur:
        for u in updates:
            cur.execute(
                f"""
                UPDATE social_posts
                SET tono_discurso = %s,
                    target_politico = %s,
                    sentimiento_politico_ajustado = %s,
                    nlp_model_version = %s,
                    llm_modelo = %s,
                    llm_processed_at = NOW(),
                    clasificacion_origen = 'ai_suggested'
                WHERE id = %s AND (tono_discurso IS NULL {where_legacy})
                """,
                (u["tono"], u["target"], u["polaridad"], MODEL_VERSION_CC, MODEL_VERSION_CC, u["id"]),
            )
        conn.commit()
    return len(updates), len(batch) - len(updates)


def lookup_dirigente_info(conn, dirigente_id: int) -> tuple[str, str]:
    """Devuelve (nombre, rol) desde la BD."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT full_name, COALESCE(rol_politico, 'oficialismo')
            FROM dirigentes
            WHERE id = %s
            """,
            (dirigente_id,),
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError(f"dirigente_id={dirigente_id} no existe")
        return row[0], row[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dirigente-id", type=int, required=True)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--include-legacy", action="store_true",
                        help="También sobreescribir posts con vocabulario legacy "
                             "(positivo/neutral/negativo · nlp_model_version IS NULL) con v2")
    args = parser.parse_args()

    with psycopg.connect(DB_URL) as conn:
        nombre, rol = lookup_dirigente_info(conn, args.dirigente_id)
        print(f"Backfill NLP posts — dirigente_id={args.dirigente_id} ({nombre}, {rol}), "
              f"limit={args.limit}, batch={args.batch_size}, dry_run={args.dry_run}")

        where_legacy = "OR sp.nlp_model_version IS NULL" if args.include_legacy else ""
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT sp.id, COALESCE(sp.content,'') AS content, sprof.platform::text
                FROM social_posts sp
                JOIN social_profiles sprof ON sp.profile_id = sprof.id
                WHERE sprof.dirigente_id = %s
                  AND (sp.tono_discurso IS NULL {where_legacy})
                ORDER BY sp.published_at DESC NULLS LAST, sp.id
                LIMIT %s
                """,
                (args.dirigente_id, args.limit),
            )
            posts = [{"id": r[0], "content": r[1], "platform": r[2]} for r in cur.fetchall()]

        total = len(posts)
        if total == 0:
            print("Nada que procesar. Salgo.")
            return

        print(f"Pull: {total} posts pendientes")

        total_updated = 0
        total_failed = 0
        t0 = time.time()
        for i in range(0, total, args.batch_size):
            batch = posts[i:i + args.batch_size]
            batch_num = i // args.batch_size + 1
            n_batches = (total + args.batch_size - 1) // args.batch_size
            elapsed = time.time() - t0
            rate = (i / elapsed) if elapsed > 0 else 0
            eta = (total - i) / rate if rate > 0 else 0
            print(f"\n[batch {batch_num}/{n_batches}] ids={[p['id'] for p in batch]} · "
                  f"elapsed={elapsed:.0f}s · eta={eta:.0f}s")
            n_u, n_f = process_batch(conn, batch, nombre, rol, args.dry_run, args.include_legacy)
            total_updated += n_u
            total_failed += n_f
            print(f"  → updated={n_u}, failed={n_f} (cum: {total_updated}/{total})")

        print(f"\nDONE — dirigente={nombre} updated={total_updated}, failed={total_failed}, "
              f"total={total}, elapsed={time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
