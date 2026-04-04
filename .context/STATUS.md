# CRECE v2.0 — Status

## Estado: FASE 1 + FASE 2 COMPLETAS
## Fecha: 2026-04-03

## Lo que está hecho

### Backend (30 tablas, 20 endpoints, 10 servicios)
- Fase 1: Diagnóstico Digital, Monitoreo Social (5 scrapers), Benchmarking, Planes IA, Ciudadanos, Eventos, Electoral
- Fase 2: Voter Scoring (ML + fallback), Content Factory (Claude API SSE), Blindaje Legal (INE SIF), Campañas WhatsApp, Smart Canvassing (PostGIS), Participación Ciudadana
- Infraestructura: Multi-tenant RLS, Modo Veda, Vector Tiles, NLP multi-modelo

### Frontend (16 páginas)
- 7 páginas Fase 1: dashboard, dirigentes, social, electoral, benchmark, planes, dirigente detail
- 6 páginas Fase 2: scoring, contenido, compliance, campanas, canvassing, participacion
- Design tokens MD: #1e3a5f primary, #d4a853 accent, Instrument Sans + DM Sans
- Login page, sidebar con Fase 2

### Mobile (React Native Expo)
- 4 screens: Login, Encuestas, Rutas, Perfil
- GPS capture, camera ready, SecureStore auth

### Integrations
- n8n-nodes-crece: 5 nodos custom (Segmentar, Sentimiento, Contenido, Canvassing, VoterScore)
- Chatwoot-MX: webhook interfaces ready (campanas + participacion)

### Infrastructure
- Docker: Dockerfiles (backend multi-stage + frontend + worker), docker-compose.prod.yml, nginx.conf
- Alembic: 3 migraciones (initial + RLS + fase 2)
- Tests: 69/71 passing

## Para producción
1. `npm install` en mobile/ + `npx expo start`
2. Configure .env con credenciales reales (Claude API key, WABA, etc.)
3. `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`
4. Deploy a Coolify en Hetzner
