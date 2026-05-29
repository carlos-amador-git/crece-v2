# Auditoría de Seguridad — CRECE v2

**Fecha:** 2026-04-25
**Auditor:** sesión Claude Code (security-engineer profile)
**Alcance:** snapshot de la rama `hotfix/23a-ui-puros` · solo lectura (sin commits, sin tests)
**Tiempo invertido:** ~50 min
**Tipo:** diagnóstico ligero — NO sustituye un pentest profesional

---

## Resumen ejecutivo

- **Sin secrets en el repo.** `.gitignore` cubre `.env`, `.env.*.local`, `.env.vercel`, `frontend/.env.production`, `backend/.env.scraping-keys`. Los `.env.example` solo contienen placeholders (`CHANGE-ME-...`). Hay un guard en `Settings._guard_production_secrets` que falla el arranque si en producción se quedaron los defaults — ✅ buen patrón.
- **JWT funcional pero con dos asuntos importantes:** `HS256` con secret simétrico (correcto para single-issuer) y expiración de 24 h (`JWT_EXPIRE_MINUTES=1440`) sin refresh token. No se observa lista de revocación; un token robado vive un día completo.
- **RLS implementado pero NO enforcement-by-default.** Hay políticas RLS sobre 5 tablas críticas (`ciudadanos, dirigentes, encuestas, eventos, users`) y un dependency `get_db_rls` que hace `SET LOCAL app.current_org_id`. **Pero** los endpoints inspeccionados (ej. `dirigentes.py`, `posts.py`) usan el `get_db` plano, no `get_db_rls`. La isolación efectiva depende de filtros aplicativos `WHERE org_id = ...` en cada query — frágil.
- **Veda Electoral middleware existe pero NO está montado.** `backend/app/core/veda.py` define `VedaElectoralMiddleware` correcto, pero `main.py` solo añade `ProxyHeaders` y `CORS`. En periodo de veda real las rutas POST/PATCH/DELETE seguirían operativas. **CRÍTICO para cumplimiento INE.**
- **Sentry/Bugsink sin PII scrubbing.** `sentry_sdk.init` no configura `before_send`, `send_default_pii`, ni denylist. Cualquier 5xx envía request body, headers (incluido `Authorization: Bearer ...`) y stacktrace al DSN. Discord webhook envía hasta 500 chars de `str(exc)` → tokens, payloads, dirigente data potencialmente filtrables.
- **`trusted_hosts=["*"]` en `ProxyHeadersMiddleware`** acepta `X-Forwarded-For` desde cualquier origen. Atrás de un solo proxy (cloudflared) es aceptable, pero abre door para spoofing del IP del cliente si el ingress cambia.

Conclusión: la base es sólida (bcrypt, slowapi, pydantic guards, ARCO endpoint, audit log de PII) pero hay **3 hallazgos críticos de configuración** que pueden corregirse en horas, no días.

---

## Tabla de hallazgos

### CRÍTICO

