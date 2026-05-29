"""cross_audit_nlp_gemini.py — Cross-audit NLP via Gemini CLI

Pasa una muestra random de comments YA clasificados (por CC o framework) a
Gemini CLI con el mismo prompt de matriz polaridad. Compara CC vs Gemini y
reporta tasas de acuerdo + tabla de discrepancias.

Gemini opera como JUEZ INDEPENDIENTE. No escribe a BD. Solo genera reporte
markdown en `.context/cross_audit_gemini_d{did}_{ts}.md`.

Threshold de aceptacion:
- agreement_full (tono + target) >= 85% -> matriz v2 valida
- agreement_polaridad (signo) >= 90% -> sin bias sistematico

Uso (desde HOST, fuera del container):
  python backend/scripts/cross_audit_nlp_gemini.py \\
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
    DB_URL,
    build_batch_prompt,
    parse_array_response,
    validate_item,
)

GEMINI_BIN = os.environ.get("GEMINI_BIN", "/Users/marxchavez/.claude/bin/gemini-clean")
DEFAULT_TIMEOUT_GEMINI = int(os.environ.get("GEMINI_TIMEOUT", "180"))
REPORT_DIR = Path(".context")


def call_gemini(prompt: str, timeout: int = DEFAULT_TIMEOUT_GEMINI) -> str | None:
    if not Path(GEMINI_BIN).exists():
        print(f"  [Gemini] binary not found at {GEMINI_BIN}", file=sys.stderr)
        return None
    try:
        result = subprocess.run(
            [GEMINI_BIN, "--mode", "analyze", "--prompt", prompt],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            print(f"  [Gemini] stderr: {result.stderr[:200]}", file=sys.stderr)
            return None
        return result.stdout
    except subprocess.TimeoutExpired:
        print(f"  [Gemini] timeout {timeout}s", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  [Gemini] error: {e}", file=sys.stderr)
        return None


def fetch_sample(conn, dirigente_id: int, sample_size: int, seed: int) -> list[dict]:
    """Random sample reproducible de comments clasificados con LLM (no heuristica)."""
    with conn.cursor() as cur:
        # setseed acepta [-1, 1]; normalizamos
        cur.execute("SELECT setseed(%s)", (max(-1.0, min(1.0, seed / 2**31)),))
        cur.execute(
            """
            SELECT sc.id, sc.content,
                   sc.nlp_tono, sc.nlp_target, sc.nlp_polaridad,
                   sc.nlp_model_version
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
        {
            "id": r[0],
            "content": r[1],
            "cc_tono": r[2],
            "cc_target": r[3],
            "cc_polaridad": r[4],
            "cc_model_version": r[5],
        }
        for r in rows
    ]


def process_audit_batch(batch: list[dict]) -> list[dict]:
    """Pide a Gemini que clasifique el batch. Retorna comparativo (CC vs Gemini)."""
    prompt = build_batch_prompt(batch)
    raw = call_gemini(prompt)
    results: list[dict] = []
    if raw is None:
        for c in batch:
            results.append({**c, "gemini_tono": None, "gemini_target": None,
                            "gemini_polaridad": None, "gemini_parse_failed": True})
        return results

    parsed = parse_array_response(raw)
    if not parsed:
        print(f"  [batch] Gemini parse failed. Raw: {raw[:200]}", file=sys.stderr)
        for c in batch:
            results.append({**c, "gemini_tono": None, "gemini_target": None,
                            "gemini_polaridad": None, "gemini_parse_failed": True})
        return results

    for i, comment in enumerate(batch):
        if i >= len(parsed):
            results.append({**comment, "gemini_tono": None, "gemini_target": None,
                            "gemini_polaridad": None, "gemini_parse_failed": True})
            continue
        item = parsed[i]
        if isinstance(item, dict) and item.get("id") != comment["id"]:
            matching = [x for x in parsed
                        if isinstance(x, dict) and x.get("id") == comment["id"]]
            if matching:
                item = matching[0]
        validated = validate_item(item, comment["id"])
        if not validated:
            results.append({**comment, "gemini_tono": None, "gemini_target": None,
                            "gemini_polaridad": None, "gemini_parse_failed": True})
            continue
        results.append({
            **comment,
            "gemini_tono": validated["tono"],
            "gemini_target": validated["target"],
            "gemini_polaridad": validated["polaridad"],
            "gemini_parse_failed": False,
        })
    return results


