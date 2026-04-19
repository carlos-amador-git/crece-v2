# Resumen ejecutivo CEO — Triangulación NLP 2026-04-18

**1 página · decisión a tomar · 5 bullets.**

## Qué se hizo

Triangulación 3-way (Claude Opus 4.7 + Gemini CLI + Gemma3:12b local) sobre **60 comments** stratified del corpus Apify 2026-04-18. Costo $0. Clock time ~2h 40min. Pipeline reproducible con seed=42.

## Números duros

| Dimensión | Consenso 3/3 | Fleiss kappa | Lectura |
|---|---:|---:|---|
| Tono | 73% | 0.761 | **Substancial** |
| Target | 63% | 0.418 | Moderado — cuello de botella |
| Polaridad | 77% | 0.744 | **Substancial** |
| Intensidad | 83% | 0.803 | **Casi perfecto** |

Gemini↔Gemma converge mejor que cualquier par con Claude (0.80+ en 3 de 4 dimensiones).

## 5 conclusiones

1. **Gemma3:12b sigue apto para producción** — converge con Gemini premium, 0 errores de parseo, ritmo ~10s/item. Observabilidad mensual recomendada (50 rows re-trianguladas, alert si kappa < 0.55).

2. **Hallazgo estructural crítico:** el prompt del runner en producción NO mapea al vocabulario de la matriz v2 (53 reglas). **El score político de comments no se está computando correctamente hoy.**

3. **3 opciones documentadas** para cerrar el gap:
   - **C — mapper intermedio (2-4h)** — recomendada como MVP, no toca producción
   - **B — realinear runner (6-8h) + re-benchmark** — recomendada a 3 meses
   - **A — migrar matriz al vocab runner (4-6h)** — descartada, pierde matices de v2

4. **6 patrones de divergencia** identificados (R1-R6) + **3 ajustes Gemini** (G1-G5 → R7-R9). El más accionable: R3 — detectar `autopromocion` cuando `author == handle_dirigente` a nivel middleware, sin llamar LLM. Gemini lo calificó "brillante".

5. **Gap central sugerido por Gemini:** mapping `pregunta → critico` en C inflaría rechazo artificialmente. **Ajustado:** default `pregunta → informativo`, sólo `critico` con hostility flag.

## 3 preguntas para ti

1. **Arquitectura matriz v3:** ¿Opción C (MVP) → B (3m), o prefieres otra ruta?
2. **Ground truth humano:** ¿hay presupuesto este mes para anotar 100-500 rows con 3 anotadores (majority vote)? Sin esto, los kappas siguen siendo silver.
3. **UI dual labels:** ¿aceptable que frontend muestre "Elogio" mientras BD guarda "celebratorio" durante transición?

## Documentos para revisar (si quieres profundizar)

- **Resumen completo:** `backend/evaluations/2026-04-18/output/REPORTE-TRIANGULACION.md`
- **Gaps detallados:** `output/rule_gaps.md` (23 rows analizados, 6 patrones)
- **Propuesta final:** `output/PROPUESTA-MATRIZ-V3.md` (con audit Gemini integrado)
- **Bitácora viva:** `productos/gobierno/crece-v2/bitacora/2026-04-18-triangulacion.md` (Obsidian)
- **Data raw:** `output/triangulation_matrix.csv`

## Status de la tarea

- **F0 · F1 · F2 · F3** — cerradas autónomamente por Joy con carta blanca
- **F4.1 (este doc)** — listo, espera decisión CEO
- **F4.2** — persistencia memoria + Obsidian + BACKLOG, se dispara tras tu decisión

---

**Recomendación ejecutiva:** aprobar Opción C + R1+R3+R6 como sprint inmediato (2-4h). Diferir R2/R4/R5 a sprint siguiente tras validación.

---

*Generado por Joy (Claude Code, sesión CRECE v2) · 2026-04-18 · costo $0 · eval humano sigue pendiente.*
