"""T0.4 - Clasificador Gemma3:12b via Ollama (Plutchik + Topics).

Endpoint primario: http://163.245.208.96:11434 (Coolify VPS)
Fallback: http://localhost:11434

Salida: one JSON row per comment en sample_60_gemma.jsonl
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

RESEARCH_DIR = Path("/Users/marxchavez/Projects/crece-v2/backend/research/2026-04-19")
SAMPLE_PATH = Path(
    "/Users/marxchavez/Projects/crece-v2/backend/evaluations/2026-04-18/data/sample_60.jsonl"
)
OUT_PATH = RESEARCH_DIR / "data" / "sample_60_gemma.jsonl"
PROMPT_PATH = RESEARCH_DIR / "t04_prompt.txt"

PRIMARY_URL = "http://localhost:11434/api/generate"
FALLBACK_URL = "http://163.245.208.96:11434/api/generate"
MODEL = "gemma3:12b"
TEMPERATURE = 0.0
SEED = 42

VALID_EMOCION = {"trust", "anger", "joy", "fear", "sadness", "disgust"}
VALID_TOPICS = {
    "economia", "seguridad", "educacion", "salud", "corrupcion", "movilidad",
    "genero", "medioambiente", "gobierno", "politica_electoral", "institucional", "otro",
}


def load_prompt_template() -> str:
    return PROMPT_PATH.read_text()


def already_done() -> set[str]:
    if not OUT_PATH.exists():
        return set()
    done = set()
    for line in OUT_PATH.read_text().strip().splitlines():
        if not line:
            continue
        try:
            done.add(json.loads(line)["id"])
        except Exception:
            continue
    return done


def parse_json(text: str) -> dict | None:
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]+?\})\s*```", text)
    cand = fenced.group(1) if fenced else None
    if not cand:
        m = re.search(r"\{[\s\S]+\}", text)
        cand = m.group(0) if m else None
    if not cand:
        return None
    try:
        return json.loads(cand)
    except json.JSONDecodeError:
        cand2 = re.sub(r",\s*([\]\}])", r"\1", cand)
        try:
            return json.loads(cand2)
        except json.JSONDecodeError:
            return None


def call_ollama(url: str, prompt: str, timeout: float = 90.0) -> str:
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": TEMPERATURE, "seed": SEED, "num_predict": 256},
        "format": "json",
    }
    r = httpx.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json().get("response", "")


def classify(comment: dict, template: str) -> dict:
    prompt = template.format(
        post_text=(comment.get("post_text") or "(sin contexto)")[:200],
        plataforma=comment["plataforma"],
        comment_text=comment["comment_text"],
    )
    err = None
    raw = ""
    for url in (PRIMARY_URL, FALLBACK_URL):
        try:
            raw = call_ollama(url, prompt)
            break
        except Exception as e:
            err = f"{url}: {type(e).__name__}: {e}"
            continue
    else:
        return {"_err": f"all_endpoints_failed: {err}", "_raw": ""}

    parsed = parse_json(raw) or {}
    emocion = (parsed.get("emocion") or "").strip().lower()
    topics_raw = parsed.get("topics") or []
    if isinstance(topics_raw, str):
        topics_raw = [topics_raw]
    topics = [t.strip().lower() for t in topics_raw if isinstance(t, str)]
    topics = [t for t in topics if t in VALID_TOPICS][:3]
    if emocion not in VALID_EMOCION:
        emocion = None
    if not topics:
        topics = ["otro"] if not parsed else []
    return {
        "emocion": emocion,
        "topics": topics,
        "_raw": raw[:500],
    }


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    samples = [
        json.loads(l) for l in SAMPLE_PATH.read_text().strip().splitlines() if l
    ]
    done = already_done()
    pending = [s for s in samples if s["id"] not in done]
    if limit:
        pending = pending[:limit]
    template = load_prompt_template()
    print(f"gemma3:12b | total={len(samples)} done={len(done)} pending={len(pending)}")

    t0 = time.time()
    for i, c in enumerate(pending, 1):
        cls = classify(c, template)
        row = {
            "id": c["id"],
            "source_model": "gemma3:12b",
            "emocion": cls.get("emocion"),
            "topics": cls.get("topics"),
            "_err": cls.get("_err"),
            "classified_at": datetime.now(UTC).isoformat(),
        }
        with OUT_PATH.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        mark = "ERR" if row.get("_err") else "ok"
        print(f"  [{i:02d}/{len(pending)}] {mark} {row['emocion']} {row['topics']}")

    dur = time.time() - t0
    print(f"Done {len(pending)} rows in {dur:.0f}s ({dur/max(len(pending),1):.1f}s/row)")


if __name__ == "__main__":
    main()
