# Recordatorio · 2026-05-03 · Cleanup backend backup CRECE

**Programado:** 2026-05-01 10:21
**Para ejecutar:** 2026-05-03 (~10:37 vía cron) o cuando el CEO arranque sesión después del 2026-05-03

## Contexto del refactor

El 2026-05-01 ejecutamos refactor multi-stage de imágenes Docker CRECE para liberar disco:

- Split `[nlp]` extra en pyproject.toml → `[nlp-light]` (backend, solo spaCy) y `[nlp-heavy]` (worker, stack completo)
- BuildKit cache mounts (pip + apt) sin inflar imagen
- Eliminado `playwright install chromium` duplicado del backend (usamos system chromium vía `executable_path=$CHROME_BIN`)
- `.dockerignore` con exclusiones (.cache, .local, data/raw, *.db, etc.)

**Resultado del 2026-05-01:**
- backend: 19.4GB → 3.33GB (-83%)
- celery-worker: 16.5GB → 11.4GB (-31%)
- celery-beat: 15.8GB → 3.33GB (-79%)
- Total recuperado ese día: -34.1GB (incluyendo `backend/.venv`)

**Lo que queda pendiente:** borrar `crece-v2-backend:pre-cleanup-2026-05-01` (19.4GB) que dejamos como red de seguridad para rollback en caso de bug post-refactor.

## Validación obligatoria antes de borrar

Ejecutar y reportar al CEO los 3 checks:

### 1. Login E2E

```bash
curl -sS -X POST http://localhost:8002/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=pina@crece.mx&password=demo2026!" \
  -w "\nHTTP %{http_code}\n"
```

Esperado: HTTP 200 con `access_token` en el body.

### 2. Plan IA demo bkwyqcbxx

Verificar con CEO que:
- El demo Plan IA bkwyqcbxx para Ballesteros corrió desde el 2026-05-01 sin issues.
- O revisar `docker logs crece-celery-worker --since 48h | grep -iE "plan_ia|error|exception"` y confirmar que no hubo regresiones.

### 3. Scraper FB Playwright (executable_path)

Verificar que el patch `executable_path=$CHROME_BIN` funcionó:
- Buscar en logs Celery worker: alguna ejecución exitosa de `FacebookScraper._fetch_with_playwright` desde el 2026-05-01.
- O ejecutar manual: `docker exec crece-celery-worker python -c "import os; print('CHROME_BIN=', os.environ.get('CHROME_BIN'))"` (esperado: `/usr/bin/chromium`)

## Si los 3 checks pasan

```bash
docker rmi crece-v2-backend:pre-cleanup-2026-05-01
```

Recupera +19.4GB. Recuperación total desde el 2026-05-01: **-53.5GB**.

Disco libre proyectado: ~91GB (vs 38GB original).

## Si algo falló

- **NO borrar el backup.**
- Rollback inmediato: `docker tag crece-v2-backend:pre-cleanup-2026-05-01 crece-v2-backend:latest && docker compose up -d --force-recreate backend`
- Investigar root cause del fallo en el image nuevo.
- Reportar al CEO antes de cualquier acción.

## Archivos modificados el 2026-05-01

- `backend/pyproject.toml` — split [nlp] extras
- `backend/Dockerfile` — BuildKit cache mounts, removed playwright install duplicate
- `backend/Dockerfile.worker` — BuildKit cache mounts
- `backend/.dockerignore` — added exclusions (.cache, .local, data/raw, *.db, etc.)
- `backend/app/scrapers/facebook.py` — added `executable_path=$CHROME_BIN` to chromium.launch (líneas ~170 y ~471)

Si necesitas revisar el plan completo con cross-audit Gemini, ver el commit del refactor en `feat/phase-b-pesos-editables`.
