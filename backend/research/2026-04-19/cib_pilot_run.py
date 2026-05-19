"""
Sprint S0 · T0.3 — CIB Pilot Test (Alejandro Piña, 128 comments)

Framework ITESO Signa_Lab (Coordinated Inauthentic Behavior):
  - Maestros de Ceremonias (MC): cuentas que lideran clustering narrativo
  - Cuentas Coro: replican mensaje con alta similaridad léxica
  - Señales: clustering temporal, similaridad cosine, account age, frecuencia autor

INPUT:
  /Users/marxchavez/Projects/crece-v2/backend/benchmarks/scraping/results/2026-04-19/nlp_layer2_gemma_out.jsonl

OUTPUT:
  cib_pilot_detections.csv  (id, author, text, baseline_cib_heuristic, pipeline_flag, reason)
  cib_pilot_test.md         (informe)

Metadatos:
  librerias: scikit-learn 1.8.0 TfidfVectorizer + cosine_similarity, numpy 2.4.4
  temperature: N/A (clasificación determinista por reglas)
  seed: 42 (para desempates numpy)
  fecha: 2026-04-19
  CEO instruction: NO humanos disponibles; baseline heurístico + pipeline ITESO

Criterio pass: >60% detección con <15% FP vs baseline.
Si no hay suficientes CIB positivos en baseline → documentar ambigüedad.
"""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

SEED = 42
np.random.seed(SEED)

INPUT = Path(
    "/Users/marxchavez/Projects/crece-v2/backend/benchmarks/scraping/results/"
    "2026-04-19/nlp_layer2_gemma_out.jsonl"
)
OUT_DIR = Path("/Users/marxchavez/Projects/crece-v2/backend/research/2026-04-19")
CSV_OUT = OUT_DIR / "cib_pilot_detections.csv"
MD_OUT = OUT_DIR / "cib_pilot_test.md"

PINA_HANDLES = {"alejandro.pinha", "alejandro_pinha"}

# ------------------------------------------------------------
# 1. Load Piña comments
# ------------------------------------------------------------
rows = []
with INPUT.open() as f:
    for line in f:
        r = json.loads(line)
        if r.get("handle_dirigente", "").lower() in PINA_HANDLES:
            rows.append(r)

N = len(rows)
print(f"[load] Piña comments: {N}")

# normalizamos claves básicas
for r in rows:
    r["text"] = (r.get("comment_text") or "").strip()
    r["author"] = r.get("author") or "unknown"
    r["intensidad"] = r.get("classification", {}).get("intensidad", 0)
    r["polaridad"] = r.get("classification", {}).get("polaridad_preliminar", "")

# ------------------------------------------------------------
# 2. Baseline heurístico automatizado (NO hay humanos hoy)
#    Regla CEO: marcar CIB-sospechoso si cualquiera de:
#     (a) autor posteó ≥3 veces en el dataset (repetición)
#     (b) texto <5 palabras Y polaridad extrema (|intensidad| >=2)
#     (c) similaridad cosine >0.8 con otro comment distinto
#     (d) clustering temporal (no hay post_id→timestamp por comment,
#         usamos fecha classified_at como proxy: >50% autores con ≥2
#         posts en ventana de 1h sobre sí misma — señal débil)
# ------------------------------------------------------------
author_counts = Counter(r["author"] for r in rows)

# TF-IDF cosine similarity
texts = [r["text"] for r in rows]
vec = TfidfVectorizer(
    analyzer="word",
    ngram_range=(1, 2),
    min_df=1,
    max_df=0.95,
    lowercase=True,
    strip_accents="unicode",
)
X = vec.fit_transform(texts)
sim = cosine_similarity(X)
np.fill_diagonal(sim, 0.0)

# umbral pipeline ITESO
SIM_THRESHOLD_PIPELINE = 0.6   # pipeline más sensible (detecta MCs/Coro tempranamente)
SIM_THRESHOLD_BASELINE = 0.8   # baseline heurístico estricto (CEO)