| # | Hallazgo | Archivo:línea | Impacto | Recomendación |
|---|----------|---------------|---------|---------------|
| C-01 | Veda Electoral middleware definido pero NO montado en `main.py` | `backend/app/core/veda.py:65` (clase OK) · `backend/app/main.py:101-113` (no aparece `app.add_middleware(VedaElectoralMiddleware)`) | Durante veda electoral INE, POSTs a `/social`, `/encuestas`, `/content/generate`, `/content/pieces` siguen funcionando. Riesgo de sanción INE + invalidación de gastos de campaña. Cumplimiento INE FALSO. | Añadir `app.add_middleware(VedaElectoralMiddleware)` en `main.py` ANTES de `add_middleware(CORSMiddleware)`. Probar con `VEDA_ELECTORAL_ACTIVE=true`. |
| C-02 | Sentry/Bugsink envía PII sin scrubbing | `backend/app/main.py:26-32` | `sentry_sdk.init(dsn=..., traces_sample_rate=0.1, environment=..., release=...)` sin `before_send`, sin `send_default_pii=False`. Stacktraces incluyen request body, headers (`Authorization`, `Cookie`), nombres de dirigentes, comments. Cumplimiento LFPDPPP roto si Bugsink está hosted fuera de México. | Añadir `before_send` callback que scrubbee `Authorization`, `Cookie`, `password`, `token`, `email`, y campos PII de dirigentes. Default `send_default_pii=False`. Ver Sentry SDK docs § Filtering. |
| C-03 | Endpoints usan `get_db` no `get_db_rls` → RLS no enforced en runtime | `backend/app/core/database.py:77-98` define `get_db_rls` correcto · `backend/app/api/v1/endpoints/dirigentes.py:40,119,282,300,344,401` usa `get_db` (igual en posts.py, social.py, etc.) | El `app.current_org_id` setting nunca se aplica → RLS policies evalúan contra `current_setting(... , true)` que retorna `''` → todas las filas con `org_id = NULL` son visibles, las demás bloqueadas. Pero como las queries SQLAlchemy ya filtran por `org_id` aplicativamente, RLS no agrega defensa-en-profundidad. Si un día alguien olvida el filtro `.where(Dirigente.org_id == ...)`, no hay red de seguridad. | Migrar progresivamente a `get_db_rls` en todos los endpoints que tocan tablas RLS. Mientras tanto: añadir test que prueba cross-tenant (org A no ve org B). Ver `migrations/77bbd5e5f495`. |

### ALTO

| # | Hallazgo | Archivo:línea | Impacto | Recomendación |
|---|----------|---------------|---------|---------------|
| A-01 | `ProxyHeadersMiddleware(trusted_hosts=["*"])` | `backend/app/main.py:101-104` | Cualquier origen puede setear `X-Forwarded-For` y spoofear IP del cliente, lo que **rompe el rate-limiter de slowapi** (key_func=`get_remote_address`). Un atacante puede rotar el header y bypassear el límite de 5/min en `/login`. | Restringir `trusted_hosts` al CIDR de cloudflared o al hostname del proxy. Cloudflare publica rangos: https://www.cloudflare.com/ips/. |
| A-02 | ARCO endpoint público sin rate-limit ni verificación de identidad | `backend/app/api/v1/endpoints/privacy_arco.py:55-119` | `POST /arco/exercise` con `tipo_derecho=cancelacion` ejecuta `DELETE FROM social_comments WHERE author_hash = ...` sin auth. El propio comentario del archivo lo reconoce ("debe agregarse verificación INE + rate limiting"). Atacante con scraper de IDs públicos puede borrar masivamente comments de oposición y disfrazar ataque como ejercicio ARCO legítimo. | (a) Añadir `@limiter.limit("3/hour")`. (b) Cambiar a flujo de "request" + validación humana antes del DELETE: insertar en tabla `arco_requests` con estado `pending`, equipo legal valida en 20 días (art. 32 LFPDPPP) y luego ejecuta. |
| A-03 | Discord webhook envía 500 chars de `str(exc)` al canal | `backend/app/main.py:158-175` + `backend/app/core/alerting.py:116` | Stack traces, payloads, contraseñas mal-tipadas, tokens en query strings, nombres de dirigentes pueden aparecer en el mensaje. El canal Discord no es "datos sensibles" según LFPDPPP — se considera filtración a tercero (Discord Inc., USA). | Sanitizar `str(exc)` antes de mandar: regex para JWT, `password=`, `token=`, emails. Mejor: enviar solo `type(exc).__name__` y un trace_id; el equipo consulta detalles en Bugsink interno. |
| A-04 | JWT sin refresh token + 24h de expiración | `backend/app/core/config.py:30` (`JWT_EXPIRE_MINUTES=1440`) · `backend/app/core/security.py:44-48` | Token robado (XSS, log accidental, console paste) sirve por 24h sin posibilidad de revocar. No hay tabla `revoked_tokens` ni `jti` claim. | Reducir a 60 min + implementar refresh token rotativo. Mientras tanto: añadir `jti` a payload y endpoint `/auth/logout` que insertra en `revoked_jti`. |
| A-05 | `JWT_SECRET` reusado como `N8N_WEBHOOK_SECRET` por fallback | `backend/app/api/v1/endpoints/webhooks_integration.py:22` (`_WEBHOOK_SECRET = ... or settings.JWT_SECRET`) | Si n8n queda mal configurado y no setea su secret, los webhooks se firman con la clave que firma JWTs de usuarios. Compromiso de uno = compromiso del otro. | Quitar el fallback. Si `N8N_WEBHOOK_SECRET` no está seteado, el endpoint debe responder 503. |

