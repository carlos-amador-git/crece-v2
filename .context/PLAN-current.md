# Plan Sprint B Cierre + Matriz v2 — 2026-04-14 tarde (REV 3)

**Origen:** `/sprint-implement` — CEO autoriza ejecución autónoma total.
**Branch destino:** `feat/playwright-carlos-sprint-b` (crear desde main)
**Contexto:** Sprint B corpus ingestado (1,185+ comments, X aggro en último tramo), matriz NLP v1 diseñada para posts necesita v2 para comments.

---

## Sprints

### Sprint 1 — Matriz v2 diseño + Gemini cross-audit (30 min)
**Objetivo:** Documentar y validar la matriz v2 (52 reglas) con contexto post vs comment.

| # | Acción | Archivos | Criterio |
|---|---|---|---|
| 1.1 | Escribir doc v2 completo | `research/memory/2026-04-14-matriz-polaridad-v2-comments.md` | 52 reglas, 3 secciones (mantenidas/overrides/nuevas dirigente-target) |
| 1.2 | `/gemini` cross-audit sobre el doc | stdin al wrapper | Reporte JSON con {aprobadas, cuestionadas, faltantes, sugerencias} |
| 1.3 | Integrar feedback Gemini al doc | mismo archivo | Sección "Ajustes post-audit" |
| 1.4 | Actualizar aprendizajes Sprint B | `2026-04-14-sprint-b-scraping-comments-mx.md` | Link a matriz v2 |

**Dependencias:** ninguna (standalone).
**Skills:** ninguno especial.

### Sprint 2 — Migration + Seed v2 (20 min)
**Objetivo:** Cargar las 52 reglas en BD con backfill de contexto.

| # | Acción | Archivos | Criterio |
|---|---|---|---|
| 2.1 | Migration `ds04` añade columna `contexto` | `backend/migrations/versions/ds04_matrix_context.py` | ALTER TABLE + DEFAULT 'post_dirigente' |
| 2.2 | Seed script para las ~20 reglas nuevas (6 overrides + 14 target=dirigente) | `backend/scripts/seed_matrix_v2.py` | INSERT idempotente con ON CONFLICT |
| 2.3 | Verificación SELECT counts | SQL | `v2` rules = 52, breakdown correcto |

**Dependencias:** Sprint 1 confirmado.
**Skills:** postgresql, fastapi.

### Sprint 3 — Prompt Layer 2 v3 (10 min)
**Objetivo:** Agregar `dirigente` como opción de target al clasificador.

| # | Acción | Archivos | Criterio |
|---|---|---|---|
| 3.1 | Extender `PROMPT_V2` → `PROMPT_V3` | `backend/app/nlp/political_llm_prompt.py` | Añade `dirigente` como target enum |
| 3.2 | Validar unit tests si existen | `backend/tests/` | pytest passes o N/A |

### Sprint 4 — NLP Batch comments (1-2h, incluye wait X)
**Objetivo:** Aplicar pipeline NLP + matriz v2 a todos los social_comments sin `nlp_model_version`.

| # | Acción | Archivos | Criterio |
|---|---|---|---|
| 4.1 | Wait X aggro run finish | — | pgrep x_replies done |
| 4.2 | Validar/adaptar `nlp_comments_batch.py` para usar matriz v2 + contexto='comment_tercero' | `backend/scripts/nlp_comments_batch.py` | Acepta contexto como param |
| 4.3 | Ejecutar batch sobre ~1,200+ comments | — | 100% con nlp_model_version |
| 4.4 | Verificación distribución polaridad por dirigente | SQL | Counts por (dirigente, polaridad) coherentes |

**Dependencias:** Sprint 2 (reglas) + Sprint 3 (prompt).

### Sprint 5 — Commits + PR consolidado (30 min)
**Objetivo:** Cerrar Sprint B en git con 4 ramas (3 Joy + 1 mía) fusionadas en PR.

| # | Acción | Criterio |
|---|---|---|
| 5.1 | Crear rama mía `feat/playwright-carlos-sprint-b` | branch push OK |
| 5.2 | Commit IG + X + YT ytdlp + FB Pineda manual + matriz v2 + docs | commit signed |
| 5.3 | Push 3 ramas de Joy (ya commiteadas) | remote visible |
| 5.4 | Abrir PR consolidado con 4 ramas mergeadas a main | PR URL |

### Sprint 6 — STATUS + DECISIONS update (10 min)
**Objetivo:** Dejar docs al día para próxima sesión.

| # | Acción | Archivos | Criterio |
|---|---|---|---|
| 6.1 | Actualizar STATUS.md con totales finales | `.context/STATUS.md` | Sección Sprint B closed |
| 6.2 | Añadir D-SI-05..09 | `.context/DECISIONS.md` | 5 nuevas decisiones |
| 6.3 | Cross-link Obsidian research ↔ producto | `productos/gobierno/crece-v2.md` | Link matriz v2 |

---

## Cross-audit (`/gemini plan`) → Sprint 1 lo hará sobre la matriz v2, no sobre este plan (scope correcto).

## Criterios de aceptación globales
- ✅ Corpus ≥ 1,200 comments con NLP completo y polaridad asignada via matriz v2
- ✅ Matriz v2 en BD con 52 reglas y columna `contexto`
- ✅ Doc Obsidian + cross-link al producto
- ✅ PR consolidado Sprint B listo para merge
- ✅ STATUS + DECISIONS actualizados

## Riesgos
| Riesgo | Mitigación |
|---|---|
| Gemini 429 RESOURCE_EXHAUSTED | Continuar sin audit, documentar como gap |
| X aggro no termina en 30 min | Proceder con NLP batch parcial sobre comments ya ingestados |
| Schema mismatch en `nlp_comments_batch.py` para matriz v2 | Update script para leer columna `contexto` |