# max similitud por fila
max_sim_baseline = sim.max(axis=1) if N > 1 else np.zeros(N)
high_sim_pairs_baseline = (sim > SIM_THRESHOLD_BASELINE)
high_sim_pairs_pipeline = (sim > SIM_THRESHOLD_PIPELINE)

def word_count(s):
    return len(s.split())

# Baseline heuristic flag per comment
baseline_flag = []
baseline_reason = []
for i, r in enumerate(rows):
    reasons = []
    # (a) autor repetido ≥3
    if author_counts[r["author"]] >= 3:
        reasons.append(f"author_freq={author_counts[r['author']]}")
    # (b) low-effort + polaridad extrema
    if word_count(r["text"]) < 5 and abs(r["intensidad"]) >= 2:
        reasons.append(f"low_effort_extreme(wc={word_count(r['text'])},int={r['intensidad']})")
    # (c) similaridad >0.8 con otro comment
    if N > 1 and max_sim_baseline[i] > SIM_THRESHOLD_BASELINE:
        reasons.append(f"cosine>{SIM_THRESHOLD_BASELINE}(max={max_sim_baseline[i]:.2f})")
    baseline_flag.append(bool(reasons))
    baseline_reason.append("|".join(reasons) if reasons else "")

baseline_positives = sum(baseline_flag)
print(f"[baseline] positivos: {baseline_positives}/{N} ({100*baseline_positives/N:.1f}%)")

# ------------------------------------------------------------
# 3. Pipeline ITESO (TF-IDF + clustering + repetition)
#    Marca CIB si cualquiera:
#     (a) autor ≥2 veces (más sensible que baseline)
#     (b) similaridad cosine >0.6 con OTRO comment (detecta Coro temprano)
#     (c) clustering temporal: >=3 comments del mismo autor en misma plataforma
#     (d) texto casi-duplicado (sim >0.9 con ≥2 pares)
# ------------------------------------------------------------
# plataforma-autor buckets
plat_author = Counter((r["plataforma"], r["author"]) for r in rows)

pipeline_flag = []
pipeline_reason = []
n_high_sim_peers = (sim > 0.9).sum(axis=1)  # cuantos vecinos casi-dup

for i, r in enumerate(rows):
    reasons = []
    # (a) autor ≥2
    if author_counts[r["author"]] >= 2:
        reasons.append(f"author_repeat={author_counts[r['author']]}")
    # (b) cosine similaridad fuerte
    ms = max_sim_baseline[i] if N > 1 else 0.0
    if ms > SIM_THRESHOLD_PIPELINE:
        reasons.append(f"cosine>{SIM_THRESHOLD_PIPELINE}(max={ms:.2f})")
    # (c) clustering plataforma-autor ≥3
    if plat_author[(r["plataforma"], r["author"])] >= 3:
        reasons.append(f"plat_author_cluster={plat_author[(r['plataforma'], r['author'])]}")
    # (d) near-duplicates
    if n_high_sim_peers[i] >= 2:
        reasons.append(f"near_dup_peers={int(n_high_sim_peers[i])}")
    pipeline_flag.append(bool(reasons))
    pipeline_reason.append("|".join(reasons) if reasons else "")

pipeline_positives = sum(pipeline_flag)
print(f"[pipeline] positivos: {pipeline_positives}/{N} ({100*pipeline_positives/N:.1f}%)")

# ------------------------------------------------------------
# 4. Métricas: detección + falsos positivos vs baseline
# ------------------------------------------------------------
true_positives = sum(1 for i in range(N) if baseline_flag[i] and pipeline_flag[i])
false_negatives = sum(1 for i in range(N) if baseline_flag[i] and not pipeline_flag[i])
false_positives = sum(1 for i in range(N) if not baseline_flag[i] and pipeline_flag[i])
true_negatives = sum(1 for i in range(N) if not baseline_flag[i] and not pipeline_flag[i])

