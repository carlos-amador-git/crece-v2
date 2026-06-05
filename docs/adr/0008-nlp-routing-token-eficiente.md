---
adr: 0008
title: NLP routing token-eficiente · textual local + político LLM batcheado
status: Proposed
date: 2026-06-04
author: AGENT linda
deciders: [ceo]
informed: [hugo]
supersedes: null
superseded_by: null
related_adr: [0001]
---

## Title

ADR-0008 · NLP routing token-eficiente — textual a `analyze_full()` local · político a LLM batcheado

## Status

**Proposed** (2026-06-04). El CEO adoptó la propuesta **por ahora** pero NO la da por
cerrada: expresó duda explícita ("no creo que sea así") sobre el supuesto de que la
polaridad política sea irreemplazablemente LLM. Ver **§ Área de investigación futura**.

## Context

El `post_ingest_enrich.py` corre 4 pasos NLP llamando scripts `_cc` (`claude --print`
subprocess) **por item / lotes chicos** sobre ~8,111 posts + 10,005 comments × 7 dirigentes.
Eso quema presupuesto del plan Claude Code. El CEO (2026-06-03) lo marcó como prioridad #1:
"nos gastamos una cantidad exagerada de tokens".

Arquitectura existente (verificada en código, no asumida):
- `backend/app/nlp/analyzer.py::analyze_full()` ya corre **transformers locales HF** ($0, no
  LLM generativo, no Ollama): pysentimiento (sentiment + emotion Ekman-6 + hate), 2 sentiment
  cross-validados, controversy (cardiffnlp), toxicity (citizenlab), topics zero-shot
  (xlm-roberta-large-xnli, 8 temas). Bug conocido (`docs/NLP-MODELOS-INVESTIGACION.md`):
  producción corrió `analyze()` básico, no `analyze_full()` → topics/controversy/toxicity nunca
  se persistieron.
- Capa política: runner LLM clasifica **tono** (7) + **target** (6) → `matriz_v3_mapper.py`
  (reglas, $0) → `framework_matrix_defaults` (53 reglas) → score político. Todo downstream del
  runner es rule-based $0.
- **ADR-0001** (Accepted): Ollama OFF por timeout Coolify. Engines gobernados = CC subprocess +
  Gemini CLI. Gemma removido del Mac después. Por eso el runner cayó a `_cc` pagado.

Cross-audit Gemini (2026-06-04, `~/.claude/bin/gemini-clean`): confirmó el diagnóstico y aportó
el caso límite que invalida "todo local": *"este gobierno son unos ladrones"* → pysentimiento
marca NEG/enojo, pero para un dirigente de oposición es polaridad política POSITIVA (ataca al
rival). El sentiment local es **ciego a la política**; si se alimenta el `matriz_v3_mapper` con
labels locales el `fallback_rate` es 100%.

## Decision (Proposed)

**Separar el routing por naturaleza del campo, no por paso:**

1. **Campos textuales → `analyze_full()` local ($0):** `sentiment_score`, `emotions`,
   `topics_extracted`, `toxicity`, `controversy`. Reusa el stack HF ya construido. NO toca
   Ollama, NO viola ADR-0001.
2. **Campos políticos → LLM, pero BATCHEADO (~20 items/llamada):** `nlp_tono`, `nlp_target`,
   `nlp_polaridad` de comments (y tono/target de posts). El runner LLM es **irreemplazable** para
   intención política — sin él el mapper colapsa. El batcheo reduce ~95% el consumo vs per-item
   sin perder fidelidad ni cambiar infraestructura.
3. **Ollama-madrugada DESCARTADO** (Gemini): alto esfuerzo/riesgo, requeriría ADR nuevo que
   supersede 0001 + re-dimensionar VPS. No vale vs el batcheo.

**Implementación: NO ahora.** Se aplica en la **próxima actualización de dirigentes** (próximo
ciclo de ingest/enrich), no se re-corre el enrich sobre data actual. Esta ADR deja el contrato
documentado para ese momento.

## Consequences

### Positivas
- ~95% menos consumo de plan CC reusando lo construido (analyze_full + scripts batch existentes).
- Sin Ollama, sin ADR nuevo, sin re-dimensionar VPS, sin evaluación de modelos nueva.
- Precisión política preservada (el runner sigue dando tono/target reales).
- Cierra el bug histórico de `analyze()` vs `analyze_full()` (topics/toxicity por fin se pueblan).

### Negativas / costo
- El paso 2 (comments político) NO se vuelve $0 — sigue consumiendo LLM, solo que mucho menos.
- Requiere refactor de `post_ingest_enrich.py` para rutear textual→local y batchear el runner.

### Riesgos aceptados
- El supuesto central ("polaridad política es irreemplazablemente LLM") NO está cerrado — ver
  abajo.

## Área de investigación futura (CEO 2026-06-04 · "no creo que sea así")

El CEO NO está convencido de que la polaridad política deba ser siempre LLM. Pregunta abierta a
investigar en su propio sprint (NO cerrar con esta ADR):

- ¿Se puede derivar `nlp_polaridad` política de forma más barata/local combinando: NER político
  (detectar gobierno/oposición/rival en el texto) + sentiment local + `rol_dirigente` + reglas,
  sin invocar un LLM por item? El `matriz_v3_mapper` ya es rule-based; ¿se le puede anteponer un
  clasificador de tono/target local (no-LLM) con precisión aceptable?
- ¿Un modelo HF zero-shot con etiquetas políticas custom (no solo los 8 topics) podría producir
  tono/target sin LLM generativo?
- Validar el `fallback_rate` real con muestra etiquetada antes de asumir 100%.

Esta es la duda del CEO registrada explícitamente para no perderla. Mientras tanto, la decisión
§Decision aplica como interino.

## Confirmation

Cuando se implemente (próxima actualización):
- `post_ingest_enrich.py` rutea sentiment/emotion/topics/toxicity a `analyze_full()` (verificable:
  grep que esos pasos NO llaman `claude` subprocess).
- El runner político batchea ~20 items/llamada (verificable en el script).
- Medir consumo CC antes/después sobre 1 dirigente real.

## More Information

- Research previa (no re-evaluar): `docs/NLP-MODELOS-INVESTIGACION.md`.
- Arquitectura mapper: `.context/PLAN-2026-05-09-nlp-v3-mapper.md` + `backend/app/nlp/matriz_v3_mapper.py`.
- ADR padre del engine: ADR-0001 (Ollama off).
- Pipeline actual: `backend/scripts/post_ingest_enrich.py`.
