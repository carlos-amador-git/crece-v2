"""NLP Layer 2 background — Gemma3 12b local sobre los 1,100 comments de hoy.

Clasifica cada comment en 3 dimensiones:
  - tono: elogio | critica | pregunta | ataque | informativo | personal | autopromocion
  - target: dirigente_post | gobierno | oposicion | ciudadania | institucion | otros
  - intensidad: -3 a +3

Output: JSON con comment_id + clasificaciones, append-only.
Costo: $0 (Ollama local). Velocidad: ~4-6 min/post → ~80h para 1,100. Idempotente.
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

RESULTS_DIR = Path(__file__).resolve().parent.parent / "benchmarks/scraping/results/2026-04-19"
OUT_PATH = RESULTS_DIR / "nlp_layer2_gemma_out.jsonl"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma3:12b"

PROMPT_TEMPLATE = """Eres un analista de sentimiento político mexicano. Clasifica este comentario.

CONTEXTO:
- Post original (del político): {post_text}
- Plataforma: {plataforma}

COMENTARIO:
"{comment_text}"

Responde SOLO en JSON válido con estos campos:
{{
  "tono": "elogio|critica|pregunta|ataque|informativo|personal|autopromocion",
  "target": "dirigente_post|gobierno|oposicion|ciudadania|institucion|otros",
  "intensidad": -3 a 3 (entero),
  "polaridad_preliminar": "aprobacion|neutral|rechazo",
  "razon_corta": "una frase"
}}
"""


def load_all_comments() -> list[dict]:
    """Junta todos los comments de los JSONs Apify con contexto."""
    out = []
    # X replies (per-handle, excluir _all)
    for p in RESULTS_DIR.glob("apify_replies_*.json"):
        if p.stem.endswith("_all"):
            continue
        handle = p.stem.replace("apify_replies_", "")
        data = json.loads(p.read_text())
        if not isinstance(data, list):
            continue
        for r in data:
            if not isinstance(r, dict):
                continue
            out.append({
                "id": f"X_{r.get('id','')}",
                "plataforma": "X",
                "handle_dirigente": handle,
                "comment_text": (r.get("text") or "")[:300],
                "post_text": (r.get("inReplyToId") or ""),
                "author": r.get("author.userName") or "",
                "likes": r.get("likeCount") or 0,
            })
    # IG inline comments
    for p in RESULTS_DIR.glob("apify_ig_*.json"):
        handle = p.stem.replace("apify_ig_", "")
        for post in json.loads(p.read_text()):
            if post.get("ownerUsername") != handle:
                continue
            post_caption = (post.get("caption") or "")[:300]
            for c in (post.get("latestComments") or []):
                out.append({
                    "id": f"IG_{post.get('id','')}_{c.get('id','')}",
                    "plataforma": "Instagram",
                    "handle_dirigente": handle,
                    "comment_text": (c.get("text") or "")[:300],
                    "post_text": post_caption,
                    "author": c.get("ownerUsername") or "",
                    "likes": c.get("likesCount") or 0,
                })
    return out


def already_processed() -> set[str]:
    if not OUT_PATH.exists():
        return set()
    return {json.loads(L)["id"] for L in OUT_PATH.read_text().strip().split("\n") if L}


def classify(comment: dict) -> dict | None:
    prompt = PROMPT_TEMPLATE.format(
        post_text=comment["post_text"][:200] or "(sin contexto)",
        plataforma=comment["plataforma"],
        comment_text=comment["comment_text"],
    )
    try:
        r = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False, "format": "json"},
            timeout=300,
        )
        if r.status_code != 200:
            return {"_err": f"HTTP {r.status_code}"}
        data = r.json()
        resp_text = data.get("response", "")
        # Gemma devuelve JSON en format mode
        try:
            parsed = json.loads(resp_text)
        except json.JSONDecodeError:
            # fallback: extract first {...} block
            m = re.search(r"\{[^{}]*\}", resp_text, re.DOTALL)
            parsed = json.loads(m.group()) if m else {"_raw": resp_text[:200]}
        return parsed
    except Exception as e:
        return {"_err": f"{type(e).__name__}: {e}"}


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0  # 0 = todos
    comments = load_all_comments()
    done = already_processed()
    pending = [c for c in comments if c["id"] not in done]
    if limit:
        pending = pending[:limit]
    print(f"Total: {len(comments)} | Ya procesados: {len(done)} | Pending: {len(pending)}")

    t0 = time.time()
    for i, c in enumerate(pending, 1):
        result = classify(c)
        row = {
            "id": c["id"],
            "handle_dirigente": c["handle_dirigente"],
            "plataforma": c["plataforma"],
            "comment_text": c["comment_text"],
            "author": c["author"],
            "classification": result,
            "classified_at": datetime.utcnow().isoformat(),
        }
        with OUT_PATH.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        elapsed = time.time() - t0
        avg = elapsed / i
        eta_min = (len(pending) - i) * avg / 60
        if i % 5 == 0 or i == 1:
            print(f"  [{i}/{len(pending)}] avg {avg:.1f}s/item · ETA {eta_min:.0f} min")


if __name__ == "__main__":
    main()
