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
