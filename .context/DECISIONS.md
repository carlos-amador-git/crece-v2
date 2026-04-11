# CRECE v2.0 — Decisiones Arquitecturales

## 2026-04-11

### D-SPRINT3-01: Kanban sin drag-and-drop (usa botones)
**Decisión:** Implementar el tablero Kanban con botones "→" y "Completar" en lugar de drag-and-drop real (`@dnd-kit` u otro).
**Razón:** Agregar una dep nueva de frontend atrasa el scaffold y la UI funcional con botones ya cumple el criterio S3.7 del plan (movimiento entre 3 columnas + edición inline + captura de métrica). Drag-and-drop es UX nice-to-have, no requisito.
**Revertible:** Sí. Si CEO quiere dnd real, instalar `@dnd-kit/core @dnd-kit/sortable` y envolver los `Card` de `kanban-board.tsx`. Cero cambios de backend.

### D-SPRINT3-02: estructura_json como JSONB en planes_ia
**Decisión:** Guardar el plan estructurado tanto como JSONB (`planes_ia.estructura_json`) **como** denormalizado en `plan_tareas`.
**Razón:** JSONB permite recuperar el plan tal como lo generó el LLM (auditoría) sin tocar `plan_tareas` cada vez. `plan_tareas` es para queries rápidas y edición humana. Las dos fuentes divergen a propósito cuando el humano edita.
**Trade-off:** Se pierde la garantía estricta de sincronización entre `estructura_json` y `plan_tareas`. Aceptable: `estructura_json` se trata como "original inmutable", `plan_tareas` como "estado vivo".

### D-SPRINT3-03: Retry schema violation en plan_structured (max 2 retries)
**Decisión:** Si el LLM devuelve JSON que no cumple `PlanEstructurado`, reintentar hasta 2 veces concatenando el error de validación al prompt.
**Razón:** Gemma local tiende a olvidar constraints en outputs largos. Un retry con feedback explícito suele funcionar.
**Límite duro:** 3 intentos totales. Al 4º, se lanza `RuntimeError`. Caller decide si fallback a `generate_plan()` (no estructurado) o avisar al usuario.

### D-COORD-01: Multi-sesión requiere worktrees (reforzado por CEO 2026-04-11)
**Decisión:** Multi-sesión concurrente sobre el mismo repo NO puede operar en el mismo `cwd`. Precondición dura.
**Razón:** claude-peers-mcp es filesystem-shared. Git ops de un peer mueven HEAD para todos.
**Aplicado:** Peer qmmine5b se movió a `../crece-v2-sprint1-deuda` rama `sprint1-deuda` a medio sprint. Yo me quedé en `main` sin git ops hasta su confirmación.
**Regla viva en:** `~/.claude/CLAUDE.md` líneas 329-351.

## 2026-04-03

### D1: Multi-tenant via RLS (no schema-per-tenant)
- org_id FK en tablas principales + PostgreSQL RLS policies
- `current_setting('app.current_org_id')` per-transaction
- Razón: menor complejidad operativa, funciona bien hasta ~100 organizaciones

### D2: WhatsApp via Chatwoot-MX (nunca directo)
- Campañas solo preparan payload, Chatwoot-MX hace delivery
- Webhooks bidireccionales: CRECE → Chatwoot (enviar), Chatwoot → CRECE (status)
- Razón: Chatwoot ya tiene WABA conectada y gestión de conversaciones

### D3: Voter Scoring con fallback rule-based
- scikit-learn RandomForest cuando hay datos suficientes
- Fallback determinista (50 ± bonuses/penalties) cuando no hay modelo entrenado
- Razón: el sistema debe funcionar desde día 1 sin datos de entrenamiento

### D4: Content Factory con etiqueta IA obligatoria
- Toda generación auto-appends "Contenido generado con IA"
- campo etiqueta_ia siempre True, modelo_ia siempre poblado
- Razón: compliance INE obligatorio para contenido político generado por IA

### D5: PostGIS canvassing con nearest-neighbor heuristic
- No TSP solver externo (demasiado complejo para MVP)
- Nearest-neighbor con ST_Distance + recursive CTE
- Razón: suficiente para rutas de 20-30 puntos en zonas urbanas CDMX

### D6: Docker port 5438 para desarrollo
- PostgreSQL local ocupa 5432, Docker PostGIS en 5438
- .env en backend/ (no project root) por pydantic-settings strict mode
- Razón: coexistencia con otros proyectos MD en la misma máquina

### D7: Alembic exclude PostGIS tiger tables + spatial indexes
- include_object() filtra tablas tiger/geocoder del autogenerate
- Spatial indexes (gist) excluidos porque GeoAlchemy2 los crea automáticamente
- Razón: evita DROP/CREATE innecesarios en cada autogenerate

### D8: API returns lowercase enum keys (2026-04-05)
- platform_scores, scraper tasks, filter params use lowercase ("twitter" not "TWITTER")
- Social endpoint accepts case-insensitive query params (platform, sentiment)
- Razón: REST API best practice, frontend-friendly, tests más legibles

