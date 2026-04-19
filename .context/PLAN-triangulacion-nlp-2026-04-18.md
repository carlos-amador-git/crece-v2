# PLAN — Triangulación NLP Layer 2 (Claude + Gemini + Gemma)

**Creado:** 2026-04-18
**Autor:** Joy
**Contexto:** Gemma3:12b corriendo Layer 2 sobre ~1,100 comments. CEO propone sumar Claude Code + Gemini CLI como co-evaluadores para construir golden set silver-grade y calibrar matriz v2.
**Referencias:**
- Memoria `gemma-ollama-benchmark-2026-04-14` (producción CEO 2026-04-14)
- `feedback_session_rem_errors.md` — reglas heredadas
- `project_sprint_b_complete.md` — matriz polaridad v2 (53 reglas)
- `docs/POLITICAL-FRAMEWORK-DEFAULTS.md` (matriz v1 pública)
- `backend/scripts/nlp_layer2_gemma_bg.py` (runner en curso, PID 42073)
- `backend/benchmarks/scraping/results/2026-04-19/nlp_layer2_gemma_out.jsonl`

---

## Objetivo

Triangular 3 clasificadores sobre la MISMA muestra stratified para producir un **golden set silver-grade** sin 100 horas humanas. Usar el resultado para:

1. Validar que Gemma3:12b Layer 2 es aceptable para producción (superar el falso 18.4% de accuracy vs BD saturada)
2. Detectar falsos 0 tipo "💪🧡 Maynez" documentados en Sprint B
3. Alimentar calibración matriz v2 (53 reglas) con casos reales
4. Establecer precedente reusable: 3-way silver golden en vez de ground truth humano 100%

**NO objetivo:** sustituir eval humano real (decisión CEO 2026-04-14 lo mantiene como sprint futuro).

---

## Principios

1. **Silver-grade, no gold.** Sin consenso humano no hay verdad absoluta. Flag cuando 3 divergen entre sí.
2. **Mismo prompt + mismo schema.** Cualquier divergencia se atribuye al modelo, no a la instrucción.
3. **Claude CC en conversación = baseline sin API key.** Precedente Sprint NLP: 79% vs majority humano, 89% vs triple consenso.
4. **Costo $0.** Gemma local + Claude sesión actual + Gemini CLI local.
5. **No ejecutar sprint sin acceptance explícito de fase previa.**

---

## Precondiciones

- Gemma3 bg corriendo sin interrupciones (ETA ~2h desde 11:44 MX)
- `/gemini` skill disponible (confirmado en available skills)
- Acceso a `nlp_layer2_gemma_out.jsonl` para hidratar muestra

---

## Matriz de fases

```
t=0 (ahora)        t=2h (Gemma done)     t=3h           t=4h         t=5h
├─ FASE 0 prep ────┤
                   ├─ FASE 1 colecta ────┤
                                         ├─ FASE 2 ─────┤
                                                        ├─ FASE 3 ───┤
                                                                     ├─ F4 ─┤
```

Fase 0 ocurre en paralelo mientras Gemma termina. Clock-time post-Gemma: ~3.5h.

---

## FASE 0 — Setup preparatorio (~65 min, paralelo a Gemma)

**Objetivo:** tener lista la infra para que Fase 1 sólo ejecute.

| Sprint | Acción | Criterio acceptance | Est |
|---|---|---|---|
| 0.1 | Crear `backend/evaluations/2026-04-18/` + README | Dir existe con README corto explicando la triangulación | 10 min |
| 0.2 | Schema JSON unificado `schema.py` (reusar dataclass de `benchmarks/scraping/schema.py` como referencia) con campos `{id, source_model, tono, target, intensidad, polaridad_preliminar, razon_corta, classified_at}` | Schema validated con pydantic + 1 fixture de ejemplo | 15 min |
| 0.3 | `scripts/stratified_sample.py` — selecciona N comments balanceados (plataforma × handle × longitud bucket). Default N=60 | Script corre contra los 284 ya clasificados, devuelve 60 IDs deterministas con seed | 25 min |
| 0.4 | Prompt unificado `prompts/layer2_triangulation.md` — exactamente el de `nlp_layer2_gemma_bg.py` pero en md | MD legible + checksum vs prompt en runner Gemma | 15 min |

**Gate Fase 0:** 4/4 sprints completos + revisión rápida CEO antes de Fase 1.

---

## FASE 1 — Recolección 3-way (~60 min, serial post-Gemma)

**Precondición:** Gemma output completo (>1,000 rows en jsonl) o decisión CEO de arrancar con subset parcial.

| Sprint | Acción | Criterio acceptance | Est |
|---|---|---|---|
| 1.1 | Correr `stratified_sample.py` → 60 comment_ids | `evaluations/2026-04-18/sample_60.jsonl` con 60 rows (plataforma+handle+texto+post_text+id) | 10 min |
| 1.2 | Claude Code (esta sesión) clasifica 60 one-shot en batch. Output: `sample_60_claude.jsonl` | 60/60 JSON válidos con mismo schema | 20 min |
| 1.3 | `/gemini` CLI clasifica 60 one-shot. Output: `sample_60_gemini.jsonl` | 60/60 JSON válidos con mismo schema | 20 min |
| 1.4 | Extraer Gemma matches del jsonl general → `sample_60_gemma.jsonl` | 60/60 rows extraídos por id | 10 min |

