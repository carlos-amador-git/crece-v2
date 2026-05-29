# Audit Estático de Calidad de Código — CRECE v2

**Fecha:** 2026-04-25
**Alcance:** `backend/app` (FastAPI / Python 3.12) y `frontend/src` (Next.js 14 / TypeScript)
**Modo:** Análisis estático puro. NO se ejecutó pytest ni jest (backend en uso).
**Herramientas:** ruff (backend), tsc (frontend), npm outdated/audit, pip list --outdated, grep estático.

---

## Resumen Ejecutivo

| Dimensión | Score 0–100 | Estado |
|---|---:|---|
| 1. Tests existentes | **62** | Cobertura backend razonable (293 tests / 29 archivos) · Frontend SIN tests unitarios |
| 2. Deuda técnica | **84** | Solo 6 marcadores reales (TODO/BLOCKER) en >200 archivos · Limpio |
| 3. Complejidad | **58** | 15+ funciones >80 líneas concentradas en 5 archivos · Refactor necesario |
| 4. Linting estático | **55** | 934 violaciones ruff (290 auto-fixables) · TSC clean (0 errores) · ESLint NO configurado |
| 5. Dependencias | **38** | 6 vulns npm (1 crítica `protobufjs`, 1 crítica `next`<14.2.25) · Next 14→16 disponible · 19 majors Python pendientes |
| **GLOBAL** | **59** | Funcional pero con deuda de seguridad y refactor en frontes específicos |

---

## 1. Tests Existentes (Score 62/100)

### Inventario backend (`backend/tests/`)

| Métrica | Valor |
|---|---:|
| Archivos `test_*.py` | 29 |
| Funciones `def test_` | 293 |
| Módulos `backend/app/*.py` | 203 |
| Ratio tests/módulos | ~1.4 tests/módulo (saludable) |

### Cobertura por subdirectorio (presencia de imports)

| Subdir backend | Archivos | Tests que lo importan | Cobertura aparente |
|---|---:|---:|---|
| `models` | 35 | 19 | Alta |
| `core` | 8 | 13 | Muy alta |
| `services` | **62** | **8** | **BAJA** (gap crítico) |
| `api/v1/endpoints` | 48 | 4 | BAJA |
| `schemas` | 21 | 2 | Baja |
| `nlp` | 7 | 2 | Media |
| `scrapers` | 12 | 1 | Muy baja |
| `workers` | 4 | 1 | Muy baja |

### Frontend

| Métrica | Valor |
|---|---:|
| Archivos `*.test.{ts,tsx}` / `*.spec.{ts,tsx}` | **0** |
| Tests E2E configurados | Sí (`test:e2e` script + Playwright) |
| Tests unitarios componentes | **AUSENTES** |

### Hallazgos clave
- Tests E2E backend cubren onboarding, alertas, content_factory, CRM, webhooks (bueno)
- `services/` (62 archivos, lógica de negocio crítica) tiene solo 8 archivos de test que lo referencian — gap principal
- Frontend dependiente exclusivamente de Playwright E2E; sin Vitest/Jest para componentes — riesgo si componentes complejos (`kanban-board`, `plan-tareas-list`) regresan
- Dos archivos `test_endpoints.py` y dos `test_services.py` (probablemente en subdirectorios distintos) — verificar duplicación

---

## 2. Deuda Técnica (Score 84/100)

### Conteo de marcadores en código fuente (excluye `__pycache__`)

| Marcador | Backend + Frontend |
|---|---:|
| TODO (real, no enum) | 6 |
| FIXME | 0 |
| HACK | 0 |
| XXX | 1 |
| BLOCKER | 1 (real) |

### Top 6 hallazgos reales (no falsos positivos por enum `EstadoTarea.TODO`)

| # | Archivo:Línea | Tipo | Categoría |
|---|---|---|---|
| 1 | `backend/app/services/location_inference.py:106` | BLOCKER | feature pendiente — modelos spaCy `es_core_news_*` no instalados en Docker |
| 2 | `backend/app/api/v1/endpoints/auth.py:114` | TODO | feature pendiente — falta dispatch de password reset por Celery |
| 3 | `backend/app/services/diagnostico/benchmark_service.py:54` | TODO(S5) | refactor — eliminar workaround cuando Onboarding Wizard declare competidores |
| 4 | `backend/app/services/onboarding/serp_service.py:123` | TODO | feature pendiente — fallback Brightdata sin token |
| 5 | `frontend/src/app/dashboard/settings/analisis-politico/page.tsx:92` | TODO | bug menor — número de validaciones hardcoded en lugar de venir del API |
| 6 | `frontend/src/app/dashboard/dirigentes/page.tsx:46` | TODO | refactor — partido/estado options idealmente vendrían de endpoint dedicado |

