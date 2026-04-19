# CIB Pilot Test — Sprint S0 T0.3 (Alejandro Piña · 128 comments)

**Fecha:** 2026-04-19
**Script:** `backend/research/2026-04-19/cib_pilot_run.py`
**Input:** `backend/benchmarks/scraping/results/2026-04-19/nlp_layer2_gemma_out.jsonl`
**Librerías:** scikit-learn 1.8.0 (TfidfVectorizer, cosine_similarity) · numpy 2.4.4
**Seed:** 42 · **Temperature:** N/A (reglas deterministas)
**Framework:** ITESO Signa_Lab — Maestros de Ceremonias + Cuentas Coro

## 1. Contexto y limitación CEO

La tarea T0.3 pedía etiquetado humano (baseline de 200 comments Piña). **No hay humanos disponibles hoy** — por instrucción CEO, se ejecuta con **baseline heurístico automatizado** y se flagea explícitamente esta limitación. Además Piña solo tiene **128 comments reales** en el dataset NLP Layer 2 (74 X + 54 Instagram), no 200 exactos. Se usa la muestra completa disponible.

## 2. Dataset

- Total analizados: **128**
- X: **74** · Instagram: **54**
- Autores únicos: **43**
- Autores con ≥2 posts: **10**
- Autores con ≥3 posts: **6**

## 3. Baseline heurístico (sustituto de humanos)

Reglas CEO (OR lógico para marcar CIB-sospechoso):
1. Autor posteó **≥3 veces** (frecuencia anómala)
2. **<5 palabras** Y **|intensidad| ≥ 2** (low-effort + polaridad extrema)
3. **Similaridad cosine >0.8** con otro comment (TF-IDF word 1-2grams)

**Baseline positivos: 110/128 (85.9%)**

## 4. Pipeline ITESO

Marca CIB si cualquiera:
1. Autor aparece **≥2 veces** (más sensible)
2. **Cosine >0.6** con otro comment (detecta Coro temprano)
3. Clustering **plataforma-autor ≥3** (MC activo en una red)
4. **≥2 vecinos** con cosine >0.9 (clúster casi-duplicado)

**Pipeline positivos: 98/128 (76.6%)**

## 5. Matriz de confusión pipeline vs baseline

| | pipeline=TRUE | pipeline=FALSE |
|---|---|---|
| **baseline=TRUE**  | TP = 97 | FN = 13 |
| **baseline=FALSE** | FP = 1 | TN = 17 |

### Métricas

- **Tasa de detección** (TP / baseline+): **88.2%**
- **FP sobre pipeline+** (FP / pipeline+): **1.0%**
- **FP sobre negativos baseline** (FP / (FP+TN)): **5.6%**

## 6. Desglose por plataforma

| plataforma | N | baseline+ | pipeline+ |
|---|---|---|---|
| X | 74 | 74 | 74 |
| Instagram | 54 | 36 | 24 |

## 7. Top autores (candidatos MCs/Coro)

| autor | freq | plataformas |
|---|---|---|
| Alejandro_Pinha | 35 | X |
| ROCIOZULEYMALO1 | 15 | X |
| OscarOlveraMC | 15 | X |
| binabytex | 10 | Instagram |
| BinaByte | 9 | X |
| guzman_andrei_gd | 3 | Instagram |
| soyjuandecortes | 2 | Instagram |
| jovenes.mc_cdmx | 2 | Instagram |
| jonacerv21 | 2 | Instagram |
| danielpalmillasmoreira | 2 | Instagram |

## 8. Top pares de alta similaridad (evidencia Coro léxico)

| # | cosine | author_A | author_B | text_A (trunc) | text_B (trunc) |
|---|---|---|---|---|---|
| 1 | 1.000 | Alejandro_Pinha | Alejandro_Pinha | Respirar aire contaminado no es sólo incomodidad.  En México miles de personas m | Respirar aire contaminado no es sólo incomodidad.  En México miles de personas m |
| 2 | 1.000 | Alejandro_Pinha | Alejandro_Pinha | El reporte State of Global Air advierte que la contaminación del aire está asoci | El reporte State of Global Air advierte que la contaminación del aire está asoci |
| 3 | 1.000 | Alejandro_Pinha | Alejandro_Pinha | Respirar aire contaminado no es sólo incomodidad.  En México miles de personas m | Respirar aire contaminado no es sólo incomodidad.  En México miles de personas m |
| 4 | 1.000 | Alejandro_Pinha | Alejandro_Pinha | Respirar aire contaminado no es sólo incomodidad.  En México miles de personas m | Respirar aire contaminado no es sólo incomodidad.  En México miles de personas m |
| 5 | 1.000 | Alejandro_Pinha | Alejandro_Pinha | El reporte State of Global Air advierte que la contaminación del aire está asoci | El reporte State of Global Air advierte que la contaminación del aire está asoci |
| 6 | 1.000 | Alejandro_Pinha | Alejandro_Pinha | El reporte State of Global Air advierte que la contaminación del aire está asoci | El reporte State of Global Air advierte que la contaminación del aire está asoci |
| 7 | 1.000 | Alejandro_Pinha | Alejandro_Pinha | Respirar aire contaminado no es sólo incomodidad.  En México miles de personas m | Respirar aire contaminado no es sólo incomodidad.  En México miles de personas m |
| 8 | 1.000 | Alejandro_Pinha | Alejandro_Pinha | Respirar aire contaminado no es sólo incomodidad.  En México miles de personas m | Respirar aire contaminado no es sólo incomodidad.  En México miles de personas m |
| 9 | 1.000 | Alejandro_Pinha | Alejandro_Pinha | Respirar aire contaminado no es sólo incomodidad.  En México miles de personas m | Respirar aire contaminado no es sólo incomodidad.  En México miles de personas m |
| 10 | 1.000 | Alejandro_Pinha | Alejandro_Pinha | El reporte State of Global Air advierte que la contaminación del aire está asoci | El reporte State of Global Air advierte que la contaminación del aire está asoci |

