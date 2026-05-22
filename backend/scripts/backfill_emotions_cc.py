"""backfill_emotions_cc.py · 2026-05-22

Pobla `social_posts.emotions` JSONB con 6 emociones Ekman vía CC subprocess.
Reemplaza el pipeline Gemma 3:12b muerto · acuerdo CEO: CC + Gemini fallback.

Batch 10 posts por LLM call para eficiencia. Procesa solo posts con
content > 30 chars (los ultra-cortos no rinden).

Output JSON por post:
  {"joy": 0.42, "anger": 0.05, "sadness": 0.10, "fear": 0.03,
   "disgust": 0.02, "surprise": 0.08, "others": 0.30}

Uso:
    python3 backfill_emotions_cc.py --dirigente-id 57 --limit 500
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

import psycopg2

CLAUDE_BIN = "/Users/marxchavez/.local/bin/claude"
GEMINI_BIN = "/Users/marxchavez/.claude/bin/gemini-clean"
CC_EFFORT = os.environ.get("CC_EFFORT", "low")
TIMEOUT_S = int(os.environ.get("CC_TIMEOUT", "120"))
BATCH = int(os.environ.get("BATCH_SIZE", "10"))

DB_URL = os.environ.get("DATABASE_URL_SYNC", "postgresql://crece:crece_dev@localhost:5438/crece")


PROMPT_TEMPLATE = """Eres clasificador de emociones Ekman para texto político en español.

Para cada post a continuación, devuelve la distribución de las 6 emociones
Ekman como floats entre 0.0-1.0 que sumen ~1.0:
- joy (alegría)
- anger (enojo)
- sadness (tristeza)
- fear (miedo)
- disgust (asco)
- surprise (sorpresa)
- others (resto · neutral, mezclas, contenido no emocional)

POSTS A CLASIFICAR (id · content):
{posts_block}

OUTPUT: JSON array EXACTO con un objeto por post, en el mismo orden:
```json
[
  {{"post_id": "<id>", "emotions": {{"joy": 0.45, "anger": 0.05, "sadness": 0.10, "fear": 0.02, "disgust": 0.03, "surprise": 0.05, "others": 0.30}}}}
]
```

REGLAS:
- Suma ~1.0 (tolerancia ±0.05).
- Si el post es neutral/informativo sin emoción clara, `others` debe ser alto.
- NO inventes post_ids: usa exactamente los del input.
- Output: ÚNICAMENTE el JSON array. Sin markdown extra, sin texto adicional.
"""


def call_llm(prompt: str) -> str | None:
    if Path(CLAUDE_BIN).exists():
        try:
            r = subprocess.run(
                [CLAUDE_BIN, "--print", "--effort", CC_EFFORT, prompt],
                capture_output=True, text=True, timeout=TIMEOUT_S,
            )
            if r.returncode == 0 and r.stdout:
                return r.stdout
        except subprocess.TimeoutExpired:
            pass
    if Path(GEMINI_BIN).exists():
        try:
            r = subprocess.run([GEMINI_BIN, "--mode", "plan", "--prompt", prompt],
                               capture_output=True, text=True, timeout=120)
            if r.returncode == 0 and r.stdout:
                return r.stdout
        except subprocess.TimeoutExpired:
            pass
    return None


def parse_json_array(raw: str) -> list | None:
    cleaned = (raw or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    try:
        d = json.loads(cleaned)
        if isinstance(d, list):
            return d
    except json.JSONDecodeError:
        pass
    # Greedy match
    m = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if m:
        try:
            d = json.loads(m.group(0))
            if isinstance(d, list):
                return d
        except json.JSONDecodeError:
            pass
    return None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dirigente-id", type=int, required=True)
    p.add_argument("--limit", type=int, default=500)
    p.add_argument("--min-chars", type=int, default=30)
    args = p.parse_args()

    conn = psycopg2.connect(DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT sp.id, LEFT(sp.content, 1000)
            FROM social_posts sp
            JOIN social_profiles sps ON sps.id = sp.profile_id
            WHERE sps.dirigente_id = %s
              AND (sp.emotions IS NULL OR sp.emotions = '{}'::jsonb)
              AND sp.content IS NOT NULL
              AND LENGTH(TRIM(sp.content)) >= %s
            ORDER BY sp.published_at DESC
            LIMIT %s
            """,
            (args.dirigente_id, args.min_chars, args.limit),
        )
        posts = [{"id": r[0], "content": r[1]} for r in cur.fetchall()]
    print(f"[meta] {len(posts)} posts a procesar · batch={BATCH} effort={CC_EFFORT}", flush=True)

    total_updated = 0
    total_failed = 0
    t0 = time.monotonic()
    for i in range(0, len(posts), BATCH):
        batch = posts[i:i + BATCH]
        posts_block = "\n".join(
            f'  - id={p["id"]} · content: """{p["content"][:600].replace(chr(10), " ")}"""'
            for p in batch
        )
        prompt = PROMPT_TEMPLATE.format(posts_block=posts_block)
        raw = call_llm(prompt)
        if not raw:
            total_failed += len(batch)
            print(f"  [batch {i//BATCH+1}] LLM fail · skip {len(batch)}", flush=True)
            continue
        parsed = parse_json_array(raw)
        if not parsed:
            total_failed += len(batch)
            print(f"  [batch {i//BATCH+1}] parse fail · skip {len(batch)}", flush=True)
            continue

        with conn.cursor() as cur:
            for item in parsed:
                try:
                    pid = int(item.get("post_id") or 0)
                    emo = item.get("emotions") or {}
                    if pid and isinstance(emo, dict) and emo:
                        cur.execute(
                            "UPDATE social_posts SET emotions = %s::jsonb WHERE id = %s",
                            (json.dumps(emo), pid),
                        )
                        total_updated += 1
                except Exception:
                    total_failed += 1
        conn.commit()

        elapsed = time.monotonic() - t0
        rate = total_updated / elapsed if elapsed > 0 else 0
        eta_s = (len(posts) - i - BATCH) / rate if rate > 0 else 0
        print(
            f"  [batch {i//BATCH+1}/{(len(posts)-1)//BATCH+1}] "
            f"updated cum={total_updated} fail={total_failed} · "
            f"elapsed={elapsed:.0f}s · eta={eta_s:.0f}s",
            flush=True,
        )

    conn.close()
    print(f"\nDONE · updated={total_updated} failed={total_failed} total={len(posts)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
