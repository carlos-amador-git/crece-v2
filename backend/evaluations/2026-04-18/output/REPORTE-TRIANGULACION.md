# Reporte — Triangulación NLP Layer 2 (Claude + Gemini + Gemma)

**Fecha:** 2026-04-18
**Autor:** Joy (sesión Claude Code, CRECE v2 branch `feat/eval-benchmark-v1`)
**Plan:** `.context/PLAN-triangulacion-nlp-2026-04-18.md`
**Bitácora viva:** `productos/gobierno/crece-v2/bitacora/2026-04-18-triangulacion.md` (Obsidian)

---

## 1. Contexto

Gemma3:12b corrió Layer 2 sobre 1,152 comments (universo completo Apify 2026-04-18). Memoria `gemma-ollama-benchmark-2026-04-14` documenta que el CEO aceptó `gemma3:12b concurrency4` como producción, pero el eval humano quedó pendiente.

Este reporte construye un **golden set silver-grade** con triangulación 3-way (Claude Opus 4.7 + Gemini CLI + Gemma3:12b) sobre una muestra stratified de **60 comments** para:

1. Validar si Gemma3:12b Layer 2 es aceptable para producción
2. Detectar divergencias sistemáticas entre los 3 modelos
3. Alimentar calibración de la matriz v2 (53 reglas)
4. Establecer precedente reusable: 3-way silver-grade en vez de ground truth humano 100%

**Costo total:** $0 (Gemma local + sesión Claude activa + Gemini CLI local).
**Clock time:** ~2h 40min (incluye ~2h de Gemma batch completo).

---

## 2. Muestra

**Fuente:** Apify replies X (507 rows) + Apify IG posts con latestComments inline (645 rows). 1,152 comments totales.
**Selección:** `scripts/stratified_sample.py` seed=42 (plataforma × handle × bucket de longitud).
**Tamaño:** 60 comments.

**Cobertura final:**
- Plataforma: Instagram 43 · X 17
- Handles: 20 distintos (dirigentes CRECE + cuentas asociadas como `movciudadanomx`, `capital21_tv`, `secturoaxaca`)
- Buckets de longitud: corto <50 chars (23) · medio 50-150 (19) · largo >150 (18)
- Errores de parseo: **0** en los 3 modelos (3×60 = 180 clasificaciones limpias)

Los 60 IDs están en `data/sample_60.jsonl`. Prompt congelado `prompts/layer2_triangulation.md` (SHA256 `b0e456...ff464499`, extraído verbatim del runner Gemma en producción).

---

## 3. Resultados — Acuerdo entre clasificadores

### 3.1 Kappas por dimensión (60 rows comunes)

| Dimensión | 3/3 agree | 2/3 majority | 3-way divergence | Cohen C-G | Cohen C-M | Cohen G-M | Fleiss 3-way |
|---|---:|---:|---:|---:|---:|---:|---:|
| **tono** | 44 (73%) | 15 | 1 | 0.743 | 0.742 | **0.802** | **0.761** |
| **target** | 38 (63%) | 20 | 2 | 0.509 | 0.331 | 0.434 | **0.418** |
| **polaridad** | 46 (77%) | 14 | 0 | 0.713 | 0.679 | **0.856** | **0.744** |
| **intensidad bucket** | 50 (83%) | 10 | 0 | 0.772 | 0.767 | **0.877** | **0.803** |

Escala de interpretación (Landis & Koch): <0 sin acuerdo · 0.00–0.20 ligero · 0.21–0.40 aceptable · 0.41–0.60 moderado · 0.61–0.80 **substancial** · 0.81–1.00 **casi perfecto**.

### 3.2 Observaciones clave

