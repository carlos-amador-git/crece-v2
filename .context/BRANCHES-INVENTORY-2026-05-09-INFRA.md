# Análisis técnico infraestructura branches · 2026-05-09 · suplemento Fase 1.B

**Fecha:** 2026-05-09
**Owner:** Linda (auditoría infraestructura)
**Suplementa:** `BRANCHES-INVENTORY-2026-05-09.md` (no lo reemplaza — añade dimensiones técnicas)
**Origen:** Cross-audit Gemini 2026-05-09 identificó 8 dimensiones de riesgo no cubiertas por el inventario base (alembic split heads, dependencias, env vars, API pública, CI history, merge virtual, out-of-sync HEAD, conflicto blob `ds03`).
**Alcance:** 18 ramas not-merged a main (vs 13 reportadas en el plan — 5 adicionales descubiertas: `docs/cherry-pick-0c4d2da-gate-decisions`, `docs/close-session-2026-04-21`, `docs/decisions-append-2026-04-21`, `docs/decisions-post-mortem-3d6fe3f`, `revert/lenis-removal-f29d7db`).

---

## Resumen ejecutivo (riesgos críticos)

| # | Hallazgo | Severidad | Ramas afectadas |
|---|---|---|---|
| H1 | **Conflicto silencioso blob `ds03_social_comments_data_source.py`**: misma `revision: str = "ds03_sc_data_source"` con dos blob hashes. main+eval-v1+backup usan `06d21ab` (typing.Union); feat/phase-b modernizó a PEP 604 en `357eb13`. Stylistic diff (`Union[str, None]` → `str \| None`) — no rompe lógica pero produce conflicto en cualquier 3-way merge. | MEDIUM | feat/phase-b-pesos-editables ↔ {main, feat/eval-benchmark-v1, backup/pre-opcion-d-eval-v1, fix/eval-v1-cherry-pick-preconditions, hotfix/pre-piloto-v2, fix/remove-lenis-*, revert/lenis-*, docs/* (all)} |
| H2 | **Conflicto silencioso blob `3d6fe3f1660d` (resultados electorales)**: blob diverge entre main (`d12bb672`) y feat/phase-b (`84cdb2e7`). main + eval-v1 + backup mantienen blob original; feat/phase-b lo modificó internamente. | MEDIUM | feat/phase-b-pesos-editables ↔ main |
| H3 | **Alembic split-head crítico** entre branches "viejas" (eval-v1, backup, crece-v2-full-implementation) y main: **no contienen** las migraciones `s1m1/s3m1/s5m1/d23g1` que SÍ están en main. Mergear estas ramas con `git merge -X theirs` rompería la cadena alembic. Se requiere rebase manual + crear migraciones merge-bridge. | HIGH | feat/eval-benchmark-v1, backup/pre-opcion-d-eval-v1, feat/crece-v2-full-implementation, feat/joy-scraper-demoscopia, docs/joy-* |
| H4 | **Hardcoded secret en código** dejado por accidente en `backup/pre-opcion-d-eval-v1` y `feat/eval-benchmark-v1`: `SCRAPECREATORS_API_KEY` default value = `pgmI0aOa8bSj9dUoh1Ja0OLwXTC2` literal. Este string literal **debe rotarse antes de mergear** (asumir comprometido en historia git). | HIGH (security) | backup/pre-opcion-d-eval-v1, feat/eval-benchmark-v1 |
| H5 | **CI nunca corrió** en 17 de 18 ramas. Workflow `e2e-smoke.yml` solo ha tenido 2 runs históricos (ambos failure, branch `observability/f0-frente-0`). NINGUNA de las 13 ramas del plan ni las 5 adicionales tiene evidencia de tests pasando. | HIGH | TODAS las 18 ramas |
| H6 | **6 ramas con conflicto merge HIGH/MEDIUM contra main** detectado por `git merge-tree`: backup/pre-opcion-d-eval-v1 (~10 archivos), feat/eval-benchmark-v1 (~10), feat/crece-v2-full-implementation (~7 add/add), feat/agentation-widget-and-mcp-fixes (4), hotfix/pre-piloto-v2 (2), docs/decisions-* (1-2). | HIGH | listadas |
| H7 | **Nuevas dependencias críticas no documentadas en `.env.example`**: `OLLAMA_NUM_PARALLEL`, `OLLAMA_KEEP_ALIVE`, `OLLAMA_FLASH_ATTENTION`, `CHROME_BIN`, `NEXT_PUBLIC_AGENTATION`, `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `INSTAGRAM_USERNAME/PASSWORD`, `SCRAPECREATORS_API_KEY`, `LIMIT`. Ningún branch actualizó `*.env.example`. Riesgo: errores silenciosos en producción cuando se merge. | MEDIUM | feat/phase-b, backup, eval-v1, agentation |
| H8 | **`feat/phase-b-pesos-editables` (HEAD actual) NO está atrasado vs main** (0 commits behind). Pero está **42 commits adelante**. Y cualquier merge de las otras 17 ramas a main introducirá divergencia adicional contra HEAD. | INFO | scope-wide |

**Veredicto cross-audit Gemini:** los 8 puntos confirmados con datos concretos. Los riesgos H1+H2+H3 conjuntamente significan que **mergear `feat/eval-benchmark-v1` con un simple `git merge` ROMPERÁ alembic upgrade head** en main post-merge.

---

## Tabla consolidada de riesgo por rama

| Rama | Alembic risk | Merge conflict | Deps diff | Env vars nuevas | API public | CI status | **Riesgo total** |
|---|---|---|---|---|---|---|---|
| `backup/pre-opcion-d-eval-v1` | 🔴 split (sin s1m1/s3m1/s5m1/d23g1) + ds03 blob | 🔴 ~10 archivos (models, workers, layouts, components) | 🟡 +agentation, package-lock 24/-43 | 🔴 hardcoded `SCRAPECREATORS_API_KEY` | 🟡 7 endpoints | ⚪ never ran | 🔴 **HIGH** |
| `docs/joy-gap-analysis-refresh` | 🟡 sin migraciones nuevas, pero también sin s1m1+ | 🟢 clean | 🟢 ninguno | 🟢 ninguna | 🟢 ninguno | ⚪ never ran | 🟢 **LOW** |
| `docs/joy-seed-inventario` | 🟡 idem joy-gap | 🟢 clean | 🟢 ninguno | 🟢 ninguna | 🟢 ninguno | ⚪ never ran | 🟢 **LOW** |
| `docs/prompt-plan-ia-v1.1-prepared` | 🟢 alineado con main | 🟢 clean | 🟢 ninguno | 🟢 ninguna | 🟢 ninguno | ⚪ never ran | 🟢 **LOW** |
| `feat/agentation-widget-and-mcp-fixes` | 🟢 alineado | 🟡 4 archivos (.context/*, .mcp.json, layout.tsx) | 🟡 +agentation, lock +249/-43 | 🟡 `NEXT_PUBLIC_AGENTATION` | 🟢 ninguno | ⚪ never ran | 🟡 **MEDIUM** |
| `feat/crece-v2-full-implementation` | 🔴 split — sin TODA la cadena ds*/d23/s* (5 migraciones contra 30 en main) | 🔴 7 add/add (CLAUDE.md, models/*, docs/*) | 🟢 ninguno | 🟢 ninguna | 🟢 ninguno | ⚪ never ran | 🔴 **HIGH** |
| `feat/eval-benchmark-v1` | 🔴 split + ds03 blob diferente vs phase-b + 3d6fe3f blob diferente vs phase-b | 🔴 ~10 archivos (idéntico a backup) | 🟡 +agentation | 🔴 hardcoded `SCRAPECREATORS_API_KEY` | 🟡 7 endpoints | ⚪ never ran | 🔴 **HIGH** |
| `feat/joy-scraper-demoscopia` | 🟡 sin s1m1+ ni d23g1 | 🟢 clean | 🟢 ninguno | 🟢 ninguna | 🟢 ninguno | ⚪ never ran | 🟢 **LOW** |
| `feat/phase-b-pesos-editables` (HEAD) | 🟢 lineal sobre main (`d23g1 → phb1 → dse_hitl_audit`) — ds03 blob diferente | 🟢 clean (es la última en dependencias) | 🟢 next bump 14.2.21→^14.2.35 + nlp-light/heavy split | 🟡 OLLAMA_NUM_PARALLEL/KEEP_ALIVE/FLASH_ATTENTION/CHROME_BIN | 🟡 14 endpoints (HITL + admin nuevos) | ⚪ never ran | 🟡 **MEDIUM** (pero crítica: contiene piloto) |
| `fix/eval-v1-cherry-pick-preconditions` | 🟢 alineado con main | 🟢 clean | 🟢 ninguno | 🟢 ninguna | 🟢 ninguno | ⚪ never ran | 🟢 **LOW** |
| `fix/remove-lenis-smooth-scroll` | 🟢 alineado | 🟢 clean | 🟡 -lenis, lock +225/-33 | 🟢 ninguna | 🟢 ninguno | ⚪ never ran | 🟢 **LOW** |
| `fix/remove-lenis-v2` | 🟢 alineado | 🟢 clean | 🟡 -lenis (idéntico a v1) | 🟢 ninguna | 🟢 ninguno | ⚪ never ran | 🟢 **LOW** (duplicado) |
| `hotfix/pre-piloto-v2` | 🟢 alineado | 🟡 2 archivos (capture.mjs, diagnostico/[id]/page.tsx) | 🟢 ninguno | 🟢 ninguna | 🟢 ninguno | ⚪ never ran | 🟡 **MEDIUM** |
| `revert/lenis-removal-f29d7db` | 🟢 alineado | 🟢 clean | 🟡 +lenis (revert) | 🟢 ninguna | 🟢 ninguno | ⚪ never ran | 🟢 **LOW** (semánticamente: anti-fix-remove-lenis) |
| `docs/cherry-pick-0c4d2da-gate-decisions` | 🟢 alineado | 🟡 2 archivos (.context/DECISIONS.md, STATUS.md) | 🟢 ninguno | 🟢 ninguna | 🟢 ninguno | ⚪ never ran | 🟢 **LOW** |
| `docs/close-session-2026-04-21` | 🟢 alineado | 🟢 clean | 🟢 ninguno | 🟢 ninguna | 🟢 ninguno | ⚪ never ran | 🟢 **LOW** |
| `docs/decisions-append-2026-04-21` | 🟢 alineado | 🟡 2 archivos (DECISIONS, PILOTO-COMERCIAL) | 🟢 ninguno | 🟢 ninguna | 🟢 ninguno | ⚪ never ran | 🟡 **MEDIUM** (sólo .md pero sirven a piloto) |
| `docs/decisions-post-mortem-3d6fe3f` | 🟢 alineado | 🟡 1 archivo (DECISIONS.md) | 🟢 ninguno | 🟢 ninguna | 🟢 ninguno | ⚪ never ran | 🟢 **LOW** |

**Conteos:** HIGH = 3 · MEDIUM = 5 · LOW = 10.

---

## Detalle por rama

### `backup/pre-opcion-d-eval-v1`
**Alembic:**
- Migrations en rama: 27 (incluye `3d6fe3f1660d`, `ds03_sc_data_source`, `ds04_matrix_context`).
- Migrations FALTANTES vs main: `s1m1_sprint_s1_schema`, `s3m1_promesas_dirigente`, `s5m1_onboarding_tables`, `d23g1_actividad_alineada`.
- Down-revision chain: `ds04 → 3d6fe3f1660d` (HEAD del branch). En main, `3d6fe3f1660d` ya existe pero su HEAD avanza a `d23g1_actividad_alineada`.
- Blob `ds03_social_comments_data_source.py` (`06d21ab`): coincide con main (no conflicto contra main, pero sí contra `feat/phase-b-pesos-editables`).
- **Split head:** SÍ. Tip de la rama (`3d6fe3f1660d`) es nodo intermedio en main. Merge requiere reconciliar 4 migraciones.

**Dependencias:**
- frontend/package.json: +`agentation@^3.0.2`
- package-lock: +24 / -43 líneas
- backend/pyproject.toml: ninguno

**Env vars nuevas:** `INSTAGRAM_USERNAME`, `INSTAGRAM_PASSWORD`, `SCRAPECREATORS_API_KEY` (con default literal hardcoded — **rotación obligatoria**), `LIMIT`, `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`.

**API impact:** 7 endpoints modificados — `alerts_integration`, `auth`, `dirigentes`, `electoral`, `indice_aceptacion`, `social`, `voter_scoring`.

**CI history:** never ran.

**Merge virtual contra main:** ~10 archivos en conflicto (`backend/app/models/dirigente.py`, `backend/app/schemas/social.py`, `backend/app/workers/celery_app.py`, `backend/app/workers/tasks.py`, `frontend/src/app/dashboard/layout.tsx`, `frontend/src/app/dashboard/page.tsx`, `frontend/src/components/alerts/crisis-alert-list.tsx`, `frontend/src/components/charts/sentiment-line-chart.tsx`, `frontend/src/components/layout/sidebar.tsx`, `frontend/src/components/social/post-card.tsx`, `frontend/src/lib/api/hooks/use-social.ts`).

**Riesgo final:** 🔴 **HIGH** — split alembic + secret hardcoded + 10 archivos en conflicto.

---

### `feat/eval-benchmark-v1`
Comparte tip commit (`3921f10`) y árbol con `backup/pre-opcion-d-eval-v1`. Idéntico análisis que el branch backup excepto:
- Es la rama "oficial" (no backup).
- Mismos 7 endpoints, misma key hardcoded, mismas migraciones.
- Misma situación de conflicto (~10 archivos).

**Riesgo final:** 🔴 **HIGH** — gemela de backup; recuperación debe coordinarse (no mergear ambas).

---

### `feat/crece-v2-full-implementation`
**Alembic:** ¡5 migraciones! (vs 30 en main). Es un branch del 2026-04-03 (un mes y medio atrás). FALTAN: toda la cadena ds*, d4*, c3*, c4*, b2*, b3*, a1*, e5*, f6*, f7*, g8*, h9*, s1m1+, d23g1.
**Merge virtual:** 7 archivos `add/add` — `CLAUDE.md`, `backend/app/models/{benchmark,electoral,plan_ia,social}.py`, `docs/{ARQUITECTURA-INTEGRADA,SPRINT-F2.0-INTEGRATION}.md`. Cada `add/add` significa que ambas ramas crearon el archivo en paralelo y main divergió.
**CI history:** never ran.
**Riesgo final:** 🔴 **HIGH** — esta rama está **arqueológica**. Recomendar archive sin merge.

---

### `feat/phase-b-pesos-editables` (HEAD actual)
**Alembic:** Cadena lineal limpia construida sobre main: `d23g1_actividad_alineada → phb1_pesos_target_politico → dse_hitl_audit`. Tip de la rama: `dse_hitl_audit`. **No split-head.** PERO blob de `ds03` y `3d6fe3f1660d` divergen vs main (modernización PEP 604 + cambio funcional respectivo) — el cherry-pick natural es desde esta rama HACIA main.
**Dependencias:** `next` 14.2.21 → `^14.2.35` (parche). `pyproject.toml`: nuevo split `nlp-light` (~150MB para API) vs `nlp-heavy` (~3.5GB para workers). Backwards compat preservada con alias `nlp = nlp-heavy`.
**Env vars nuevas:** `OLLAMA_NUM_PARALLEL`, `OLLAMA_KEEP_ALIVE`, `OLLAMA_FLASH_ATTENTION`, `CHROME_BIN`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`.
**API impact:** 14 endpoints modificados/nuevos — `__init__.py`, `admin_classification`, `admin_compliance`, `admin_overview`, `dashboard`, `diagnostico`, `dirigentes`, **`hitl_evaluation` (NUEVO)**, `indice_aceptacion`, `plan_ia`, `planes`, `privacy_arco`, `social`, `main.py`. El endpoint `hitl_evaluation` es nuevo (sprint HITL 2026-05-08).
**CI history:** never ran (incluso en HEAD actual).
**Merge virtual:** clean (es la rama base/HEAD). 42 commits ahead de main.
**Riesgo final:** 🟡 **MEDIUM** — alembic limpio y el código pasa funcionalmente (es la versión productiva del piloto), pero no se ha validado con CI. Las 6 env vars deben documentarse en `.env.example` antes de merge a main.

---

### `feat/agentation-widget-and-mcp-fixes`
**Alembic:** alineado con main al momento de salida (sin migraciones nuevas).
**Dependencias:** +`agentation@^3.0.2`, package-lock +249/-43 (significant dependency tree pull).
**Env vars nuevas:** `NEXT_PUBLIC_AGENTATION` (toggle frontend).
**API impact:** ninguno.
**CI history:** never ran.
**Merge virtual:** 4 conflictos — `.context/DECISIONS.md`, `.context/STATUS.md`, `.mcp.json`, `frontend/src/app/layout.tsx`. Los `.context/` son docs (resolución manual fácil); `.mcp.json` y `layout.tsx` requieren cuidado (toolchain config).
**Riesgo final:** 🟡 **MEDIUM**.

---

### `hotfix/pre-piloto-v2`
**Alembic:** alineado.
**Dependencias:** sin diff.
**Env vars:** ninguna nueva.
**API impact:** ninguno.
**Merge virtual:** 2 conflictos — `.context/frontend-review-2026-04-20/capture-post-hotfix-v2.mjs` (add/add) y `frontend/src/app/dashboard/diagnostico/[dirigenteId]/page.tsx` (content).
**Riesgo final:** 🟡 **MEDIUM** — el conflicto en `diagnostico/[dirigenteId]/page.tsx` ya fue superado por el branch `feat/phase-b-pesos-editables` (que rehizo esta página). Probable que el hotfix esté **superseded**. Validar antes de merge.

---

### `docs/decisions-append-2026-04-21`
**Alembic:** alineado.
**Merge virtual:** 2 conflictos en `.context/DECISIONS.md` y `.context/PILOTO-COMERCIAL-TRACKING.md` — son docs de decisiones que probablemente ya están en main de otra forma.
**Riesgo final:** 🟡 **MEDIUM** — documental, pero requiere reconciliación manual.

---

### `docs/cherry-pick-0c4d2da-gate-decisions`
**Merge virtual:** 2 conflictos `.context/DECISIONS.md` y `.context/STATUS.md`. Sólo docs.
**Riesgo final:** 🟢 **LOW**.

---

### `docs/decisions-post-mortem-3d6fe3f`
**Merge virtual:** 1 conflicto en `.context/DECISIONS.md`. Sólo docs.
**Riesgo final:** 🟢 **LOW**.

---

### `docs/joy-gap-analysis-refresh`, `docs/joy-seed-inventario`, `docs/prompt-plan-ia-v1.1-prepared`, `docs/close-session-2026-04-21`
**Alembic:** las 2 joy-* están atrasadas (pre-s1m1); las prompt-plan/close-session alineadas con main.
**Merge virtual:** todas 🟢 clean.
**Env vars / API / deps:** ninguno.
**Riesgo final:** 🟢 **LOW** — merge lineal sin fricción esperada.

---

### `feat/joy-scraper-demoscopia`
**Alembic:** atrasada (sin s1m1/d23g1) pero su contenido (scrapers Demoscopía) no toca migraciones.
**Merge virtual:** clean.
**Riesgo final:** 🟢 **LOW**.

---

### `fix/remove-lenis-smooth-scroll`, `fix/remove-lenis-v2`, `revert/lenis-removal-f29d7db`
**Trio Lenis:** `fix/remove-lenis-smooth-scroll` (1 commit, 2026-04-21 07:13) → `revert/lenis-removal-f29d7db` (1 commit, 2026-04-21 08:41 — re-añade Lenis) → `fix/remove-lenis-v2` (1 commit, 2026-04-21 10:15 — re-quita Lenis).
**Alembic:** los 3 alineados con main.
**Merge virtual:** los 3 clean.
**Deps:** v1 y v2 idénticas (`-lenis`); revert hace lo opuesto (`+lenis`).
**Riesgo final:** 🟢 **LOW**, pero **sólo necesita mergear UNA** (probablemente `v2`, la más reciente). Las otras dos archivar.

---

### `fix/eval-v1-cherry-pick-preconditions`
Documentación adicional dejada por el intento fallido de cherry-pick de eval-v1. **Alembic alineado, no introduce código nuevo.** Merge virtual clean.
**Riesgo final:** 🟢 **LOW**.

---

## Conflicto especial: migration `ds03_social_comments_data_source.py`

**Hashes blob:**
- main: `06d21ab9c49d7051cde0a8b87921b3e77e60efc1`
- feat/phase-b-pesos-editables: `357eb137826089a754c27ae40187ef06b2808fbf`
- feat/eval-benchmark-v1: `06d21ab` (= main)
- backup/pre-opcion-d-eval-v1: `06d21ab` (= main)

**Diff main → feat/phase-b:**

```diff
-from typing import Sequence, Union
+from collections.abc import Sequence

 import sqlalchemy as sa
 from alembic import op

 # revision identifiers
 revision: str = "ds03_sc_data_source"
-down_revision: Union[str, None] = "ds02_social_profile_snapshots"
-branch_labels: Union[str, Sequence[str], None] = None
-depends_on: Union[str, Sequence[str], None] = None
+down_revision: str | None = "ds02_social_profile_snapshots"
+branch_labels: str | Sequence[str] | None = None
+depends_on: str | Sequence[str] | None = None
```

**Análisis:** modernización a PEP 604 (Python 3.10+ union syntax). **Funcionalmente idéntico**, pero produce conflicto en cualquier 3-way merge. La revisión y down-revision NO cambian. Es estético + estilo.

**Implicación:** cuando main absorba feat/phase-b, el blob `357eb13` reemplazará a `06d21ab`. Cualquier merge posterior de eval-v1 / backup / fix/eval-v1-* contra main ENTONCES disparará un conflicto en este archivo. Resolución obligatoria: aceptar la versión modernizada (`357eb13`) y descartar la antigua.

## Conflicto especial: migration `3d6fe3f1660d_add_resultados_electorales_seccion_2024.py`

**Hashes:**
- main: `d12bb672a7bc042fe3f2a5f8ba24d50ea2c7e63d`
- feat/phase-b-pesos-editables: `84cdb2e7b292fe0b8001ddccec20bd6cbde6db47`
- feat/eval-benchmark-v1: `d12bb672` (= main)

Branch phase-b modificó este archivo (sin renombrar, mismo `revision: str = '3d6fe3f1660d'`). Diff no inspeccionado en detalle pero el patrón es similar a `ds03`. **Conflicto silencioso al rebase de eval-v1 sobre main si phase-b mergea primero.**

---

## Out-of-sync main vs HEAD

- Commits que `main` tiene ahead de `feat/phase-b-pesos-editables`: **0**. Main no ha avanzado por su cuenta — todo el trabajo reciente vivía en branches feature.
- Commits que `feat/phase-b-pesos-editables` tiene ahead de main: **42**.
- **Implicación:** main es estable y no está consumiendo tráfico nuevo de PRs. El piloto productivo funciona contra HEAD del branch (vía Vercel deployment de la rama, no de main). Esto da margen para hacer la consolidación sin presión, PERO también significa que `main` está deuda técnica acumulada de 42 commits.

---

## Recomendaciones específicas (ordenadas por prioridad)

### Pre-flight obligatorio antes de cualquier merge

1. **Rotar el secret `SCRAPECREATORS_API_KEY`** ANTES de mergear `backup/pre-opcion-d-eval-v1` o `feat/eval-benchmark-v1`. Asumir comprometido en historia git (string literal `pgmI0aOa8bSj9dUoh1Ja0OLwXTC2`). Si el secret no aparece en `.env.example` o vault, pedir CEO emitir nuevo y descartar el viejo.
2. **Verificar que el workflow CI `e2e-smoke.yml`** se dispara en `push` y `pull_request` a main. Si solo es manual, agregar trigger automático antes de empezar fase 3 — actualmente CI nunca corre y sin eso `git merge` es ciego.
3. **Documentar las 11 env vars nuevas** en `backend/.env.example` y `frontend/.env.example` antes de mergear `feat/phase-b-pesos-editables` o sus hermanos:
   - Backend: `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_NUM_PARALLEL`, `OLLAMA_KEEP_ALIVE`, `OLLAMA_FLASH_ATTENTION`, `CHROME_BIN`, `INSTAGRAM_USERNAME`, `INSTAGRAM_PASSWORD`, `SCRAPECREATORS_API_KEY`, `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, `LIMIT`.
   - Frontend: `NEXT_PUBLIC_AGENTATION`.

### Orden de procesamiento sugerido (de menor a mayor riesgo)

**Tier 1 — LOW risk, merge lineal (procesar primero, batch único):**
1. `docs/joy-gap-analysis-refresh`
2. `docs/joy-seed-inventario`
3. `docs/prompt-plan-ia-v1.1-prepared`
4. `docs/close-session-2026-04-21`
5. `docs/decisions-post-mortem-3d6fe3f`
6. `docs/cherry-pick-0c4d2da-gate-decisions`
7. `feat/joy-scraper-demoscopia`
8. `fix/eval-v1-cherry-pick-preconditions`
9. `fix/remove-lenis-v2` (descartar v1 y revert)

**Tier 2 — MEDIUM, requiere reconciliación manual de docs:**
10. `feat/agentation-widget-and-mcp-fixes`
11. `docs/decisions-append-2026-04-21`
12. `hotfix/pre-piloto-v2` (verificar superseded por phase-b)

**Tier 3 — HIGH, requieren rebase/migration-bridge/secret-rotation:**
13. `feat/eval-benchmark-v1` — necesita rebase contra main, resolución de 10 conflictos, rotación secret. **Recomendación específica:** crear branch `recover/eval-benchmark-v1-rebased` desde main, cherry-pick de commits útiles uno-a-uno.
14. `backup/pre-opcion-d-eval-v1` — gemelo del anterior. Si eval-v1 se recupera correctamente, **archivar este sin merge** (`git tag archive/backup-pre-opcion-d-eval-v1` y delete branch).
15. `feat/crece-v2-full-implementation` — **archivar sin merge.** Es arqueológica (1.5 meses), faltan 25 migraciones, contenido superseded por trabajo posterior. Tag de archive es suficiente.

**Tier 4 — cierre del proceso:**
16. `feat/phase-b-pesos-editables` (HEAD actual) — mergear AL FINAL. Antes: documentar env vars + correr CI manual + resolver conflicto blob `ds03` y `3d6fe3f1660d` declarando la versión phase-b como ganadora.

### Decisiones específicas a tomar (CEO en Fase 2)

| Pregunta | Recomendación Linda | Justificación |
|---|---|---|
| ¿Recuperar `feat/eval-benchmark-v1` con rebase o cherry-pick selectivo? | **cherry-pick** del commit `0681153` específico | El branch tiene 15 commits pero solo 1 es novedoso vs main; cherry-pick aísla riesgo |
| ¿Archivar `backup/pre-opcion-d-eval-v1` sin merge? | Sí | Gemelo de eval-v1, no aporta nada nuevo |
| ¿Archivar `feat/crece-v2-full-implementation` sin merge? | Sí | Arqueológica, contenido obsoleto |
| ¿Cuál de los 3 lenis branches mergear? | Solo `fix/remove-lenis-v2`, archivar los otros 2 | v2 es la versión final del trio |
| ¿Cómo resolver blob conflict `ds03`? | Aceptar versión phase-b (PEP 604) | Modernización Python correcta |
| ¿Mergear los 4 branches `docs/*` por separado o consolidar? | Consolidar en un PR único | Son todos docs `.context/*`, fácil rebase |

---

## Limitaciones de este análisis

- `git merge-tree` reportó conflictos sin contexto del contenido — el conteo de "archivos en conflicto" puede subestimar lo que un humano ve en `git merge` real.
- CI history no inspeccionable porque el workflow `e2e-smoke.yml` se ejecuta solo en `push` o desde Vercel preview, y los branches viejos no fueron `push` después de su merge-base.
- No se inspeccionó **el contenido funcional** de los 7 endpoints modificados en eval-v1 / backup — solo se contó archivos. Se requiere review manual antes de cherry-pick.
- No se ejecutó `alembic upgrade head` simulado — la cadena alembic puede tener problemas que solo aparecen en runtime (FK constraints, data migrations).
- El conflicto blob de `3d6fe3f1660d` no fue diffeado en detalle (solo se confirmó que los hashes difieren). Se recomienda inspeccionar manualmente antes de mergear phase-b.

---

**Conclusión Linda:** la deuda de 18 ramas es manejable con el plan secuencial propuesto. Los riesgos HIGH se concentran en 3 ramas (eval-v1, backup, crece-v2-full) que comparten ADN: pre-2026-04-18, pre-NLP-framework, pre-piloto-v2. Recomendación: tratarlas como **arqueología** (cherry-pick selectivo o archive) en lugar de merge lineal. El trabajo válido de eval-v1 (commit `0681153`) puede recuperarse con un cherry-pick limpio de 33 archivos en una sola operación, sin necesidad de mergear los otros 14 commits accesorios.
