# AUDIT-INFO-LOGIC · 2026-05-15

Auditor: agente paralelo · scope `audit/multi-2026-05-15` (rama)
Modo: READ-ONLY total. Sin escrituras a BD, sin cambios a archivos del backend/frontend.
Container BD: `crece-db` · Backend: `crece-backend:8002`

## Resumen ejecutivo
- Checks ejecutados: 11 (A3, A4, A5, A6, A7, A8, A9, A10, A11, C1, C2, C3, C4, C5, F1, F2, F3)
- Findings CRÍTICOS: 1
- Findings ALTOS: 4
- Findings MEDIOS: 4
- Findings BAJOS: 2
- PASS netos: 6

## CRÍTICO (escalar)

### CRIT-1 · `plan_generator` NO tiene cascada Claude → Gemini → Ollama (sólo Claude OR Ollama por flag)
- Lugar: `backend/app/services/plan_generator.py:418-449`.
- Comportamiento real: `provider = _get_provider()` lee `settings.AI_PROVIDER`. Si vale `"ollama"` → llama Ollama, si no → llama Claude. **No hay fallback automático en caso de fallo**: si Claude tira excepción, después de 2 intentos retorna la cadena literal `"Error generando plan. Intente nuevamente."` y la persiste como plan (línea 332).
- Impacto: el campo `modelo_ia` queda con el modelo intentado pero el contenido es texto de error visible al usuario; tasas reales se pierden. Documentación de CLAUDE.md de proyecto describe pipeline "Claude → Gemini → Ollama" pero el código no la implementa.
- Acción sugerida: implementar el cascade o ajustar la doc para evitar promesas que el código no cumple.

## A · Información / data integrity

### A3 · Sentiment counts consistentes overview vs ia-summary — **FAIL (ALTO)**
- Para Piña (id=1), Solano (id=2), Saymi (id=3):

| dirigente | total_comments en `/aceptacion/overview` | suma comments incluida en `/dirigentes/{id}/ia-summary` |
|---|---:|---:|
| Piña (1) | 430 | 336 (18 posts ≥ 5 comments) |
| Solano (2) | 24 | 15 (1 post ≥ 5 comments) |
| Saymi (3) | 510 | 402 (24 posts ≥ 5 comments) |

- Discrepancia: ia-summary aplica `HAVING COUNT(c.id) >= 5` por post (línea 188 de `indice_aceptacion.py`), descartando posts con < 5 comments. Overview no aplica ese gate. Resultado: total_comments mostrado al usuario es distinto entre vistas para el mismo dirigente.
- Severidad: ALTO — usuario verá "430 comments" en overview y "336 en 18 posts" en detalle, sin explicación.
- Recomendación: documentar HAVING en metodología del endpoint detalle, o exponer ambos números (corpus_total vs corpus_usado).

### A4 · IPD coherencia entre fórmula declarada y valor mostrado — **PASS con observación (MEDIO)**
- Fórmula en `app/services/diagnostico/legacy.py:54-156`:
  - 30% follower (vs benchmark por plataforma)
  - 30% engagement (vs benchmark por plataforma)
  - 40% frequency (posts 30d) → ponderada por `PLATFORM_WEIGHTS` (suma 1.00)
  - +20% coverage bonus
- IPD stored para los tres pilotos:

| dirigente | ipd_score | ipd_updated_at |
|---|---:|---|
| Piña | 2.69 | 2026-04-15 |
| Solano | 2.34 | 2026-04-15 |
| Saymi | 5.29 | 2026-04-15 |

- Issue (MED-1): **valores stale 30 días**. No hay tarea Celery beat para recálculo IPD. Si frontend muestra `ipd_score` desde BD sin recalcular, mensajes pueden estar desfasados.
- Issue (MED-2): `social_posts.engagement_rate` muestra valores con escalas mezcladas: min `-0.029`, max `35.04`, avg `0.63` sobre los últimos 30 días (767 posts). El IPD divide por `ENGAGEMENT_BENCHMARKS` que asume fracción 0-1 (ej. `0.02 = 2%`). Si alguien guardó engagement como porcentaje (35 = 35%), el componente engagement satura `min(35/0.02, 1.0) = 1.0` y queda "9-10/10" falsamente. Riesgo: IPD inflado en plataformas con percentage storage.
- Recomendación: 1) job nightly que rerun `calculate_ipd` y persiste; 2) auditar normalización de engagement_rate (fracción vs porcentaje) en ETL.

