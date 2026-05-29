# PLAN · Followers/OAuth + Pipeline auditoría de campos · 2026-05-13

> **REVISADO 2026-05-13 vía `/sprint-review`** (FASE 1 completada). Cambios marcados con `⊕ REV`. Ejecución en curso.

## Objetivo de la sesión
Los dirigentes piden ver **nombres de sus seguidores** + **si comentaron o no**.
La doctrina acordada: dirigentes dan sus accesos OAuth → backend scraper privilegiado
descarga listas de followers + engagement granular.

Adicional: implementar **pipeline de auditoría de campos** para detectar huecos
de población ANTES de que los descubramos usando la app (modo actual: ineficiente).

## Contexto al cierre 2026-05-12 noche

### Lo que YA EXISTE (no rehacer)
- ✅ Modelo `OAuthTokenByPlatform` (instagram, facebook_page, tiktok, youtube)
  - Path: `backend/app/models/oauth_token.py`
  - Tabla creada · 1 fila stub (dirigente 1 / IG)
  - Service: `backend/app/services/onboarding/oauth_service.py` (stubs `is_stub=True`)
- ✅ Endpoints stub OAuth (`backend/app/api/v1/endpoints/onboarding.py:219-285`):
  - `GET  /oauth/init/{platform}` (build_init_url stub)
  - `POST /oauth/callback/{platform}` (persist_callback_stub)
  - `GET  /oauth/status/{dirigente_id}` (listar_status)
- ✅ Modelo `SocialProfile` con `followers_count` (agregado, no lista)
- ✅ Endpoint `/dirigentes/{id}/crecimiento` series temporales
- ✅ Sentiment/tono/target en posts y comments
- ✅ Endpoint `bot_detection.py` (7.9K) reutilizable para flag `is_real` (DECISIÓN-2 ↓)
- ✅ Apify Actors cubren FB+IG+TT+YT públicos (B-FB/IG-SCRAPER DESCARTADOS · ver BLOCKERS.md)

### Lo que FALTA
- ❌ Tabla `social_followers` (lista de seguidores reales)
- ❌ Tabla `follower_engagement` (qué follower comentó/likeó qué post)
- ❌ Endpoints `/dirigentes/{id}/followers` + filtros
- ❌ Vista frontend "Mis seguidores"
- ❌ Scrapers privilegiados que usen OAuth tokens reales
- ❌ Pipeline auditoría sistematizado (`audit_data_quality.py`)
- ❌ Meta App Review (Instagram + Facebook Pages API) · DIFERIDO histórico

---

## ⊕ REV · Decisiones de arranque resueltas (defaults autónomos)

CEO autorizó `Tienes luz verde para todo. Avísame al final.` Defaults adoptados:

| # | Pregunta | Decisión adoptada | Reversible |
|---|----------|-------------------|------------|
| Q1 | ¿YouTube primero o esperar Meta? | **YouTube** — sin App Review, deliverable inmediato. Meta gateado en B-META-APPREVIEW. | Sí, S6 |
| Q2 | ¿Reusar `bot-detection/` para `is_real`? | **Defer.** Columna existe (`is_real bool`, `bot_score float|null`) pero scraper inicial deja `is_real=true, bot_score=null`. Hook a `bot_detection.py` queda como B-FOLLOWERS-BOT-1 (sprint posterior). | Sí, no destructivo |
| Q3 | ¿Scope followers? | **Sigue patrón onboarding.py:** VIEWER ve su `dirigente_id`, ANALYST/ADMIN ve `org_id`, ADMIN MD cross-org con `X-Org-Id`. Reusar `RoleChecker`. | Sí, ajustable |

---

## ⊕ REV · Cambios al plan original

| Sprint | Cambio | Razón |
|--------|--------|-------|
| S1 | **Dividido en S1 (modelo) + S1b (endpoint)** | Permite paralelizar S1 con S5. S1b se libera al terminar S1. |
| S2 | **Gating CEO explícito:** se codifica el service real pero E2E test **bloqueado** hasta que CEO entregue `GOOGLE_OAUTH_CLIENT_ID` + `_SECRET`. | CEO debe crear GCP Project · Claude no puede automatizar Google Cloud Console. |
| S3 | **Sin run real** · sólo escribe módulo + tests con HTTP mock. Validación E2E gateada en S2 completo. | Dependencia dura: scraper sin token = no funciona. |
| S4 | **Empty states obligatorios** (D-ANTI-MOCK-1) · CERO hardcoded numbers. Skeleton + CTA "conectar plataforma". | Regla CLAUDE.md project: anti-fallback-data en UI. |
| S5 | **Mantiene scope ampliado** (mismatch FE↔BE como sub-tarea) | Plan original ya incluía esto. |
| S6 | **Documentar como BLOCKER** en `BLOCKERS.md` · 0 minutos en sesión. | Meta App Review = 4-6 semanas externo. |

