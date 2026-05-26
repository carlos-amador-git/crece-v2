"""post_ingest_enrich.py · 2026-05-26

Cadena de enriquecimiento NLP por-dirigente, a correr DESPUÉS de ingestar datos
nuevos (RADAR/Apify). Orquesta los scripts de backfill existentes en orden —
NO reimplementa NLP. Cada paso es idempotente (WHERE campo IS NULL) → re-correr
solo procesa el delta nuevo.

Decisión CEO 2026-05-26 (opción A · "Calidad>Tiempo, Eficiencia>Tiempo"): un solo
comando reusable en vez de backfills manuales sueltos.

Pasos (en orden):
  1. Posts NLP        → tono_discurso + target_politico   (backfill_nlp_posts)
  2. Comments NLP     → nlp_tono + nlp_target + nlp_polaridad (backfill_nlp_saymi, generalizado)
  3. Emotions posts   → social_posts.emotions             (backfill_emotions_cc --type posts)
  4. Emotions comments→ social_comments.emotions          (backfill_emotions_cc --type comments)
  5. Topics           → topics_extracted                  (extract_topics_saymi_cc, generalizado)

ER y author_hash NO van aquí: ya nacen limpios en el ingest (event listener +
guard, 2026-05-26). Sentiment_score/label se computa vía analyze_sentiment
(Celery) — pendiente confirmar cobertura post-ingest RADAR (ver NOTA).

Uso (HOST · claude CLI vive en el host):
    python3 backend/scripts/post_ingest_enrich.py --dirigente-id 1 --dry-run
    python3 backend/scripts/post_ingest_enrich.py --dirigente-id 1 --limit 1000

NOTA sentiment: si tras E2E con Piña se ve sentiment_score NULL, agregar paso 0
que despache analyze_sentiment o un backfill de sentiment. Confirmar con datos reales.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable


def _step(label: str, script: str, extra: list[str], dirigente_id: int, dry_run: bool) -> tuple[str, bool]:
    cmd = [PYTHON, str(SCRIPTS_DIR / script), "--dirigente-id", str(dirigente_id), *extra]
    if dry_run:
        cmd.append("--dry-run")
    print(f"\n{'='*60}\n▶ {label}\n  {' '.join(cmd)}\n{'='*60}", flush=True)
    t0 = time.monotonic()
    r = subprocess.run(cmd, text=True)
    ok = r.returncode == 0
    print(f"  ← {label}: {'OK' if ok else 'FALLÓ (returncode %d)' % r.returncode} · {time.monotonic()-t0:.0f}s", flush=True)
    return label, ok


def main() -> int:
    p = argparse.ArgumentParser(description="Cadena de enriquecimiento NLP por dirigente")
    p.add_argument("--dirigente-id", type=int, required=True)
    p.add_argument("--limit", type=int, default=2000, help="límite por paso")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    did = args.dirigente_id
    lim = ["--limit", str(args.limit)]
    print(f"\n=== post_ingest_enrich · dirigente={did} · limit/paso={args.limit} · dry={args.dry_run} ===")

    steps = [
        ("1. Posts NLP (tono+target)", "backfill_nlp_posts.py", lim),
        ("2. Comments NLP (tono+target+polaridad)", "backfill_nlp_saymi.py", lim),
        ("3. Emotions posts", "backfill_emotions_cc.py", [*lim, "--type", "posts"]),
        ("4. Emotions comments", "backfill_emotions_cc.py", [*lim, "--type", "comments"]),
        ("5. Topics", "extract_topics_saymi_cc.py", lim),
    ]

    results = [_step(lbl, scr, extra, did, args.dry_run) for lbl, scr, extra in steps]

    print(f"\n{'='*60}\nRESUMEN · dirigente {did}")
    all_ok = True
    for lbl, ok in results:
        print(f"  {'✓' if ok else '✗'} {lbl}")
        all_ok = all_ok and ok
    print(f"{'='*60}")
    if not all_ok:
        print("Algún paso falló — re-correr es seguro (idempotente, salta lo ya hecho).")
        return 1
    print("Cadena completa. Cards B0x/B14/B08/FODA leen el dato enriquecido on-read.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
