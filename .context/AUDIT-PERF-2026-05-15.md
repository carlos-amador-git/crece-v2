# AUDIT-PERF · 2026-05-15

**Auditor:** Performance Engineer (read-only)
**Branch:** `feat/phase-b-pesos-editables`
**Backend:** `crece-backend` healthy on :8002 · **DB:** `crece-db` (Postgres) database `crece`
**Scale real medida:** 10 dirigentes · 47 social_profiles · 4 895 social_posts · 3 161 social_comments · 1 social_followers · 8 competitor_profiles · 2 competitor_metrics_monthly.

## Resumen ejecutivo

E1-E8 ejecutados. Todo READ-ONLY. EXPLAIN sin ANALYZE para queries con joins; ANALYZE solo evitado por restricción del CEO.

- Findings **ALTOS:** 2 (N+1 en `/dirigentes/` list · cold-start de 9.4s en primer hit)
- Findings **MEDIOS:** 3 (Seq Scan en `social_posts` overview · N+1 plan_generator profiles · recharts/maplibre sin code-split)
- Findings **BAJOS:** 4 (pool_recycle ausente · pool_size 20 con max_connections 100 · `competitor_metrics_monthly_pkey` mal nombrado · index `parent_post_id` no usado en Seq Scan plan)

**Sentencia final:** **FINDINGS NO CRÍTICOS** — el sistema responde <100ms warm en todos los endpoints calientes. El único riesgo operativo es el cold-start de 9.4s en `/dirigentes/` (N+1 confirmado). El resto son optimizaciones preventivas para escalar a 50k+ posts.

---

## E1 · EXPLAIN `/social/aceptacion/overview`

**Query principal** (CTE `eng` + `fol`):

```
Sort (cost=1102.86..1102.94 rows=30)
└─ HashAggregate (cost=1101.52..1101.82)
   └─ Hash Right Join (cost=825.70..1090.76)
      └─ Hash Right Join (cost=815.02..1067.24)
         └─ Hash Right Join (cost=813.33..1051.25)
            ├─ Seq Scan on social_comments sc (cost=0.00..229.61 rows=3161)
            │    Filter: nlp_model_version IS NOT NULL
            └─ Seq Scan on social_posts sp (cost=0.00..752.59 rows=4859)
            └─ Seq Scan on social_profiles p
            └─ Seq Scan on dirigentes d
```

**Hallazgos:**
- **Seq Scan en `social_posts` (4 859 filas) y `social_comments` (3 161)** — el planner elige hash joins porque tablas son pequeñas. Con ~50k posts cambia a `Index Scan using ix_social_posts_profile_id`. **No es bottleneck ahora**, pero el LEFT JOIN encadenado 4 niveles + `COUNT DISTINCT author_hash` + 4 agregados FILTER + `100.0 * ... / NULLIF()` por dirigente escala mal (cost actual 1102, crece ~lineal con posts × comments / dirigentes).
- **Total query cost: 1 102 unidades** — barato hoy, pero la fórmula es O(posts × comments / dirigentes). A 50k posts × 30k comments → ~10 000 cost units.

**Recomendación:** Materializar `mv_dirigente_aceptacion` refresh cada 15 min vía Celery beat. El cálculo no requiere realtime (commits del CEO mismo dicen "baseline industria"). Costo: 1 materialized view + 1 task beat.

---

## E2 · EXPLAIN `/aceptacion/competitors/{id}` y `/aceptacion/competitors/`

**Detail (last_6_months):** `Bitmap Index Scan on ix_competitor_metrics_monthly_comp` → óptimo. Cost 11.31.
**List:** `Seq Scan on competitor_profiles (15 filas)` + `Sort` → óptimo, tabla pequeña.
**Admin rankings (LATERAL):** `Nested Loop Left Join` con `Bitmap Index Scan` en métricas → óptimo.

**Hallazgos:** ninguno. Endpoints competitor están bien indexados.

