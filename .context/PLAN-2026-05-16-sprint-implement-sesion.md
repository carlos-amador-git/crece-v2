# PLAN · 2026-05-16 · /sprint-implement sesión (batch OAuth + infra backend)

## Origen
CEO invocó `/sprint-implement` con luz verde general. Esta sesión ejecuta subset del PLAN-2026-05-16-pendientes-consolidado.md: 5 sprints chicos que comparten dominio (OAuth + scrapers + infra backend) sin requerir decisiones adicionales del CEO.

## Decisiones / supuestos (Karpathy "Think Before Coding")

1. **Scope cerrado:** 5 sprints listados abajo. NO se expande a BLOQUE 4 UI (sesión propia), NO se expande a BLOQUE 8 watchlist (sesión propia post-coordinación Juan).
2. **Arquitectura onboarding:** mantener `dirigente_id` en URL (más RESTful · alineamiento BE → FE).
3. **PII encryption:** reusar `app.services.pii.encrypt_value` con pgcrypto (precedente `ciudadanos_legacy` D-DATA-02).
4. **HMAC state:** usar `JWT_SECRET` para firmar (no nuevo secreto · reuso existente).
5. **Dockerfile:** agregar yt-dlp + Playwright en imagen backend principal (NO image separada · simplicity first).
6. **No mocks:** todas las validaciones contra BD real, container real, HTTP real (regla CRECE).
7. **Surgical changes (Karpathy):** cero refactor adyacente · cada línea trazable al sprint.

## Sprints

### Q-1 · B-26-02 · `get_scraper(platform)` lowercase fix (5 min)
**Objetivo:** registry de scrapers acepta uppercase enum values.
**Archivos:**
- `backend/app/scrapers/base.py:97` — cambiar `scrapers.get(platform)` → `scrapers.get(platform.lower())`
- `backend/tests/scrapers/test_base.py` — unit test (uppercase + lowercase ambos OK)
**Criterio aceptación:**
- `pytest backend/tests/scrapers/test_base.py` verde
- `get_scraper("TWITTER")` retorna scraper válido
- `get_scraper("twitter")` también funciona
**Dependencias:** ninguna.

### Q-2 · B-OAUTH-YT-STATE-1 · HMAC firma state (30 min)
**Objetivo:** state OAuth firmado con `JWT_SECRET`; tampering rechazado en callback.
**Archivos:**
- `backend/app/services/oauth_state.py` (NEW si no existe) — `sign_state(payload) -> str` + `verify_state(state) -> dict`
- `backend/app/api/v1/endpoints/onboarding.py` — usar `sign_state()` en redirect, `verify_state()` en callback
- `backend/tests/test_oauth_state.py` — roundtrip + tampering rechazado
**Criterio aceptación:**
- Roundtrip sign → verify retorna payload original
- State manipulado → `verify_state` raise `ValueError`
- Callback con state inválido → HTTP 400
**Dependencias:** ninguna.

### Q-3 · B-OAUTH-YT-CRYPTO-1 · Tokens OAuth cifrados (1h)
**Objetivo:** `OAuthTokenByPlatform.token_hash` y `refresh_token_hash` guardados cifrados.
**Archivos:**
- `backend/app/services/oauth_yt_service.py` (o equivalente) — wrap inserts/reads con `encrypt_value`/`decrypt_value`
- `backend/migrations/versions/oauth_encrypt_existing.py` (NEW) — re-encrypt fila id=2 existente (1 row real)
- `backend/tests/test_oauth_crypto.py` — SELECT directo muestra `\x...`, service decrypt retorna plain
**Criterio aceptación:**
- Insertar token nuevo: BD muestra cifrado
- Leer via service: token plain válido
- Fila existente (id=2 dirigente_id=1 Benjamin) sigue funcionando post-migration
- pgcrypto disponible en container (verificar)
**Dependencias:** ninguna (pgcrypto ya usado por `ciudadanos_legacy`).

### Q-4 · B-ONBOARDING-FE-BE-MISMATCH-1 · Alinear endpoints onboarding (1.5h)
**Objetivo:** FE↔BE alineados con `{dirigente_id}` en URL.
**Archivos backend:**
- `backend/app/api/v1/endpoints/onboarding.py` — refactor 5 endpoints para aceptar `dirigente_id` como path param
- `backend/tests/test_onboarding_endpoints.py` — smoke tests por endpoint
**Archivos frontend:**
- `frontend/src/lib/api/hooks/use-onboarding.ts` (o equivalente) — verificar shapes coinciden
**Endpoints afectados:**
- `POST /onboarding/{dirigente_id}/profile`
- `POST /onboarding/{dirigente_id}/accounts-manual`
- `POST /onboarding/{dirigente_id}/confirm-accounts`
- `POST /onboarding/{dirigente_id}/competidores`
- `POST /onboarding/{dirigente_id}/promesas`
**Criterio aceptación:**
- Cada endpoint responde 200/201 con `dirigente_id` en path
- RBAC valida `dirigente_id` del path contra `user.dirigente_id` (multi-tenant)
- Smoke test E2E del wizard onboarding completo desde curl
**Dependencias:** ninguna.

