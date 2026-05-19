# PLAN — NLP Layer 2 v3 Mapper · D+0 (2026-05-09)

**Owner:** Linda (CRECE-electoral)
**Origen:** decisiones CEO 2026-05-08 (`.context/DECISIONES-CEO-2026-05-08.md`)
**Aprobación:** C — Mapper intermedio · 100 rows ground truth · UI dual labels opción B · 7 días

## Hallazgo crítico que cambia el plan

Tabla `framework_matrix_defaults` **NO existe en BD**. Migration
`f7a8b9c0d1e2_political_framework.py` está huérfana del chain
(`down_revision='d5d6d7d8d9e0'` no encadena con la cabeza actual
`phb1_pesos_target_politico`). Resultado: `political_framework.get_political_score()`
retorna fallback 0 para TODO comment. **Sistema corre sin matriz política
operativa.**

Antes de construir el mapper hay que:
1. Re-encadenar la migration f7a8b9c0d1e2 al chain actual
2. Aplicarla → crea tabla
3. Correr `seed_matrix_v2.py` → puebla 53 reglas
4. Verificar que `get_political_score()` ahora retorna scores reales

Recién entonces el mapper tiene contra qué mapear.

---

## Sprints D+0

### S1 · Re-encadenar migration f7a8b9c0d1e2 (15 min)

**Objetivo:** la migration political_framework debe aplicarse limpiamente.

**Acciones:**
1. Editar `f7a8b9c0d1e2_political_framework.py`: `down_revision='phb1_pesos_target_politico'`
2. `alembic upgrade head`
3. Verificar tabla con `\d framework_matrix_defaults`

**Criterio aceptación:**
- ✅ `alembic current` reporta `f7a8b9c0d1e2`
- ✅ Tabla existe con columnas (id, version, rol, tono, target, contexto, score_politico, descripcion)

### S2 · Seed matriz v2 (15 min)

**Objetivo:** poblar 53 reglas v2 + ds04_matrix_context (post/comment).

**Acciones:**
1. Correr `python scripts/seed_matrix_v2.py` (idempotente)
2. Correr `python scripts/patch_matrix_v2_post_audit.py` si aplica
3. Verificar: `SELECT COUNT(*) FROM framework_matrix_defaults`

**Criterio aceptación:**
- ✅ ≥ 53 rows en framework_matrix_defaults
- ✅ Probar `get_political_score(rol='oposicion', tono='ataque', target='gobierno')` retorna score ≠ 0

### S3 · Implementar mapper v2→v3 (1.5h)

**Objetivo:** módulo `backend/app/nlp/matriz_v3_mapper.py` con TONO_MAPPING +
TARGET_MAPPING + ajustes G1-G5.

**Acciones:**
1. Crear archivo con docstring + tablas de mapping
2. Implementar `map_runner_to_v2(runner_output: dict) -> dict`
3. R3 (autopromoción runtime) — wrapper que detecta `author == handle_dirigente` antes del mapper y devuelve label directo
4. R5 (G1) — `pregunta → informativo` default, `→ critico` solo con hostility flag (regex de tokens hostiles)
5. R2 (G4) — `emoji-breve → afirmativo_breve` solo si `target=dirigente`
6. R7 (G3) — añadir `mapping_version='v3.0.0'` a output
7. R8 (G5) — counter `_fallbacks` para alert si fallback rate >5%
8. Tests: `tests/nlp/test_matriz_v3_mapper.py`

**Criterio aceptación:**
- ✅ Todos los 7 tonos del runner mappean a tono v2 válido
- ✅ Todos los 6 targets del runner mappean a target v2 válido
- ✅ R3 atrapa autopromoción antes del LLM (regression test)
- ✅ R5 distingue hostility vs informativo
- ✅ Tests >90% cobertura del módulo

### S4 · Smoke contra triangulación 2026-04-18 (30 min)

**Objetivo:** validar que mapper + matriz v2 producen scores razonables sobre
los 60 comments triangulados con ground truth Gemma+Claude+Gemini.

**Acciones:**
1. Cargar `triangulation_matrix.csv` (60 rows con tono/target Gemma)
2. Aplicar mapper → tono_v2/target_v2
3. Llamar `get_political_score()` con (rol, tono_v2, target_v2)
4. Comparar score resultante vs los acuerdos 3/3 de la triangulación
5. Generar `SMOKE-MAPPER-2026-05-09.md` con métricas

**Criterio aceptación:**
- ✅ ≥80% de los 60 comments producen score no-null
- ✅ Concordancia mapper vs Gemini agreement_3of3 ≥75% en tono
- ✅ Reporte legible para CEO

### S5 · Reporte delta v2 vs v3 producción (30 min)

**Objetivo:** medir el impacto si activamos el mapper sobre todos los comments
en BD ahora.

**Acciones:**
1. Sample 500 comments con `nlp_tono` populated (corrida runner Gemma actual)
2. Aplicar mapper a cada uno
3. Calcular score con (rol_dirigente, tono_v2, target_v2)
4. Reporte: distribución tonos antes/después + delta agregado por dirigente

**Criterio aceptación:**
- ✅ Reporte muestra cuántos comments cambian de polaridad efectiva
- ✅ KPIs por dirigente con delta pre/post mapper

### S6 · Update STATUS + DECISIONS + commit (15 min)

Documentar resultado, próximo paso (D+1 = ground truth 100 rows).

---

## Branches / fallback

- **Si S1 falla:** la migration tiene problemas internos no relacionados al
  encadenamiento. Inspect manualmente, reportar y pausar.
- **Si S2 produce <53 rows:** el seed tiene bug post-rebase. Auditar contra
  el doc fuente `research/memory/2026-04-14-matriz-polaridad-v2-comments.md`.
- **Si S4 da concordancia <60%:** mapper o matriz v2 desalineados. Iterar
  TONO_MAPPING/TARGET_MAPPING antes de S5.

## Dependencies

S1 → S2 (chain DB) → S3 (mapper depende de tabla) → S4 → S5 → S6
(todos secuenciales)