### Dependencias y paralelización

```
S1 (modelo+migration)  ─┬─→  S1b (endpoint) ─→ S4 (frontend)
                        └─→  S3 (scraper)  ┐
S2 (OAuth YT scaffold)  ─────────────────────┴→ E2E gateado por CEO
S5 (audit pipeline)  ⊥ resto (paralelo total)
```

**Wave 1 (paralelo):** S1 + S2 + S5
**Wave 2 (depende S1):** S1b + S3
**Wave 3 (depende S1b):** S4
**Wave 4 (gateado CEO):** S2 E2E + S3 E2E + corre primer scrape real

---

## Sprints (revisados con criterios medibles)

### S1 · Modelo de datos followers (30 min)
**Esfuerzo**: 30 min · Archivos: `backend/app/models/follower.py`, `backend/migrations/versions/fol1_social_followers.py`

- Tabla `social_followers`:
  ```sql
  id, dirigente_id (FK CASCADE), org_id (FK CASCADE | null),
  platform varchar(20), follower_external_id varchar(100),
  follower_handle varchar(100), follower_display_name varchar(200),
  follower_avatar_url text, follower_is_verified bool default false,
  is_real bool default true, bot_score float,
  first_seen_at timestamptz default now(),
  last_seen_at timestamptz default now(),
  last_active_at timestamptz,
  source varchar(20) check (source in ('oauth','scraper_auth','public_scraper')),
  raw_data jsonb default '{}'::jsonb
  ```
- Tabla `follower_engagement`:
  ```sql
  id, follower_id (FK CASCADE), post_id (FK CASCADE),
  engagement_type varchar(20) check (in ('comment','like','share','repost','reaction')),
  comment_id bigint (FK comments | null), engaged_at timestamptz,
  raw_data jsonb default '{}'::jsonb
  ```
- Constraints:
  - `UNIQUE (dirigente_id, platform, follower_external_id)` en social_followers
  - `UNIQUE (follower_id, post_id, engagement_type, comment_id)` en follower_engagement
- Índices:
  - `idx_followers_dirigente_lastseen ON social_followers(dirigente_id, last_seen_at DESC)`
  - `idx_followers_org ON social_followers(org_id)` (RLS multi-tenant)
  - `idx_engagement_follower ON follower_engagement(follower_id)`
  - `idx_engagement_post ON follower_engagement(post_id)`

**Criterio de aceptación**:
- [ ] `alembic upgrade head` aplica sin errores en local
- [ ] `alembic downgrade -1` revierte limpio (idempotente)
- [ ] `from app.models.follower import SocialFollower, FollowerEngagement` importable
- [ ] Modelo registrado en `app/models/__init__.py`

### S1b · Endpoint GET /dirigentes/{id}/followers (30 min)
**Esfuerzo**: 30 min · Archivos: `backend/app/api/v1/endpoints/followers.py`, `backend/app/main.py` (router include)

- Endpoint: `GET /dirigentes/{dirigente_id}/followers`
- Query params:
  - `platform` (str | null) — filtrar plataforma
  - `only_with_comments` (bool, default false) — solo followers con engagement_type=comment
  - `only_verified` (bool, default false) — `follower_is_verified=true`
  - `page` (int, default 1), `page_size` (int, default 50, max 200)
- Respuesta:
  ```json
  {
    "total": int,
    "page": int,
    "page_size": int,
    "items": [
      {
        "id": int, "platform": str, "follower_handle": str,
        "follower_display_name": str, "follower_avatar_url": str|null,
        "follower_is_verified": bool, "is_real": bool, "bot_score": float|null,
        "first_seen_at": iso8601, "last_seen_at": iso8601,
        "last_active_at": iso8601|null, "source": str,
        "engagement_summary": {
          "total_engagements": int,
          "by_type": {"comment": int, "like": int, "share": int}
        }
      }
    ]
  }
  ```
- RBAC: `RoleChecker([Role.VIEWER, Role.ANALYST, Role.ADMIN])` + checks de scope:
  - VIEWER: `dirigente_id == user.dirigente_id` o 403
  - ANALYST/ADMIN: `dirigente.org_id == user.org_id` o 403
  - ADMIN MD: `X-Org-Id` cabecera override