## 9. Criterio pass/fail

**Criterio Sprint S0:** >60% detección con <15% FP.

- Detección: **88.2%**
- FP (sobre marcados por pipeline): **1.0%**
- FP (sobre negativos baseline): **5.6%**

### Veredicto: **PASS con caveat — tasas cumplen criterio binario, pero baseline heurístico es demasiado permisivo (85.9% positivos) para servir como ground truth real**

**Interpretación honesta:**
- El criterio binario del Sprint S0 se cumple numéricamente (88.2% detección, 1.0% FP sobre pipeline+, 5.6% FP sobre negativos).
- PERO el baseline heurístico marcó **110/128 (86%)** como CIB-sospechoso, lo cual es implausible en data real (prevalencia típica CIB en dirigentes mexicanos 15-35% según Signa_Lab). La regla (b) `<5 palabras Y polaridad extrema` captura comments cortos normales en Twitter/IG, no solo CIB.
- En consecuencia, el "PASS" debe leerse como **señal direccional** más que validación estadística dura. La infraestructura técnica funciona (TF-IDF + clustering + repetición) y detecta señales reales (Coro léxico, MCs con clustering plataforma-autor ≥3).

## 10. Decisión go/no-go infraestructura bloque #12 MVP

**GO con scaffolding parcial en S1 (no S3 completo):**

- La infraestructura actual (TF-IDF cosine + author repetition + clustering plataforma-autor) **sirve como motor MVP bloque #12**. Las señales que detecta son reales y trazables.
- **Requisito obligatorio para MVP S1:** etiquetado humano real de 100-200 comments sobre 3 dirigentes distintos (Piña + 2 más) para recalibrar umbrales. Sin ground truth humano, los umbrales actuales son arbitrarios.
- **Scaffolding adicional S3 deseable (no bloqueante):**
  - Scraper de metadata de cuenta (account age, ratio follower/following) — eleva precisión sustancialmente.
  - Timestamps reales por comment (actualmente el pipeline NLP Layer 2 no los preserva) — habilita clustering temporal >50% 1ra hora.
  - Embeddings semánticos (sentence-transformers multilingual) para capturar Coro con léxico distinto pero mismo mensaje.
- **Recomendación operativa:** codificar umbrales actuales como defaults configurables por dirigente; exponer en UI admin de Sprint S3 para calibración por cliente.

## 11. Limitaciones documentadas

- **Sin etiquetado humano.** Baseline heurístico aproxima pero no replica juicio humano sobre intención coordinada. La tasa de detección es relativa al baseline, no ground truth.
- **Baseline over-flagging.** El baseline marcó 85.9% de la muestra como CIB-sospechoso — prevalencia inverosímil. La regla (b) `<5 palabras + polaridad extrema` es demasiado laxa en redes donde los comments cortos emocionales son la norma. Esto infla artificialmente el denominador de "detección" y deflata FP.
- **Piña no llega a 200.** Muestra real = 128 (74 X + 54 IG). Instrucción CEO aceptó la muestra disponible.
- **No hay account age real.** ITESO original usa edad de cuenta como feature principal; aquí se aproxima con frecuencia de autor en el dataset. Scraping de metadata de cuenta queda pendiente para Sprint S3.
- **No hay timestamp por comment.** Framework pedía clustering temporal (>50% en 1ra hora del post). El pipeline NLP Layer 2 no preserva timestamp del comment original, solo `classified_at`. Regla (d) del pipeline usa clustering por autor-plataforma como proxy.
- **TF-IDF léxico, no semántico.** Comments con mismo mensaje pero léxico distinto (sinonimos, emojis) no se detectan. Gap para Sprint S3: agregar embeddings (sentence-transformers multilingual).

## 12. Hallazgos cualitativos

- El autor más frecuente en la muestra es **Alejandro_Pinha** con 35 comments.
- 6 autores superan el umbral de 3 posts (regla baseline).
- 353 pares de comments distintos exceden cosine 0.7 (evidencia de mensaje replicado o quoted reply patterns).

## 13. Reproducibilidad

```bash
cd /Users/marxchavez/Projects/crece-v2
./backend/.venv/bin/python backend/research/2026-04-19/cib_pilot_run.py
```

Outputs deterministas: seed=42, reglas puras (sin LLM), mismo input → mismo output.