### A5 · `data_source` nunca UNKNOWN/NULL — **FAIL (ALTO)**
- `social_comments.data_source`: **306 rows NULL** sobre ~2161 totales (~14%). Otros valores OK: apify-fb-deep, apify-refresh, brightdata-fb-comments-v1, chrome-devtools-tweet-detail-v1, playwright-ig-cookies-v1, playwright-x-cookies-v1, twscrape-replies-v1, ytdlp-v1.
- `social_followers.source`: única fila tiene `source='oauth'`. PASS.
- `social_profiles.data_source`: 35 automated_scraper, 4 manual_host_ingest, 8 manual_onboarding. PASS.
- Severidad: ALTO. Viola la regla de proyecto "`data_source` NUNCA UNKNOWN/NULL". 306 comments sin trazabilidad de origen → no se puede auditar provenance.

### A6 · Coords MX en rangos válidos — **N/A**
- `dirigentes` no tiene columnas `lat/lon/lng`. Verificado vía `information_schema.columns`.
- Única tabla con columna geo en schema: `alcaldias_cdmx.geom` (PostGIS, no en scope de chequeo).
- No hay tablas `eventos` ni `puntos_canvassing` con columnas geo crudas. N/A.

### A7 · Followers totales vs suma plataforma — **PASS**
- No existe campo `dirigente.total_followers` ni cache table. La fuente única es `SUM(social_profiles.followers_count)`. PASS por construcción.

| dirigente | sum followers (5 profiles típicos) |
|---|---:|
| Piña (1) | 12,829 |
| Solano (2) | 8,730 |
| Saymi (3) | 155,953 |

### A8 · competitor_metrics_monthly refresh — **FAIL (ALTO)**
- 8 competidores activos. **6 sin métricas** (last_metrics = NULL): Santiago Taboada (Alcalde) [id 8], Omar García Harfuch [6], Clara Brugada [7], Martí Batres [3], Santiago Taboada Cortina [4 y 5 — duplicado de cuenta].
- 2 con métricas (Ivette Morán [2], Susana Harp [1]) ambos `computed_at = 2026-05-15 04:18` (hoy). PASS para esos dos.
- Observación adicional: hay dos `competitor_profiles` con `display_name='Santiago Taboada Cortina'` (ids 4 y 5) — posible duplicado de competidor.
- Severidad: ALTO. 75% de competidores activos sin métricas mensuales → benchmarking quedará vacío para esos casos.

### A9 · `modelo_ia` poblado en tablas relevantes — **PASS (con caveat sobre CRIT-1)**
| tabla | rows | con `modelo_ia` | NULL/'' |
|---|---:|---:|---:|
| contenido_piezas | 0 | 0 | 0 |
| planes_ia | 41 | 41 | 0 |
| contenidos_generados | 0 | 0 | 0 |
| ia_content_registry | 0 | 0 | 0 |

- Las 41 filas de `planes_ia` tienen `modelo_ia` poblado. Sin embargo, ver CRIT-1: cuando Claude falla, el modelo se loguea pero el contenido es literal "Error generando plan.". Convendría validar planes recientes para detectar este patrón.

### A10 · Apify MTD status — **BAJO (visibility) + finding ENV (MEDIO)**
- Cuenta `APIFY_TOKEN_INICIAL`: `$4.59 USD / $5.00 USD = 91.9% del cap MTD`. Ciclo 2026-04-24 → 2026-05-23. **Quedan ~$0.41 antes del rate limit duro**.
- Otras cuentas (`RAFA`, `ANGEL`, `SOPORTE`) presentes en `.env` no consultadas para evitar más tráfico.
- ENV finding (MEDIO): `APIFY_TOKEN` está en `.env` raíz **pero NO está inyectado al container `crece-backend`** (`docker exec crece-backend env | grep APIFY` retorna vacío). Confirma feedback `env_file root-only` en MEMORY del proyecto pero la inyección selectiva tampoco arrastra APIFY_* al contenedor. Cualquier código que use `os.environ.get('APIFY_TOKEN')` en el container resolverá vacío.