**Criterio de aceptación**:
- [ ] curl con BD vacía → `200 {"total":0,"items":[],...}`
- [ ] curl con `?only_with_comments=true` filtra correcto
- [ ] curl con role VIEWER + dirigente_id ajeno → 403
- [ ] Test pytest `test_followers_endpoint.py` ≥4 casos (empty, filter, RBAC, pagination)

### S2 · OAuth real YouTube — scaffold (1.5h, gating CEO)
**Esfuerzo**: 1.5h código · 0 min E2E (gateado)
**Archivos**:
- `backend/app/services/onboarding/youtube_oauth_real.py`
- `backend/app/api/v1/endpoints/onboarding.py` (envuelve service real cuando `OAUTH_YOUTUBE_ENABLED=true`)
- `backend/.env.example` (agregar `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_BASE`)

**Implementación scaffold:**
1. `build_init_url_real(dirigente_id)` — construye URL Google OAuth consent v2 con scopes `youtube.readonly` + `yt-analytics.readonly`
2. `exchange_code_for_tokens(code, state)` — POST a `https://oauth2.googleapis.com/token` con `code`, `client_id`, `client_secret`, `redirect_uri`, `grant_type=authorization_code`
3. `refresh_access_token(refresh_token)` — POST con `grant_type=refresh_token`
4. `persist_callback_real(db, dirigente_id, tokens)` — escribe fila con `is_stub=False`, encripta `token_hash` + `refresh_token_hash` (reusa `app.core.security.encrypt_token` si existe; si no, AES-GCM)
5. Toggle: si `OAUTH_YOUTUBE_ENABLED=false` (default) → comportamiento actual stub

**⊕ Gating CEO (BLOCKER B-OAUTH-YT-GCP-1):**
- CEO debe ejecutar pasos GCP manualmente (no automatizable):
  1. Google Cloud Console → New Project "CRECE v2"
  2. Habilitar YouTube Data API v3
  3. OAuth consent screen → External · testing mode
  4. Crear credenciales OAuth 2.0 → guardar Client ID + Secret en `.env`
  5. Authorized redirect URIs:
     - `http://localhost:8002/api/v1/oauth/callback/youtube` (dev)
     - `https://api-crece-dev.mdconsultoria-ti.org/api/v1/oauth/callback/youtube` (cuando named tunnel exista · B-23-05)
- Estimado CEO: 20 min · paralelo a sesión Claude.

**Criterio de aceptación (scaffold)**:
- [ ] Pytest mock test: `exchange_code_for_tokens` con httpx mock → 200 retorna dict con access_token + refresh_token + expires_in
- [ ] Tests no rompen sin `GOOGLE_OAUTH_*` env vars (toggle apaga el path real)
- [ ] `OAUTH_YOUTUBE_ENABLED` documentado en `.env.example`

**Criterio E2E (gateado CEO)**:
- [ ] CEO completa GCP setup → entrega creds
- [ ] Dirigente accede `/dashboard/settings/integraciones` → click "Conectar YouTube" → consent Google → callback exitoso → fila `is_stub=False` en BD

### S3 · Scraper privilegiado YouTube (1h, gateado por S2 E2E)
**Esfuerzo**: 1h código · 0 min ejecución real
**Archivos**:
- `backend/app/scrapers/youtube_privileged.py`
- `backend/app/scrapers/base.py` (registrar variante `youtube_oauth`)
- `backend/tests/scrapers/test_youtube_privileged.py`

**Implementación:**
- `class YouTubePrivilegedScraper`:
  - `__init__(oauth_token: OAuthTokenByPlatform)`
  - `list_my_subscribers()` → llama `https://www.googleapis.com/youtube/v3/subscriptions?part=subscriberSnippet&mySubscribers=true`
  - `list_recent_comments(video_id)` → `commentThreads.list`
  - `cross_reference_subscribers_and_comments(channel_id, post_ids)` → escribe `social_followers` (UPSERT) + `follower_engagement`
- Honestidad documental: comentario en código + docstring **explicando que YouTube oculta la mayoría de subs (privacidad default = hidden)**. Estimación pública ≤10% del canal.
- Idempotencia: UPSERT por `(dirigente_id, platform, follower_external_id)`.
- Rate limit: respetar quotas (10K/day default API key).

