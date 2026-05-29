"""T0.4 - Computa kappa + precision topics + matrices confusion.

Inputs:
  data/sample_60_gemma.jsonl   (clasificador bajo validacion)
  data/sample_60_gemini.jsonl  (proxy experto 1)
  data/sample_60_claude.jsonl  (proxy experto 2, opcional)

Outputs:
  plutchik_topics_raw.jsonl  (1 row por comment con las 2-3 etiquetas)
  plutchik_topics_stats.json (kappa + precision + matrices)
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

RESEARCH_DIR = Path("/Users/marxchavez/Projects/crece-v2/backend/research/2026-04-19")
DATA_DIR = RESEARCH_DIR / "data"
SAMPLE_PATH = Path(
    "/Users/marxchavez/Projects/crece-v2/backend/evaluations/2026-04-18/data/sample_60.jsonl"
)

EMOCIONES = ["trust", "anger", "joy", "fear", "sadness", "disgust"]
TOPICS = [
    "economia", "seguridad", "educacion", "salud", "corrupcion", "movilidad",
    "genero", "medioambiente", "gobierno", "politica_electoral", "institucional", "otro",
]


def load_jsonl(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    out: dict[str, dict] = {}
    for line in path.read_text().splitlines():
        if not line:
            continue
        try:
            r = json.loads(line)
            out[r["id"]] = r
        except Exception:
            continue
    return out


def cohen_kappa(labels_a: list[str], labels_b: list[str], categories: list[str]) -> float:
    """Cohen's kappa for two raters, symmetric. Skips None pairs."""
    pairs = [(a, b) for a, b in zip(labels_a, labels_b) if a and b]
    if not pairs:
        return float("nan")
    n = len(pairs)
    # observed agreement
    po = sum(1 for a, b in pairs if a == b) / n
    # expected by chance
    cats = set(categories) | {a for a, _ in pairs} | {b for _, b in pairs}
    pe = 0.0
    for c in cats:
        pa = sum(1 for a, _ in pairs if a == c) / n
        pb = sum(1 for _, b in pairs if b == c) / n
        pe += pa * pb
    if pe >= 1.0:
        return 1.0 if po == 1.0 else float("nan")
    return (po - pe) / (1 - pe)


def fleiss_kappa(ratings: list[list[str]], categories: list[str]) -> float:
    """Fleiss kappa. ratings: list de [r1, r2, r3] por item."""
    rated = [r for r in ratings if all(x for x in r)]
    if not rated:
        return float("nan")
    n = len(rated)
    k_raters = len(rated[0])
    cats = sorted(set(categories) | {x for r in rated for x in r})
    # build matrix counts[i][j] = # raters on item i assigning cat j
    counts = []
    for row in rated:
        c = Counter(row)
        counts.append([c.get(cat, 0) for cat in cats])
    # P_i per item
    P = [
        (sum(n_ij * n_ij for n_ij in row) - k_raters) / (k_raters * (k_raters - 1))
        for row in counts
    ]
    P_bar = sum(P) / n
    # p_j per cat
    p = [sum(row[j] for row in counts) / (n * k_raters) for j in range(len(cats))]
    P_e = sum(pj * pj for pj in p)
    if P_e >= 1.0:
        return 1.0 if P_bar == 1.0 else float("nan")
    return (P_bar - P_e) / (1 - P_e)


def confusion_matrix(
    a: list[str], b: list[str], categories: list[str]
) -> list[list[int]]:
    idx = {c: i for i, c in enumerate(categories)}
    m = [[0] * len(categories) for _ in categories]
    for x, y in zip(a, b):
        if x in idx and y in idx:
            m[idx[x]][idx[y]] += 1
    return m


def majority_vote(labels: list[str]) -> str | None:
    vals = [l for l in labels if l]
    if not vals:
        return None
    c = Counter(vals)
    top, ct = c.most_common(1)[0]
    # if tie with 2 raters, first wins (gemma ranked last in order passed in)
    return top


