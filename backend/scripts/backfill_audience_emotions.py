"""backfill_audience_emotions.py · 2026-05-22

Analiza el sentimiento AGREGADO de la audiencia (comentarios) para cada post.
Pobla `sentiment_analyses.emotions` con 6 emociones Ekman.
Esto diversifica el Radar B05 que actualmente solo muestra el post (caption).

Uso:
    python3 backfill_audience_emotions.py --dirigente-id 57 --limit 50
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

import psycopg2

CLAUDE_BIN = "/Users/marxchavez/.local/bin/claude"
GEMINI_BIN = "/opt/homebrew/bin/gemini"
CC_EFFORT = os.environ.get("CC_EFFORT", "low")
DB_URL = os.environ.get("DATABASE_URL_SYNC", "postgresql://crece:crece_dev@localhost:5438/crece")

PROMPT_TEMPLATE = """Eres un analista de opinión pública. Clasifica el clima emocional de la AUDIENCIA basándote en sus comentarios a un post político.

POST ORIGINAL: "{post_caption}"

COMENTARIOS DE LA GENTE:
{comments_block}

Para la AUDIENCIA en su conjunto, devuelve la distribución de las 6 emociones Ekman como floats (0.0-1.0) que sumen ~1.0:
- joy (alegría/apoyo)
- anger (enojo/rechazo)
- sadness (tristeza/empatía por problemas)
- fear (miedo/preocupación)
- disgust (asco/indignación)
- surprise (sorpresa)
- others (neutral/otros)

RESPONDE EXCLUSIVAMENTE UN OBJETO JSON:
{{"joy": 0.45, "anger": 0.05, "sadness": 0.10, "fear": 0.02, "disgust": 0.03, "surprise": 0.05, "others": 0.30}}
"""

def call_llm(prompt: str) -> str | None:
    # 1. Claude fallback
    if Path(CLAUDE_BIN).exists():
        try:
            r = subprocess.run([CLAUDE_BIN, "--print", "--effort", CC_EFFORT, prompt], 
                               capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
            if r.returncode == 0 and r.stdout: return r.stdout
        except: pass
    # 2. Gemini fallback
    if Path(GEMINI_BIN).exists():
        try:
            r = subprocess.run([GEMINI_BIN, "--sandbox", "--approval-mode", "plan", "-p", prompt],
                               capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL)
            if r.returncode == 0 and r.stdout: return r.stdout
        except: pass
    return None

def parse_json(raw: str) -> dict | None:
    cleaned = (raw or "").strip()
    m = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if m:
        try: return json.loads(m.group(0))
        except: pass
    return None

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dirigente-id", type=int, required=True)
    p.add_argument("--limit", type=int, default=50)
    args = p.parse_args()

    conn = psycopg2.connect(DB_URL)
    with conn.cursor() as cur:
        # Buscar posts con comentarios que no tengan análisis de audiencia reciente
        cur.execute("""
            SELECT sp.id, sp.content, string_agg(sc.content, ' | ') as comments
            FROM social_posts sp
            JOIN social_comments sc ON sc.parent_post_id = sp.id
            JOIN social_profiles sps ON sps.id = sp.profile_id
            WHERE sps.dirigente_id = %s
              AND NOT EXISTS (
                  SELECT 1 FROM sentiment_analyses sa 
                  WHERE sa.post_id = sp.id AND sa.model_used = 'audience-v1'
              )
            GROUP BY sp.id
            ORDER BY sp.published_at DESC
            LIMIT %s
        """, (args.dirigente_id, args.limit))
        posts = [{"id": r[0], "caption": r[1] or "", "comments": r[2]} for r in cur.fetchall()]

    print(f"[meta] {len(posts)} posts con comentarios a procesar")

    for p in posts:
        t0 = time.monotonic()
        prompt = PROMPT_TEMPLATE.format(
            post_caption=p["caption"][:300],
            comments_block=p["comments"][:3000]
        )
        raw = call_llm(prompt)
        res = parse_json(raw)
        
        if res:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sentiment_analyses 
                    (post_id, model_used, sentiment_score, sentiment_label, emotions, is_toxic, toxicity_score, analyzed_at)
                    VALUES (%s, 'audience-v1', %s, %s, %s, false, 0.0, NOW())
                """, (
                    p["id"], 
                    res.get("joy", 0) - res.get("anger", 0),
                    "POSITIVE" if res.get("joy", 0) > 0.5 else "NEUTRAL",
                    json.dumps(res)
                ))
            conn.commit()
            print(f"  [OK] post_id={p['id']} ({time.monotonic()-t0:.1f}s)")
        else:
            print(f"  [FAIL] post_id={p['id']}")

    conn.close()

if __name__ == "__main__":
    main()