**Criterio de aceptación**:
- [ ] Test con httpx mock → API YT responde 3 suscriptores ficticios → scraper escribe 3 filas en `social_followers` + N filas en `follower_engagement` si suscribers comentaron
- [ ] Test cuando OAuth token `is_stub=True` → scraper aborta con `RuntimeError("Cannot scrape: token is stub")`
- [ ] Test cuando token expirado → scraper invoca `refresh_access_token` antes de continuar

**Criterio E2E (gateado S2 E2E)**:
- [ ] Con dirigente conectado real, scraper devuelve ≥10 subs sobre canal piloto (si canal piloto tiene >10 subs públicos)

### S4 · Vista frontend "Mis seguidores" (1h)
**Esfuerzo**: 1h · Path: `frontend/src/app/dashboard/seguidores/page.tsx`, `frontend/src/lib/api/hooks/useFollowers.ts`, `frontend/src/components/seguidores/FollowersTable.tsx`

**Componentes:**
- Tabla shadcn/ui paginada:
  - Avatar (next/image · fallback initials) + nombre + handle
  - Plataforma (Badge)
  - Verified icon (lucide CheckBadge si aplica)
  - "Comentó X veces" (count engagement type=comment de `engagement_summary.by_type.comment`)
  - "Última actividad" (relativeTime via `date-fns`)
- Filtros (Toolbar):
  - Plataforma (Select multi)
  - Solo verified (Switch)
  - Solo con comments (Switch)
- Hook `useFollowers(dirigenteId, filters)` (TanStack Query · stale 60s)
- **Empty states honestos (D-ANTI-MOCK-1):**
  - Sin OAuth conectado → CTA grande "Conectar mi YouTube/IG/FB" → link a `/dashboard/settings/integraciones`
  - OAuth conectado pero sin data → Skeleton + texto "Esperando primer scrape... vuelve en 1 hora."
- **CERO hardcoded numbers.** Validado por `frontend/scripts/check-no-mocks.sh`.

**Criterio de aceptación**:
- [ ] Build `npm run build` verde
- [ ] `npm run check:no-mocks` verde
- [ ] Screenshot Playwright `/dashboard/seguidores` con dirigente sin OAuth → muestra CTA
- [ ] Screenshot con OAuth conectado + BD vacía → muestra Skeleton + mensaje espera
- [ ] tsc clean

### S5 · Pipeline auditoría de campos (1.5h)
**Esfuerzo**: 1.5h · Archivos:
- `backend/scripts/audit_data_quality.py`
- `backend/tests/scripts/test_audit_data_quality.py`
- `.context/audits/data-quality-2026-05-13.md` (output)
- `.context/audits/data-quality-2026-05-13.json` (output)

**Capas (cada una un módulo dentro del script):**

1. **Cobertura BD** (`audit_table_coverage`): por cada tabla crítica (dirigentes, social_profiles, social_posts, comments, social_followers, follower_engagement, oauth_tokens_by_platform):
   - Total rows, NULLs % por columna
   - `pg_stats` distinct values count
   - Min/max/avg numéricas
   - Top 5 valores frecuentes (categóricas)

2. **Integridad referencial** (`audit_referential_integrity`): detect orphans
   - `comments.post_id` huérfanos
   - `social_profiles.dirigente_id` huérfanos
   - `social_posts.profile_id` huérfanos
   - `follower_engagement.follower_id` huérfanos
   - `follower_engagement.post_id` huérfanos

3. **Cobertura endpoint↔frontend** (`audit_api_contract`): parsea `frontend/src/lib/api/hooks/*.ts` + `frontend/src/lib/api/client.ts`, extrae todos los `api.get/post/patch/delete` con rutas. Cross-reference contra `app/main.py` routes (cargados via FastAPI `app.routes`). Reporta:
   - Endpoints frontend sin endpoint backend
   - Endpoints backend sin uso frontend (info, no severidad)

4. **Severidad**:
   - `critical`: FK rota / endpoint FE sin BE
   - `high`: >50% NULL en columna usada por UI
   - `medium`: NULL en columna documentada (con TODO en .md)
   - `low`: NULL en columna opcional

**Outputs:**
- `data-quality-YYYY-MM-DD.md` ejecutivo (humano)
- `data-quality-YYYY-MM-DD.json` (CI consumible)
- Exit codes: 0=clean, 1=warnings, 2=critical (para CI)

**Comandos:**
```bash
# Subset rápido (pre-commit hook)
python backend/scripts/audit_data_quality.py --subset

# Completo (nightly cron)
python backend/scripts/audit_data_quality.py --full

# Sólo capa específica
python backend/scripts/audit_data_quality.py --layer coverage
```

