# Sprint 4 — Motor de Trends MVP — Diseño

**Estado:** Diseño + esqueletos. Ejecución real requiere sesión dedicada (7 días de trabajo).

## Componentes y archivos

### Modelo TopicTrend (S4.2)
Archivo: `backend/app/models/topic_trend.py` (scaffold creado, ver archivo)

Campos:
- `id`, `org_id` (FK para RLS), `alcaldia_id` (FK catálogo INEGI)
- `topic_label: str` — etiqueta humana (producida por Ollama en batch)
- `topic_embedding: Vector(384)` — pgvector para similitud
- `time_bucket: TIMESTAMPTZ` — ventana de 1h
- `post_count: int`, `sentiment_avg: float`, `growth_rate_24h: float`
- `sample_posts: JSONB` — subset top 5 posts del cluster

### Catálogo alcaldías INEGI (S4.1)
Tabla `alcaldias_cdmx` con `id`, `nombre`, `clave_inegi`, `geom` (Polygon 4326).
Seed desde shapefile oficial INEGI MGN CDMX. Script: `backend/scripts/seed_alcaldias_cdmx.py` (stub).

### Seed cuentas semilla (S4.3)
YAML: `backend/app/data/seed_accounts_cdmx.yaml` — 150-300 cuentas por alcaldía (3 pilotos: Cuauhtémoc, Benito Juárez, Miguel Hidalgo).

### Location inference (S4.4)
`backend/app/services/location_inference.py` (scaffold creado).
Flujo:
1. spaCy NER sobre `content` del post
2. Match contra catálogo de lugares MX
3. Fallback: bio de cuenta semilla
4. Retorna `alcaldia_id | None`

Precisión esperada: 60-70% (MVP).

### Worker trends_detector (S4.5)
`backend/app/workers/tasks/trends_tasks.py` (stub).
Corre cada 1h. Procesa ventana 24h. HNSW clustering con **filtro `org_id` ANTES del vector search** (S4.8 — requisito de seguridad RLS).

### Ollama batch labeling (S4.6)
Cola Celery dedicada `trends_labeling` con `concurrency=2`. No 1-a-1.

### RSS ingest (S4.7)
`backend/app/services/news_ingest.py` + worker. Fuentes:
- Presidencia MX, Gaceta CDMX, Congreso
- IECM
- El Universal, Milenio, Animal Político, Aristegui

### Endpoint `/trends/geo` (S4.9)
Query params: `alcaldia_id`, `period` (24h|7d|30d).
Response: top N trends con growth_rate, sample_posts, label humano.

### UI Card "Trending ahora en [alcaldía]" (S4.10)
Dentro de `/dashboard/social`. NO página nueva. Reusa Card, Badge, FilterSelect.

## Dependencias y orden crítico
1. S4.1 (alcaldías) → S4.4 (inference)
2. S4.8 (RLS en HNSW) **DEBE** aplicarse antes de S4.5 (worker). NO revertir orden — riesgo crítico de fuga multi-tenant.
3. S4.7 (RSS) es paralelo, puede arrancar día 3.

## Cortes de scope confirmados
- ❌ Muestreo followers (shadowban)
- ❌ Threads scraping
- 🟡 TikTok baja prioridad