### Q-5 · B-26-03 · yt-dlp + Playwright en container backend (30 min)
**Objetivo:** scrapers YT + TT funcionales en container.
**Archivos:**
- `backend/Dockerfile` — agregar `pip install yt-dlp playwright` + `playwright install --with-deps chromium`
- `docker-compose.yml` — confirmar no necesita volumen extra para browser cache
**Criterio aceptación:**
- `docker compose build backend` exitoso
- `docker exec crece-backend yt-dlp --version` muestra versión
- `docker exec crece-backend python -c "from playwright.sync_api import sync_playwright; print('OK')"` OK
- Tamaño imagen final medido (Playwright pesa ~400MB · documentar)
**Riesgo:** imagen Docker crece significativamente. Mitigación: si pasa de 2GB, considerar multi-stage build.
**Dependencias:** Q-1 a Q-4 deben pasar tests antes (no romper build).

## Orden de ejecución
1. Q-1 (item más chico · valida que el ciclo edit-test funciona)
2. Q-2 (HMAC · self-contained · sin migration)
3. Q-3 (pgcrypto · necesita migration · requiere container running)
4. Q-4 (onboarding · cambios bilaterales BE+FE)
5. Q-5 (Dockerfile · al final · rebuild image cierra sesión)

## Verificación cross-sprint
Después de cada sprint:
- `pytest backend/tests/` sub-set relevante
- Si Q-3 o Q-4 tocan endpoints expuestos: curl smoke test contra `localhost:8002`
- Cero `npm run` mid-sesión (frontend solo cambia en Q-4 verificación shapes)

## Out of scope esta sesión
- BLOQUE 4 UI sistémica (S1, Sprint A, S3, S6) — sesión propia con CEO presente
- S-8.1 endpoint Juan ingest-reactions-bulk — sesión propia post-coordinación Juan
- S-5.1 Brightdata IG followers — requiere validación credenciales IG con CEO
- BLOQUE 7 Plan IA refactor — sprint propio cuando se prenda
- BLOQUE 2 piloto operativo (named tunnel, refresh scrapers) — riesgo BD piloto

## Estimado total
~3.5h ejecución + ~30 min cross-audit Gemini + verificación = ~4h sesión.

## Mitigaciones post Gemini cross-audit (2026-05-16 07:50Z)

Gemini identificó 3 riesgos accionables. Plan actualizado:

### R-1 (Q-4 BE/FE desincronización) → retrocompat temporal
**Riesgo:** Cambiar rutas a `/{dirigente_id}/` produce 404 en pestañas activas del piloto (clientes con app cargada que no recargan).
**Mitigación:** Agregar las nuevas rutas con `{dirigente_id}` en path **manteniendo las viejas como alias** que llaman al mismo handler. Frontend migra a nuevas. Deprecar viejas después de N días con métricas verificadas (log access count en cada alias).
**Cambio en Q-4:** crear nuevos endpoints + dejar viejos como `@deprecated` con WARN log. NO eliminar viejos esta sesión.

### R-2 (Q-5 OOM build Playwright) → build local Mac Mini
**Riesgo:** Build Docker con Playwright + Chromium consume RAM/CPU significativa. Si se ejecuta en VPS Coolify, puede tirar containers running.
**Mitigación:** Build SOLO en Mac Mini local (este desarrollo). Monitorear RAM con `docker stats` durante build. Documentar tamaño imagen final. **NO push automático al VPS** — CEO decide cuándo desplegar.
**Cambio en Q-5:** agregar `docker stats` snapshot pre/durante/post build. Si imagen > 2.5GB, considerar multi-stage.

### R-3 (Q-3 migration contexto secretos) → separar schema vs datos
**Riesgo:** Alembic puede no cargar el contexto de la app (env vars, encrypt_value service) correctamente, fallando la re-encriptación de fila existente.
**Mitigación:** Alembic migration **solo agrega columna/marca** `encrypted_at` timestamp y `version` int. La re-encriptación de fila id=2 existente se hace vía script Python standalone `backend/scripts/encrypt_existing_oauth_tokens.py` ejecutado vía `docker exec` con el contexto completo de la app.
**Cambio en Q-3:**
- Migration Alembic: solo ALTER TABLE add encrypted_at/version (idempotent).
- Script Python: lee fila id=2, encrypt con `encrypt_value()`, UPDATE con encrypted_at=now().
- Test: SELECT directo muestra cifrado post-script.

## Próximo paso inmediato
Arrancar FASE 4 ejecución (Q-1 primero · es independiente · 5 min).