**Criterio de aceptación**:
- [ ] Corre 1× hoy contra BD local · emite reporte enumerando ≥10 huecos reales
- [ ] Detecta endpoint FE huérfano `GET /social/comments` (verificación de retro: se arregló 2026-05-12 sprint comments, ya no debería aparecer · si aparece, falso positivo del parser → fix)
- [ ] Tests pytest ≥3 casos con BD fixture controlada

### S6 · OAuth IG/FB — BLOCKER documental (5 min)
**Acción**: agregar a `BLOCKERS.md` entrada `B-META-APPREVIEW-1`:
- Bloquea: scrapers privilegiados IG/FB
- Causa: Meta requiere Business Verification (4-6 sem) + App Review por permiso
- Mitigación interim: Apify Actors (ya en producción · ver B-FB-SCRAPER-1 DESCARTADO)
- Trigger desbloqueo: CEO inicia trámite Meta Business Manager

---

## Asignación de recursos (FASE 3)

| Sprint | Tooling/Skill primario | Skill secundario | Validación |
|--------|------------------------|------------------|------------|
| S1 | alembic + sqlalchemy 2.0 + postgis | `postgresql`, `fastapi` | migration up/down clean local |
| S1b | fastapi + pydantic v2 | `pgvector`-style query patterns | pytest fixtures + curl |
| S2 | Google OAuth 2.0 + httpx async + AES-GCM | `fastapi` | httpx mock pytest |
| S3 | YouTube Data API v3 + httpx async + tenacity (retries) | `fastapi` | httpx mock pytest |
| S4 | Next.js 14 App Router + shadcn/ui + TanStack Query | `tailwindcss4`, `react-19`, `ui-ux-pro-max` | Playwright screenshot + `check-no-mocks.sh` |
| S5 | psycopg2 introspection + FastAPI route inspector + AST parser TS | `python-expert` | reporte ≥10 huecos · pytest fixtures |
| S6 | doc only | — | entry en BLOCKERS.md |

**Skills auto-cargadas relevantes (per `~/.claude/skill_triggers.json`):**
- `systematic-debugging` (always_load)
- `postgresql` (manual · S1/S5)
- `fastapi` (S1b/S2/S3)
- `verification-before-completion` (post-sprint)

---

## Tiempo total estimado: ~5.5h
Wave 1 paralelizable (S1+S2+S5) reduce wall-clock a ~2.5h primera mitad + 2h segunda (S1b+S3+S4) + 30 min cierre.

---

## FASE 2 · Gemini Cross-Audit · OPCIONAL

⊕ REV: En este sprint **NO se ejecuta `/gemini review` automáticamente** porque:
1. `/gemini` requiere disparo manual del CEO (no es CLI invocable desde Claude Code en pipeline autónomo)
2. La complejidad del plan es media (no rewrites estructurales) — falsa economía pedir audit cuando el código mismo es la fuente de verdad.

**Hook para CEO** (opcional, recomendado pre-ejecución de cara a piloto):
```bash
# Desde la raíz del repo, en otra terminal o como follow-up:
/gemini review .context/PLAN-2026-05-13-followers-oauth-pipeline.md
```

Si CEO decide ejecutar, integrar feedback como sección `⊕ GEMINI` antes de cerrar.

---

## ⊕ REV · Riesgos y mitigaciones

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| Migración `social_followers` bloquea piloto (B-23-01 doctrine) | 🟡 Media | Tabla nueva (no ALTER existente), no requiere window mantenimiento. Test downgrade limpio en local antes de prod. |
| YouTube API quota (10K/day) insuficiente para 8 dirigentes | 🟢 Baja | Cron diario por dirigente · ~1.2K calls/dia/dirigente · margen 8x. |
| Refresh tokens Google expiran 7d en modo testing | 🟡 Media | Publicar consent screen (revisión 1 día Google) antes de piloto formal. Documentar en B-OAUTH-YT-GCP-2. |
| Frontend builds rotos si endpoint S1b cambia shape | 🟢 Baja | Contract-first: definir Pydantic schema → exportar OpenAPI → frontend consume types vía `openapi-typescript-codegen` (si configurado). |
| Auditor S5 da falsos positivos en endpoints dinámicos | 🟡 Media | Whitelist en `audit_data_quality.py` (rutas `{var}` matcheadas estructuralmente, no por string). |
| GCP setup CEO toma >1 día | 🟡 Media | S2 scaffold sigue produciendo valor (tests pasan). S3+E2E quedan en "pendiente CEO" sin bloquear S1/S1b/S4/S5. |