**Gate Fase 1:** 3 archivos con 60 rows c/u, mismo schema, mismos IDs. Persistir SHA256 de cada uno para auditoría.

---

## FASE 2 — Análisis de acuerdo (~65 min)

| Sprint | Acción | Criterio acceptance | Est |
|---|---|---|---|
| 2.1 | `scripts/triangulate.py` — merge 3 jsonl por id, calcular Cohen's kappa pairwise + Fleiss kappa 3-way | Output `triangulation_matrix.csv` con columnas `id, tono_claude, tono_gemini, tono_gemma, agreement_level, notes` | 25 min |
| 2.2 | Categorizar cada comment: `3/3 agree` · `2/3 majority` · `3-way divergence` | Conteos en `agreement_summary.md`. Umbral esperado: ≥40% en 3/3 (precedente Sprint NLP) | 15 min |
| 2.3 | Reporte `evaluations/2026-04-18/REPORTE-TRIANGULACION.md` — metodología, tablas, divergencias notables, conclusiones, recomendación | MD con 6 secciones: contexto, muestra, resultados, divergencias, limitaciones, next | 25 min |

**Gate Fase 2:** Reporte generado + link desde `.context/STATUS.md`.

---

## FASE 3 — Calibración matriz v2 (~60 min)

**Precondición:** Reporte Fase 2 aprobado por CEO (decision point).

| Sprint | Acción | Criterio acceptance | Est |
|---|---|---|---|
| 3.1 | Mapear divergencias contra las 53 reglas matriz v2 (32 post + 21 comment) | Tabla `rule_gaps.md` con columnas `divergence_id, rule_matched, rule_gap, sugerencia` | 20 min |
| 3.2 | Propuesta de ajustes: nuevas reglas, reglas a retirar, ajuste de scores. NO aplicar — sólo propuesta | `PROPUESTA-MATRIZ-V3.md` con diff vs v2 + justificación por regla | 25 min |
| 3.3 | Cross-audit con `/gemini` de la propuesta | Reporte Gemini en el mismo MD como sección final | 15 min |

**Gate Fase 3:** Propuesta documentada + audit Gemini integrado. Sin merge automático.

---

## FASE 4 — Decisión CEO + persistencia (~30 min)

| Sprint | Acción | Criterio acceptance | Est |
|---|---|---|---|
| 4.1 | Presentar resumen ejecutivo CEO: % agreement, top divergencias, recomendación matriz v3 | CEO decide: aplicar v3 / iterar / descartar | 10 min |
| 4.2 (condicional) | Persistir memoria + Obsidian + actualizar BACKLOG | 1 nueva memoria `project_triangulation_layer2_2026-04-18.md` + nota Obsidian en `productos/gobierno/crece-v2/bitacora/` | 20 min |

---

## Riesgos + mitigaciones

| Riesgo | Mitigación |
|---|---|
| Gemma no termina antes de mañana | Arrancar Fase 1 con subset parcial + re-correr cuando Gemma complete |
| Claude + Gemini sesgan igual (modelos grandes entrenados en corpus similar) | Flag 3-way divergence explícitamente. Considerar 4to modelo (Ollama gemma4) si presupuesto tiempo |
| Muestra 60 insuficiente estadísticamente | Aumentar a 100 si Fase 2 muestra intervalos de confianza amplios. Decisión en gate Fase 2 |
| Prompt Gemma ≠ prompt Claude/Gemini | Sprint 0.4 valida checksum + el prompt .md es fuente de verdad para Fases 1.2 y 1.3 |
| "Majority of two" error arrastra al golden | Documentar como limitación explícita. No llamarlo gold — silver |

---

## Integración al plan CRECE existente

**No bloquea:**
- Meta OAuth Setup (puede correr en paralelo por otra sesión o el CEO directamente con Business Manager)
- Retomar Gemma3 Layer 2 como prod (esta triangulación es pre-requisito para firmar "prod lista")

**Bloquea / alimenta:**
- Sprint B+1 item #1 (Gemma Layer 2 batch comments) — valida el batch contra golden silver
- Calibración matriz v2 (era deuda documentada en `project_sprint_b_complete.md`)
- Eval humano futuro (provee sample estratificado + flags de alta divergencia = casos prioritarios para anotación)

**Actualizaciones necesarias tras cierre:**
- `.context/STATUS.md` con link al reporte
- `.claude/context.json` → `proximosPasos` agrega `Matriz v3 si aprobada por CEO`
- Memoria `project_sprint_b_complete.md` extender con sección triangulación
- Obsidian vault `productos/gobierno/crece-v2/bitacora/2026-04-18-triangulacion.md`

---

## Total timeline

- Fase 0: ~65 min (paralelo a Gemma, arranca ya)
- Fase 1: ~60 min
- Fase 2: ~65 min
- Fase 3: ~60 min
- Fase 4: ~30 min

**Total trabajo:** ~4h 40min. **Clock post-Gemma:** ~3.5h.

---

## Gate inicial

¿Apruebas arrancar Fase 0 (sprints 0.1-0.4) ahora mientras Gemma termina? Después de cada fase hay acceptance explícito antes de seguir.