1. **Intensidad bucket (polaridad magnitud) es la dimensión más sólida: Fleiss 0.803 (casi perfecto), 3/3 en 83% de rows.** Los 3 modelos convergen en *cuán intenso* es el sentimiento, aunque diverjan en la *etiqueta de tono* exacta.
2. **Tono converge substancialmente (Fleiss 0.761)**, con 73% de 3/3. Sólo 1 row muestra 3-way divergence en tono.
3. **Polaridad (aprobacion/neutral/rechazo) converge substancialmente (0.744)** con 77% 3/3, pero Claude tiende a `neutral` cuando Gemini+Gemma dicen `rechazo` (patrón P1).
4. **Target es el cuello de botella (Fleiss 0.418, moderado)**. El vocabulario target del prompt (6 opciones) vs matriz v2 (8 opciones) genera ambigüedad sistemática. Claude↔Gemma kappa 0.331 (aceptable), el par más débil.
5. **Gemini↔Gemma es el par consistentemente más alineado** (0.802, 0.856, 0.877 en tono/pol/intens). Claude se posiciona como outlier más frecuente pero no siempre incorrecto.

### 3.3 Distribución por modelo

```
Tono     | elogio | critica | ataque | personal | autopromo | pregunta | informativo
Claude   |   20   |   13    |   10   |    8     |     4     |    3     |     2
Gemini   |   21   |   16    |    9   |    6     |     2     |    1     |     4
Gemma    |   24   |   15    |    8   |    4     |     3     |    2     |     4

Polaridad| aprobacion | neutral | rechazo
Claude   |    27      |   15    |   18
Gemini   |    27      |    8    |   25
Gemma    |    30      |    9    |   21
```

**Lectura:** Gemini es el más polarizante (menos `neutral`). Gemma tiende a ver más elogios (24 vs 20/21). Claude es el más balanceado en polaridad.

---

## 4. Divergencias sistemáticas

23/60 rows (38%) tienen algún desacuerdo en tono o polaridad. Detalle completo en `rule_gaps.md`.

### 4.1 Seis patrones identificados

| # | Patrón | Volumen | Modelos afectados | Impacto |
|---|---|---|---|---|
| **P1** | Crítica constructiva → Claude marca neutral, G+M marcan rechazo | 6 rows (26% gaps) | Claude outlier | Score político ±1 |
| **P2** | Comments cortos con emojis → Claude personal, G+M elogio | 4 rows | Claude outlier | Score ±1 |
| **P3** | Self-posts del dirigente → Claude autopromocion, G+M informativo | 3 rows | Claude outlier | Score ±1 |
| **P4** | Sarcasmo / ironía → Claude ataque, Gemma critica | 3 rows | Gemma conservador | Intens -3 vs -1 |
| **P5** | Preguntas con crítica implícita → 3 modelos difieren | 2 rows | Gemini outlier | Tono no en v2 |
| **P6** | 3-way divergence genuina | 1 row | Los 3 divergen | Candidato humano |

### 4.2 Gap estructural — vocabulario runner vs matriz v2

| Dimensión | Prompt runner (producción) | Matriz v2 schema BD |
|---|---|---|
| tono | elogio · critica · pregunta · ataque · informativo · personal · autopromocion | critico · propositivo · celebratorio · informativo · solidario · ataque · personal |
| target | dirigente_post · gobierno · oposicion · ciudadania · institucion · otros | gobierno · oposicion · ciudadania · medios · autopromocion · dirigente · tema_especifico · otro |

**Implicación:** el output de Gemma actualmente NO mapea directo a `framework_matrix_defaults.get_polarity()`. Este es el hallazgo estructural más importante del reporte — se aborda en detalle en `PROPUESTA-MATRIZ-V3.md`.

---

## 5. Limitaciones