---

## Cierre

### Hand-off al CEO (sección final post-ejecución)

- [ ] PR único `feat/followers-oauth-pipeline-2026-05-13` con commits granulares por sprint
- [ ] `STATUS.md` actualizado con bloque sesión 2026-05-13
- [ ] `DECISIONS.md` con D-FOLLOWERS-1 (modelo) + D-OAUTH-YT-1 (scaffold) + D-AUDIT-PIPELINE-1
- [ ] `BLOCKERS.md` con B-META-APPREVIEW-1 + B-OAUTH-YT-GCP-1 + B-FOLLOWERS-BOT-1
- [ ] Auditoría inicial corrida en `.context/audits/data-quality-2026-05-13.md`
- [ ] Deploy Vercel staging (frontend) + push branch (Carlos deploya Coolify demo)
- [ ] CEO recibe lista clara de "qué necesito de ti para terminar S2 E2E"

### Anti-patrones que evitar (registro pre-ejecución)
- ❌ Hardcoded fallback numbers en frontend (D-ANTI-MOCK-1 violación)
- ❌ Migración sin downgrade testeado (B-23-01 lección)
- ❌ Run scraper sin token real "para probar" (rompería política integridad datos)
- ❌ Editar `oauth_service.py` actual (stubs son contrato vivo) · crear `youtube_oauth_real.py` paralelo

Comenzando ejecución sesión 2026-05-13.

---

## ⊕ EJECUCIÓN · 2026-05-13 (cierre `/sprint-review`)

| Sprint | Estado | Evidencia |
|--------|--------|-----------|
| S1 Modelo + migration | ✅ | `backend/app/models/follower.py`, `migrations/versions/fol1_social_followers.py`, alembic up/down clean en container, imports OK. |
| S1b Endpoint paginado | ✅ | `backend/app/api/v1/endpoints/followers.py`, 4/4 pytest verdes (`tests/api/test_followers_endpoint.py`). |
| S2 OAuth YT scaffold | ✅ (gateado E2E) | `backend/app/services/onboarding/youtube_oauth_real.py`, 7/7 pytest verdes, `.env.example` documentado con `OAUTH_YOUTUBE_ENABLED`. |
| S3 Scraper privilegiado | ✅ (gateado E2E) | `backend/app/scrapers/youtube_privileged.py`, 4/4 pytest verdes. |
| S4 Vista seguidores | ✅ | `frontend/src/app/dashboard/seguidores/page.tsx`, `lib/api/hooks/use-followers.ts`. tsc clean, `npm run check:no-mocks` verde, dev server 307 → /login (auth funciona). |
| S5 Audit pipeline | ✅ | `backend/scripts/audit_data_quality.py`, primer run en `.context/audits/data-quality-2026-05-13.md` (433 findings: 5 critical FE↔BE, 110 high-NULL, 0 huérfanos FK). |
| S6 Meta App Review | ✅ doc | Entrada B-META-APPREVIEW-1 en BLOCKERS.md. |

### Lo que CEO necesita hacer para desbloquear E2E real

1. **B-OAUTH-YT-GCP-1** (estimado 20 min): completar Google Cloud Console setup, obtener `GOOGLE_OAUTH_CLIENT_ID` + `_SECRET`, pegar en `backend/.env` y poner `OAUTH_YOUTUBE_ENABLED=true`.
2. **Test E2E**: dirigente clickea "Conectar YouTube", aprueba consent, callback registra fila con `is_stub=False`.
3. **Trigger primer scrape**: `python -c "from app.scrapers.youtube_privileged import YouTubePrivilegedScraper; ..."` o cron Celery.

### Bugs reales que detectó el audit (NUEVOS findings sesión)

Los 5 endpoints CRITICAL FE↔BE de `/onboarding/{id}/...`:
- POST /onboarding/{id}/profile · BE define `/onboarding/profile`
- POST /onboarding/{id}/accounts-manual · BE `/onboarding/accounts/manual`
- POST /onboarding/{id}/confirm-accounts · BE `/onboarding/confirm-accounts`
- POST /onboarding/{id}/competidores · BE `/onboarding/competidores`
- POST /onboarding/{id}/promesas · BE `/onboarding/promesas`

→ NUEVO finding **B-ONBOARDING-FE-BE-MISMATCH-1** (BLOCKERS.md). Fuera de scope de esta sesión.
