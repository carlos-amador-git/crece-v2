# Audit Funcional · CRECE v2 · 2026-04-25

**Ejecutor:** Claude Code (sesión Opus 4.7) · **Branch:** `hotfix/23a-ui-puros` · **CWD:** `/Users/marxchavez/Projects/crece-v2`

**Definición de "funciona":** un usuario real obtiene valor end-to-end. NO "compila".

**Método:** queries directas a `crece-db`, llamadas REST autenticadas a `localhost:8002` con token admin, ping a `https://frontend-zeta-sepia-46.vercel.app`. Sin pytest (backend ocupado). Sin browser navigation pesada (Playwright omitido para no presionar backend que hoy genera Plan IA — D-23-G' Day 4 backfill en curso).

**Pilotos:** Piña (id=1) · Máynez (id=7) · Ballesteros (id=8). Roster completo: 8 dirigentes (3 piloto + 5 shadow).

---

## Runtime Health

| Servicio | Estado | Notas |
|---|---|---|
| `crece-db` | Up healthy | PostgreSQL :5438 |
| `crece-backend` | Up healthy 48 min | `localhost:8002`, OpenAPI 193 paths |
| `crece-celery-worker` | Up | Ejecutando backfill D-23-G' Day 4 |
| `crece-celery-beat` | Up **unhealthy** | Heartbeat fail — no impide queries pero debería investigarse |
| `crece-frontend` | Up | Local |
| Vercel prod | 200 root · 307 rutas privadas | Auth redirect correcto |

`/api/v1/health` devuelve 404 (path inexistente) pero `/docs` 200 y servicios responden. El healthcheck base no está expuesto bajo `/api/v1`.

---

## Tabla Resumen por Módulo

| Módulo | Score | Datos reales? | Bloqueante demo? | Evidencia | Notas |
|---|---|---|---|---|---|
| **1. Diagnóstico Digital (IPD)** | 6 | Parcial · solo Piña/Ballesteros | NO si demo es Piña/Ballesteros · SÍ si es Máynez | IPD: Piña 2.69, Ballesteros 3.12, Máynez 0/null. API devuelve `ipd_score=None` en bloques pero `resumen.ok=6/10` Piña, 7/10 Ballesteros, **1/10 Máynez** | API y DB **divergen** en IPD: GET `/dirigentes/1` devuelve `ipd_score=2.44`, DB tiene `2.69`. Drift no documentado. |
| **2. Monitoreo Social** | 7 | SÍ Piña+Ballesteros, NO Máynez | Sí para Máynez (cero datos) | Posts totales: Piña 320, Ballesteros 151, **Máynez 0** (5 perfiles registrados, ninguno scrapeado). `posts_7d=0` en los 3 (último scrape 2026-04-18). 1,272 social_comments, 809 sentiment_analyses, 14 alertas_crisis | Ventana 7d vacía afecta `actividad_alineada` y `total_posts_7d` en hero. CEO dependiente de scrape manual semanal. |
| **3. Benchmarking** | 4 | Parcial | Sí — datos rotos para vista comparativa | `/benchmark/ranking` devuelve 5 entries con `avg_engagement=0.0` para todas, 3 de 5 con 0 followers e IPD 0. Solo Taboada (354K) y Batres (285K) reales. `competidor_social_profiles=3` rows totales | Pool de competidores está casi vacío. Vista pública sería embarazosa. |
| **4. Planes IA** | 6 | SÍ Piña, NO Máynez/Ballesteros | Sí para 2/3 pilotos | Planes_ia: **Piña 3 (todo `aprobado=False`), Máynez 0, Ballesteros 0**. Sí están los Plan_tareas (83) y Recomendaciones (22, distribuidas Piña 18 + Ballesteros 4). Ningún `aprobado=true` global · 11 de 18 recoms Piña están `rechazada` | Demo solo funciona para Piña. Generador parece operativo (modelos: claude-sonnet-4, foda-derived-v3, data-driven-v1) pero nadie aprobó nada. |
| **5. Onboarding wizard** | 7 | SÍ los 3 marcan ready/100% | NO bloqueante | `/dirigentes/{id}/onboarding-progress` devuelve `sync_status=ready, progress_pct=100, steps len=4` para Piña/Máynez/Ballesteros. `updated_at=null` para 1 y 7 (sospechoso) | Wizard tiene 9 pasos en código (`step1-perfil`...`step9-activacion`), pero progress API solo muestra 4 steps. Inconsistencia code vs API. |
| **6. Panel Evaluación (Phase B)** | 8 | SÍ estructura · NO datos cuando 7d vacío | Demo OK con disclaimer | `/dirigentes/{id}` devuelve `actividad_alineada` + `actividad_alineada_default` + `actividad_alineada_ajustada` + `pesos_target_politico` correctamente. Página `/dashboard/evaluacion/[id]/page.tsx` existe con presets+doble KPI | Para los 3 pilotos: `score=null, total_classified=0, empty_state='no_classified'` porque la ventana son 7 días y los últimos posts son del 2026-04-18 (7d cae fuera). El panel **funcional pero hoy 25/04 vacío.** Backfill Day 4 en curso debería arreglar Ballesteros parcialmente. |

---

## Hallazgos Críticos

### H-01 · Máynez (id=7) prácticamente vacío end-to-end
- 5 social_profiles registrados, **0 social_posts**
- 0 planes_ia, 0 recomendaciones, IPD `null`/0
- `actividad_alineada.empty_state='no_classified'`
- Diagnóstico: 1/10 bloques `ok` (solo B04_benchmark, los 9 restantes `insufficient_data`)
- **Implicación demo:** si la demo del 26-30/04 incluye a Máynez, no hay nada que mostrar. Documentado en `DIAGNOSTICO-ESTADO-PILOTO-2026-04-24.md` pero el plan reciente sigue listándolo como "piloto activo".

### H-02 · IPD divergencia API vs DB
- DB Piña: `ipd_score=2.69` (2026-04-15)
- API `/dirigentes/1` devuelve `ipd_score=2.44`
- DB Máynez: 0 · API: 1.11
- Hay un cómputo on-the-fly en API que no escribe a DB. **No es bloqueante demo** pero confunde si CEO compara dashboards entre sesiones.

### H-03 · Ventana 7d en hero está siempre vacía
- Último scrape exitoso: 2026-04-18 · hoy 2026-04-25 = 7 días exactos en frontera.
- `total_posts_7d=0` para los 3 pilotos.
- `actividad_alineada` (KPI hero del nuevo D-23-G') mostrará empty_state hoy.
- Solución corta: scrape automático semanal vía Celery beat (que está unhealthy, ver runtime).

### H-04 · Benchmark ranking degradado
- 3 de 5 competidores con todos los KPIs en 0.
- Demo de la sección benchmark sería evidencia de "data gap" más que de capacidad analítica.

### H-05 · Recomendaciones IA tienen alta tasa de rechazo
- Piña: 11 rechazada / 18 totales = 61% rechazo, 0 pendientes.
- Sugiere o bien (a) los modelos están proponiendo cosas malas, o (b) el CEO/asesor está rechazando todo agresivamente sin retroalimentar el modelo.
- No bloqueante demo pero impacta narrativa "IA accionable".

### H-06 · `/api/v1/health` devuelve 404
- El path correcto parece estar fuera de `/api/v1`. Si Coolify/cloudflared espera `/api/v1/health` el healthcheck falla silencioso.

### H-07 · `crece-celery-beat` unhealthy
- Heartbeat falla. Tasks programadas (scrapes recurrentes, NLP backfills) no se están ejecutando confiablemente.
- Correlaciona con H-03 (sin scrape fresco).

### H-08 · Onboarding wizard: 9 pasos en código, 4 en API
- Frontend tiene `step1-perfil`...`step9-activacion`. Backend devuelve `steps len=4`.
- Mismatch: o el progress API resume a 4 fases lógicas, o algunos pasos no son trackeados. No verificado in-depth.

---

## Tabla Detalle Datos Reales

| Tabla | Filas | Comentario |
|---|---|---|
| `dirigentes` | 8 | 3 piloto + 5 shadow · todos con `rol_politico` poblado |
| `social_profiles` | 13 (pilotos) | Piña 5, Máynez 5 vacíos, Ballesteros 4 (sin TikTok) |
| `social_posts` | 471 (pilotos) | Piña 320, Máynez 0, Ballesteros 151 |
| `social_posts.target_politico` | 70 classified | Piña 30 (FB), Ballesteros 40 (FB+YT). Cero en otras plataformas |
| `social_comments` | 1,272 | Sustenta `/aceptacion/overview` |
| `sentiment_analyses` | 809 | Razón ~64% de posts |
| `planes_ia` | 18 (todos los dirigentes) | 3 por dirigente para 6 de 8 (Piña 3, Solano 3, Pineda 3, Nolasco 3, Jiménez 3, Cravioto 3). **Máynez 0, Ballesteros 0** |
| `plan_tareas` | 83 | Subtasks de planes |
| `recomendaciones_plan_ia` | 22 | Piña 18, Ballesteros 4. 5 aprobadas, 11 rechazadas |
| `competidores` | 5 | Pool pobre |
| `competidor_social_profiles` | 3 | Solo 2 con followers reales (Taboada, Batres) |
| `metricas_sociales` | **0** | Tabla vacía — endpoint `/metricas-sociales/` existe pero no hay datos |
| `social_profile_snapshots` | **0** | Histórico de seguidores no se está guardando · `follower_growth_30d` será 0 |
| `alertas_crisis` | 14 | Activas · usadas en dashboard |
| `alertas_compliance` | (no contado) | Veda |

---

## Bloqueantes Demo · Por Persona

### Piña (id=1) · Demo viable
- Score viable: 7/10
- Diagnóstico Tier1 6/10 ok + Tier2 8/8 ok
- 320 posts · 18 recomendaciones · 3 planes
- Hero `actividad_alineada` saldría empty si la demo se hace antes que llegue scrape fresco. **Mostrar ventana 30d** o esperar scrape.

### Ballesteros (id=8) · Demo viable con limitaciones
- Score viable: 6/10
- Diagnóstico Tier1 7/10 ok
- 151 posts · 4 recoms · **0 planes_ia** (no se ha generado nada)
- **Recomendación:** generar al menos 1 plan IA antes del demo.

### Máynez (id=7) · NO MOSTRAR
- Score viable: 1/10
- Cero posts, cero planes, cero recoms, IPD null
- **Recomendación:** retirarlo del flow demo o ejecutar onboarding+scrape full antes (mínimo 24h con scrape exitoso) o explícitamente posicionarlo como "pendiente activación".

---

## Resumen Ejecutivo

- **Demo de Piña/Ballesteros:** viable con ajustes menores (generar plan IA Ballesteros, mostrar ventana 30d en hero, evitar sección benchmark).
- **Demo de Máynez:** **no viable hoy.** Sin datos.
- **Backend:** estable. Endpoints responden. Hay drift IPD API vs DB documentar.
- **Pipeline scrape:** **frágil.** Última corrida 2026-04-18, celery-beat unhealthy. Riesgo de que próximo scrape no salga sin intervención manual.
- **NLP target_politico:** 70/471 posts piloto clasificados (15%). El backfill Day 4 corrige Ballesteros pero Piña queda con 30/320 = 9% clasificado.
- **Concuerda con `DIAGNOSTICO-ESTADO-PILOTO-2026-04-24.md`** (~80% funcional para 2 de 3 pilotos · gaps específicos no narrativa de catástrofe).

---

## No Verificado (declarado explícito)

- Navegación con browser real (Playwright headless) — backend ocupado con backfill, omitido por instrucción CEO.
- Generación end-to-end de un Plan IA streaming SSE — interfere con backfill activo.
- OAuth flows reales (Twitter/IG/FB tokens válidos) — solo se verificó `/oauth/status/{id}` existe.
- Performance bajo carga concurrente.
- Tests pytest — explícitamente prohibidos por instrucción.
- Renderizado real de `/dashboard/evaluacion/1` y comprobación de que el doble KPI hero rendea sin crash con `empty_state='no_classified'`.
