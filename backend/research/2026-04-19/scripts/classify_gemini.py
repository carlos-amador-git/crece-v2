"""T0.4 - Clasificador Gemini CLI (Plutchik + Topics) - proxy humano experto 1.

Usa gemini -p con el prompt congelado. Un call por comment.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

RESEARCH_DIR = Path("/Users/marxchavez/Projects/crece-v2/backend/research/2026-04-19")
SAMPLE_PATH = Path(
    "/Users/marxchavez/Projects/crece-v2/backend/evaluations/2026-04-18/data/sample_60.jsonl"
)
OUT_PATH = RESEARCH_DIR / "data" / "sample_60_gemini.jsonl"
PROMPT_PATH = RESEARCH_DIR / "t04_prompt.txt"

VALID_EMOCION = {"trust", "anger", "joy", "fear", "sadness", "disgust"}
VALID_TOPICS = {
    "economia", "seguridad", "educacion", "salud", "corrupcion", "movilidad",
    "genero", "medioambiente", "gobierno", "politica_electoral", "institucional", "otro",
}


def load_template() -> str:
    return PROMPT_PATH.read_text()


def already_done() -> set[str]:
    if not OUT_PATH.exists():
        return set()
    out = set()
    for l in OUT_PATH.read_text().splitlines():
        if not l:
            continue
        try:
            out.add(json.loads(l)["id"])
        except Exception:
            pass
    return out


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


def call_gemini(prompt: str, timeout: int = 120) -> str:
    r = subprocess.run(
        ["gemini", "-p", prompt],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return r.stdout or ""


def classify(comment: dict, template: str) -> dict:
    prompt = template.format(
        post_text=(comment.get("post_text") or "(sin contexto)")[:200],
        plataforma=comment["plataforma"],
        comment_text=comment["comment_text"],
    )
    try:
        raw = call_gemini(prompt)
    except subprocess.TimeoutExpired:
        return {"_err": "timeout"}
    except Exception as e:
        return {"_err": f"{type(e).__name__}: {e}"}
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
    return {"emocion": emocion, "topics": topics, "_raw": raw[:400]}


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    samples = [json.loads(l) for l in SAMPLE_PATH.read_text().splitlines() if l]
    done = already_done()
    pending = [s for s in samples if s["id"] not in done]
    if limit:
        pending = pending[:limit]
    tpl = load_template()
    print(f"gemini-cli | total={len(samples)} done={len(done)} pending={len(pending)}")
    t0 = time.time()
    for i, c in enumerate(pending, 1):
        cls = classify(c, tpl)
        row = {
            "id": c["id"],
            "source_model": "gemini-cli",
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
    print(f"Done in {dur:.0f}s")


if __name__ == "__main__":
    main()
