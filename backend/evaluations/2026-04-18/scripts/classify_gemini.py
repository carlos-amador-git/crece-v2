"""Clasifica los 60 comments de sample_60.jsonl con Gemini CLI (headless -p).

Usa el prompt congelado (mismo que Gemma/Claude). Output: sample_60_gemini.jsonl.
No ve output de Claude ni de Gemma.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent.parent
SAMPLE_PATH = EVAL_DIR / "data" / "sample_60.jsonl"
OUT_PATH = EVAL_DIR / "data" / "sample_60_gemini.jsonl"

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


def already_done() -> set[str]:
    if not OUT_PATH.exists():
        return set()
    return {json.loads(l)["id"] for l in OUT_PATH.read_text().strip().split("\n") if l}


def call_gemini(prompt: str, timeout: int = 120) -> str:
    result = subprocess.run(
        ["gemini", "-p", prompt],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return (result.stdout or "") + ("\n" + result.stderr if result.returncode != 0 else "")


def parse_json_from_response(text: str) -> dict | None:
    # 1) Bloque ```json ... ```
    fenced = re.search(r"```json\s*(\{.+?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else None
    if not candidate:
        # 2) Bloque de cualquier fence
        fenced_any = re.search(r"```\s*(\{.+?\})\s*```", text, re.DOTALL)
        candidate = fenced_any.group(1) if fenced_any else None
    if not candidate:
        # 3) Primer objeto JSON balanceado greedy
        m = re.search(r"\{[\s\S]+\}", text)
        candidate = m.group(0) if m else None
    if not candidate:
        return None
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def classify(comment: dict) -> dict:
    prompt = PROMPT_TEMPLATE.format(
        post_text=(comment.get("post_text") or "(sin contexto)")[:200],
        plataforma=comment["plataforma"],
        comment_text=comment["comment_text"],
    )
    try:
        raw = call_gemini(prompt)
    except subprocess.TimeoutExpired:
        return {"_err": "timeout"}
    parsed = parse_json_from_response(raw)
    if parsed is None:
        return {"_err": "no_json", "_raw": raw[:200]}
    return parsed


def normalize_row(comment: dict, classification: dict) -> dict:
    return {
        "id": comment["id"],
        "source_model": "gemini-cli",
        "tono": classification.get("tono"),
        "target": classification.get("target"),
        "intensidad": classification.get("intensidad"),
        "polaridad_preliminar": classification.get("polaridad_preliminar"),
        "razon_corta": (classification.get("razon_corta") or "")[:500],
        "classified_at": datetime.utcnow().isoformat(),
        "_err": classification.get("_err"),
    }


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    samples = [json.loads(l) for l in SAMPLE_PATH.read_text().strip().split("\n")]
    done = already_done()
    pending = [s for s in samples if s["id"] not in done]
    if limit:
        pending = pending[:limit]
    print(f"Total: {len(samples)} | done: {len(done)} | pending: {len(pending)}")

    t0 = datetime.utcnow()
    for i, c in enumerate(pending, 1):
        cls = classify(c)
        row = normalize_row(c, cls)
        with OUT_PATH.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        err = row.get("_err")
        marker = "ERR" if err else "ok"
        print(f"  [{i}/{len(pending)}] {marker} {c['id'][:40]}")

    dur = (datetime.utcnow() - t0).total_seconds()
    print(f"Done en {dur:.0f}s")


if __name__ == "__main__":
    main()
