"""audit_cc_effort_high.py — Re-clasifica la muestra cross-audit con CC effort=high

Toma el mismo seed=42 sample=50 de Saymi (dirigente_id=3) que uso
cross_audit_nlp_gemini.py, llama Claude Code subprocess con `--effort high`
(vs `low` del backfill), y compara nueva clasificacion CC vs lo stored
en BD. NO escribe a BD.

Objetivo: decidir si el sesgo "todo a personal/+0" del backfill era por
effort=low o por prompt/matriz estructural.

Uso (desde HOST):
  python backend/scripts/audit_cc_effort_high.py \\
      --dirigente-id 3 --sample-size 50 --seed 42
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import psycopg2 as psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backfill_nlp_saymi import (  # type: ignore[import-not-found]
    CLAUDE_BIN,
    DB_URL,
    build_batch_prompt,
    parse_array_response,
    validate_item,
)

REPORT_DIR = Path(".context")
TIMEOUT_CC_HIGH = int(os.environ.get("CC_HIGH_TIMEOUT", "600"))  # high tarda mas


def call_cc_high(prompt: str, timeout: int = TIMEOUT_CC_HIGH) -> str | None:
    if not Path(CLAUDE_BIN).exists():
        print(f"  [CC] binary not found at {CLAUDE_BIN}", file=sys.stderr)
        return None
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "--print", "--effort", "high", prompt],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            print(f"  [CC-high] stderr: {result.stderr[:200]}", file=sys.stderr)
            return None
        return result.stdout
    except subprocess.TimeoutExpired:
        print(f"  [CC-high] timeout {timeout}s", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  [CC-high] error: {e}", file=sys.stderr)
        return None


def fetch_sample(conn, dirigente_id: int, sample_size: int, seed: int) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute("SELECT setseed(%s)", (max(-1.0, min(1.0, seed / 2**31)),))
        cur.execute(
            """
            SELECT sc.id, sc.content,
                   sc.nlp_tono, sc.nlp_target, sc.nlp_polaridad
            FROM social_comments sc
            JOIN social_posts sp ON sc.parent_post_id = sp.id
            JOIN social_profiles spr ON sp.profile_id = spr.id
            WHERE spr.dirigente_id = %s
              AND sc.nlp_tono IS NOT NULL
              AND sc.content IS NOT NULL
              AND LENGTH(sc.content) > 3
              AND sc.nlp_model_version NOT LIKE 'heuristic-%%'
            ORDER BY random()
            LIMIT %s
            """,
            (dirigente_id, sample_size),
        )
        rows = cur.fetchall()
    return [
        {"id": r[0], "content": r[1],
         "stored_tono": r[2], "stored_target": r[3], "stored_polaridad": r[4]}
        for r in rows
    ]


def process_batch(batch: list[dict]) -> list[dict]:
    prompt = build_batch_prompt(batch)
    raw = call_cc_high(prompt)
    out: list[dict] = []
    if raw is None:
        for c in batch:
            out.append({**c, "new_tono": None, "new_target": None,
                        "new_polaridad": None, "fail": True})
        return out
    parsed = parse_array_response(raw)
    if not parsed:
        print(f"  [batch] CC-high parse failed. Raw: {raw[:200]}", file=sys.stderr)
        for c in batch:
            out.append({**c, "new_tono": None, "new_target": None,
                        "new_polaridad": None, "fail": True})
        return out

    for i, c in enumerate(batch):
        if i >= len(parsed):
            out.append({**c, "new_tono": None, "new_target": None,
                        "new_polaridad": None, "fail": True})
            continue
        item = parsed[i]
        if isinstance(item, dict) and item.get("id") != c["id"]:
            matching = [x for x in parsed if isinstance(x, dict) and x.get("id") == c["id"]]
            if matching:
                item = matching[0]
        v = validate_item(item, c["id"])
        if not v:
            out.append({**c, "new_tono": None, "new_target": None,
                        "new_polaridad": None, "fail": True})
            continue
        out.append({**c, "new_tono": v["tono"], "new_target": v["target"],
                    "new_polaridad": v["polaridad"], "fail": False})
    return out


def write_report(dirigente_id: int, sample_size: int, seed: int,
                 results: list[dict]) -> Path:
    REPORT_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    path = REPORT_DIR / f"audit_cc_effort_high_d{dirigente_id}_{ts}.md"

    valid = [r for r in results if not r.get("fail")]
    n_total = len(results)
    n_valid = len(valid)
    n_changed = sum(1 for r in valid if r["new_tono"] != r["stored_tono"]
                    or r["new_target"] != r["stored_target"])
    n_pol_changed = sum(1 for r in valid if r["new_polaridad"] != r["stored_polaridad"])
    n_critico_detected = sum(1 for r in valid
                              if r["new_tono"] in ("critico", "ataque")
                              and r["stored_tono"] not in ("critico", "ataque"))
    n_personal_to_celeb = sum(1 for r in valid
                              if r["stored_tono"] == "personal"
                              and r["new_tono"] == "celebratorio")

    pct = lambda x: f"{100*x/n_valid:.1f}%" if n_valid else "n/a"

    lines = [
        f"# Audit CC effort=high · Dirigente {dirigente_id} · {ts}",
        "",
        f"**Sample:** {sample_size} · **Seed:** {seed} · **CC effort:** high",
        "",
        "## Comparativo CC-high (nuevo) vs CC-stored (effort=low del backfill)",
        "",
        f"- Total muestreados: **{n_total}** · CC-high parse OK: **{n_valid}** · fail: {n_total - n_valid}",
        f"- **Comments con clasificacion distinta:** {n_changed} ({pct(n_changed)})",
        f"- **Comments con polaridad signo distinta:** {n_pol_changed} ({pct(n_pol_changed)})",
        f"- **Criticas detectadas por CC-high pero NO por CC-low:** {n_critico_detected}",
        f"- **Pasaron de personal -> celebratorio:** {n_personal_to_celeb}",
        "",
        "## Diagnostico empirico",
        "",
        "- Si `criticas detectadas` >= 5 -> bug era effort=low, fix = re-correr backfill con effort=high",
        "- Si `criticas detectadas` < 3 y `cambios totales` < 30% -> bug es estructural (prompt/matriz), needs opcion b",
        "- Si ambos altos -> ambos problemas existen, fix combinado",
        "",
        "## Tabla completa",
        "",
        "| id | content (60c) | CC-low stored | CC-high nuevo | cambio? |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        content = (r["content"] or "")[:60].replace("|", "·").replace("\n", " ")
        stored = f"{r['stored_tono']}/{r['stored_target']}/{r['stored_polaridad']:+d}"
        if r.get("fail"):
            new = "FAIL"
            changed = "?"
        else:
            np = r["new_polaridad"]
            new = f"{r['new_tono']}/{r['new_target']}/{np:+d}"
            changed = "✓" if (r["new_tono"] != r["stored_tono"]
                              or r["new_target"] != r["stored_target"]) else "—"
        lines.append(f"| {r['id']} | {content} | {stored} | {new} | {changed} |")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dirigente-id", type=int, default=3)
    parser.add_argument("--sample-size", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batch", type=int, default=5)
    args = parser.parse_args()

    print(f"Audit CC effort=high dirigente={args.dirigente_id} "
          f"sample={args.sample_size} seed={args.seed}")

    with psycopg.connect(DB_URL) as conn:
        sample = fetch_sample(conn, args.dirigente_id, args.sample_size, args.seed)
    print(f"Sampled {len(sample)} comments de BD")
    if not sample:
        print("Empty sample. Abort.")
        return

    results: list[dict] = []
    total_batches = (len(sample) + args.batch - 1) // args.batch
    for i in range(0, len(sample), args.batch):
        chunk = sample[i:i + args.batch]
        batch_no = i // args.batch + 1
        print(f"  [batch {batch_no}/{total_batches}] ids={[c['id'] for c in chunk]}")
        results.extend(process_batch(chunk))

    valid = [r for r in results if not r.get("fail")]
    n_changed = sum(1 for r in valid if r["new_tono"] != r["stored_tono"]
                    or r["new_target"] != r["stored_target"])
    n_critico = sum(1 for r in valid
                    if r["new_tono"] in ("critico", "ataque")
                    and r["stored_tono"] not in ("critico", "ataque"))

    path = write_report(args.dirigente_id, args.sample_size, args.seed, results)

    print("\n=== RESUMEN ===")
    print(f"Cambios totales: {n_changed}/{len(valid)}")
    print(f"Criticas detectadas por effort=high (no detectadas antes): {n_critico}")
    print(f"Report: {path}")


if __name__ == "__main__":
    main()