def compute_metrics(comparisons: list[dict]) -> dict:
    n_total = len(comparisons)
    if not n_total:
        return {"n_total": 0}
    valid = [c for c in comparisons if not c.get("gemini_parse_failed")]
    n_valid = len(valid)
    n_tono = sum(1 for c in valid if c["gemini_tono"] == c["cc_tono"])
    n_target = sum(1 for c in valid if c["gemini_target"] == c["cc_target"])
    n_pol = sum(1 for c in valid if c["gemini_polaridad"] == c["cc_polaridad"])
    n_full = sum(1 for c in valid
                 if c["gemini_tono"] == c["cc_tono"]
                 and c["gemini_target"] == c["cc_target"])
    pct = lambda x: f"{100*x/n_valid:.1f}%" if n_valid else "n/a"
    return {
        "n_total": n_total,
        "n_valid": n_valid,
        "n_invalid": n_total - n_valid,
        "n_agree_tono": n_tono,
        "n_agree_target": n_target,
        "n_agree_polaridad": n_pol,
        "n_agree_full": n_full,
        "agreement_tono": pct(n_tono),
        "agreement_target": pct(n_target),
        "agreement_polaridad": pct(n_pol),
        "agreement_full": pct(n_full),
    }


def write_report(dirigente_id: int, sample_size: int, seed: int,
                 metrics: dict, discrepancies: list[dict]) -> Path:
    REPORT_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    report_path = REPORT_DIR / f"cross_audit_gemini_d{dirigente_id}_{ts}.md"

    lines = [
        f"# Cross-audit NLP · Dirigente {dirigente_id} · {ts}",
        "",
        f"**Sample size pedido:** {sample_size} · **Seed:** {seed}",
        "",
        "## Metrics",
        "",
        f"- Total muestreados: **{metrics['n_total']}**",
        f"- Gemini parse OK: **{metrics['n_valid']}** · parse fail: {metrics['n_invalid']}",
        f"- Acuerdo tono: **{metrics['agreement_tono']}** ({metrics['n_agree_tono']}/{metrics['n_valid']})",
        f"- Acuerdo target: **{metrics['agreement_target']}** ({metrics['n_agree_target']}/{metrics['n_valid']})",
        f"- Acuerdo polaridad signo: **{metrics['agreement_polaridad']}** ({metrics['n_agree_polaridad']}/{metrics['n_valid']})",
        f"- Acuerdo total (tono+target): **{metrics['agreement_full']}** ({metrics['n_agree_full']}/{metrics['n_valid']})",
        "",
        "## Threshold de aceptacion",
        "",
        "- `agreement_full >= 85%` -> matriz v2 valida sin cambios",
        "- `agreement_polaridad >= 90%` -> sin bias sistematico de signo",
        "- Por debajo de cualquiera -> revisar matriz o re-entrenar",
        "",
        "## Discrepancias",
        "",
    ]
    if not discrepancies:
        lines.append("_Cero discrepancias en esta muestra._")
    else:
        lines.append("| id | content (60c) | CC tono/target/pol | Gemini tono/target/pol |")
        lines.append("|---|---|---|---|")
        for c in discrepancies[:80]:
            content = (c["content"] or "")[:60].replace("|", "·").replace("\n", " ")
            cc = f"{c['cc_tono']}/{c['cc_target']}/{c['cc_polaridad']:+d}"
            gp = c.get("gemini_polaridad")
            gp_str = f"{gp:+d}" if gp is not None else "?"
            gem = f"{c.get('gemini_tono','?')}/{c.get('gemini_target','?')}/{gp_str}"
            lines.append(f"| {c['id']} | {content} | {cc} | {gem} |")
        if len(discrepancies) > 80:
            lines.append(f"\n_... y {len(discrepancies)-80} mas (capeado para legibilidad)._")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dirigente-id", type=int, default=3)
    parser.add_argument("--sample-size", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batch", type=int, default=5)
    args = parser.parse_args()

    print(f"Cross-audit dirigente={args.dirigente_id} "
          f"sample={args.sample_size} seed={args.seed}")

    with psycopg.connect(DB_URL) as conn:
        sample = fetch_sample(conn, args.dirigente_id, args.sample_size, args.seed)
    print(f"Sampled {len(sample)} comments de BD")
    if not sample:
        print("Empty sample. Abort.")
        return

    comparisons: list[dict] = []
    total_batches = (len(sample) + args.batch - 1) // args.batch
    for i in range(0, len(sample), args.batch):
        chunk = sample[i:i + args.batch]
        batch_no = i // args.batch + 1
        print(f"  [batch {batch_no}/{total_batches}] ids={[c['id'] for c in chunk]}")
        comparisons.extend(process_audit_batch(chunk))

    discrepancies = [
        c for c in comparisons
        if not c.get("gemini_parse_failed")
        and (c["gemini_tono"] != c["cc_tono"] or c["gemini_target"] != c["cc_target"])
    ]
    metrics = compute_metrics(comparisons)
    report_path = write_report(args.dirigente_id, args.sample_size, args.seed,
                               metrics, discrepancies)

    print("\n=== REPORTE ===")
    print(f"Total: {metrics['n_total']} (validos: {metrics['n_valid']})")
    print(f"Acuerdo tono:           {metrics['agreement_tono']}")
    print(f"Acuerdo target:         {metrics['agreement_target']}")
    print(f"Acuerdo polaridad:      {metrics['agreement_polaridad']}")
    print(f"Acuerdo full (t+t):     {metrics['agreement_full']}")
    print(f"Discrepancias: {len(discrepancies)}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