### MEDIO

| # | Hallazgo | Archivo:línea | Impacto | Recomendación |
|---|----------|---------------|---------|---------------|
| M-01 | Frontend usa `localStorage` para JWT (inferido) | No verificado: requiere leer `frontend/src/lib/`. Cookie HttpOnly no fue observada en config CORS (`allow_credentials` solo TRUE si origins != `["*"]`). | Tokens en `localStorage` son vulnerables a XSS. | Verificar y migrar a cookie HttpOnly+Secure+SameSite=Strict si es el caso. |
| M-02 | `CLAUDE_API_KEY` en backend `.env` ejecuta calls a Anthropic con datos de dirigentes | `backend/app/core/config.py:45` | Dirigentes políticos mexicanos enviados a infraestructura US. Aceptable bajo LFPDPPP con aviso, pero requiere Privacy Policy actualizada (que existe — `/legal/privacidad`). Validado. | Documentar en aviso que Anthropic procesa datos en US. Considerar Ollama on-prem para PII (ya disponible: `AI_PROVIDER` config). |
| M-03 | Default `POSTGRES_PASSWORD=crece_dev` en docker-compose.yml dev | `docker-compose.yml:28` | Aceptable en dev local, pero si alguien expone el puerto 5438 a internet (hosting compartido, port-forward Cloudflare), la BD es accesible con credencial pública. | Confirmar que Coolify/prod usa `docker-compose.prod.yml` que tiene `${POSTGRES_PASSWORD:?...}` — ✅ ya está bien. Solo bloquear puerto 5438 de fuera del host en dev. |
| M-04 | `oauth2_scheme_optional` permite request sin token a llegar al code path JWT | `backend/app/core/security.py:19, 72-138` | Endpoints que dependen de `get_current_user` sí lanzan 401, pero el "optional" pattern es frágil — un endpoint que olvide chequear el return puede tratar `None` como anónimo. Inspección manual no encontró bug, pero el patrón invita errores. | Mantener nombres distintos: `get_current_user` (auto-error) y `get_current_user_or_none`. Hoy el alias `get_current_user_or_api_key = get_current_user` añade confusión. |
| M-05 | Logs `level=DEBUG` cuando `APP_DEBUG=True` (default en dev) | `backend/app/main.py:34-37` | SQLAlchemy con `echo=settings.APP_DEBUG` también imprime queries con valores. Si dev `.env` se copia a producción por error, logs filtran PII a stdout (Coolify, journalctl). | Setear `APP_ENV=production` en Coolify garantiza el guard. Añadir fail-fast: si `APP_ENV=production AND APP_DEBUG=True` → ValueError en startup. |

### BAJO

| # | Hallazgo | Archivo:línea | Recomendación |
|---|----------|---------------|---------------|
| B-01 | `forgot_password` correcto (no enumera emails) — confirmar tras implementar dispatch real | `backend/app/api/v1/endpoints/auth.py:100-120` | Cuando se implemente Celery dispatch, mantener mismo response time si el usuario no existe (timing attack). |
| B-02 | `MINIO_ACCESS_KEY/SECRET=minioadmin` defaults | `backend/app/core/config.py:39-40` | Igual que C-03 con Postgres: prod debe overridear. Confirmar en `.env.coolify.example` que se sobreescribe. |
| B-03 | `oauth2_scheme` apunta a `/api/v1/auth/login` mientras `oauth2_scheme_optional` apunta al mismo | `backend/app/core/security.py:18-19` | Cosmético — solo afecta el botón "Authorize" de Swagger UI. |
| B-04 | API keys hashed con SHA256 (sin salt) | `backend/app/core/security.py:110` | Dado que las keys generadas son aleatorias largas (`generate_api_key()`), rainbow tables no aplican. SHA256 es OK aquí. Si las keys fueran short-form, requeriría bcrypt/argon2. |