### D9: Dashboard overview uses proxy IPD (2026-04-05)
- GET /dashboard/overview calcula avg_ipd como proxy (avg_platforms/6 * 10)
- No ejecuta diagnostico completo por dirigente (costoso en O(n*m) queries)
- Razón: suficiente para overview card, detalle real en /dirigentes/{id}/diagnostico

### D10: Docker ports CRECE dev (2026-04-05)
- PostgreSQL: 5438, Redis: 6383, MinIO: 9006/9007, Backend: 8002, Frontend: 3001
- Razón: coexistencia con 40+ contenedores de otros proyectos MD en misma máquina

### D11: Scrapers — librerías obligatorias, no código custom (2026-04-05)
- Patrón de resiliencia: Librería probada → Custom fallback → Apify
- Instagram: instaloader (requiere auth en 2026)
- Twitter: twscrape (requiere cuentas auth)
- Facebook: facebook_page_scraper (bug selenium-wire, evaluar alternativa)
- YouTube: scrapetube (FUNCIONA sin API key, validado con datos reales de Piña)
- TikTok: TikTok-Api v7.3.2 (Playwright)
- Razón: CEO detectó que se escribió código custom en vez de usar librerías del plan original

### D12: Ollama modelo gemma3:12b (2026-04-05)
- Default cambiado de gemma4:27b a gemma3:12b
- Razón: VPS Coolify tiene 16GB RAM, ~8GB disponibles. 27b no cabe. 12b sí.
- Se puede override vía .env: OLLAMA_MODEL=gemma3:27b

### D13: Ollama timeout 600s para Content Factory (2026-04-05)
- httpx timeout en content_factory.py aumentado de 300s a 600s
- Razón: con prompt completo (dirigente context + constraints), gemma3:12b CPU-only tarda ~480s
- Streaming disponible como alternativa para UX

### D14: Voter Scoring — datos sintéticos INEGI Census 2020 (2026-04-05)
- 200 ciudadanos con data_source='synthetic_census_2020'
- Distribuciones basadas en INEGI Censo 2020 CDMX (edad, género, escolaridad, alcaldía)
- NUNCA confundir con datos reales — campo data_source es obligatorio
- RF accuracy=1.0 es esperado en datos sintéticos; con datos reales será menor
- Script idempotente: backend/scripts/seed_synthetic_citizens.py

## 2026-04-11 — Sprint 1 Saneamiento

### D16: RLS enforcement vía user.dirigente_id en endpoints (2026-04-11)
- Aunque existe migración `77bbd5e5f495` con políticas RLS a nivel DB, el enforcement principal es en los endpoints FastAPI vía `current_user.dirigente_id` check
- `org_id` en users y dirigentes está en None para los 3 demo users (single-org CRECE)
- El DB-level RLS es defense-in-depth; cuando se agregue multi-tenancy real (Sprint 5 wizard), habrá que poblar org_id correctamente
- Verificado: Piña ve 191 posts, Solano 190, admin 381 (split perfecto)

### D17: KpiOverviewResponse extendido con campos políticos (2026-04-11)
- Campos legacy (total_dirigentes, avg_ipd_score, posts_monitored_24h, active_alerts, *_change) se mantienen para backward compat
- Nuevos campos: total_audiencia (sum followers), contactos_periodo (CRM en window), tema_urgente (texto de alerta más reciente o None)
- contactos_periodo y tema_urgente tienen try/except para degradar grácilmente si las tablas no existen
- Razón: evita romper consumers legacy mientras se habilitan métricas del político

### D18: Period parameter en /dashboard/overview (2026-04-11)
- Literal["today", "7d", "30d", "90d"] con default "30d"
- Calcula window_start y prev_window_start dinámicamente
- Legacy name `last_24h` se mantiene internamente pero ahora tracks el period
- Razón: activeFilter del frontend estaba roto porque nunca llegaba al backend

### D19: NLP reprocess reemplaza scores del seed (2026-04-11)
- `backend/scripts/reprocess_nlp.py --force` sobrescribe sentiment_score/sentiment_label/emotions
- Seed inicial tenía valores canned (0.7/0.5/0.1) — ahora son scores reales de pysentimiento
- Razón: filosofía "cero mockups" requiere que incluso el demo tenga análisis real
- Side effect: los tests que asumían los valores canned pueden fallar — a revisar en Sprint 2

### D20: Frontend sentiment_label es string | null (2026-04-11)
- Tipado `SocialPost.sentiment_label: string | null` (antes `sentiment: SentimentType`)
- `SentimentBadge` acepta `string | null | undefined` y normaliza con `.toLowerCase()`
- Bug previo: frontend leía `post.sentiment` que no existía en response → `else neutral++` siempre
- Razón: el backend siempre devolvió `sentiment_label` en mayúsculas; el frontend tenía un tipo inventado

---

### D15: Bot detection pattern-based, no ML (2026-04-05)
- Servicio basado en heurísticas, no ML (no hay dataset de bots mexicanos)
- 3 analizadores: username, profile metadata, post patterns
- Threshold: ≥0.70 = likely_bot, ≥0.40 = suspicious, <0.40 = human
- Razón: para MVP, heurísticas son suficientes y explicables. ML requiere labeled data.
