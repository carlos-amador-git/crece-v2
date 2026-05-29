# Inventario de branches not-merged · 2026-05-09

> Auditoría forense solo-lectura. Sin checkouts. Sin merges. Sin push.
> Producido por sesión Jess (CRECE v2). Base de comparación: `main` (HEAD `713b526`).

## Resumen ejecutivo

- **13 ramas not-merged a main** (verificado vía `git branch --no-merged main`).
- **9 ramas remotas (origin/)** + **4 ramas locales-only** sin tracking remoto:
  - Locales-only: `feat/brightdata-browser-joy`, `feat/brightdata-yt-joy`, `feat/scraperapi-tiktok-joy`, `feat/scrapling-v2`.
- **2 ramas con migrations alembic críticas no presentes en main:**
  - `feat/phase-b-pesos-editables` — 31 migrations únicas (fase-b live + ds01-04 + dse_hitl + s1m1/s3m1/s5m1 + h9c0d1e2f3g4 + g8b9c0d1e2f3 + f7a8b9c0d1e2 + phb1).
  - `backup/pre-opcion-d-eval-v1` ≡ `feat/eval-benchmark-v1` (idénticas árbol y commits, hash último 3921f10).
- **1 rama con código operativo crítico ✅ ACTIVA**: `feat/phase-b-pesos-editables` (head propio + 42 commits + 337 archivos cambiados, +42 308 / -704 LOC).
- **3 ramas con valor histórico-forense pero superadas por phase-b**: `feat/eval-benchmark-v1`, `backup/pre-opcion-d-eval-v1`, `feat/scrapling-v2`. Contienen árbol completo de `backend/eval/layer2_benchmark/` + benchmarks scrapecreators/apify/brightdata 2026-04-18 y 2026-04-19 (≈190 archivos únicos vs phase-b).
- **3 ramas docs livianas** (1 commit de docs cada una): `docs/joy-gap-analysis-refresh`, `docs/joy-seed-inventario`, `docs/prompt-plan-ia-v1.1-prepared`.
- **5 ramas pequeñas con scripts** que YA fueron restaurados en phase-b commit `dccd7aa restaurar 5 scripts perdidos`: `feat/brightdata-browser-joy`, `feat/brightdata-yt-joy`, `feat/scraperapi-tiktok-joy`, `feat/joy-scraper-demoscopia`, `feat/agentation-widget-and-mcp-fixes`.
- **1 rama del primer scaffold superado**: `feat/crece-v2-full-implementation` (PR #1 closed, no merged).
- **PRs abiertos asociados**: 3 → #15 (eval-benchmark-v1), #35 (agentation), #48 (phase-b).
- **Recomendación global de orden**: (1) merge `feat/phase-b-pesos-editables` a main vía PR #48 con squash o merge regular — incluye TODO lo que el piloto necesita; (2) cherry-pick árbol `backend/eval/layer2_benchmark/` desde `feat/eval-benchmark-v1` hacia phase-b ANTES del merge si se quiere preservar; (3) archivar el resto.

---

## Glosario / convenciones

- ✅ ACTIVO: trabajo vivo, alto valor, indispensable para piloto / próximas sprints.
- ⚠️ MIXTO: parte vivo, parte superado por otra rama.
- 🟡 SUPERADO: trabajo ya integrado a través de otra ruta (cherry-pick, restauración manual, etc.).
- ❌ ABANDONADO: experimental, sin uso productivo, sin PR vigente.

---

## Hallazgo crítico sobre `0681153`

Commit `0681153 feat(encuestas+eval): Oraculus + Demoscopía scrapers + benchmark 4H×4M completo` (2026-04-14) introdujo:

1. **`backend/app/scrapers/encuestas_oraculus.py`** — ✅ HOY EN `feat/phase-b-pesos-editables` (re-introducido en commit `dccd7aa restaurar 5 scripts perdidos`). NO en main.
2. **`backend/app/scrapers/encuestas_demoscopia.py`** — ✅ HOY EN `feat/phase-b-pesos-editables`. NO en main.
3. **`backend/eval/layer2_benchmark/`** (árbol completo: schema.json, datasets v1+v2, scripts compare_v2/final, reports comparison_final.md, ~33 archivos) — ❌ NO EN PHASE-B, NO EN MAIN. Solo vive en `feat/eval-benchmark-v1`, `backup/pre-opcion-d-eval-v1`, `feat/scrapling-v2`.

**Inferencia:** los cherry-picks de `eval-v1` (PRs #38, #39, #41) restauraron parte del trabajo pero NO el directorio `backend/eval/layer2_benchmark/`. Si el CEO necesita ese benchmark, hay que cherry-pickearlo explícitamente.

---

## Por cada rama (13 secciones)

### `feat/phase-b-pesos-editables` (current)

- **Última actividad:** 2026-05-08 13:54
- **Autor último commit:** MarxCha (`c5cbffe`)
- **Commits únicos vs main:** 42
- **LOC neto:** +42 308 / -704 (337 archivos)
- **Archivos clave únicos vs main:**
  - `.context/PLAN-D-23-H-panel-editable-2026-04-24.md`, `.context/PLAN-2026-05-09-editor-hitl.md`, `.context/PLAN-2026-05-09-nlp-v3-mapper.md`, `.context/DECISIONES-CEO-2026-05-08.md`
  - `backend/app/scrapers/encuestas_oraculus.py`, `encuestas_demoscopia.py`, `encuestas_mitofsky_pdf.py`, `encuestas_mitosky.py`, `encuestas_pollsmx.py`
  - `backend/app/api/v1/endpoints/hitl_evaluation.py`, `nlp_v3.py`, `pesos_target_politico.py` (inferred from migrations)
  - `backend/tests/api/test_hitl_evaluation.py`, `e2e/test_hitl_evaluation_flow.py`, `nlp/test_matriz_v3_mapper.py`, `services/test_score_recompute.py`
  - 7 audit artifacts AUDIT-*-2026-04-25 + frontend-review-2026-04-20 screenshots
- **Migrations alembic (32 nuevas vs main):** `s1m1_sprint_s1_schema`, `s3m1_promesas_dirigente`, `s5m1_onboarding_tables`, `f7a8b9c0d1e2_political_framework`, `g8b9c0d1e2f3_encuestas_publicas`, `h9c0d1e2f3g4_social_comments`, `ds01_data_source_enum`, `ds02_social_profile_snapshots`, `ds03_social_comments_data_source` (versión MODIFICADA vs main — ver §Conflictos), `ds04_matrix_context`, `dse_hitl_audit`, `phb1_pesos_target_politico` (down_revision: `d23g1_actividad_alineada`).
- **Schema BD:** Pesos editables en `dirigentes` (3 cols con CHECK 0.5-1.5 + last_modified), tablas HITL audit, social_profile_snapshots, encuestas_publicas, political_framework, social_comments + data_source col, matrix_context.
- **Tests nuevos:** sí, `backend/tests/{api,e2e,nlp,services}/` con 4 archivos test + __init__.py.
- **Estado de tests:** depende (no se corre — solo lectura de árbol).
- **Trabajo activo en otro lado:** no — esta rama es el HEAD vivo del proyecto.
- **Dependencias:** consume contenido restaurado de `feat/eval-benchmark-v1` (commits cherry-picked vía PRs #38/#39/#41) excepto `backend/eval/layer2_benchmark/`.
- **PR asociado:** #48 OPEN (`feat: Phase B (D-23-H) + hardening AUDIT 2026-04-25`).
- **Estado:** ✅ ACTIVO.
- **Acción recomendada:** **merge a main vía PR #48** (orden #1).
- **Razón:** Es la rama de trabajo viva; consolida HITL, NLP v3, encuestas públicas pipeline, audits 2026-04-25, hardening AUDIT, ruff sweep, Docker multi-stage, panel editable D-23-H Phase B.
- **Notas:** la versión de `ds03_social_comments_data_source.py` aquí difiere de main (hash `357eb137` vs `06d21ab9` en main). Hay que decidir cuál se queda durante el merge — ver sección Conflictos.

---

### `backup/pre-opcion-d-eval-v1`

- **Última actividad:** 2026-04-18 11:27
- **Autor último commit:** MarxCha (`3921f10`)
- **Commits únicos vs main:** 15
- **LOC neto:** +174 194 / -695 (242 archivos — incluye XLS binarios calibración 7 dirigentes)
- **Archivos clave únicos vs main:** ÁRBOL IDÉNTICO a `feat/eval-benchmark-v1` (verificado: `git diff feat/eval-benchmark-v1..backup/pre-opcion-d-eval-v1` → vacío).
- **Migrations alembic:** `3d6fe3f1660d_add_resultados_electorales_seccion_2024.py` (presente en main HOY post-PR #42), `ds03_social_comments_data_source.py` (presente en main HOY).
- **Schema BD:** ya cubierto por main.
- **Tests nuevos:** ninguno.
- **Estado de tests:** no aplica.
- **Trabajo activo en otro lado:** sí — es backup pre-merge de `feat/eval-benchmark-v1`. Idéntica.
- **Dependencias:** ninguna.
- **PR asociado:** ninguno.
- **Estado:** 🟡 SUPERADO (duplicado).
- **Acción recomendada:** **archive con tag** (`git tag archive/backup-pre-opcion-d-eval-v1` y luego `git branch -D` opcionalmente).
- **Razón:** redundante con `feat/eval-benchmark-v1`. Su única utilidad es servir como punto-de-rollback congelado pre-cherry-pick. Si phase-b se mergea, este backup queda superado.
- **Notas:** El nombre `pre-opcion-d` se refiere a una decisión arquitectural histórica (Triangulación NLP Layer 2 § paquete §5 cerrado 2026-05-08).

---

### `docs/joy-gap-analysis-refresh`

- **Última actividad:** 2026-04-14 17:13
- **Autor último commit:** MarxCha (`668dcb1`)
- **Commits únicos vs main:** 2
- **LOC neto:** +104
- **Archivos clave únicos vs main:** `.context/GAP-ANALYSIS-2026-04-14.md`
- **Migrations alembic:** ninguna.
- **Schema BD:** ninguno.
- **Tests nuevos:** ninguno.
- **Estado de tests:** no aplica.
- **Trabajo activo en otro lado:** no — es docs aislado.
- **Dependencias:** ninguna.
- **PR asociado:** ninguno.
- **Estado:** ⚠️ MIXTO (docs vigente pero hace 24 días sin tocar; hay PLANs más recientes en phase-b que probablemente lo superan).
- **Acción recomendada:** **revisar manualmente, decidir si copiar el MD a `.context/` en phase-b o archive**. Si decisiones P0-1/P0-2 Ollama ya están en main vía gap-analysis posterior, archive.
- **Razón:** el MD habla de gaps Ollama resueltos por Carlos. Si esa info ya migró a STATUS o DECISIONS, redundante.
- **Notas:** mensaje del commit dice "P0-1 + P0-2 Ollama as resolved per Carlos confirmation" → probablemente ya migrado a memoria de sesión.

---

### `docs/joy-seed-inventario`

- **Última actividad:** 2026-04-14 17:32
- **Autor último commit:** MarxCha (`b89aa91`)
- **Commits únicos vs main:** 1
- **LOC neto:** +202
- **Archivos clave únicos vs main:** `.context/SEED-INVENTARIO-2026-04-14.md`
- **Migrations alembic:** ninguna.
- **Schema BD:** ninguno.
- **Tests nuevos:** ninguno.
- **Estado de tests:** no aplica.
- **Trabajo activo en otro lado:** posible — phase-b tiene `.context/SEED-PLAN-2026-04-14.md` y `SEED-INVENTARIO` puede haber sido absorbido.
- **Dependencias:** ninguna.
- **PR asociado:** ninguno.
- **Estado:** 🟡 SUPERADO (probable).
- **Acción recomendada:** **verificar contenido vs phase-b's `.context/SEED-PLAN-2026-04-14.md`**; si está duplicado, archive. Si tiene info no portada, copiar el MD a phase-b antes de archive.
- **Razón:** investigación pre-seed-plan; el seed-plan posterior ya consume sus hallazgos.

---

### `docs/prompt-plan-ia-v1.1-prepared`

- **Última actividad:** 2026-04-20 13:52
- **Autor último commit:** MarxCha (`403dd31`)
- **Commits únicos vs main:** 1
- **LOC neto:** +368
- **Archivos clave únicos vs main:** `backend/research/2026-04-19/PROMPT-PLAN-IA-v1.1.md`
- **Migrations alembic:** ninguna.
- **Schema BD:** ninguno.
- **Tests nuevos:** ninguno.
- **Estado de tests:** no aplica.
- **Trabajo activo en otro lado:** no.
- **Dependencias:** ninguna.
- **PR asociado:** ninguno.
- **Estado:** ⚠️ MIXTO — el commit dice "preparado (no activo)". Es un draft de prompt v1.1.
- **Acción recomendada:** **cherry-pick el archivo a phase-b si v1.1 sigue siendo el target activo**, o archive si ya hay v1.2 en phase-b.
- **Razón:** prompt LLM listo para deploy condicional. Bajo costo de absorción.
- **Notas:** verificar si phase-b tiene `backend/research/2026-04-19/` o estructura equivalente.

---

### `feat/agentation-widget-and-mcp-fixes`

- **Última actividad:** 2026-04-20 23:00
- **Autor último commit:** MarxCha (`0c4d2da`)
- **Commits únicos vs main:** 2
- **LOC neto:** +431 / -725 (13 archivos — net negativo por test-results purge)
- **Archivos clave únicos vs main:**
  - `frontend/src/components/providers/agentation-provider.tsx` (NUEVO en esta rama)
  - `.mcp.json`, `frontend/src/app/layout.tsx` modificados
  - 4 archivos `frontend/test-results/.../error-context.md` (basura de tests Playwright)
- **Migrations alembic:** ninguna.
- **Schema BD:** ninguno.
- **Tests nuevos:** ninguno (sólo error-contexts auto-generados).
- **Estado de tests:** no aplica.
- **Trabajo activo en otro lado:** posible — phase-b tiene MCP/agentation fixes propios. Verificar `.mcp.json` y layout.tsx en phase-b.
- **Dependencias:** ninguna.
- **PR asociado:** #35 OPEN (`feat(frontend+mcp): agentation widget + crawlbase node22 fix`).
- **Estado:** ⚠️ MIXTO — tiene 1 archivo nuevo (agentation-provider) que puede o no estar en phase-b.
- **Acción recomendada:** **cherry-pick `agentation-provider.tsx` y diff de `.mcp.json` + `layout.tsx` a phase-b si no existen ahí**; cerrar PR #35.
- **Razón:** memoria de sesión menciona "Agentation MCP config fix (restart CC requerido)" como pendiente Joy 2026-04-20 → puede ser justo este trabajo.

---

### `feat/brightdata-browser-joy` (LOCAL-ONLY, sin tracking)

- **Última actividad:** 2026-04-14 08:07
- **Autor último commit:** MarxCha (`7766484`)
- **Commits únicos vs main:** 2
- **LOC neto:** +511 (3 archivos)
- **Archivos clave únicos vs main:**
  - `backend/app/services/brightdata_browser.py`
  - `backend/scripts/brightdata_facebook_comments.py`
  - `backend/scripts/brightdata_twitter_replies_test.py`
- **Migrations alembic:** ninguna.
- **Schema BD:** ninguno.
- **Tests nuevos:** ninguno.
- **Estado de tests:** no aplica.
- **Trabajo activo en otro lado:** **probable** — phase-b commit `dccd7aa restaurar 5 scripts perdidos + archive Brightdata` sugiere que estos scripts fueron archivados/movidos.
- **Dependencias:** ninguna.
- **PR asociado:** ninguno (sin remoto).
- **Estado:** 🟡 SUPERADO (probable).
- **Acción recomendada:** **diff vs phase-b `backend/app/services/` y `backend/scripts/`**. Si ya existen (incluso bajo `_archive/`), borrar rama local. Si son originales no portados, push a origin + crear PR consultivo o archivar bajo tag.
- **Razón:** Sprint B trabajo sobre Brightdata; el comentario "archive Brightdata" en phase-b indica decisión de retirar este stack.
- **Notas:** rama LOCAL-ONLY. Pérdida silenciosa si se borra el repo local sin push.

---

### `feat/brightdata-yt-joy` (LOCAL-ONLY, sin tracking)

- **Última actividad:** 2026-04-14 11:30
- **Autor último commit:** MarxCha (`fe15510`)
- **Commits únicos vs main:** 1
- **LOC neto:** +440 (3 archivos)
- **Archivos clave únicos vs main:**
  - `.context/NOTES-YT-BRIGHTDATA-SPRINTB.md`
  - `backend/app/services/brightdata_browser.py` (NOTA: mismo nombre que `feat/brightdata-browser-joy` — versión divergente)
  - `backend/scripts/brightdata_youtube_comments.py`
- **Migrations alembic:** ninguna.
- **Schema BD:** ninguno.
- **Tests nuevos:** ninguno.
- **Estado de tests:** no aplica.
- **Trabajo activo en otro lado:** **probable** — phase-b "archive Brightdata" sugiere retirado.
- **Dependencias:** **conflicto potencial** con `feat/brightdata-browser-joy` (mismo `brightdata_browser.py` con divergencia).
- **PR asociado:** ninguno.
- **Estado:** 🟡 SUPERADO (probable).
- **Acción recomendada:** **mismo trato que `brightdata-browser-joy`**: diff + decidir archive. Probable archive bajo tag `archive/brightdata-experiments-sprint-b`.
- **Razón:** stack de scraping descontinuado. NOTES md probablemente útil como referencia histórica.

---

### `feat/crece-v2-full-implementation`

- **Última actividad:** 2026-04-03 23:58
- **Autor último commit:** MarxCha (`281e2a5`)
- **Commits únicos vs main:** 1
- **LOC neto:** +1 289 / -27 (8 archivos)
- **Archivos clave únicos vs main:**
  - `backend/app/models/{benchmark,electoral,plan_ia,social}.py`
  - `docs/ARQUITECTURA-INTEGRADA.md`, `docs/SPRINT-F2.0-INTEGRATION.md`, `docs/TASK-integration-endpoints.md`
- **Migrations alembic:** ninguna (sólo modelos sin migration).
- **Schema BD:** los 4 modelos del scaffold inicial — superados por migrations posteriores en main.
- **Tests nuevos:** ninguno.
- **Estado de tests:** no aplica.
- **Trabajo activo en otro lado:** sí — el ecosistema completo evolucionó después de este scaffold inicial.
- **Dependencias:** ninguna.
- **PR asociado:** #1 CLOSED (no merged).
- **Estado:** 🟡 SUPERADO (scaffold inicial + 4 docs).
- **Acción recomendada:** **archive con tag** `archive/crece-v2-full-implementation-scaffold`. Verificar antes que los 3 docs (`ARQUITECTURA-INTEGRADA`, `SPRINT-F2.0`, `TASK-integration-endpoints`) no contengan info no migrada.
- **Razón:** primer commit "ecosystem context"; el repo ya superó esa estructura por completo.

---

### `feat/eval-benchmark-v1`

- **Última actividad:** 2026-04-18 11:27
- **Autor último commit:** MarxCha (`3921f10`) — IDÉNTICO a `backup/pre-opcion-d-eval-v1`.
- **Commits únicos vs main:** 15
- **LOC neto:** +174 194 / -695 (242 archivos)
- **Archivos clave únicos vs main:**
  - **Trabajo NO en phase-b** (reapilación crítica):
    - `backend/eval/layer2_benchmark/` ÁRBOL COMPLETO (~33 archivos): schema.json, datasets/v1+v2 (samples.json, samples.xlsx, answers/{claude_opus_4_6, gemini_cli, gemma3_4b, persona_1..4_marx, pipeline_bd}.json), reports/v2_2026-04-14/{comparison.md, comparison_final.md, comparison_schema2.md}, scripts/{compare_all,compare_final,compare_v2,compare_v2_schema2,export_excel,export_excel_v2,extract_pipeline_bd,import_human,import_human_v2}.py.
    - `backend/benchmarks/scraping/` resultados scrapecreators 2026-04-18 (~80 archivos JSON 13 dirigentes × IG/TT/X/FB/YT) + apify 2026-04-19 + brightdata 2026-04-19 + scrapling_x_v2 2026-04-19 + calibracion XLS 7 dirigentes.
    - `.context/HANDOFF-REM-2026-04-18.md`, `.context/SEED-PLAN-2026-04-14.md`, `.context/SPRINT-REVIEW-2026-04-14.md`.
    - `backend/app/scrapers/comments.py`, `encuestas_mitosky.py` (variante pre-pipeline final).
- **Migrations alembic:** `3d6fe3f1660d` (en main hoy), `ds03_social_comments_data_source.py` (en main hoy).
- **Schema BD:** ya cubierto por main.
- **Tests nuevos:** ninguno.
- **Estado de tests:** no aplica.
- **Trabajo activo en otro lado:** parcial — los scrapers `encuestas_oraculus.py` y `encuestas_demoscopia.py` ya están en phase-b vía commit `dccd7aa`. El árbol `backend/eval/layer2_benchmark/` y los benchmarks NO.
- **Dependencias:** ninguna.
- **PR asociado:** #15 OPEN (`feat(joy-day): aceptacion drill-down + Gemma3 Layer 2 + P0 org scope + migrations`).
- **Estado:** ⚠️ MIXTO — alta densidad de trabajo histórico forense; bajo retorno operativo; alto valor de evidencia.
- **Acción recomendada:** **(a)** Cherry-pick `backend/eval/layer2_benchmark/` ÁRBOL COMPLETO + `.context/HANDOFF-REM-2026-04-18.md` + `.context/SEED-PLAN-2026-04-14.md` + `.context/SPRINT-REVIEW-2026-04-14.md` a phase-b (preservar evidencia decisiones §5 cerradas 2026-05-08). **(b)** Cerrar PR #15. **(c)** Tag `archive/feat-eval-benchmark-v1` y borrar rama remota tras absorción.
- **Razón:** contiene la decisión cuantitativa "schema v2 simplificado sube agreement humano de 9.3% → 74.1% / Claude Opus 95.5% / Gemma 4B 79.5% / pipeline 52.3%" — base del paquete §5 cerrado 2026-05-08.
- **Notas:** los 174K LOC son ~95% binarios XLS y JSON de benchmark. Si CEO acepta perder los benchmarks crudos y conservar solo `backend/eval/layer2_benchmark/`, baja a +5K LOC.

---

### `feat/joy-scraper-demoscopia`

- **Última actividad:** 2026-04-14 20:23
- **Autor último commit:** MarxCha (`b08c54e`)
- **Commits únicos vs main:** 1
- **LOC neto:** +296 (1 archivo)
- **Archivos clave únicos vs main:** `backend/app/scrapers/encuestas_demoscopia.py`
- **Migrations alembic:** ninguna.
- **Schema BD:** ninguno.
- **Tests nuevos:** ninguno.
- **Estado de tests:** no aplica.
- **Trabajo activo en otro lado:** **sí** — phase-b YA TIENE `encuestas_demoscopia.py` (introducido en `dccd7aa`).
- **Dependencias:** ninguna.
- **PR asociado:** ninguno.
- **Estado:** 🟡 SUPERADO.
- **Acción recomendada:** **archive con tag**, ya que phase-b consume el script.
- **Razón:** rama de desarrollo aislada; objetivo logrado vía absorción en phase-b.
- **Notas:** verificar diff entre versión phase-b vs esta rama por si phase-b regresó a versión anterior.

---

### `feat/scraperapi-tiktok-joy` (LOCAL-ONLY, sin tracking)

- **Última actividad:** 2026-04-14 07:08
- **Autor último commit:** MarxCha (`057e51c`)
- **Commits únicos vs main:** 2
- **LOC neto:** +319 (2 archivos)
- **Archivos clave únicos vs main:**
  - `backend/migrations/versions/ds03_social_comments_data_source.py` (idéntica a main, hash `06d21ab9`)
  - `backend/scripts/scraperapi_tiktok_comments.py`
- **Migrations alembic:** `ds03_social_comments_data_source.py` (NO conflictiva — ya en main).
- **Schema BD:** ya en main.
- **Tests nuevos:** ninguno.
- **Estado de tests:** no aplica.
- **Trabajo activo en otro lado:** **sí** — phase-b commit `0611313 feat(scrapers): TT comments via ScraperAPI (restaurado de Sprint B abr-14)` indica que el script fue restaurado.
- **Dependencias:** ninguna.
- **PR asociado:** ninguno.
- **Estado:** 🟡 SUPERADO.
- **Acción recomendada:** **archive (rama local-only, no requiere push)**; verificar que el script en phase-b tenga la misma intención funcional.
- **Razón:** trabajo absorbido por phase-b explícitamente.

---

### `feat/scrapling-v2` (LOCAL-ONLY, sin tracking, marcada con `+` = checked-out alguna vez)

- **Última actividad:** 2026-04-15 14:21
- **Autor último commit:** MarxCha (`73337b9`)
- **Commits únicos vs main:** 12
- **LOC neto:** +9 531 / -466 (65 archivos)
- **Archivos clave únicos vs main:**
  - `backend/eval/layer2_benchmark/` ÁRBOL COMPLETO (33 archivos — IDÉNTICO al de `feat/eval-benchmark-v1`).
  - `.context/SEED-PLAN-2026-04-14.md`, `.context/SPRINT-REVIEW-2026-04-14.md` (mismos que eval-benchmark-v1).
  - `backend/app/scrapers/encuestas_demoscopia.py`, `encuestas_oraculus.py`.
  - `backend/migrations/versions/ds03_social_comments_data_source.py` (hash `06d21ab9` — idéntico main).
- **Migrations alembic:** `ds03_social_comments_data_source.py` (NO conflictiva — idéntica main).
- **Schema BD:** sin cambios.
- **Tests nuevos:** ninguno.
- **Estado de tests:** no aplica.
- **Trabajo activo en otro lado:** **sí** — `backend/eval/layer2_benchmark/` también está en `feat/eval-benchmark-v1`. Los 12 commits de scrapling-v2 son subset frontend-fixes + seed + 0681153 + Gemma3 Layer 2 + 4 fixes UI iOS.
- **Dependencias:** ninguna.
- **PR asociado:** ninguno.
- **Estado:** 🟡 SUPERADO (duplica trabajo de eval-benchmark-v1).
- **Acción recomendada:** **archive con tag** `archive/feat-scrapling-v2-snapshot`. Si CEO quiere conservar tree puro `backend/eval/layer2_benchmark/`, basta el tag desde `feat/eval-benchmark-v1`.
- **Razón:** redundante. 12 commits vs 15 commits de eval-benchmark-v1 = subset.
- **Notas:** **rama LOCAL-ONLY con `+` (checked-out alguna vez)**. Si se borra accidentalmente sin push, se pierde junto con el trabajo de la `+`. Esta rama probablemente fue el WIP previo al backup.

---

## Dependencias y conflictos entre ramas

### Tabla cruzada · archivos compartidos relevantes

| Archivo | Ramas que lo modifican | Riesgo conflicto |
|---|---|---|
| `backend/migrations/versions/ds03_social_comments_data_source.py` | main, scraperapi-tiktok-joy, scrapling-v2, eval-benchmark-v1 (todas hash `06d21ab9`); `phase-b` (hash distinto `357eb137`) | **MEDIO** — phase-b regresó a versión modificada del archivo. Debe revisarse el diff antes del merge a main. |
| `backend/migrations/versions/3d6fe3f1660d_add_resultados_electorales_seccion_2024.py` | main (post PR #42), eval-benchmark-v1, backup, phase-b | **BAJO** — ya integrada y post-mortem cerrado (D-OPS-07..10). |
| `backend/app/scrapers/encuestas_oraculus.py` | phase-b, eval-benchmark-v1, backup, scrapling-v2 | **BAJO** — phase-b lo restauró vía `dccd7aa`. |
| `backend/app/scrapers/encuestas_demoscopia.py` | phase-b, eval-benchmark-v1, backup, scrapling-v2, joy-scraper-demoscopia | **BAJO** — múltiples versiones; phase-b mantiene la canónica. |
| `backend/app/services/brightdata_browser.py` | brightdata-browser-joy, brightdata-yt-joy | **MEDIO interno** — los dos branches Brightdata divergen entre sí; phase-b dice "archive Brightdata" → ambos archivables. |
| `backend/scripts/scraperapi_tiktok_comments.py` | scraperapi-tiktok-joy, phase-b | **BAJO** — phase-b lo restauró. |
| `backend/eval/layer2_benchmark/*` | eval-benchmark-v1, backup (idéntico), scrapling-v2 (idéntico) | **NULO** — ningún branch destino lo tiene. |
| `frontend/src/components/providers/agentation-provider.tsx` | agentation-widget-and-mcp-fixes | **BAJO** — único introductor; verificar si phase-b lo tiene equivalente. |

### Migrations alembic conflictivas

- **No hay heads divergentes en alembic chain.** El head canónico vivo es `phb1_pesos_target_politico` (down_revision `d23g1_actividad_alineada`).
- **Riesgo único**: `ds03_social_comments_data_source.py` tiene 2 versiones por blob hash distintos. Ambas tienen el mismo `Revision ID: ds03_sc_data_source` y mismo `Revises: ds02_social_profile_snapshots`. La diferencia debe ser en el cuerpo (no inspeccionado en este audit). Si se mergea phase-b sin reconciliar, alembic upgrade head no fallará pero la DB tendrá la versión phase-b. Si la diferencia es semántica (cambio de columna), se requiere migration nueva.

### Scripts duplicados con divergencias

- `backend/app/services/brightdata_browser.py` entre `feat/brightdata-browser-joy` y `feat/brightdata-yt-joy` (NO inspeccionado el diff exacto en este audit, solo nombre).

---

## Plan de orden de acción recomendado

> Justificación: foundation primero, evidencia histórica antes de archivar, ramas livianas al final.

1. **Pre-merge cleanup phase-b PR #48** — revisar diff `ds03_social_comments_data_source.py` phase-b vs main (`git diff main:...phb-version`). Si la diferencia es benigna (comentarios, formato), descartar phase-b version. Si es semántica, crear migration nueva en phase-b antes de mergear.
2. **Cherry-pick `backend/eval/layer2_benchmark/` ÁRBOL desde `feat/eval-benchmark-v1` hacia `feat/phase-b-pesos-editables`** — preserva evidencia cuantitativa del paquete §5 (decisiones 2026-05-08) sin perder los datasets de calibración humana.
3. **(Opcional) Cherry-pick `agentation-provider.tsx` + `.mcp.json` diff desde `feat/agentation-widget-and-mcp-fixes`** — si phase-b no los tiene equivalentes; cerrar PR #35 después.
4. **(Opcional) Cherry-pick `backend/research/2026-04-19/PROMPT-PLAN-IA-v1.1.md`** — si v1.1 sigue activo en roadmap.
5. **Merge `feat/phase-b-pesos-editables` → main vía PR #48** (squash o merge regular según política del repo).
6. **Cerrar PRs huérfanos** — #15 (eval-benchmark-v1) y #35 (agentation) post-merge phase-b.
7. **Archivar con tags y borrar ramas** (en este orden):
   - `archive/feat-eval-benchmark-v1` ← `feat/eval-benchmark-v1` (post cherry-pick)
   - `archive/backup-pre-opcion-d-eval-v1` ← `backup/pre-opcion-d-eval-v1` (idéntica a la anterior, conserva referencia histórica)
   - `archive/feat-scrapling-v2-snapshot` ← `feat/scrapling-v2` (LOCAL — push primero opcional para preservar)
   - `archive/feat-crece-v2-full-implementation` ← `feat/crece-v2-full-implementation`
   - `archive/feat-joy-scraper-demoscopia` ← `feat/joy-scraper-demoscopia`
   - `archive/feat-scraperapi-tiktok-joy` ← `feat/scraperapi-tiktok-joy` (LOCAL — push primero)
   - `archive/feat-brightdata-browser-joy` ← `feat/brightdata-browser-joy` (LOCAL)
   - `archive/feat-brightdata-yt-joy` ← `feat/brightdata-yt-joy` (LOCAL)
   - `archive/docs-joy-gap-analysis-refresh` ← `docs/joy-gap-analysis-refresh`
   - `archive/docs-joy-seed-inventario` ← `docs/joy-seed-inventario`
   - `archive/docs-prompt-plan-ia-v1.1-prepared` ← `docs/prompt-plan-ia-v1.1-prepared`

> **PRINCIPIO RECTOR**: ninguna rama se borra antes de tag. Tag = commit referenciable que no caduca. Después del tag, `git branch -D` o `git push origin :branch` son seguros.

> **Foundation vs cleanup**: phase-b es la foundation. Debe mergearse PRIMERO. Todas las demás se evalúan en relación a si fueron absorbidas por phase-b o si son reliquias forenses.

---

## Limitaciones del inventario

- **No se inspeccionó el contenido binario** de XLS/PNG/PDF — solo se contaron como archivos nuevos.
- **No se ejecutaron tests** — el campo "Estado de tests: depende" en `phase-b` significa que no se verificó si los 4 archivos de tests pasan vs main HEAD.
- **No se hizo diff content-level** entre las dos versiones de `ds03_social_comments_data_source.py` (main hash `06d21ab9` vs phase-b hash `357eb137`). El diff cabal queda como prerrequisito antes del merge.
- **No se verificó que `feat/agentation-widget-and-mcp-fixes` tenga su MCP fix también en phase-b** — sólo se inspeccionó nombre de archivo `.mcp.json` modificado, no el diff.
- **Las 4 ramas LOCAL-ONLY** son frágiles: si el repo se clona desde origin se pierden. Riesgo recomendado: push a `origin/<rama>` antes de archive si CEO quiere preservar.
- **No se contrastaron** los tests de phase-b contra el árbol vivo (no se sabe si compilan o pasan).
- **El audit es estático**. El repo puede haber tenido más actividad intermedia entre el momento de fetch de origin y este snapshot.
- **Commit `0681153`** está físicamente en 3 ramas (`backup/pre-opcion-d-eval-v1`, `feat/eval-benchmark-v1`, `feat/scrapling-v2`) **pero no en `feat/phase-b-pesos-editables`** ni en main. Solo los archivos `encuestas_*.py` migraron a phase-b vía un commit posterior independiente (`dccd7aa`).
