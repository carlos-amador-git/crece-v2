# Backend CRECE v2.0 — setup de desarrollo local

Stack: **FastAPI + SQLAlchemy 2.0 async + PostgreSQL 16 + PostGIS 3.4 + pgvector + Alembic + Celery + Redis**.

## Modo Docker (recomendado — default para dev y CI)

```bash
make dev           # levanta crece-backend + crece-db (Postgres con PostGIS + pgvector) + redis + minio + celery
make migrate       # alembic upgrade head dentro del contenedor
make shell         # bash en crece-backend
```

Todas las dependencias viven en la imagen Docker. Cualquier comando alembic/pytest/pip corre dentro del contenedor. No se requiere venv local para flujos estándar.

## Modo venv local (solo si se necesita ejecutar scripts Python fuera del contenedor)

**Requisito crítico:** el paquete `pgvector>=0.3.0` está en `pyproject.toml` y es import obligatorio por `app/models/topic_trend.py`. Sin él, cualquier `alembic`, `pytest` o import del paquete `app` falla con `ModuleNotFoundError: No module named 'pgvector'`.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .                      # instala backend + todas las deps de pyproject incluyendo pgvector, asyncpg, geoalchemy2
# verificar:
python -c "from pgvector.sqlalchemy import Vector; print('ok')"
alembic current                       # debe mostrar head sin errores
```

Si `pip install -e .` falla, revisar que las libs nativas estén presentes: `brew install postgresql@16 libpq` en macOS; `apt-get install libpq-dev` en Debian/Ubuntu.

## Verificación post-setup (4 comandos que deben correr limpios)

```bash
alembic current             # debe mostrar la head actual (ej. 3d6fe3f1660d) sin errores de chain
alembic history | head -3   # cadena coherente base → head
docker exec crece-backend alembic check   # detecta drift models vs DB (warnings permitidos, fatal no)
pytest -x                   # al menos 1 test pasa (sanity)
```

## Troubleshooting conocido

| Síntoma | Causa | Fix |
|---|---|---|
| `pydantic_core._pydantic_core.ValidationError: extra_forbidden` al cargar Settings | `.env` tiene keys no declaradas en `Settings` | Verificar que `Settings.model_config` tenga `extra="ignore"` (fijado 2026-04-19) |
| `KeyError: 'ds03_sc_data_source'` al correr alembic | Chain roto por merge/rebase — migration files faltantes | Revisar que `backend/migrations/versions/` contenga todos los revisions referenciados por down_revision |
| `ModuleNotFoundError: pgvector` | venv local sin sincronizar con pyproject.toml | `pip install -e .` desde `backend/` |
| Backend container `unhealthy` | healthcheck falla por bug en Settings u otro init — NO implica que el app no sirva | `docker logs crece-backend` para diagnóstico |

## Variables de entorno

Ver `backend/.env.example`. Las env vars de integración externa (Meta/Twitter/Apify/Brightdata) son opcionales; el backend arranca con defaults para dev local.