### A11 · Rate-limits scrapers nativos — **PASS parcial (MEDIO)**
| scraper | sleep / retry / backoff |
|---|---|
| twitter.py | 14 matches. `_sleep_with_jitter` (AWS-style exponential + jitter). USADO en múltiples paths (líneas 164, 201, 298, 317, 325, 401, 421, 504, 613). OK. |
| tiktok.py | 2 matches |
| instagram.py | 1 match (`time.sleep(5 * (attempt+1))`) |
| facebook.py | 0 |
| youtube.py | 0 |
| youtube_privileged.py | 0 |
| bluesky.py | 0 |
| threads.py | 0 |
| telegram.py | 0 |

- Severidad: MEDIO. Twitter es el único scraper con back-off bien diseñado. Facebook/YouTube/Threads/Telegram/Bluesky sin retry/backoff explícito → vulnerable a 429/throttle silencioso. No hay circuit breaker en ninguno.

## C · Lógica / reglas de negocio

### C1 · Veda mode — **PASS**
- Módulo: `backend/app/core/veda.py`. Middleware `VedaElectoralMiddleware` registrado en `app/main.py:141`.
- Paths bloqueados (POST/PATCH/PUT) durante veda activa:
  - `/api/v1/social` (POST, PATCH, PUT)
  - `/api/v1/encuestas` (POST)
  - `/api/v1/content/pieces` (PATCH)
  - `/api/v1/content/generate` (POST)
- Paths siempre permitidos: `/api/v1/health`, `/api/v1/auth`, todos los GET.
- Decisión documentada explícitamente: `/api/v1/planes` NO está bloqueada (análisis interno, cross-audit Gemini).
- Activación por flag `settings.VEDA_ELECTORAL_ACTIVE` + ventana opcional `VEDA_ELECTORAL_INICIO/FIN`.
- Observación (BAJO): `_VEDA_BLOCKED_PATHS` no incluye `DELETE` aunque el comentario del dispatch dice "POST/PATCH/DELETE". DELETE sobre social/encuestas/content pasaría el middleware. Si se quiere bloquearlo, falta agregarlo al set.
- Servicio adicional: `app/services/diagnostico_tier2/veda_compliance_service.py` — calcula compliance score, ortogonal al middleware.

### C2 · Plan IA cascada Claude → Gemini → Ollama — **FAIL** (ver CRIT-1)
- Switch binario por flag, no cascada. Sin Gemini. Logging del modelo elegido OK (línea 462, 505: `modelo_ia=model_name`).

### C3 · Mapeo comments → aceptación (matriz v2 53 reglas) — **PASS**
- Endpoint: `app/api/v1/endpoints/indice_aceptacion.py`. Filtra por `nlp_model_version = 'comment-framework-v2'` (líneas 204, 222, 302, etc.).
- Metodología expuesta en `metodologia` field del response (línea 347).
- La aplicación de reglas (matriz v2) ocurre upstream en el pipeline NLP (workers/tasks). El endpoint asume que el resultado vive en `social_comments.nlp_polaridad` / `nlp_model_version` y agrega.

### C4 · Cron jobs (Celery beat) — **PASS con caveat (BAJO)**
- Definidos en `backend/app/workers/celery_app.py:45-95`:

| task | frecuencia | nota |
|---|---|---|
| `scrape_all_profiles` | 24h | — |
| `detect_trends` | 1h | — |
| `ingest_rss_feeds` | 3h | — |
| `dispatch_scheduled_campaigns` | 5min | — |
| `cleanup_old_comments` | 24h | retention LFPDPPP 180d |
| `ollama_health_smoke` | 5min | — |
| `ollama_prewarm` | 4h | — |
| `plan_ia_seguimiento_diario` | crontab 03:00 UTC | — |
| `plan_ia_cierre_diario` | crontab 04:00 UTC | — |
| `plan_ia_reporte_semanal` | crontab lunes 09:00 UTC | — |

