# Reporte — Triangulación NLP Layer 2 (Claude + Gemini + Gemma)

**Fecha:** 2026-04-18
**Autor:** Joy (sesión Claude Code, CRECE v2 branch `feat/eval-benchmark-v1`)
**Plan:** `.context/PLAN-triangulacion-nlp-2026-04-18.md`

> Documento en formato skeleton. Se rellena automáticamente al cerrar Fase 2 con datos reales.
> Secciones marcadas `[AUTO]` se generan desde scripts; las `[MANUAL]` requieren lectura humana.

---

## 1. Contexto [AUTO]

Gemma3:12b está procesando ~1,152 comments en Layer 2 (clasificación política con 5 dimensiones). Memoria `gemma-ollama-benchmark-2026-04-14` documenta que el CEO aceptó `gemma3:12b concurrency4` como producción, pero el eval humano quedó pendiente.

Este reporte construye un golden set silver-grade con triangulación 3-way (Claude Opus 4.7 + Gemini CLI + Gemma3:12b) sobre una muestra stratified de 60 comments.

---

## 2. Muestra [AUTO]

**Fuente:** Apify replies X + IG posts de 7 dirigentes CRECE (2026-04-18)
**Selección:** stratified seed=42 (plataforma × handle × bucket de longitud)
**Tamaño:** 60 comments

**Cobertura:**
- Plataformas: _AUTO_
- Handles: _AUTO_
- Buckets de longitud: _AUTO_

IDs seleccionados en `data/sample_60.jsonl`. Todos alcanzan el output Gemma porque los 3 corredores usan el mismo loader (`load_all_comments`).

---

## 3. Resultados — Acuerdo entre clasificadores [AUTO]

_Placeholder para tabla de `output/agreement_summary.md`._

### 3.1 Distribución por dimensión [AUTO]

Tabla: por cada dimensión (tono, target, polaridad, intensidad-bucket):
- Conteo de rows con 3/3 agreement (los 3 coinciden exactamente)
- Conteo de 2/3 majority
- Conteo de 3-way divergence
- Cohen's kappa pairwise (Claude-Gemini, Claude-Gemma, Gemini-Gemma)
- Fleiss' kappa 3-way

### 3.2 Errores de parseo [AUTO]

_Conteo de rows con `_err`: no_json, timeout, etc._

---

## 4. Divergencias notables [MANUAL]

### 4.1 Patrones recurrentes

_Identificar durante lectura:_

1. **Elogios cortos con emojis** — ¿se clasifican igual como elogio o hay confusión con "personal"?
2. **Sátira / ironía** — ¿los 3 modelos la detectan?
3. **Target ambiguo dirigente_post vs gobierno** — ¿consistencia?
4. **Autopromoción de dirigente (self-RT)** — ¿todos lo detectan?

### 4.2 Casos con 3-way divergence

_Top 5-10 casos donde los 3 modelos no coinciden — requieren lectura humana y son candidatos primarios para anotación ground truth futura._

### 4.3 Casos con 2/3 majority split

_Casos donde 2 coinciden y 1 diverge — ¿qué modelo es el outlier? ¿hay patrón sistemático?_

---

## 5. Limitaciones [MANUAL]

1. **Silver, no gold.** Sin consenso humano, todo "acuerdo" es de proxies.
2. **"Majority of two" bias.** Si Claude + Gemini entrenan sobre corpus similares, pueden sesgar igual y dominar el "majority" sin que eso signifique corrección.
3. **Muestra de 60.** Intervalos de confianza amplios; útil como señal, no como benchmark definitivo.
4. **Prompt fijo en español.** No se probó robustez a reformulaciones del prompt.
5. **Contexto parcial del comment.** Los comments llegan sin ver otras interacciones del hilo — pierde contexto conversacional.

---

## 6. Recomendaciones [MANUAL + AUTO]

### 6.1 Veredicto Gemma para producción [MANUAL]

Según resultados:
- Si Gemma converge con Claude+Gemini en ≥60% de 3/3 agreement → **OK seguir como producción** (con observabilidad sobre divergencias)
- Si Gemma converge <40% → **revisar prompt** o considerar modelo superior (gemma3:27b, llama3.3:70b)
- Si Gemma diverge más que Claude/Gemini entre sí → **Gemma es el outlier, no los otros**

### 6.2 Gaps de matriz v2 [MANUAL]

_Identificados en `rule_gaps.md` (Fase 3). Lista abreviada de aquí:_

### 6.3 Próximo paso: matriz v3 [MANUAL]

Propuesta concreta en `PROPUESTA-MATRIZ-V3.md` con diff vs v2 + justificación.

---

## 7. Anexos [AUTO]

- `data/sample_60.jsonl` — muestra stratified
- `data/sample_60_claude.jsonl` · `_gemini.jsonl` · `_gemma.jsonl` — outputs por modelo
- `output/triangulation_matrix.csv` — matriz completa
- `output/agreement_summary.md` — kappas
- `output/rule_gaps.md` — Fase 3
- `prompts/layer2_triangulation.md` — prompt congelado SHA256 `b0e456...`
- `scripts/` — pipeline reproducible

---

_Generado el [AUTO] · Reproducible con seed=42 + prompt SHA256 congelado._