def main() -> None:
    samples = {
        json.loads(l)["id"]: json.loads(l)
        for l in SAMPLE_PATH.read_text().splitlines()
        if l
    }
    gemma = load_jsonl(DATA_DIR / "sample_60_gemma.jsonl")
    gemini = load_jsonl(DATA_DIR / "sample_60_gemini.jsonl")
    claude = load_jsonl(DATA_DIR / "sample_60_claude.jsonl")

    have_claude = bool(claude)
    ids = sorted(samples)

    raw_rows = []
    emo_gemma: list[str] = []
    emo_gemini: list[str] = []
    emo_claude: list[str] = []
    emo_majority: list[str] = []
    topic_gemma: list[str] = []
    topic_gemini: list[str] = []
    topic_claude: list[str] = []
    topic_majority: list[str] = []

    for cid in ids:
        rg = gemma.get(cid, {})
        ri = gemini.get(cid, {})
        rc = claude.get(cid, {})

        e_g = rg.get("emocion")
        e_i = ri.get("emocion")
        e_c = rc.get("emocion") if have_claude else None

        tg_list = rg.get("topics") or []
        ti_list = ri.get("topics") or []
        tc_list = rc.get("topics") or []
        t_g = tg_list[0] if tg_list else None
        t_i = ti_list[0] if ti_list else None
        t_c = tc_list[0] if tc_list and have_claude else None

        # majority (between proxies only: Gemini [+Claude])
        if have_claude:
            e_maj = majority_vote([e_i, e_c])
            t_maj = majority_vote([t_i, t_c])
        else:
            e_maj = e_i
            t_maj = t_i

        emo_gemma.append(e_g)
        emo_gemini.append(e_i)
        emo_claude.append(e_c)
        emo_majority.append(e_maj)
        topic_gemma.append(t_g)
        topic_gemini.append(t_i)
        topic_claude.append(t_c)
        topic_majority.append(t_maj)

        raw_rows.append({
            "id": cid,
            "comment_text": samples[cid]["comment_text"][:180],
            "plataforma": samples[cid]["plataforma"],
            "gemma": {"emocion": e_g, "topics": tg_list},
            "gemini": {"emocion": e_i, "topics": ti_list},
            "claude": {"emocion": e_c, "topics": tc_list} if have_claude else None,
            "majority": {"emocion": e_maj, "topic_principal": t_maj},
        })

    out_raw = RESEARCH_DIR / "plutchik_topics_raw.jsonl"
    with out_raw.open("w") as f:
        for r in raw_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # --- Stats ---
    stats: dict = {"n_items": len(ids), "have_claude": have_claude}

    # Kappa emocion: Gemma vs majority
    stats["kappa_emocion_gemma_vs_majority"] = cohen_kappa(
        emo_gemma, emo_majority, EMOCIONES
    )
    # Kappa entre proxies
    if have_claude:
        stats["kappa_emocion_gemini_vs_claude"] = cohen_kappa(
            emo_gemini, emo_claude, EMOCIONES
        )
        stats["fleiss_emocion_3way"] = fleiss_kappa(
            [[g, i, c] for g, i, c in zip(emo_gemma, emo_gemini, emo_claude)],
            EMOCIONES,
        )
    else:
        stats["kappa_emocion_gemma_vs_gemini"] = cohen_kappa(
            emo_gemma, emo_gemini, EMOCIONES
        )

    # Precision topic principal Gemma vs majority
    hits = sum(1 for g, m in zip(topic_gemma, topic_majority) if g and m and g == m)
    denom = sum(1 for g, m in zip(topic_gemma, topic_majority) if g and m)
    stats["topic_principal_precision_gemma_vs_majority"] = hits / denom if denom else 0.0
    stats["topic_principal_n_compared"] = denom
    stats["topic_principal_hits"] = hits

    # Confusion matrices
    stats["confusion_emocion_gemma_rows_vs_majority_cols"] = {
        "categories": EMOCIONES,
        "matrix": confusion_matrix(emo_gemma, emo_majority, EMOCIONES),
    }
    stats["confusion_topic_gemma_rows_vs_majority_cols"] = {
        "categories": TOPICS,
        "matrix": confusion_matrix(topic_gemma, topic_majority, TOPICS),
    }

    # Class distributions
    stats["dist_emocion_gemma"] = dict(Counter(e for e in emo_gemma if e))
    stats["dist_emocion_majority"] = dict(Counter(e for e in emo_majority if e))
    stats["dist_topic_gemma"] = dict(Counter(t for t in topic_gemma if t))
    stats["dist_topic_majority"] = dict(Counter(t for t in topic_majority if t))

    # Missing
    stats["missing_gemma"] = sum(1 for e in emo_gemma if not e)
    stats["missing_gemini"] = sum(1 for e in emo_gemini if not e)
    stats["missing_claude"] = sum(1 for e in emo_claude if not e) if have_claude else None

    out_stats = RESEARCH_DIR / "plutchik_topics_stats.json"
    with out_stats.open("w") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False, default=str)

    # Print summary
    print(f"n={stats['n_items']} claude={have_claude}")
    print(f"kappa emocion Gemma-vs-majority: {stats['kappa_emocion_gemma_vs_majority']:.3f}")
    if have_claude:
        print(f"fleiss 3-way:                     {stats['fleiss_emocion_3way']:.3f}")
    print(f"topic principal precision:        {stats['topic_principal_precision_gemma_vs_majority']:.3f} ({hits}/{denom})")
    print(f"outputs: {out_raw}, {out_stats}")


if __name__ == "__main__":
    main()
