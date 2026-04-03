# CRECE v2.0 — Plataforma de Inteligencia Electoral y Social

## Qué es
Plataforma de inteligencia política para Movimiento Ciudadano CDMX. Reemplaza sistema Oracle APEX anterior.
Cliente: ConsultoríaMD (relación de 4+ años con MC).

## Stack
- **Backend**: FastAPI (Python 3.12+), SQLAlchemy 2.0 async, PostgreSQL 16 + PostGIS 3.4
- **Frontend**: Next.js 14+ (App Router), TypeScript, Tailwind CSS, shadcn/ui, MapLibre GL JS, Recharts
- **Workers**: Celery + Redis (scrapers, NLP, IA)
- **Storage**: MinIO (S3-compatible)
- **Deploy**: Docker Compose → Coolify sobre VPS

## Estructura
```
crece-v2/
├── backend/           # FastAPI app
│   ├── app/
│   │   ├── api/v1/    # Endpoints REST
│   │   ├── core/      # Config, auth, DB
│   │   ├── models/    # SQLAlchemy (user, dirigente, social, electoral, benchmark, plan_ia)
│   │   ├── schemas/   # Pydantic v2
│   │   ├── services/  # Lógica de negocio (diagnostico, sentiment, plan_generator)
│   │   ├── scrapers/  # Scrapers por plataforma (twitter, ig, fb, tiktok, yt)
│   │   ├── nlp/       # pysentimiento + spaCy
│   │   └── workers/   # Celery tasks
│   ├── migrations/    # Alembic
│   ├── scripts/       # seed.py
│   └── tests/
├── frontend/          # Next.js dashboard
│   └── src/
│       ├── app/       # App Router pages
│       ├── components/ # UI components
│       └── lib/       # API client, hooks, utils
├── docker/            # Nginx, Postgres init, Coolify config
├── docker-compose.yml
├── docker-compose.prod.yml
└── Makefile
```

## Comandos
```bash
make dev          # Levantar entorno desarrollo
make build        # Build containers
make migrate      # Alembic upgrade head
make seed         # Poblar datos iniciales
make test         # Pytest
make logs         # Ver logs
make down         # Detener todo
make reset-db     # Reset completo
```

## Módulos Fase 1
1. **Diagnóstico Digital**: Índice de Penetración Digital (IPD) 0-10 por dirigente
2. **Monitoreo Social**: Scrapers + NLP (pysentimiento, spaCy) + alertas de crisis
3. **Benchmarking**: Comparación vs competidores y MC nacional
4. **Planes IA**: Generación con Claude API (streaming SSE) + Ollama local

## Módulos Fase 2 (futuro)
- WhatsApp Campaign Manager
- Smart Canvassing (rutas optimizadas)
- Content Factory con IA
- CRM Político + Voter Scoring
- Participación Ciudadana (Decidim)
- Blindaje Legal

## Reglas importantes
- Coordenadas México: lat 14.5-32.7, lon -118.4 a -86.7. SRID 4326.
- NUNCA inventar datos electorales. Solo datos reales del INE.
- Sentimiento normalizado por plataforma (Twitter skews negative, Instagram positive).
- Todo contenido generado con IA debe tener campo `modelo_ia` poblado.
- Cumplimiento INE: modo veda, trazabilidad de gastos, etiquetado IA.

## Plan de referencia
`/Users/marxchavez/Downloads/Reporte_Consolidado_CRECE_v2_Final.md`

## Perfiles de prueba
- **Alejandro Piña** (IPD ~4/10): Twitter 3.1K, Instagram 2.2K, Facebook 1.8K, sin TikTok/YT
- **Rafael Solano** (IPD ~2/10): Instagram personal, LinkedIn 170, sin presencia política digital
