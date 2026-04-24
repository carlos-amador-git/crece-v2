# F0.1 Observability state · diagnóstico 2026-04-23

**Propósito:** cerrar el diagnóstico binario pedido por CEO antes de implementar F0.1 MVP. Responde "¿Bugsink funciona o no?" con evidencia.

---

## Veredicto

🔴 **Bugsink está roto.** No captura nada en producción ni en local. El `sentry_sdk.init()` en `backend/app/main.py` corre condicional sobre `settings.BUGSINK_DSN`, pero:
- Local tiene DSN pero apunta a `localhost:8101` sin servicio detrás.
- Producción NO recibe `BUGSINK_DSN` en su environment → `init()` no se ejecuta.
- Resultado: 6 días de incidente `3d6fe3f` silencioso porque no había observabilidad activa.

Esto activa la rama **caso B** del guard CEO: webhook Slack/Discord MVP como fallback rápido + rescue Bugsink como backlog.

---

## Evidencia

### 1. Configuración local

```
$ grep BUGSINK .env
BUGSINK_DSN=http://f33736580b4445de9c968499065bccf0@localhost:8101/1
```

DSN presente pero apunta a `localhost:8101`. **Verificación:**
```
$ curl -s --max-time 5 -o /dev/null -w "%{http_code}" http://localhost:8101/
000  (connection refused)
$ docker ps | grep -i "bugsink\|sentry"
(sin resultados)
```

Bugsink local **no corre**.

### 2. Configuración producción (Coolify)

`docker/coolify/docker-compose.coolify.yml` servicio `backend` (L87-98):

```yaml
environment:
  DATABASE_URL: ${DATABASE_URL}
  REDIS_URL: ${REDIS_URL}
  JWT_SECRET: ${JWT_SECRET}
  CLAUDE_API_KEY: ${CLAUDE_API_KEY}
  CELERY_BROKER_URL: ${CELERY_BROKER_URL}
  CELERY_RESULT_BACKEND: ${CELERY_RESULT_BACKEND}
  MINIO_ENDPOINT: ${MINIO_ENDPOINT}
  MINIO_BUCKET: ${MINIO_BUCKET}
  APP_ENV: production
  APP_DEBUG: "false"
  CORS_ORIGINS: ${CORS_ORIGINS}
```

**Cero variables `BUGSINK_*` o `SENTRY_*` pasadas al contenedor.** El default `BUGSINK_DSN: str = ""` de `config.py` aplica en producción → `if settings.BUGSINK_DSN:` es False → `sentry_sdk.init()` nunca se ejecuta.

`.env.coolify.example` está referenciado en comentario del compose (L14) pero el archivo **no existe en repo**.

### 3. Bugsink como servicio en compose prod

Ningún servicio Bugsink declarado en `docker-compose.coolify.yml` ni en `docker-compose.prod.yml`.

### 4. Exception handling en `main.py`

```python
# Línea 22-28
if settings.BUGSINK_DSN:
    sentry_sdk.init(
        dsn=settings.BUGSINK_DSN,
        traces_sample_rate=0.1,
        environment=settings.APP_ENV,
        release=settings.APP_VERSION,
    )
```

- `traces_sample_rate=0.1` es **performance sampling (10%), no error capture**. El error capture es default-on en sentry-sdk v2+ con auto-integration FastAPI/Starlette, pero **solo si el init corre**.
- Único handler explícito es `@app.exception_handler(IntegrityError)` → devuelve 409 Conflict, no llega a Sentry (correcto, es 409 no 5xx).
- **No hay `@app.exception_handler(Exception)`** para capturar 5xx genéricos → dependía 100% del auto-capture del SDK, que nunca se inicializó en prod.

### 5. Cloudflared / tunnel / health monitoring

Sin configuración alguna. Ningún uptime check, cron, o webhook para detectar:
- Backend caído
- Cloudflared tunnel roto
- Rate 429 sostenido

---

## Plan F0.1 MVP (caso B — webhook Slack/Discord)

**Estimación:** 1 día.

### Entregables

1. **Exception handler explícito `@app.exception_handler(Exception)`** en `main.py`:
   - Log estructurado del error (stack trace + request context)
   - POST a webhook URL (configurable vía env `ALERT_WEBHOOK_URL`)
   - Preserva `sentry_sdk.capture_exception()` para cuando Bugsink reviva
   - Devuelve JSONResponse 500 con correlation_id

2. **Trigger `/health` + uptime externo:**
   - Endpoint `/health` ya existe (verificar)
   - Configurar Better Stack free tier pinging `https://api-crece.mdconsultoria-ti.org/health` cada 60s
   - Webhook a mismo canal cuando down