---

## Top 5 acciones recomendadas (orden de prioridad)

1. **Montar VedaElectoralMiddleware** en `main.py` (1 línea de código, riesgo INE alto). [C-01]
2. **Configurar `before_send` de Sentry** para scrubbear Authorization, password, token, email. **PRE-REQUISITO antes de exponer Bugsink a producción.** [C-02]
3. **Sanitizar payloads de Discord webhook** — regex denylist sobre `details.message` antes de POST. Implementar en `_build_embed`. [A-03]
4. **Cerrar ARCO endpoint público:** rate-limit + flujo pending/validated. Mientras tanto, considerar deshabilitarlo si el piloto aún no requiere ARCO público. [A-02]
5. **Restringir `trusted_hosts` del ProxyHeaders** al CIDR de cloudflared. **De esto depende que el rate-limiter de login funcione.** [A-01]

Tras resolver 1-5: planificar migración de `get_db` → `get_db_rls` (defensa-en-profundidad RLS). [C-03] · este es trabajo de varios días pero baja-prioridad mientras los filtros aplicativos se mantengan revisados.

---

## NO verificado (sin inventar resultados)

- **Frontend localStorage vs HttpOnly cookie:** no leí `frontend/src/lib/api-client.ts` ni componentes. Reportar como TODO.
- **CSRF tokens:** si frontend usa cookies, falta verificar protección CSRF (FastAPI no provee built-in). No revisado.
- **PII encryption en columnas de `ciudadanos_legacy`:** existe `PII_ENCRYPTION_KEY` y referencias a `pgp_sym_encrypt`. No verifiqué que efectivamente se use en runtime ni que la rotación esté planificada.
- **Path traversal:** no hay grep claro de uploads/downloads de archivos del usuario. MinIO existe pero no audité los endpoints de upload.
- **CORS preflight:** la lista `CORS_ORIGINS` incluye `http://localhost:3000`, `http://localhost:5173`, y la URL Vercel. No verifiqué que en prod no se incluyan `*` ni dominios obsoletos.
- **NEXT_PUBLIC_ env vars** del frontend: solo leí `.env.local.example` (API_URL, MAPLIBRE_STYLE — ambos públicos por diseño). No revisé el dashboard de Vercel para confirmar que no haya leakage de keys privadas en `NEXT_PUBLIC_*`.
- **Test coverage de cross-tenant:** no ejecuté pytest (regla del CEO). No verifiqué si existe test que pruebe que org A no lee datos de org B.
- **Logs de stdout en runtime:** backend está corriendo en `:8002` pero no inspeccioné qué está escribiendo ahora mismo. No puedo afirmar que logs estén limpios.
- **Dependencias outdated/CVE:** no corrí `pip-audit` ni `npm audit`.

---

## Notas de proceso

- Audit basado en lectura estática de código (grep + Read en archivos clave). NO se ejecutó código, NO se modificó nada, NO se hicieron commits.
- Los archivos `.env` reales en disco (`backend/.env`) NO fueron leídos para preservar secretos del CEO.
- `git ls-files` confirmó que solo `.env.example`, `.env.coolify.example` y similares están versionados. ✅
- Stack reviewed: FastAPI, SQLAlchemy 2.0 async, slowapi, sentry_sdk, bcrypt, PyJWT, pydantic-settings, ProxyHeadersMiddleware.

**Disclaimer:** este audit es un spot-check de 50 min, no un pentest. No cubre lógica de negocio en `services/`, scrapers (que llegan al exterior), workers Celery, ni infrastructure (Coolify, Cloudflare tunnel, MinIO bucket policies, PostgreSQL `pg_hba.conf`). Para producción con datos electorales reales, recomendar audit profesional con SAST + DAST + revisión de infraestructura.