### Hallazgos clave
- Deuda muy contenida — ratio TODO/LOC excelente
- Único BLOCKER explícito (spaCy en Docker) ya documentado en código + `.context/BLOCKERS.md`
- No hay HACKs ni FIXMEs ocultos — disciplina alta del equipo

---

## 3. Complejidad (Score 58/100)

### Top 5 funciones más largas (>80 LOC, heurística)

| # | Archivo:Línea | Función | LOC aprox |
|---|---|---|---:|
| 1 | `services/plan_generator.py:1478` | `_build_prompt(tipo, context, extra)` | ~170 |
| 2 | `services/canvassing.py:2455` | `optimize_route_postgis(...)` | ~159 |
| 3 | `services/news_ingest.py:3709` | `search_similar_posts(...)` | ~136 |
| 4 | `services/campaign_manager.py:3148` | `compute_divergencia(...)` | ~134 |
| 5 | `services/canvassing.py:2278` | `optimize_route(...)` | ~131 |

### Top 5 archivos más grandes (services + endpoints)

| # | Archivo | LOC |
|---|---|---:|
| 1 | `api/v1/endpoints/dirigentes.py` | 975 |
| 2 | `services/content_factory.py` | 648 |
| 3 | `services/plan_ia/llm_pipeline.py` | 592 |
| 4 | `api/v1/endpoints/canvassing.py` | 552 |
| 5 | `services/canvassing.py` | 551 |

### Hallazgos clave
- `_build_prompt` (170 líneas) en plan_generator.py es **god-function** clara — split por `tipo` plan recomendado
- `canvassing.py` y `participacion.py` son hot-spots con múltiples funciones >80 LOC — candidatos a partición por sub-modulos
- `dirigentes.py` (975 LOC en un solo endpoint module) excede umbral típico de 500 LOC — partir por concern (CRUD, métricas, perfiles)
- Nota metodológica: la heurística usa `def`-to-`def` sobre archivos concatenados; los conteos son aproximados pero los nombres de función y archivo son confiables.

---

## 4. Linting Estático (Score 55/100)

### Backend (ruff)

| Métrica | Valor |
|---|---:|
| Total violaciones | **934** |
| Auto-fixables (`--fix`) | 290 (31%) |
| Reglas distintas | 47 |

### Top 10 reglas violadas

| Code | Count | Regla | Auto-fix |
|---|---:|---|:---:|
| E501 | 506 | line-too-long | No |
| UP007 | 75 | non-pep604-annotation-union (`Optional[X]` → `X \| None`) | Sí |
| F401 | 73 | unused-import | Sí (parcial) |
| I001 | 60 | unsorted-imports | Sí |
| RUF002 | 35 | ambiguous-unicode-character-docstring | No |
| UP035 | 25 | deprecated-import | Sí |
| F541 | 16 | f-string-missing-placeholders | Sí |
| RUF100 | 14 | unused-noqa | Sí |
| B905 | 11 | zip-without-explicit-strict | No |
| E741 | 11 | ambiguous-variable-name (`l`, `I`, `O`) | No |

### Frontend

| Check | Resultado |
|---|---|
| `npm run type-check` (tsc --noEmit) | **0 errores** (PASA) |
| ESLint | **NO CONFIGURADO** — `next lint` interactivo solicita setup inicial |

### Hallazgos clave
- 506 violaciones `line-too-long` (E501) sugieren ausencia de pre-commit con autoformat (Black/ruff format)
- 73 imports no usados (F401) + 60 imports desordenados (I001) — `ruff check --fix --select I,F401` resolvería 133 issues en 1 comando
- 290 issues son auto-fix safe — el equipo puede ganar ~31% del backlog en una sesión
- TSC limpio en frontend = excelente · pero **ausencia de ESLint es gap importante** (sin reglas de hooks, accessibility, react-best-practices)

---

## 5. Dependencias Outdated/Vulnerables (Score 38/100)

### Backend (Python — `pip list --outdated`)

| Métrica | Valor |
|---|---:|
| Paquetes outdated | 64 |
| Major-version jumps | 19 |
| `pip-audit` ejecutado | No (no instalado en venv) — gap a cubrir |

### Top jumps mayor backend (riesgo breaking)