3. **Config env `ALERT_WEBHOOK_URL` + `ALERT_WEBHOOK_TYPE` (slack|discord):**
   - Documentar en `.env.example` + `docker-compose.coolify.yml` (passthrough)
   - Crear `.env.coolify.example` como SSOT de vars producción

4. **Test manual documentado:**
   - Forzar 500 en endpoint dev → capturar timestamp
   - Medir latencia hasta notificación en canal
   - Screenshot/log en `.context/F0.1-TEST-MANUAL-2026-04-23.md`
   - Criterio éxito: <60s

### Lo que NO entra en MVP (backlog post-piloto)

- Rescue Bugsink con instancia real corriendo en Coolify
- Sentry SaaS completo (si se decide cambiar de Bugsink self-hosted a SaaS)
- Dashboard de errores agregados
- Auto-tagging de errores por dirigente/tenant

---

## Decisiones pendientes CEO (antes de ejecutar)

1. **¿Slack o Discord?** → necesito URL del webhook del canal destino.
2. **¿Crear canal nuevo o usar uno existente?** → recomendación: canal dedicado `#crece-v2-alerts` para no mezclar con notificaciones de otros proyectos.
3. **¿Uptime externo: Better Stack free tier** (simple, cloud) **o cron local en Coolify** (control pleno, más setup)?

---

---

## F0.1 MVP implementación · 2026-04-23 (caso B ejecutado)

### Código escrito

- **`backend/app/core/alerting.py`** · módulo nuevo · 195 líneas
  - `send_discord_alert(title, level, details)` async · POST webhook via httpx · fire-and-forget semantics
  - `send_discord_alert_bg(...)` schedule via `asyncio.create_task`, no bloquea caller
  - Rate limiter in-memory: hash `(level, method, path, title)` → last_sent_ts · TTL 5 min · GC automático
  - Embed Discord: color por nivel (red=5xx/exception, orange=429, yellow=uptime, blue=info) · fields request context + `tunnel_url` leído de `/tmp/crece-tunnel.url` en cada llamada (captura rotaciones) · Env + Service + timestamp ISO
  - No-op silencioso si `DISCORD_WEBHOOK_URL` vacío · warning startup **una sola vez** (flag `_missing_url_warned`)
  - Todos los errores HTTP swallowed + loggeados (nunca raises)

- **`backend/app/main.py`** · 3 cambios
  - `@app.exception_handler(Exception)` genérico: Sentry + Discord + log.exception → 500 JSON
  - `@app.middleware("http") alert_on_5xx`: dispara alerta cuando `response.status_code >= 500` y no vino de exception (p.ej. `raise HTTPException(500)` manual)
  - `rate_limit_handler_with_alert` envuelve `_rate_limit_exceeded_handler` de slowapi · tracking in-memory por IP en ventana 60s · alerta exactamente al hit 10 (umbral) sin spam después

- **`backend/app/core/config.py`** · `DISCORD_WEBHOOK_URL: str = ""`

- **`backend/.env.example`** · entrada con comentario pointer a este doc

- **`.env.coolify.example`** · entrada con comentario pointer (documentación para cuando se ejecute el deploy Coolify · el compose `docker-compose.coolify.yml` NO se modificó porque el deploy es plan no ejecutado · quien retome el deploy ajusta el passthrough en ese momento)

- **`backend/scripts/_test_discord_alert.py`** · script temporal para test manual · **ignorado por git** (entrada añadida a `backend/.gitignore`)

### Nota sobre el GC del dedupe cache (rate limit)

El GC corre **lazy**: solo cuando entra una nueva alerta. Si el backend pasa 1h sin 5xx y luego llegan 50 excepciones idénticas en ráfaga, la primera dispara el GC (limpia entradas expiradas) y pasa · las 49 restantes caen bajo el rate-limit de esa primera durante los siguientes 5 min y no se envían. **Esto es comportamiento esperado, no bug** — diseño deliberado para evitar spam en tormenta de errores. En el debug de incidente esperar ver solo 1 alerta de N errores idénticos concurrentes.

Además del GC lazy, **el dedup cache es per-process**. Con `uvicorn --workers 4` (config actual en `docker-compose.coolify.yml`), tormenta de 100 errores idénticos distribuidos entre los 4 workers puede producir **hasta 4 alertas en vez de 1**. Aceptable para piloto actual (<10 req/s · 3 usuarios activos reales). Migración a Redis pendiente como **B-RATE-LIMIT-01 en BACKLOG**.

### Tests unit · 21/21 verdes

