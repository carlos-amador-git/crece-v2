#!/usr/bin/env python3
"""
Pilot v2: Gemma3:12b SOLO clasifica tono+target (prompt compacto).
Python aplica la matriz del tenant para calcular score_politico.

Output markdown table para CEO review.

Usage (host, venv local):
    python3 backend/scripts/llm_political_pilot.py > /tmp/pilot-output.md
"""
import os
import sys
import time

import psycopg2
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.nlp.political_llm_prompt import apply_matrix, build_prompt, parse_response

DB_URL = os.environ.get("DATABASE_URL_SYNC", "postgresql://crece:crece_dev@localhost:5438/crece")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = "gemma3:12b"
TIMEOUT = 60  # compact prompt should respond fast


def get_effective_matrix(cur, org_id: int) -> list[dict]:
    cur.execute(
        """
        SELECT d.rol, d.tono, d.target,
               COALESCE(o.score_politico, d.score_politico) AS score_effective,
               d.descripcion
        FROM framework_matrix_defaults d
        LEFT JOIN framework_overrides_org o
            ON o.org_id = %s AND o.rol = d.rol AND o.tono = d.tono AND o.target = d.target
        WHERE d.version = 'v1'
        ORDER BY d.rol, d.tono, d.target
        """,
        (org_id,),
    )
    return [
        {"rol": r[0], "tono": r[1], "target": r[2],
         "score_effective": r[3], "descripcion": r[4]}
        for r in cur.fetchall()
    ]


def call_gemma(prompt: str) -> tuple[str, float]:
    t0 = time.time()
    r = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 120, "num_ctx": 2048},
            "format": "json",
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["response"], time.time() - t0


def main():
    N_POSTS = int(os.environ.get("PILOT_N", "10"))

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Curated sample: mix of dirigentes + RT + whisper transcribed
    cur.execute("""
        (SELECT p.id, p.content, d.full_name, d.rol_politico, sp.platform::text, d.org_id, d.id
         FROM social_posts p JOIN social_profiles sp ON p.profile_id = sp.id JOIN dirigentes d ON sp.dirigente_id = d.id
         WHERE d.id = 1 AND p.content NOT LIKE 'RT @%' AND length(p.content) > 50
         ORDER BY random() LIMIT 2)
        UNION ALL
        (SELECT p.id, p.content, d.full_name, d.rol_politico, sp.platform::text, d.org_id, d.id
         FROM social_posts p JOIN social_profiles sp ON p.profile_id = sp.id JOIN dirigentes d ON sp.dirigente_id = d.id
         WHERE d.id = 2 AND length(p.content) > 50 ORDER BY random() LIMIT 2)
        UNION ALL
        (SELECT p.id, p.content, d.full_name, d.rol_politico, sp.platform::text, d.org_id, d.id
         FROM social_posts p JOIN social_profiles sp ON p.profile_id = sp.id JOIN dirigentes d ON sp.dirigente_id = d.id
         WHERE d.id = 6 AND p.content NOT LIKE 'RT @%' AND length(p.content) > 50 ORDER BY random() LIMIT 2)
        UNION ALL
        (SELECT p.id, p.content, d.full_name, d.rol_politico, sp.platform::text, d.org_id, d.id
         FROM social_posts p JOIN social_profiles sp ON p.profile_id = sp.id JOIN dirigentes d ON sp.dirigente_id = d.id
         WHERE d.id = 3 AND p.raw_data->>'transcribed' = 'true' AND length(p.content) > 80 ORDER BY random() LIMIT 2)
        UNION ALL
        (SELECT p.id, p.content, d.full_name, d.rol_politico, sp.platform::text, d.org_id, d.id
         FROM social_posts p JOIN social_profiles sp ON p.profile_id = sp.id JOIN dirigentes d ON sp.dirigente_id = d.id
         WHERE p.content LIKE 'RT @%' AND length(p.content) > 50 ORDER BY random() LIMIT 2)
    """)
    posts = cur.fetchall()[:N_POSTS]

    matrix_cache: dict[int, list[dict]] = {}

    print("# Pilot v2 — Gemma compact + Python matrix\n")
    print(f"**Modelo:** {MODEL} · **Prompt:** v2 compacto (~300 tokens)")
    print("**Arquitectura:** LLM clasifica tono+target · Python aplica matriz del tenant\n")
    print("---\n")

    times = []
    for idx, (post_id, content, nombre, rol, platform, org_id, _d_id) in enumerate(posts, 1):
        if org_id not in matrix_cache:
            matrix_cache[org_id] = get_effective_matrix(cur, org_id)
        matriz = matrix_cache[org_id]

        prompt = build_prompt(texto=content, plataforma=platform)

        try:
            raw, elapsed = call_gemma(prompt)
            parsed = parse_response(raw)
        except Exception as e:
            raw, elapsed, parsed = f"ERROR: {type(e).__name__}: {str(e)[:80]}", 0, None

        times.append(elapsed)

        print(f"## Post #{idx} — {nombre} ({rol}, {platform})")
        print(f"**ID:** {post_id} · **Gemma:** {elapsed:.1f}s")
        print(f"**Texto:** {content[:300].replace(chr(10), ' ')}\n")
        if parsed:
            score, desc = apply_matrix(rol, parsed["tono"], parsed["target"], matriz)
            sign = "+" if score > 0 else ""
            print(f"- **Gemma**: tono=`{parsed['tono']}` · target=`{parsed['target']}` · es_rt={parsed['es_rt']}")
            print(f"- **Razón Gemma**: _{parsed.get('razon','')}_")
            print(f"- **Score político (Python):** **{sign}{score}** — {desc or '(caso no en matriz → 0)'}")
        else:
            print(f"- **❌ Parse failed.** Raw: `{raw[:200]}`")
        print("\n---\n")
        sys.stdout.flush()

    print(f"\n**Tiempo promedio:** {sum(times)/max(len(times),1):.1f}s · **Total:** {sum(times):.0f}s")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
