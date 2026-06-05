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
  4. Topics           → topics_extracted                  (extract_topics_saymi_cc, generalizado)

(emotions es post-level: social_comments NO tiene columna emotions.)

# ── CAMBIO PENDIENTE · ADR-0008 (Proposed, 2026-06-04) — aplicar en la PRÓXIMA
# actualización de dirigentes, NO re-correr sobre data actual ──────────────────
# POR QUÉ cambiamos: los pasos vía scripts `_cc` (claude --print subprocess) queman
# presupuesto del plan CC (prioridad #1 del CEO 2026-06-03). Cross-audit Gemini
# 2026-06-04 + lectura de analyzer.py confirman el routing correcto:
#   - Campos TEXTUALES (emotions paso 3, topics paso 4, sentiment, toxicity) → mover a
#     analyzer.analyze_full() LOCAL (HF transformers, $0, no Ollama, no viola ADR-0001).
#     Bug histórico: producción corrió analyze() básico, no analyze_full().
#   - Campos POLÍTICOS (paso 2: tono/target/polaridad de comments + tono/target posts)
#     SE QUEDAN en LLM pero BATCHEADO ~20 items/llamada (~95% menos consumo). El runner
#     LLM es irreemplazable: el matriz_v3_mapper exige labels de intención política;
#     sentiment local es ciego a la política (oposición criticando gobierno = NEG textual
#     pero polaridad política POSITIVA para el dirigente).
# ÁREA DE INVESTIGACIÓN FUTURA (CEO "no creo que sea así"): validar si la polaridad
# política puede derivarse local/barata (NER político + reglas) sin LLM. NO cerrado.
# Detalle completo: docs/adr/0008-nlp-routing-token-eficiente.md
# ───────────────────────────────────────────────────────────────────────────────

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
import os
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable

# Guard de recursos (capa runtime del enforcement · docs/adr/0006).
sys.path.insert(0, str(SCRIPTS_DIR))
from _guard_resources import guard_heavy_job  # noqa: E402

# SLO de cobertura de enriquecimiento (regla e · warn primero). Umbral configurable.
SLO_MIN_COVERAGE = float(os.environ.get("CRECE_SLO_MIN_COVERAGE", "0.70"))


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


def _report_slo(did: int) -> None:
    """SLO de cobertura post-enrich (regla e · warn). Mide cobertura TOTAL del
    dirigente (no del delta) — auditoría Gemini: en un delta chico la cobertura
    absoluta sigue siendo la métrica correcta. Defensivo: si no hay psycopg2 ni
    DATABASE_URL_SYNC en este entorno, avisa y sigue (no rompe el host CLI)."""
    url = os.environ.get("DATABASE_URL_SYNC")
    if not url:
        print("ℹ️  SLO: DATABASE_URL_SYNC no seteada en este entorno → no verificable aquí.")
        return
    try:
        import psycopg2  # type: ignore
    except ImportError:
        print("ℹ️  SLO: psycopg2 no disponible → cobertura no verificable aquí.")
        return
    try:
        conn = psycopg2.connect(url)
        with conn, conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FILTER (WHERE tono_discurso IS NOT NULL), count(*) "
                "FROM social_posts sp JOIN social_profiles spr ON sp.profile_id = spr.id "
                "WHERE spr.dirigente_id = %s", (did,))
            enriched, total = cur.fetchone()
        conn.close()
    except Exception as exc:  # noqa: BLE001
        print(f"ℹ️  SLO: no se pudo medir cobertura ({exc}).")
        return
    if not total:
        print(f"ℹ️  SLO: dirigente {did} sin posts → nada que medir.")
        return
    cov = enriched / total
    flag = "✓" if cov >= SLO_MIN_COVERAGE else "⚠️ "
    msg = (f"{flag} SLO cobertura tono_discurso dir {did}: {enriched}/{total} "
           f"({cov:.0%}) · umbral {SLO_MIN_COVERAGE:.0%}")
    print(msg)
    if cov < SLO_MIN_COVERAGE:
        print("   ⚠️  Cobertura bajo umbral — re-correr el enrich (idempotente) o "
              "investigar filas sin enriquecer. (warn, no bloquea · regla e)")


def main() -> int:
    p = argparse.ArgumentParser(description="Cadena de enriquecimiento NLP por dirigente")
    p.add_argument("--dirigente-id", type=int, required=True)
    p.add_argument("--limit", type=int, default=2000, help="límite por paso")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--allow-unattended", action="store_true",
                   help="permite correr sin TTY (background/cron). El crash RAM "
                        "2026-05-27 fue unattended — úsalo a conciencia.")
    args = p.parse_args()

    # Guard de recursos al arranque (RAM available macOS-aware + check unattended).
    if not args.dry_run:
        guard_heavy_job("post_ingest_enrich", allow_unattended=args.allow_unattended)

    did = args.dirigente_id
    lim = ["--limit", str(args.limit)]
    print(f"\n=== post_ingest_enrich · dirigente={did} · limit/paso={args.limit} · dry={args.dry_run} ===")

    # Nota: emotions es post-level (social_comments NO tiene columna emotions).
    steps = [
        ("1. Posts NLP (tono+target)", "backfill_nlp_posts.py", lim),
        ("2. Comments NLP (tono+target+polaridad)", "backfill_nlp_saymi.py", lim),
        ("3. Emotions posts", "backfill_emotions_cc.py", [*lim, "--type", "posts"]),
        ("4. Topics", "extract_topics_saymi_cc.py", lim),
    ]

    results = [_step(lbl, scr, extra, did, args.dry_run) for lbl, scr, extra in steps]

    print(f"\n{'='*60}\nRESUMEN · dirigente {did}")
    all_ok = True
    for lbl, ok in results:
        print(f"  {'✓' if ok else '✗'} {lbl}")
        all_ok = all_ok and ok
    print(f"{'='*60}")
    if not args.dry_run:
        print()
        _report_slo(did)
    if not all_ok:
        print("Algún paso falló — re-correr es seguro (idempotente, salta lo ya hecho).")
        return 1
    print("Cadena completa. Cards B0x/B14/B08/FODA leen el dato enriquecido on-read.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