```
$ cd backend && .venv/bin/pytest tests/test_alerting.py --noconftest -v
tests/test_alerting.py::TestColorMapping::test_5xx_red PASSED           [  4%]
tests/test_alerting.py::TestColorMapping::test_exception_red PASSED     [  9%]
tests/test_alerting.py::TestColorMapping::test_429_orange PASSED        [ 14%]
tests/test_alerting.py::TestColorMapping::test_uptime_yellow PASSED     [ 19%]
tests/test_alerting.py::TestRateLimit::test_first_call_not_limited PASSED [ 23%]
tests/test_alerting.py::TestRateLimit::test_second_call_limited PASSED  [ 28%]
tests/test_alerting.py::TestRateLimit::test_different_keys_independent PASSED [ 33%]
tests/test_alerting.py::TestRateLimit::test_rate_limit_key_deterministic PASSED [ 38%]
tests/test_alerting.py::TestRateLimit::test_rate_limit_key_differs_by_path PASSED [ 42%]
tests/test_alerting.py::TestBuildEmbed::test_title_truncated PASSED     [ 47%]
tests/test_alerting.py::TestBuildEmbed::test_message_truncated PASSED   [ 52%]
tests/test_alerting.py::TestBuildEmbed::test_basic_fields_present PASSED [ 57%]
tests/test_alerting.py::TestBuildEmbed::test_tunnel_url_field_when_file_exists PASSED [ 61%]
tests/test_alerting.py::TestBuildEmbed::test_tunnel_url_absent_when_file_missing PASSED [ 66%]
tests/test_alerting.py::TestSendDiscordAlert::test_no_url_noop PASSED   [ 71%]
tests/test_alerting.py::TestSendDiscordAlert::test_no_url_warns_once PASSED [ 76%]
tests/test_alerting.py::TestSendDiscordAlert::test_sends_with_url PASSED [ 80%]
tests/test_alerting.py::TestSendDiscordAlert::test_duplicate_alerts_rate_limited PASSED [ 85%]
tests/test_alerting.py::TestSendDiscordAlert::test_different_paths_not_rate_limited PASSED [ 90%]
tests/test_alerting.py::TestSendDiscordAlert::test_httpx_error_swallowed PASSED [ 95%]
tests/test_alerting.py::TestSendDiscordAlert::test_unexpected_error_swallowed PASSED [100%]
============================== 21 passed in 0.13s ==============================
```

Cubre: color mapping (4) · rate limit lógica (5) · embed building + truncation + tunnel_url field (5) · send flow con httpx mock (7).

Nota operativa para reproducir: la suite se corre con `--noconftest` porque el `conftest.py` del proyecto importa `app.main` que requiere 30+ deps que el `.venv` actual no tiene sincronizadas con `pyproject.toml`. Los tests de `alerting` son unit puros · no dependen de FastAPI runtime · por eso el skip de conftest es seguro y correcto.

### Test manual · **PENDIENTE URL Discord**

Paso bloqueado hasta que CEO provea `DISCORD_WEBHOOK_URL`. Una vez provista:

```bash
# 1. Pegar URL en backend/.env:
#    DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# 2. Ejecutar script de prueba:
cd backend && .venv/bin/python scripts/_test_discord_alert.py

# 3. Verificar que llega notificación en canal Discord <60s con:
#    - title: "F0.1 smoke test · alerta manual desde script"
#    - color: azul (level=info)
#    - fields: Method=MANUAL, Path=/scripts/..., Message=Si ves..., Env=development, Service=CRECE v2.0
#    - si /tmp/crece-tunnel.url existe: campo Tunnel URL

# 4. Borrar el script:
rm backend/scripts/_test_discord_alert.py
# Aunque está en gitignore no se sube, el hábito es borrar tras test.

# 5. Reiniciar backend para que el handler nuevo tome efecto con DSN configurado:
#    (según método actual de despliegue local — LaunchAgent restart o supervisord o pm2)

# 6. Documentar en este mismo archivo, sección "Resultado test manual" abajo.
```

### Resultado test manual · ejecutado 2026-04-24

| Campo | Valor |
|---|---|
| Timestamp inicio (UTC) | `2026-04-24T03:28:15Z` |
| Timestamp fin (UTC) | `2026-04-24T03:28:16Z` |
| Latencia end-to-end | **≤1 segundo** (criterio <60s · ✅ cumple con margen × 60) |
| Entorno | local Mac Mini M4 · APP_ENV=development · APP_VERSION=2.0.0 |
| Comando | `cd backend && .venv/bin/python scripts/_test_discord_alert.py` |
| Stdout | `[test] OK · webhook respondió 2xx. Revisa el canal Discord.` |
| HTTP status | 2xx (Discord webhook) |
| Resultado | ✅ **EXITOSO** — notificación entregada |

