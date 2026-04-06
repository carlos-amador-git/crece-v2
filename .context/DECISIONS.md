# CRECE v2.0 — Decisiones Arquitecturales

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

### D15: Bot detection pattern-based, no ML (2026-04-05)
- Servicio basado en heurísticas, no ML (no hay dataset de bots mexicanos)
- 3 analizadores: username, profile metadata, post patterns
- Threshold: ≥0.70 = likely_bot, ≥0.40 = suspicious, <0.40 = human
- Razón: para MVP, heurísticas son suficientes y explicables. ML requiere labeled data.