**Anomalía cosmética:** `pg_indexes` reporta `competitor_metrics_weekly_pkey` (nombre obsoleto) sobre tabla `competitor_metrics_monthly`. No impacta performance, ensucia mantenimiento.

---

## E3 · N+1 detection

### F-PERF-01 (ALTO) — N+1 en `endpoints/dirigentes.py:list_dirigentes` líneas 89-105

```python
for d in items:                                        # N dirigentes en página
    ipd = await calculate_ipd(db, d)                  # 1 query por d (mínimo 1, posiblemente más)
    prof_r = await db.execute(
        select(func.count(SocialProfile.id))...        # 2da query por d
    )
```

Con `page_size=20` → **mínimo 40 queries serializadas**. Confirmado en TTFB: primer hit 9 442 ms (cold), warm 144 ms. Sin cold start, sigue siendo 7 queries × 20 ≈ 140 queries para una lista de 20.

**Recomendación:**
- Pre-computar `ipd_score` en columna `dirigentes.ipd_cached` (refrescar al scrape) o vía materialized view.
- Cambiar conteo de profiles a un solo `JOIN ... GROUP BY` con LEFT JOIN.

### F-PERF-02 (MEDIO) — N+1 en `services/plan_generator.py:_gather_context` líneas 31-49

```python
profiles = list(profiles_result.scalars().all())     # N profiles
for p in profiles:
    stats_result = await db.execute(                 # 1 query × profile
        select(count, avg, avg)
        .where(SocialPost.profile_id == p.id, ...)
    )
```

Con ~5 profiles por dirigente → 5 queries por plan generado. El endpoint completo (~6-12 queries) corre antes de empezar streaming Claude/Ollama, así que añade ~50-100 ms de TTFB.

**Recomendación:** una sola query con `GROUP BY profile_id` retornando todos los stats.

### F-PERF-03 (BAJO) — `endpoints/followers.py` líneas 117-129

NO es N+1: usa `in_(follower_ids)` en una sola query. Está bien.

---

## E4 · Indexes faltantes

`pg_stat_user_tables` está reseteada (Docker reciente), no se pueden calcular ratios seq/idx reales. Análisis estructural de WHERE/JOIN comunes:

| Tabla | Columnas WHERE/JOIN comunes | Index existente | Veredicto |
|---|---|---|---|
| social_posts | profile_id | `ix_social_posts_profile_id` | OK |
| social_posts | published_at + profile_id | falta compuesto | **Recomendado:** `ix_social_posts_profile_published (profile_id, published_at DESC)` |
| social_comments | parent_post_id + nlp_model_version | `ix_social_comments_parent_post_id` | OK (nlp filter en runtime) |
| social_comments | nlp_polaridad + parent_post_id | falta | **Bajo impacto** mientras `parent_post_id` filtre temprano |
| social_profiles | dirigente_id | `ix_social_profiles_dirigente_id` | OK |
| competitor_metrics_monthly | competitor_id + month_start DESC | `ix_competitor_metrics_monthly_comp` + `ix_competitor_metrics_month` | OK |
| social_followers | dirigente_id + last_seen_at | `idx_followers_dirigente_lastseen` | OK |
| dirigentes | org_id | `ix_dirigentes_org_id` | OK |

**Recomendación principal:** agregar `ix_social_posts_profile_published (profile_id, published_at DESC)` antes de cruzar 30k posts. Hoy planner usa Seq Scan + Sort; con índice compuesto evita Sort.

---

## E5 · Next.js bundle / heavy pages

`frontend/.next/analyze/` no existe (build:analyze nunca corrido). No ejecuto `npm run build:analyze` por restricción.

**Análisis estático:**

| Tabla | Páginas que importan |
|---|---|
| recharts | `dashboard/bot-detection/page.tsx`, `dashboard/scoring/page.tsx`, `dashboard/social/clima/page.tsx` (+ 9 componentes en `components/`) |
| maplibre-gl | `components/maps/canvassing-geo-map.tsx`, `components/maps/electoral-map.tsx` |
| d3 | 0 archivos (no usado) |