1. **Silver, no gold.** Sin consenso humano, "acuerdo 3/3" es proxy — no verdad absoluta.
2. **"Majority of two" bias.** Si Claude + Gemini entrenan sobre corpus similares, pueden sesgar igual. No obstante, los datos no sugieren este patrón: Gemini↔Gemma convergen más entre sí que Claude↔ambos.
3. **Muestra N=60.** Estadísticamente razonable para detección de patrones, pero intervalos de confianza amplios. 6 patrones identificados con 23 rows es apoyo suficiente para propuesta de ajustes, no para cerrar preguntas.
4. **Prompt fijo.** No se probó robustez a reformulaciones.
5. **Contexto parcial del comment.** Los comments llegan sin ver otras interacciones del hilo.
6. **Sin majority vote humano.** Los casos 3-way divergence (P6) requieren anotación humana para resolverse.

---

## 6. Recomendaciones

### 6.1 Veredicto Gemma para producción

**VERDE — Gemma3:12b continúa apto para Layer 2.** Justificación:

- Fleiss 3-way en 3 de 4 dimensiones es substancial+ (≥0.744)
- Gemini↔Gemma kappa 0.802+ en tono/pol/intens → Gemma alinea con un modelo premium
- 0 errores de parseo en 60 rows
- Ritmo estable ~10s/item coincide con benchmark 2026-04-14 aceptado

**Observabilidad requerida:**
- Muestra mensual de 50-100 rows re-trianguladas para detectar drift
- Alert si % de 3/3 tono cae <60% o kappa Fleiss <0.55

### 6.2 Acciones sobre el runner y la matriz

Ver `PROPUESTA-MATRIZ-V3.md` para detalles. Resumen:

1. **Corto plazo (1 sprint):** mapper bidireccional runner↔matriz en Layer 3 — desbloquea score político inmediato sin tocar producción.
2. **Medio plazo (3 meses):** realinear runner al vocab matriz v2 — unifica fuente de verdad.
3. **Matriz v3:** decisión CEO — depende del ajuste de vocabulario y de la decisión sobre si `pregunta` es tono distinto o se mapea a `critico/informativo`.

### 6.3 Candidatos prioritarios para anotación humana

Los 23 rows con disagreement — en particular:
- El row 3-way divergence (X_2043431834365653363) como caso ambiguo prototípico
- Los 4 rows P2 (personal vs elogio cortos) como test de emoji-sentiment preprocessing
- Los 6 rows P1 (crítica constructiva) para calibrar threshold Claude vs G+M

---

## 7. Anexos

- `data/sample_60.jsonl` — muestra stratified input
- `data/sample_60_claude.jsonl` · `_gemini.jsonl` · `_gemma.jsonl` — outputs por modelo
- `output/triangulation_matrix.csv` — matriz completa
- `output/agreement_summary.md` — kappas crudos generados por `triangulate.py`
- `output/rule_gaps.md` — análisis detallado 23 gaps + 6 patrones
- `output/PROPUESTA-MATRIZ-V3.md` — propuesta (Fase 3)
- `prompts/layer2_triangulation.md` — prompt congelado SHA256 `b0e456860173...ff464499`
- `scripts/` — pipeline reproducible (seed=42)

---

## 8. Resumen ejecutivo para CEO

- **60 comments clasificados por 3 modelos independientes** (Claude Opus 4.7, Gemini CLI, Gemma3:12b local). Costo $0.
- **Acuerdo alto** en tono (73% 3/3, Fleiss 0.761) y polaridad magnitud (83%, Fleiss 0.803).
- **Gemma alinea con Gemini** (kappa 0.80+) — Gemma3:12b es apto para producción con observabilidad mensual.
- **Hallazgo estructural:** el prompt del runner en producción **no mapea al vocabulario de la matriz v2** (53 reglas). Actualmente el score político no se está computando bien desde el output Gemma.
- **3 opciones** documentadas en propuesta v3: mapper (2-4h), realinear runner (6-8h + re-benchmark), adoptar vocab runner en matriz v3 (4-6h).
- **Recomendación:** mapper como MVP → realinear runner a 3 meses.
- **Decisión pendiente:** matriz v3 requiere tu visto bueno sobre opción A/B/C.

---

*Generado 2026-04-18 · Reproducible con seed=42 + prompt SHA256 congelado + auto-trigger bg.*