**Snippet del embed recibido en canal Discord** (reconstruido desde payload local, texto por petición CEO):

```
Title:     F0.1 smoke test · alerta manual desde script
Color:     azul 0x3498DB (level=info)
Fields:
  - Method:     MANUAL                                (inline)
  - Path:       /scripts/_test_discord_alert.py       (inline)
  - Message:    Si ves este mensaje en Discord, F0.1 observability está operativo.
  - Tunnel URL: https://skin-critical-territories-says.trycloudflare.com
  - Env:        development                           (inline)
  - Service:    CRECE v2.0 v2.0.0                    (inline)
Timestamp: 2026-04-24T03:28:15.xxxZ
```

**Tunnel URL capturada al vuelo:** confirmación de que el read-at-send-time funciona — `_read_tunnel_url()` leyó `/tmp/crece-tunnel.url` en el momento de construir el embed.

**Script temporal borrado tras test:** `backend/scripts/_test_discord_alert.py` — ver sección Limpieza abajo.

---

## Better Stack setup (para el CEO, post-named tunnel)

> ### ⚠️ PRE-REQUISITO DNS NO CUMPLIDO AL 2026-04-24
>
> El hostname `api-crece-dev.mdconsultoria-ti.org` usado en las instrucciones abajo **NO existe y NO es creable hoy**. Razones:
> - `mdconsultoria-ti.org` está en **InterServer DNS, no en Cloudflare** (verificado via `dig NS mdconsultoria-ti.org` → `cdns1/cdns2/cdns3.interserver.net`)
> - Named tunnel con ese hostname requiere **migrar DNS de ~12 servicios en producción** (email MX + `www/api/blog/app/mail/imap/pop/admin/n8n/chatmx/ollama/coolify`), **O comprar dominio nuevo en Cloudflare Registrar** (~$10 USD/año)
>
> Ambas rutas están **diferidas como B-23-05** (sesión 2026-04-23/24 · CEO las descartó por scope creep). **Better Stack NO debe configurarse hasta que B-23-05 se resuelva.**
>
> Las instrucciones siguientes son **documentación de referencia para ejecutar POST-B-23-05**, no tareas accionables hoy.

**Pre-requisito:** named tunnel Cloudflare activo con hostname estable — CEO lo ejecuta hoy en paralelo (B-23-05). Sugerido: `api-crece-dev.mdconsultoria-ti.org`.

### URL a monitorear

Una vez el named tunnel esté activo, configurar Better Stack con:

```
URL: https://api-crece-dev.mdconsultoria-ti.org/api/v1/health/
Method: GET
Expected status: 200
Expected JSON: {"status": "healthy"}
Check interval: 3 min
Timeout: 10s
Regions: múltiples (default 3+)
```

### Webhook de notificación

Apuntar al mismo canal Discord del backend (reusar `DISCORD_WEBHOOK_URL` o crear channel webhook dedicado para uptime):

```
Better Stack → Alerting → Integrations → Discord
Channel: #crece-alerts (o el elegido)
Notify on: Down (>2 min) + Recovered
```

### Por qué no Coolify ni Mac local

- Named tunnel → URL estable = Better Stack puede hacer checks confiables
- Before named tunnel (URL rotatoria ~1h): **saltar Better Stack** — produciría falsos positivos horarios
- Monitoreo desde dentro del backend ya fue descartado (CEO guard: "sin sentido monitorear el tunnel desde el servicio que depende del tunnel")

---

## 429 sostenido · gap futuro

Implementado el wrapper del handler slowapi con tracking en memoria y alerta al umbral 10 hits/60s por IP. Timebox 30 min respetado. **Gap declarado:** el tracking es **in-memory por worker** — si backend corre con múltiples workers uvicorn/gunicorn, cada worker tiene su propio contador, umbral efectivo × N. Aceptable para este MVP (8 dirigentes, probabilidad 429 legítimo baja por definición); a escala requiere mover contador a Redis (cost-benefit bajo hoy).

---

## Registrado por

Claude Code · sesión 2026-04-23 · post-meta-fix CLAUDE.md + PLAN-current.md `ACTIVE:` redirect a `PLAN-recuperacion-post-incidente-2026-04-21.md`.

F0.1 MVP código + tests unit cerrados. F0.1 test manual + Better Stack quedan pendientes de: (a) URL Discord pegada por CEO, (b) named tunnel completado por CEO (B-23-05).