detection_rate = (true_positives / baseline_positives) if baseline_positives else None
# FP rate: marcados por pipeline pero no por baseline / marcados pipeline
fp_rate_over_pipeline = (false_positives / pipeline_positives) if pipeline_positives else 0.0
# FP rate clasico: FP / (FP + TN) sobre el conjunto no-CIB baseline
denom_negs = false_positives + true_negatives
fp_rate_over_negatives = (false_positives / denom_negs) if denom_negs else 0.0

print(f"[metrics] TP={true_positives} FN={false_negatives} FP={false_positives} TN={true_negatives}")
print(f"[metrics] detección={detection_rate}  FP_over_pipeline={fp_rate_over_pipeline:.3f}  "
      f"FP_over_negatives={fp_rate_over_negatives:.3f}")

# ------------------------------------------------------------
# 5. CSV output
# ------------------------------------------------------------
with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["id", "author", "text", "baseline_cib_heuristic", "pipeline_flag", "reason"])
    for i, r in enumerate(rows):
        reason_combined = pipeline_reason[i] or baseline_reason[i]
        w.writerow([
            r.get("id", ""),
            r["author"],
            r["text"].replace("\n", " ")[:500],
            "TRUE" if baseline_flag[i] else "FALSE",
            "TRUE" if pipeline_flag[i] else "FALSE",
            reason_combined,
        ])
print(f"[write] {CSV_OUT}")

# ------------------------------------------------------------
# 6. Stats extra para el informe
# ------------------------------------------------------------
# top autores (posibles MCs/Coro)
top_authors = author_counts.most_common(10)

# pares de alta similaridad (muestra MCs+Coro)
pair_pool = []
if N > 1:
    iu = np.triu_indices(N, k=1)
    for i, j in zip(*iu):
        if sim[i, j] > 0.7:
            pair_pool.append((float(sim[i, j]), i, j))
pair_pool.sort(reverse=True)
top_pairs = pair_pool[:10]

# desglose por plataforma
per_plat = defaultdict(lambda: {"n": 0, "baseline": 0, "pipeline": 0})
for i, r in enumerate(rows):
    p = r["plataforma"]
    per_plat[p]["n"] += 1
    if baseline_flag[i]:
        per_plat[p]["baseline"] += 1
    if pipeline_flag[i]:
        per_plat[p]["pipeline"] += 1

# ------------------------------------------------------------
# 7. Markdown report
# ------------------------------------------------------------
def fmt_pct(n, d):
    return f"{100*n/d:.1f}%" if d else "n/a"

# decision logic
AMBIGUOUS_THRESHOLD = 10  # si <10 CIB positivos baseline, direccional
if baseline_positives < AMBIGUOUS_THRESHOLD:
    verdict = "AMBIGUO (muestra positiva insuficiente)"
    go_decision = (
        "Infraestructura actual PUEDE soportar bloque #12 en modo MVP con "
        "limitación documentada: muestra Piña no tiene volumen suficiente "
        "de CIB para validación estadística dura. Recomendación: lanzar MVP "
        "bloque #12 con umbrales conservadores + etiquetado humano en Sprint S3 "
        "antes de exponer al cliente."
    )
elif detection_rate is not None and detection_rate > 0.60 and fp_rate_over_pipeline < 0.15:
    verdict = "PASS"
    go_decision = (
        "Infraestructura actual es suficiente para lanzar bloque #12 en "
        "MVP S1. No requiere scaffolding adicional en S3. Recomendación: "
        "codificar umbrales actuales como defaults y exponer como configuración "
        "avanzada por dirigente."
    )
elif detection_rate is not None and detection_rate >= 0.60:
    verdict = "FAIL por FP%"
    go_decision = (
        "Detección suficiente pero falsos positivos exceden 15%. "
        "Requiere scaffolding en Sprint S3: re-ranking con account age real "
        "(requiere scraper de metadata de cuenta), whitelist de cuentas "
        "verificadas, y umbral cosine ajustable por dirigente."
    )
else:
    verdict = "FAIL por detección"
    go_decision = (
        "Detección por debajo de 60%. Requiere scaffolding S3: "
        "embeddings semánticos (no solo TF-IDF léxico), ventana temporal "
        "post-a-post real (requiere timestamp por comment), y account "
        "metadata (age, ratio follower/following)."
    )