- Idempotencia: no auditada por archivo aquí. Conviene verificar a nivel de tarea (tasks.py 39K lines, no leído). Severidad: BAJO (no observado problema directo).
- **Falta tarea de recálculo IPD** (relacionado con MED-1 en A4).

### C5 · IPD weights por plataforma — **PASS**
- `PLATFORM_WEIGHTS` (legacy.py:14):

| plataforma | weight |
|---|---:|
| Twitter | 0.30 |
| Facebook | 0.25 |
| Instagram | 0.20 |
| TikTok | 0.10 |
| YouTube | 0.10 |
| Bluesky | 0.05 |

- Suma = 1.00. No hay weights=0. Cubre 6 plataformas (no las 7 mencionadas en encabezado del check — Threads y Telegram no participan en IPD).
- Coverage bonus adicional: `+coverage * 10 * 0.20`. La fórmula final es `base * 0.80 + coverage * 10 * 0.20`. PASS.

## F · Coverage ligero

### F1 · Backend coverage — **no coverage report cached**
- No existe `backend/htmlcov/`, `.coverage`, ni `coverage.xml`. Última run no persiste output. Sin pytest --cov, no se puede dar % concreto.

### F2 · E2E Playwright — **PASS con observación (MEDIO)**
Archivos en `frontend/e2e/`:

| spec | feature cubierta |
|---|---|
| `diagnostico.spec.ts` | Diagnostico Tier 1 |
| `diagnostico-tier2.spec.ts` | Diagnostico Tier 2 |
| `onboarding-wizard.spec.ts` | Onboarding |
| `plan-ia-flow.spec.ts` | Plan IA flow |
| `plan-kanban.spec.ts` | Plan Kanban |
| `pages.spec.ts` | Smoke pages |
| `visual.spec.ts` | Visual regression |

- Sin smoke E2E para: aceptacion (overview/fantasmas), watched-profiles, competitors, indice_aceptacion endpoints (los nuevos del sprint post-§9.8), benchmark, sentiment views.
- Severidad: MEDIO. Cobertura E2E centrada en flows clásicos, los flows nuevos de Fase 2 (aceptación, watched, competitors) están sin smoke.

### F3 · Migrations idempotencia (últimas 5) — **PASS**
Ultimas 5 por mtime:

| migración | downgrade() implementado |
|---|---|
| cs2_drop_competidores_legacy.py | Sí — recrea tabla `competidores` vacía |
| cp3_followers_total.py | Sí — `drop_column followers_total` |
| sc1_commenter_handle.py | Sí — drop index + drop column |
| cp2_competitor_monthly.py | Sí — RENAME constraints + indexes |
| cp1_competitor_profiles.py | Sí — drop indexes + drop tables |

- Ninguna tiene `pass` vacío. PASS.

## Sentencia final

**ESCALAR** — Findings que requieren decisión antes de pasar a fase 3:

1. **CRIT-1**: `plan_generator` documentación promete cascada que el código no implementa. Decidir si: (a) implementar cascade real con Gemini intermedio o (b) actualizar docs y CLAUDE.md para reflejar comportamiento real.
2. **A3 (ALTO)**: discrepancia overview vs ia-summary en mismo dirigente. Decidir si exponer ambos en UI o documentar HAVING.
3. **A5 (ALTO)**: 306 comments con `data_source` NULL. Backfill con valor `legacy` o `unknown_pre_audit` y enforce NOT NULL en migration.
4. **A8 (ALTO)**: 6 de 8 competidores activos sin métricas mensuales. Ejecutar scraper de competitors o desactivar perfiles huérfanos.
5. **A10 ENV (MEDIO)**: APIFY_TOKEN no inyectado al container (`.env` root-only sin sync al compose). Confirmar si scrapers Apify del backend están corriendo en blanco.
6. **A4 MED-1/MED-2**: tarea nightly recalc IPD + auditar normalización `engagement_rate`.
7. **F2 (MEDIO)**: agregar smoke E2E a flows nuevos (aceptación, watched, competitors).

Resto de checks PASS o N/A. No hay blocker absoluto para fase 3 si se documentan los findings; CRIT-1 es decisión de producto + docs, no bloquea ejecución técnica.

— FIN AUDIT —