| Paquete | Actual | Latest | Riesgo |
|---|---|---|---|
| cryptography | 46.0.6 | 47.0.0 | Seguridad — actualizar prioritario |
| anthropic | 0.89.0 | 0.97.0 | API Claude — verificar compatibilidad LLM pipeline |
| fastapi | 0.135.3 | 0.136.1 | Patch menor — seguro |
| huggingface_hub | 1.9.0 | 1.12.0 | NLP pipeline — testear |
| moviepy | 1.0.3 | 2.2.1 | Major (si se usa) |
| googletrans | 3.1.0a0 | 4.0.2 | Si se usa, breaking |

### Frontend (Node — `npm outdated` + `npm audit`)

| Métrica | Valor |
|---|---:|
| Paquetes outdated | 16 |
| Major-version jumps | 12 |
| Vulnerabilidades npm audit | **6 (3 moderate, 1 high, 2 critical)** |
| Total deps prod | 361 |

### Vulnerabilidades críticas y altas (resumen)

| Paquete | Severidad | Issue | Fix |
|---|---|---|---|
| `next` 14.2.21 | **CRITICAL** | Authorization Bypass in Middleware (GHSA-f82v-jwr5-mffw, CVSS 9.1) + 13 advisories más (DoS, SSRF, cache poisoning) | Update a >=14.2.34 (mínimo) o 16.x |
| `protobufjs` | **CRITICAL** | Arbitrary code execution (CVSS 9.8, GHSA-xq3m-2v4x-88gg) | Update transitive a >=7.5.5 |
| `xlsx` | HIGH | Prototype Pollution + ReDoS (CVSS 7.8) | Mover a alternativa o `>=0.20.2` (npm registry no tiene fix; considerar `exceljs`) |
| `dompurify` | MODERATE | XSS via FORBID_TAGS bypass + 3 más | Update a >=3.4.0 |
| `postcss` | MODERATE | XSS unescaped `</style>` | Update a >=8.5.10 |
| `protocol-buffers-schema` | MODERATE | Prototype pollution | Update transitive a >=3.6.1 |

### Hallazgos clave
- **`next` 14.2.21 expone Authorization Bypass crítico (CVSS 9.1)** — mitigar inmediatamente con upgrade a 14.2.34+ (preserva mayor) o saltar a 16.x con plan de migración
- `xlsx` (SheetJS) sin fix oficial en npm — considerar reemplazo por `exceljs`
- Backend sin auditoría de vulnerabilidades automatizada — instalar `pip-audit` o `safety` en CI
- Major jumps acumulados sugieren ausencia de Renovate/Dependabot

---

## Top 5 Acciones Recomendadas (priorizadas)

| # | Acción | Esfuerzo | Impacto |
|---|---|---|---|
| **1** | **Upgrade `next` a >=14.2.34** (mínimo) para cerrar Authorization Bypass crítico (CVSS 9.1) + 13 advisories de DoS/SSRF | 2–4 h | CRÍTICO seguridad |
| **2** | **Instalar `pip-audit` y configurar Dependabot/Renovate** en CI para tener trazabilidad de vulns; remover `xlsx` (sin fix) y migrar a `exceljs` | 1 día | Alto seguridad |
| **3** | **Setup ESLint en frontend** (`next lint` con preset Strict) + correr `ruff check --fix` para resolver los 290 auto-fixables backend | 4 h | Alto calidad |
| **4** | **Cubrir `services/` con tests unitarios** — solo 8 de 62 archivos están referenciados en tests; priorizar `plan_generator`, `sentiment_service`, `canvassing` (hot-spots de complejidad) | 3–5 días | Alto regresión |
| **5** | **Refactor de god-functions** en `plan_generator._build_prompt` (170 LOC), `canvassing.optimize_route_postgis` (159 LOC) y partir `endpoints/dirigentes.py` (975 LOC) por concern | 2–3 días | Medio mantenibilidad |

---

## Notas metodológicas

- Ruff ejecutado con `.venv/bin/ruff check . --statistics --output-format=json` desde `backend/`
- TSC ejecutado con `npm run type-check` (`tsc --noEmit`)
- ESLint NO se pudo ejecutar — `next lint` requiere setup interactivo no completado
- `pip-audit` no instalado en venv — vulnerabilidades backend NO verificadas (gap)
- Heurística de funciones >80 LOC usa `awk` sobre archivos concatenados; los nombres y archivos son confiables, los conteos exactos requieren AST tools (radon, lizard)
- Tests NO ejecutados conforme a la regla del CEO (backend en uso)