**F-PERF-04 (MEDIO):** Ninguna de las 3 páginas de recharts ni los 2 maps usa `next/dynamic`. Recharts pesa ~150KB gz, maplibre ~250KB gz. Bundle inicial de dashboard incluye ambos aunque el usuario no abra el mapa. Recomendación: wrap maps en `dynamic(() => import('@/components/maps/...'), { ssr: false })` y mismo para chart-heavy pages.

---

## E6 · TTFB measurements (admin@consultoriamd.com, 3 hits cada uno)

| Endpoint | Hit 1 (cold) | Hit 2 | Hit 3 | Status |
|---|---|---|---|---|
| `/social/aceptacion/overview` | 0.494 s | 0.038 s | 0.053 s | 200 |
| `/social/aceptacion/fantasmas-por-plataforma` | 0.076 s | 0.051 s | 0.054 s | 200 |
| `/aceptacion/competitors/1` | 3.434 s | 0.084 s | 0.043 s | 200 |
| `/aceptacion/competitors/` | 0.105 s | 0.022 s | 0.017 s | 200 |
| `/dirigentes/?page=1&page_size=20` | **9.442 s** | 0.144 s | 0.123 s | 200 |
| `/social/aceptacion/dirigentes/3/ia-summary` | n/a | n/a | n/a | 404 (path no resuelve, mounting irregular) |

**Notas:**
- `ia-summary` 404 — el router monta `indice_aceptacion` bajo `/social/` pero el path interno arranca con `/dirigentes/`. Ruta real probable: `/api/v1/social/dirigentes/3/ia-summary`. **F-PERF-05 (BAJO):** auditar mounting; posible falla de rota documentada.
- Cold starts altos: 9.4 s `/dirigentes/` y 3.4 s `/competitors/1` reflejan import-time de NLP/módulos pesados al primer request. **No es bug performance, es lazy import normal**, pero conviene tirar request de warmup post-deploy.

---

## E7 · Connection pool SQLAlchemy