md_lines = [
    "# CIB Pilot Test — Sprint S0 T0.3 (Alejandro Piña · 128 comments)",
    "",
    "**Fecha:** 2026-04-19",
    "**Script:** `backend/research/2026-04-19/cib_pilot_run.py`",
    "**Input:** `backend/benchmarks/scraping/results/2026-04-19/nlp_layer2_gemma_out.jsonl`",
    "**Librerías:** scikit-learn 1.8.0 (TfidfVectorizer, cosine_similarity) · numpy 2.4.4",
    "**Seed:** 42 · **Temperature:** N/A (reglas deterministas)",
    "**Framework:** ITESO Signa_Lab — Maestros de Ceremonias + Cuentas Coro",
    "",
    "## 1. Contexto y limitación CEO",
    "",
    "La tarea T0.3 pedía etiquetado humano (baseline de 200 comments Piña). "
    "**No hay humanos disponibles hoy** — por instrucción CEO, se ejecuta con "
    "**baseline heurístico automatizado** y se flagea explícitamente esta limitación. "
    "Además Piña solo tiene **128 comments reales** en el dataset NLP Layer 2 "
    "(74 X + 54 Instagram), no 200 exactos. Se usa la muestra completa disponible.",
    "",
    "## 2. Dataset",
    "",
    f"- Total analizados: **{N}**",
    f"- X: **{per_plat['X']['n']}** · Instagram: **{per_plat['Instagram']['n']}**",
    f"- Autores únicos: **{len(author_counts)}**",
    f"- Autores con ≥2 posts: **{sum(1 for v in author_counts.values() if v >= 2)}**",
    f"- Autores con ≥3 posts: **{sum(1 for v in author_counts.values() if v >= 3)}**",
    "",
    "## 3. Baseline heurístico (sustituto de humanos)",
    "",
    "Reglas CEO (OR lógico para marcar CIB-sospechoso):",
    "1. Autor posteó **≥3 veces** (frecuencia anómala)",
    "2. **<5 palabras** Y **|intensidad| ≥ 2** (low-effort + polaridad extrema)",
    "3. **Similaridad cosine >0.8** con otro comment (TF-IDF word 1-2grams)",
    "",
    f"**Baseline positivos: {baseline_positives}/{N} ({fmt_pct(baseline_positives, N)})**",
    "",
    "## 4. Pipeline ITESO",
    "",
    "Marca CIB si cualquiera:",
    "1. Autor aparece **≥2 veces** (más sensible)",
    "2. **Cosine >0.6** con otro comment (detecta Coro temprano)",
    "3. Clustering **plataforma-autor ≥3** (MC activo en una red)",
    "4. **≥2 vecinos** con cosine >0.9 (clúster casi-duplicado)",
    "",
    f"**Pipeline positivos: {pipeline_positives}/{N} ({fmt_pct(pipeline_positives, N)})**",
    "",
    "## 5. Matriz de confusión pipeline vs baseline",
    "",
    "| | pipeline=TRUE | pipeline=FALSE |",
    "|---|---|---|",
    f"| **baseline=TRUE**  | TP = {true_positives} | FN = {false_negatives} |",
    f"| **baseline=FALSE** | FP = {false_positives} | TN = {true_negatives} |",
    "",
    "### Métricas",
    "",
    f"- **Tasa de detección** (TP / baseline+): **{fmt_pct(true_positives, baseline_positives)}**",
    f"- **FP sobre pipeline+** (FP / pipeline+): **{fmt_pct(false_positives, pipeline_positives)}**",
    f"- **FP sobre negativos baseline** (FP / (FP+TN)): **{fmt_pct(false_positives, denom_negs)}**",
    "",
    "## 6. Desglose por plataforma",
    "",
    "| plataforma | N | baseline+ | pipeline+ |",
    "|---|---|---|---|",
]
for p, d in per_plat.items():
    md_lines.append(f"| {p} | {d['n']} | {d['baseline']} | {d['pipeline']} |")

