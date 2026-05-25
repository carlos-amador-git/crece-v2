"""backfill_emotions_cc.py · 2026-05-22

Pobla `social_posts.emotions` (o `social_comments.emotions`) con 6 emociones
Ekman vía CC/Gemini. Reemplaza el pipeline unario de Gemma.

Uso:
    python3 backfill_emotions_cc.py --dirigente-id 57 --limit 500 --type posts
    python3 backfill_emotions_cc.py --dirigente-id 3 --limit 200 --type comments --force
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
  {{"post_id": <id>, "emotions": {{"joy": 0.45, "anger": 0.05, "sadness": 0.10, "fear": 0.02, "disgust": 0.03, "surprise": 0.05, "others": 0.30}}}}
]
```

REGLAS:
- Suma ~1.0 (tolerancia ±0.05).
- Si el post es neutral/informativo sin emoción clara, `others` debe ser alto.
- NO inventes post_ids: usa exactamente los del input.
- Output: ÚNICAMENTE el JSON array. Sin markdown extra, sin texto adicional.
"""


def call_llm(prompt: str) -> str | None:
    # 1. Intentar Claude CLI (CC)
    if Path(CLAUDE_BIN).exists():
        try:
            r = subprocess.run(
                [CLAUDE_BIN, "--print", "--effort", CC_EFFORT, prompt],
                capture_output=True, text=True, timeout=TIMEOUT_S,
                stdin=subprocess.DEVNULL,
            )
            if r.returncode == 0 and r.stdout:
                return r.stdout
        except subprocess.TimeoutExpired:
            pass

    # 2. Fallback a Gemini CLI (headless)
    GEMINI_CMD = "/opt/homebrew/bin/gemini"
    if Path(GEMINI_CMD).exists():
        try:
            r = subprocess.run(
                [GEMINI_CMD, "--sandbox", "--approval-mode", "plan", "-p", prompt],
                capture_output=True, text=True, timeout=180,
                stdin=subprocess.DEVNULL,
            )
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
    m = re.search(r"\[\s*\{.*\}\s*\]", cleaned, re.DOTALL)
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
    p.add_argument("--type", choices=["posts", "comments"], default="posts")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    conn = psycopg2.connect(DB_URL)
    with conn.cursor() as cur:
        if args.type == "posts":
            sql = """
                SELECT sp.id, LEFT(sp.content, 1000)
                FROM social_posts sp
                JOIN social_profiles sps ON sps.id = sp.profile_id
                WHERE sps.dirigente_id = %s
                  AND sp.content IS NOT NULL
                  AND LENGTH(TRIM(sp.content)) >= %s
            """
            if not args.force:
                sql += " AND (sp.emotions IS NULL OR sp.emotions = '{}'::jsonb)"
            sql += " ORDER BY sp.published_at DESC LIMIT %s"
            cur.execute(sql, (args.dirigente_id, args.min_chars, args.limit))
        else:
            sql = """
                SELECT sc.id, LEFT(sc.content, 1000)
                FROM social_comments sc
                JOIN social_posts sp ON sp.id = sc.parent_post_id
                JOIN social_profiles sps ON sps.id = sp.profile_id
                WHERE sps.dirigente_id = %s
                  AND sc.content IS NOT NULL
                  AND LENGTH(TRIM(sc.content)) >= %s
            """
            if not args.force:
                sql += " AND (sc.emotions IS NULL OR sc.emotions = '{}'::jsonb)"
            sql += " ORDER BY sc.published_at DESC LIMIT %s"
            cur.execute(sql, (args.dirigente_id, args.min_chars, args.limit))

        items = [{"id": r[0], "content": r[1]} for r in cur.fetchall()]

    print(f"[meta] {len(items)} {args.type} a procesar · batch={BATCH} effort={CC_EFFORT}", flush=True)

    total_updated = 0
    total_failed = 0
    t0 = time.monotonic()
    
    table = "social_posts" if args.type == "posts" else "social_comments"

    for i in range(0, len(items), BATCH):
        batch = items[i:i + BATCH]
        posts_block = "\n".join(
            f'  - id={p["id"]} · content: """{p["content"][:600].replace(chr(10), " ")}"""'
            for p in batch
        )
        prompt = PROMPT_TEMPLATE.format(posts_block=posts_block)
        raw = call_llm(prompt)
        if not raw:
            total_failed += len(batch)
            print(f"  [batch {i//BATCH+1}] LLM fail")
            continue
        
        parsed = parse_json_array(raw)
        if not parsed:
            total_failed += len(batch)
            print(f"  [batch {i//BATCH+1}] parse fail (raw len={len(raw)})")
            continue

        with conn.cursor() as cur:
            for item in parsed:
                # El LLM puede devolver post_id o id
                pid = item.get("post_id") or item.get("id")
                ems = item.get("emotions")
                if pid and isinstance(ems, dict):
                    try:
                        cur.execute(
                            f"UPDATE {table} SET emotions = %s::jsonb WHERE id = %s",
                            (json.dumps(ems), int(pid)),
                        )
                        if cur.rowcount > 0:
                            total_updated += 1
                        else:
                            total_failed += 1
                    except Exception:
                        total_failed += 1
        conn.commit()

        elapsed = time.monotonic() - t0
        rate = total_updated / elapsed if elapsed > 0 else 0
        eta_s = (len(items) - (i + len(batch))) / rate if rate > 0 else 0
        print(
            f"  [batch {i//BATCH+1}/{(len(items)-1)//BATCH+1 if items else 1}] "
            f"updated cum={total_updated} fail={total_failed} · "
            f"elapsed={elapsed:.0f}s · eta={eta_s:.0f}s",
            flush=True,
        )

    conn.close()
    print(f"\nDONE · updated={total_updated} failed={total_failed} total={len(items)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
