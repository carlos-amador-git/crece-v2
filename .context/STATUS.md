# CRECE v2.0 — Status

## Estado: FASE 1 + FASE 2 + LANDING + HARDENING COMPLETO
## Fecha: 2026-04-05

## Inventario verificado (código real + tests + visual)

### Backend (105 archivos Python)
- **25 modelos** (todos con archivos .py, 0 faltantes)
- **~90 endpoints** en 26 routers
- **11 servicios** de lógica de negocio
- **119/123 tests passing** (4 fallos pre-existentes de casing enum)
- **4 migraciones** Alembic aplicadas
- Dual AI: Claude API + Ollama/Gemma 4 local
- `email-validator` agregado a dependencias

### Frontend (80+ archivos TS/TSX)
- **16 páginas**: 1 landing + 1 login + 1 forgot-password + 13 dashboard
- **8 componentes landing**: navbar, hero, stats, features, client-results, how-it-works, cta, footer
- **15 hooks** React Query — todos conectados a API real
- Tipos alineados con API: User (full_name/role), Dirigente (full_name), SentimentBadge (case-insensitive)
- Auth: OAuth2 form-encoded login + cookie para middleware server-side
- Build: limpio, 0 errores TypeScript

### Docker (puertos corregidos para coexistencia)
- PostgreSQL: **5438**:5432 (evita conflicto con otros proyectos)
- Redis: **6383**:6379
- MinIO: **9006/9007**:9000/9001
- Backend: **8002**:8000
- Frontend: **3001**:3000
- Servicios internos usan Docker network names (db, redis, minio)

### Verificado visualmente
- Landing page: hero, stats, features, client results (Piña + Solano), how-it-works, CTA, footer
- Login: OAuth2 form + forgot-password link
- Dashboard: sidebar, KPIs, sentiment chart, top dirigentes, publicaciones, mapa electoral
- Dirigentes: tabla con Piña y Solano, social profiles, IPD scores

## Bugs arreglados en esta sesión (total 12)

1. ✅ 4 model files faltantes (benchmark, electoral, plan_ia, social)
2. ✅ CrmInteraccion `registrado_por_id` → `promotor_id`
3. ✅ ContentPieceResponse UUID→str field_validator
4. ✅ Port conflicts docker-compose (5432→5438, 6379→6383, etc.)
5. ✅ Docker internal networking (env overrides para db/redis/minio)
6. ✅ `email-validator` missing en pyproject.toml
7. ✅ Server-side auth middleware (cookie-based JWT check)
8. ✅ OAuth2 login form-encoded (frontend enviaba JSON, backend espera form)
9. ✅ User type mismatch (nombre/rol → full_name/role)
10. ✅ Dirigente type mismatch (nombre/apellido → full_name)
11. ✅ SentimentBadge case-insensitive (POSITIVE → positive)
12. ✅ Test conftest truncation strategy (evita enum conflicts entre tests)

## Known Issues (restantes)

1. ⚠️ 4 test failures pre-existentes (enum casing: lowercase vs UPPERCASE en assertions)
2. ⚠️ Docker PostGIS image linux/amd64 en ARM Mac (funcional, warning)
3. ⚠️ Scrapers usan APIs no oficiales (pueden romperse)

## Para producción

1. Carlos deploys a Coolify (163.245.208.96)
2. DNS: crece.mdconsultoria-ti.org + api-crece.mdconsultoria-ti.org
3. Generar secrets: JWT_SECRET, POSTGRES_PASSWORD, MINIO_ROOT_PASSWORD
4. CLAUDE_API_KEY para Content Factory
5. Seed: python scripts/seed.py
6. API key para n8n post-deploy