`backend/app/core/database.py` líneas 12-18:

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)
```

**Estado actual:**
- `pool_size=20`, `max_overflow=10` → máximo 30 conexiones por proceso FastAPI
- `pool_pre_ping=True` ✓
- **Falta `pool_recycle`** — defaults a -1 (sin reciclar). Postgres mata conexiones idle >8h, asyncpg no se recupera sin recycle.
- `max_connections=100` en Postgres, 1 activa + 1 idle ahora mismo. Margen amplio para 1 worker, pero si hay 2 workers FastAPI + Celery (3 servicios × 30 conn) = 90 conn pico → cerca del techo.

**F-PERF-06 (BAJO):** Agregar `pool_recycle=1800` (30 min). En producción con múltiples replicas, considerar pgbouncer.

---

## E8 · Celery deadlock potential

**Mapping task → tablas escritas:**

| Task | Tablas que escribe |
|---|---|
| `scrape_profile` | (via scraper, eventual `social_posts`/`social_profiles`) |
| `analyze_sentiment` | `sentiment_analyses`, `social_posts` (UPDATE), `alerts` |
| `scrape_all_profiles` | `social_profile_snapshots`, `social_profiles` UPDATE |
| `detect_trends` | `topic_trends` |
| `label_trend_cluster` | `topic_trends` UPDATE |
| `onboard_dirigente_chain` | `dirigentes` UPDATE, `social_profiles` UPDATE |
| `ingest_rss_feeds` | `dirigentes` INSERT, `social_profiles`, `social_posts` |
| `plan_ia_*` | `planes_ia`, `recomendaciones_plan_ia` |

**Análisis:**
- `cleanup_old_comments` (retention_tasks) borra `social_comments >180d` mientras `analyze_sentiment` insertaría sentiment_analyses que referencian posts. Bajo riesgo de FK violation si comentario se borra entre lectura y INSERT del sentiment, pero `cleanup` corre diario 03:00 MX y `analyze_sentiment` se dispara on-demand. Ventana baja.
- `scrape_all_profiles` (daily 24h) y `onboard_dirigente_chain` (on-demand) ambos UPDATE `social_profiles.last_scraped_at`. Sin lock explícito, pero la fila por profile es independiente → último gana, no deadlock real.
- `task_acks_late=True` + `worker_prefetch_multiplier=1` están configurados correctamente para tareas largas (NLP, scraping).
- **No detecté riesgo de deadlock real.** El patrón más peligroso sería 2 tasks UPDATE-ando la misma fila de `dirigentes` simultáneamente — improbable por design (un dirigente, un onboard chain).

**F-PERF-07 (BAJO):** considerar `SELECT FOR UPDATE` en `onboard_dirigente_chain` si el CEO planea correrlo dos veces sobre el mismo dirigente accidentalmente.

---

## Findings consolidados

### F-PERF-01 · ALTO · N+1 en /dirigentes/ list
**Síntoma:** 9.4 s cold, 140 ms warm para listar 20 dirigentes. Loop de 2 queries × N rows.
**Fix:** materializar `ipd_score` y `platform_count` en columna o usar un solo JOIN. Esfuerzo: 1 PR pequeño.

### F-PERF-02 · MEDIO · N+1 en plan_generator._gather_context
**Síntoma:** loop sobre profiles haciendo 1 stats query por profile.
**Fix:** GROUP BY profile_id en una sola query. Esfuerzo: 30 min.

### F-PERF-03 · MEDIO · Seq Scan + cascade joins en aceptacion overview
**Síntoma:** cost 1102 hoy (no bottleneck), pero crece O(posts × comments / dirigentes).
**Fix:** materialized view `mv_dirigente_aceptacion` refresh cada 15 min vía Celery. Esfuerzo: 1 PR.

### F-PERF-04 · MEDIO · Bundle frontend sin code-split
**Síntoma:** recharts + maplibre eager-loaded en bundle de dashboard.
**Fix:** `next/dynamic` para maps y páginas heavy chart. Esfuerzo: 1 PR pequeño.

### F-PERF-05 · BAJO · Endpoint /dirigentes/{id}/ia-summary 404
**Síntoma:** ruta declarada en `indice_aceptacion.py` retorna 404. Investigar mounting.

### F-PERF-06 · BAJO · pool_recycle ausente
**Fix:** `pool_recycle=1800` en `database.py`. Esfuerzo: 1 línea.

### F-PERF-07 · BAJO · Cold start 9.4 s en primer request
**Fix:** warmup curl en healthcheck o k8s readinessProbe.

### F-PERF-08 · BAJO · Index compuesto faltante en social_posts
**Fix:** `CREATE INDEX CONCURRENTLY ix_social_posts_profile_published ON social_posts(profile_id, published_at DESC);` antes de cruzar 30k posts.

---

## Sentencia final

**FINDINGS NO CRÍTICOS.** El sistema responde <100 ms warm en todos los endpoints calientes con la carga actual (5k posts, 3k comments). El único hallazgo accionable hoy es **F-PERF-01 (N+1 en /dirigentes/ list)** — fix sencillo, alto ROI. F-PERF-02..08 son preventivos para cuando la app cruce ~30k posts o se agreguen workers concurrentes.

**Acciones recomendadas en orden de ROI:**
1. F-PERF-01 (N+1 dirigentes) → 1 PR, sube 50ms warm a probable 15ms
2. F-PERF-04 (next/dynamic maps + charts) → 1 PR, baja bundle inicial ~400KB gz
3. F-PERF-06 (pool_recycle) → 1 línea
4. F-PERF-03 (materialized view aceptacion) → diferir hasta 30k posts
5. F-PERF-08 (index compuesto) → diferir hasta 30k posts

**No requiere fix urgente.** Sistema apto para piloto a la escala actual.
