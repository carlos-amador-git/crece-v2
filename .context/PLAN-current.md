# CRECE v2.0 — Plan FASE 2 + Transversales

## Estado: EN EJECUCIÓN
## Fecha: 2026-04-03

---

## BATCH 5A — Core Services (3 agentes paralelos)

### S1: Voter Scoring Engine
- `backend/app/services/voter_scoring.py` — scikit-learn pipeline
  - Features: edad_rango, escolaridad, es_simpatizante_mc, nivel_interes, intencion_voto,
    programas_sociales count, encuestas count, eventos attended, proximidad_geografica
  - Output: score 0-100, probabilidad de voto MC, segmento (promotable/persuadible/opositor/indeciso)
  - Train on encuestas data, predict on all ciudadanos
- `backend/app/models/voter_score.py` — VoterScore model (ciudadano FK, score, segmento, features JSONB)
- `backend/app/api/v1/endpoints/voter_scoring.py` — POST /score/run, GET /score/{ciudadano_id}, GET /score/by-seccion/{id}
- `backend/app/schemas/voter_score.py`

### S2: Content Factory
- `backend/app/services/content_factory.py` — Claude API multi-format generation
  - Input: dirigente, topic, platform, tone
  - Output: text post, reel script, infographic copy, thread
  - Platform-aware formatting (Twitter 280 chars, Instagram caption, TikTok hook)
  - compliance: auto-tag with "Contenido generado con IA" per INE rules
- `backend/app/models/contenido.py` — ContenidoGenerado model
- `backend/app/api/v1/endpoints/contenido.py` — POST /generate, GET /history, SSE stream
- `backend/app/schemas/contenido.py`

### S3: Blindaje Legal + Compliance
- `backend/app/services/blindaje.py` — compliance engine
  - Gastos tracking: GastoElectoral model con categorías SIF del INE
  - Bot detection heuristics on social posts (engagement anomalies, follower ratios)
  - IA content labeling enforcement
  - Veda calendar integration (already have middleware, add calendar/notifications)
- `backend/app/models/gasto_electoral.py` — GastoElectoral, CategoriaGasto
- `backend/app/api/v1/endpoints/blindaje.py` — gastos CRUD, compliance report, bot analysis
- `backend/app/schemas/blindaje.py`

## BATCH 5B — Campaign & Field (3 agentes paralelos)

### S4: WhatsApp Campaign Manager (CRECE-side)
- `backend/app/models/campana.py` — Campana, CampanaSegmento, CampanaMensaje, CampanaResultado
- `backend/app/services/campaign_manager.py` — segmentation logic, template management
  - Segment ciudadanos by: seccion, intencion_voto, edad_rango, escolaridad, programas
  - Campaign states: draft → scheduled → sending → completed → analyzed
  - Integration point: POST to Chatwoot-MX webhook (not implemented yet, just the interface)
- `backend/app/api/v1/endpoints/campanas.py` — full CRUD + /send + /results
- `backend/app/schemas/campana.py`

### S5: Smart Canvassing
- `backend/app/services/canvassing.py` — route optimization with PostGIS
  - Input: seccion_id, encuestadores disponibles, ciudadanos target
  - Output: optimized routes (ST_MakeLine, nearest neighbor heuristic)
  - Assignment: RutaCanvassing model linking encuestador → ciudadanos → orden
- `backend/app/models/canvassing.py` — RutaCanvassing, PuntoRuta
- `backend/app/api/v1/endpoints/canvassing.py` — POST /optimize, GET /routes, PATCH /complete
- `backend/app/schemas/canvassing.py`

### S6: Participación Ciudadana
- `backend/app/models/solicitud.py` — SolicitudCiudadana (intake from WhatsApp/web)
  - tipo: queja, propuesta, solicitud_info, reporte_problema
  - status: recibida → en_proceso → resuelta → cerrada
  - Geolocalización del reporte
- `backend/app/services/participacion.py` — intake processing, categorization, routing
- `backend/app/api/v1/endpoints/participacion.py` — CRUD + dashboard stats
- `backend/app/schemas/solicitud.py`

## BATCH 6 — Frontend Pages for Phase 2

### F1: New dashboard pages
- /dashboard/campanas — campaign management
- /dashboard/canvassing — route map + assignments
- /dashboard/contenido — content factory
- /dashboard/scoring — voter scoring heatmap
- /dashboard/compliance — blindaje legal dashboard
- /dashboard/participacion — citizen requests

## BATCH 7 — Transversal

### T1: md-design-system integration
- Update tailwind.config.ts with MD tokens
- Replace generic fonts with Instrument Sans / DM Sans
- Apply color palette: #1e3a5f primary, #d4a853 accent, #10b981 emerald

### T2: React Native scaffold (Expo)
- `mobile/` directory with Expo app
- Screens: Login, Encuestas (field survey), Canvassing (route map), Camera (INE photo)

### T3: Production deploy config
- Dockerfile for backend (multi-stage)
- docker-compose.prod.yml refinement
- Coolify deployment config