md_lines += [
    "",
    "## 7. Top autores (candidatos MCs/Coro)",
    "",
    "| autor | freq | plataformas |",
    "|---|---|---|",
]
for a, c in top_authors:
    plats_a = sorted({r["plataforma"] for r in rows if r["author"] == a})
    md_lines.append(f"| {a} | {c} | {', '.join(plats_a)} |")

md_lines += [
    "",
    "## 8. Top pares de alta similaridad (evidencia Coro léxico)",
    "",
    "| # | cosine | author_A | author_B | text_A (trunc) | text_B (trunc) |",
    "|---|---|---|---|---|---|",
]
for k, (s, i, j) in enumerate(top_pairs, 1):
    ta = rows[i]["text"].replace("|", "/").replace("\n", " ")[:80]
    tb = rows[j]["text"].replace("|", "/").replace("\n", " ")[:80]
    md_lines.append(f"| {k} | {s:.3f} | {rows[i]['author']} | {rows[j]['author']} | {ta} | {tb} |")

md_lines += [
    "",
    "## 9. Criterio pass/fail",
    "",
    "**Criterio Sprint S0:** >60% detección con <15% FP.",
    "",
    f"- Detección: **{fmt_pct(true_positives, baseline_positives)}**",
    f"- FP (sobre marcados por pipeline): **{fmt_pct(false_positives, pipeline_positives)}**",
    f"- FP (sobre negativos baseline): **{fmt_pct(false_positives, denom_negs)}**",
    "",
    f"### Veredicto: **{verdict}**",
    "",
    "## 10. Decisión go/no-go infraestructura bloque #12 MVP",
    "",
    go_decision,
    "",
    "## 11. Limitaciones documentadas",
    "",
    "- **Sin etiquetado humano.** Baseline heurístico aproxima pero no replica "
    "juicio humano sobre intención coordinada. La tasa de detección es relativa "
    "al baseline, no ground truth.",
    "- **Piña no llega a 200.** Muestra real = 128 (74 X + 54 IG). Instrucción "
    "CEO aceptó la muestra disponible.",
    "- **No hay account age real.** ITESO original usa edad de cuenta como feature "
    "principal; aquí se aproxima con frecuencia de autor en el dataset. Scraping "
    "de metadata de cuenta queda pendiente para Sprint S3.",
    "- **No hay timestamp por comment.** Framework pedía clustering temporal "
    "(>50% en 1ra hora del post). El pipeline NLP Layer 2 no preserva timestamp "
    "del comment original, solo `classified_at`. Regla (d) del pipeline usa "
    "clustering por autor-plataforma como proxy.",
    "- **TF-IDF léxico, no semántico.** Comments con mismo mensaje pero léxico "
    "distinto (sinonimos, emojis) no se detectan. Gap para Sprint S3: agregar "
    "embeddings (sentence-transformers multilingual).",
    "",
    "## 12. Hallazgos cualitativos",
    "",
    f"- El autor más frecuente en la muestra es **{top_authors[0][0]}** con "
    f"{top_authors[0][1]} comments.",
    f"- {sum(1 for v in author_counts.values() if v >= 3)} autores superan el "
    "umbral de 3 posts (regla baseline).",
    f"- {len(pair_pool)} pares de comments distintos exceden cosine 0.7 "
    "(evidencia de mensaje replicado o quoted reply patterns).",
    "",
    "## 13. Reproducibilidad",
    "",
    "```bash",
    "cd /Users/marxchavez/Projects/crece-v2",
    "./backend/.venv/bin/python backend/research/2026-04-19/cib_pilot_run.py",
    "```",
    "",
    "Outputs deterministas: seed=42, reglas puras (sin LLM), mismo input → mismo output.",
    "",
]

MD_OUT.write_text("\n".join(md_lines), encoding="utf-8")
print(f"[write] {MD_OUT}")
print(f"[done] verdict: {verdict}")
