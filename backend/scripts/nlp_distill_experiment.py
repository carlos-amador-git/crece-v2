"""Experimento de destilación NLP (CEO 2026-06-11 · ADR-0008 §Área de investigación).

Hipótesis del CEO: con la base propia ya etiquetada por LLM (~17k items) se puede
entrenar un clasificador local simple que reemplace (parte de) las llamadas LLM.

Diseño eval-first:
- Corpus: social_comments con nlp_polaridad/nlp_tono/nlp_target (labels = LLM teacher).
- Features: embeddings sentence-transformers MiniLM multilingüe (mismo modelo que
  app/services/embeddings.py — ya en la imagen, $0).
- Modelo: LogisticRegression (sklearn) — lo más simple que puede funcionar.
- Validación: (a) split aleatorio 80/20 (techo optimista) y (b) leave-one-dirigente-out
  para los 3 dirigentes con más datos (generalización REAL a dirigente nuevo).
- Regla de decisión (plan): acuerdo ≥85-90% en held-out → campo ruteable a local.

Corre DENTRO del container backend (torch+sklearn+ST en la imagen):
  docker exec crece-backend python scripts/nlp_distill_experiment.py [--field nlp_polaridad]
Output: JSON report a stdout + /tmp/distill_report_<field>.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

import numpy as np


def _fetch_corpus(field: str) -> list[dict]:
    import psycopg2

    dsn = os.environ.get("DATABASE_URL_SYNC") or os.environ.get(
        "DATABASE_URL_RAW", "postgresql://crece:crece_dev@db:5432/crece"
    )
    # settings DATABASE_URL del container es asyncpg → normalizar
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")
    conn = psycopg2.connect(dsn)
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT c.content, c.{field}::text, sp.dirigente_id
        FROM social_comments c
        JOIN social_posts p ON p.id = c.parent_post_id
        JOIN social_profiles sp ON sp.id = p.profile_id
        WHERE c.{field} IS NOT NULL AND length(trim(c.content)) >= 3
        """
    )
    rows = [{"text": r[0], "label": r[1], "dirigente_id": r[2]} for r in cur.fetchall()]
    conn.close()
    return rows


def _embed(texts: list[str]) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return model.encode(texts, batch_size=128, show_progress_bar=False, convert_to_numpy=True)


def _eval(y_true, y_pred, labels) -> dict:
    from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "macro_f1": round(float(f1_score(y_true, y_pred, average="macro")), 4),
        "confusion": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "labels": list(labels),
        "n": len(y_true),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="nlp_polaridad",
                    choices=["nlp_polaridad", "nlp_tono", "nlp_target"])
    ap.add_argument("--min-class", type=int, default=30,
                    help="descartar clases con < N ejemplos (cola larga)")
    args = ap.parse_args()

    from sklearn.linear_model import LogisticRegression

    rows = _fetch_corpus(args.field)
    print(f"corpus: {len(rows)} comments etiquetados ({args.field})", flush=True)

    # Filtrar clases raras (no entrenables; el mapper las colapsa de todas formas)
    counts = Counter(r["label"] for r in rows)
    keep = {label for label, n in counts.items() if n >= args.min_class}
    dropped = {label: n for label, n in counts.items() if label not in keep}
    rows = [r for r in rows if r["label"] in keep]
    print(f"clases: {dict(counts)} · descartadas <{args.min_class}: {dropped}", flush=True)

    texts = [r["text"] for r in rows]
    y = np.array([r["label"] for r in rows])
    dirigentes = np.array([r["dirigente_id"] for r in rows])
    labels = sorted(keep)

    print("embedding (MiniLM, CPU)...", flush=True)
    X = _embed(texts)

    report: dict = {"field": args.field, "corpus_n": len(rows),
                    "class_dist": {k: int(v) for k, v in counts.items() if k in keep},
                    "dropped_classes": dropped}

    # (a) Split aleatorio 80/20 — techo optimista
    rng = np.random.RandomState(42)
    idx = rng.permutation(len(rows))
    cut = int(len(rows) * 0.8)
    tr, te = idx[:cut], idx[cut:]
    clf = LogisticRegression(max_iter=2000, class_weight="balanced")
    clf.fit(X[tr], y[tr])
    report["random_split"] = _eval(y[te], clf.predict(X[te]), labels)
    print(f"random 80/20: acc={report['random_split']['accuracy']} "
          f"macroF1={report['random_split']['macro_f1']}", flush=True)

    # (b) Leave-one-dirigente-out — generalización real a dirigente nuevo
    top3 = [d for d, _ in Counter(dirigentes.tolist()).most_common(3)]
    report["leave_one_dirigente_out"] = {}
    for d in top3:
        mask_te = dirigentes == d
        if mask_te.sum() < 50 or (~mask_te).sum() < 200:
            continue
        clf = LogisticRegression(max_iter=2000, class_weight="balanced")
        clf.fit(X[~mask_te], y[~mask_te])
        res = _eval(y[mask_te], clf.predict(X[mask_te]), labels)
        report["leave_one_dirigente_out"][str(d)] = res
        print(f"held-out dirigente {d}: acc={res['accuracy']} "
              f"macroF1={res['macro_f1']} (n={res['n']})", flush=True)

    out = f"/tmp/distill_report_{args.field}.json"
    with open(out, "w") as f:
        json.dump(report, f, indent=2)
    print(f"report → {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
