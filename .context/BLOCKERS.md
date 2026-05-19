# CRECE v2 — BLOCKERS

Esta es la fila de riesgos/bloqueos formalmente reconocidos pero **diferidos**.
Actualizar al abrir cualquier PR que toque el área del riesgo.

---

## Activos

### B-26-01 · Plan IA timeout Coolify — RESUELTO PARCIAL 2026-05-19

- **Origen:** Sesión 2026-05-12 noche, `/plan-ia/generate` con Ollama gemma3:12b cuelga ≥9 min en Coolify (host.docker.internal no llega).
- **Status:** 🟡 **RESUELTO PARCIAL.** Generación de planes ahora funciona offline vía `backend/scripts/regen_plan_dirigente.py` (Sprint F PLAN-2026-05-17 cerrado 2026-05-19). Stack: CC subprocess `claude --print --effort high` con fallback `gemini-clean --mode plan`. Persiste a `planes_ia` + `recomendaciones_plan_ia`.
- **Lo que NO se resuelve (decisión expresa D-1 CEO 2026-05-17):** el endpoint `/plan-ia/generate` sigue en 503. `llm_pipeline.py` Ollama-based NO se toca. Razón: D-PLAN-IA-CC-GEMINI-CLI-1 = generación offline por script standalone, no via API runtime.
- **Caso de uso piloto:** operador corre `nohup python backend/scripts/regen_plan_dirigente.py --dirigente-id N > log.log 2>&1 &` cuando el cliente pide un plan fresco. UI consume el plan recién insertado desde `planes_ia`.
- **Diferido a sesión dedicada:** tests pytest del script (script con deps externas LLM, mock no trivial).

### B-IG-DATACENTER-IP-1 · IG bloquea queries desde Docker

- **Origen:** Sesión 2026-05-13 noche, prueba E2E con `chatmx_oficial`.
- **Status:** 🔴 **CONFIRMADO en vivo.** `instaloader` aceptó login con `soporte@consultoriamd.com.mx`, guardó sesión, pero `Profile.from_username(L.context, 'instagram')` (cuenta oficial IG, siempre existe) retorna `ProfileNotExistsException`. Patrón idéntico al ya documentado para YT/TikTok desde container Docker.
- **Bloquea:** scraper privilegiado IG (lista followers + commenters cross-reference).
- **Caminos:** plan completo en `.context/PLAN-2026-05-14-tier2-ux-followers-ig.md` Sprint B (Brightdata proxy 1.5h o Apify wiring 1h).

### B-COMPETIDORES-MODELO-1 · Modelo `competidores` huérfano del pipeline

- **Origen:** Audit 2026-05-14 al intentar agregar Ivette + Susana para Saymi.
- **Status:** ⏸️ **DIFERIDO.** La tabla `competidores` (+ `competidor_social_profiles`) existe pero NO está conectada a ningún scraper. `social_posts` solo cuelga de `social_profiles` (dirigentes). El benchmarking real usa `dirigentes.competidor_directo_ids INT[]` apuntando a otros dirigentes (precedente Saymi.competidor_directo_ids={4} → Yesenia Nolasco como dirigente real).
- **Estado actual:** 7 competidores en BD: 5 originales (3 sin perfiles, 2 con handles solo metadata), 2 nuevos hoy (Ivette + Susana, partido='TBD' pendiente CEO).
- **Precedente funcional:** Pepe Monroy (dirigente id=57, partido='PAZ') tiene 25 posts + 110 comments full pipeline.
- **Sprint corto cuando se retome:** (a) migrar Ivette + Susana a `dirigentes` con `partido='COMPETIDOR_OAX'` o similar, link via Saymi.competidor_directo_ids; (b) decidir si tabla `competidores` se deprecia o se renombra a "directorio extendido" para metadata no-scrape.
- **Bloquea:** scrape comparativo Saymi vs Ivette/Susana hasta que se resuelva.

### B-META-APPREVIEW-1 · IG/FB privilegiados — DIFERIDO INDEFINIDO 2026-05-16

- **Origen:** sprint `/sprint-review` 2026-05-13 (PLAN-2026-05-13 S6).
- **Status:** ⏸️ **DIFERIDO INDEFINIDO 2026-05-16 (D-1.3 CEO).** Decisión: Meta App Review queda fuera de scope mientras Apify + scrapers públicos cubran el caso. Razones: (a) Graph API solo aplica a Pages/IG Business propias del dirigente, no a competidores que es el caso de mayor valor; (b) Apify cubre 80% del valor a costo marginal; (c) 4-6 semanas de trámite documental sin desbloquear caso de negocio concreto.
- **Re-evaluar SOLO si:** cliente pide webhooks tiempo real para SU propia Page, Apify cambia política/precios, o caso de negocio nuevo lo requiere.
- **No es bloqueante para piloto:** Apify (`apify_refresh_all.py`) cubre posts + comments IG/FB públicos sin fricción.

### B-CALENDARIO-PLANES-IA-1 · Integración efemérides → planes_ia diferida

- **Origen:** Sesión 2026-05-12 sprint pepe + calendario (S3.7 del plan).
- **Texto:** El plan original incluía cron mensual que generaría tareas tipo `efemeride_sugerida` en `plan_tareas` para cada dirigente. La lógica del cron + del modelo de plan_tareas requiere más diseño (¿qué efemerides priorizar? ¿solo viralidad alta? ¿con qué frecuencia?).
- **Status:** ⏸️ **DIFERIDO** a próxima sesión.
- **Mitigación:** los dirigentes pueden ver "Próximas fechas" en `/dashboard/calendario` y generar post on-demand. Funcional sin integración a planes_ia.

---

### ~~B-TWITTER-COMMENTS-1~~ · DESCARTADO 2026-05-12

Falso positivo. Apify actor de Twitter no captura comments, pero el stack tiene scripts complementarios: `backend/scripts/twscrape_tw_replies.py` y `backend/scripts/playwright_x_replies.py`. **BD tiene 1,029 comments de Twitter persistidos.** CEO corrigió 2026-05-12 noche.

---

### ~~B-CLAUDE-API-KEY-1~~ · DESCARTADO 2026-05-12

CEO clarificó 2026-05-12 noche: análisis se hacen vía Claude Code (yo), NO se requiere `CLAUDE_API_KEY` server-side en backend. Endpoint `/calendario/sugerir-post` queda con plantilla fallback como output legítimo y suficiente. NO es blocker.

---

### ~~B-FB-SCRAPER-1~~ · DESCARTADO 2026-05-12

Falso positivo de la sesión. Los scrapers locales del backend (`FacebookScraper` con Selenium/ChromeDriver, `InstagramScraper` con ensta/instaloader) son código **legacy** que NO se usa en producción. El stack real es `backend/scripts/apify_refresh_all.py` con Apify Actors. Verificado 2026-05-12 corriendo Apify para Pepe Monroy con éxito (10 posts FB + 37 comments, costo $0.11).

---

### ~~B-IG-SCRAPER-1~~ · DESCARTADO 2026-05-12

Idéntico caso a B-FB-SCRAPER-1. Apify cubre IG con `apify/instagram-post-scraper` que trae posts + `latestComments` embebidos. Verificado: 15 posts + 73 comments para Pepe Monroy, costo $0.07.

---

### ~~B-ER-SCALE-1~~ · RESUELTO 2026-05-12

Verificado vía SQL: `SELECT COUNT(*) WHERE platform='TWITTER' AND engagement_rate BETWEEN 0 AND 1 AND published_at < NOW() - INTERVAL '28 days'` → **0 posts**. El recálculo previo (D-ER-SCALE-1) ya cubrió todo el historial relevante. No hay posts en escala fracción que requieran normalización.

---

### B-23-01 · Downtime BD en piloto · riesgo no mitigado

- **Origen:** Gemini cross-audit 2026-04-23 sobre `PLAN-REVISADO.md` Sprint 23-B.
- **Texto original Gemini:** *"Ejecutar migraciones de Alembic (Sprint 23-B) en un entorno de producción (piloto) puede generar bloqueos de tabla. Esto requiere una ventana de mantenimiento programada."*
- **Status:** ✅ **MITIGADO evitando la migración.** Propuesta P1 (URL computada en schema sin migration) elegida sobre P2 (columna persistida).
- **Deuda residual:** Propuestas P2 (columna `url` persistida) y P3 (nullable counters para distinguir 0-real vs no-recolectado) documentadas en `frontend-review-2026-04-23/SPRINT-23B-INVESTIGACION.md`. Escaladas a §9.8 del 2026-05-20, con obligación de ventana de mantenimiento + plan de rollback al ejecutarse.

### B-23-02 · Fragilidad scrapers comment/share counts · riesgo reconocido

- **Origen:** Gemini cross-audit 2026-04-23.
- **Texto original Gemini:** *"Intervenir los scrapers para extraer comment_count y share_count requiere revalidación de límites de rate y estructuras de la plataforma origen (ej. Facebook/Twitter). Es un proceso inherentemente frágil que excede el tiempo estimado de 45 min y podría romper la recolección actual de datos del piloto."*
- **Status:** ⚠️ **DIFERIDO sin mitigación.** Los campos `comments`/`shares` siguen mostrando 0 en UI cuando el scraper no logra leerlos (ambigüedad 0-real vs no-recolectado). No se tocó código scraper en Sprint 23 — sería incompatible con piloto activo.
- **Impacto en piloto:** usuarios ven "0 comentarios" en posts donde sí hay comentarios reales que el scraper perdió. CEO ya lo señaló en F-23-05 con "aparecen cero comentarios".
- **Plan:** abordar dentro de §9.8 del 2026-05-20 junto con Propuesta P3 (nullable counters) para que BD distinga explícitamente los dos casos. Pre-requisito: inventario por plataforma de qué scrapers leen bien y cuáles no.

### B-23-03 · Motor sentimiento con afiliación no conectado al dashboard

- **Origen:** Findings F-23-01 + F-23-06 review CEO 2026-04-23.
- **Status:** 🟢 **MITIGADO 2026-04-25 vía reframe D-23-G'.** El KPI principal pasó de "Sentimiento Prom. flipeado" a "Actividad Política Alineada (% por target_politico)". El flip × -1 ya no se aplica · ya no necesitamos conectar la matriz 3-capas al `SentimentBadge` porque el KPI hero no usa polaridad. Plan reformulado: `.context/PLAN-D-23-G-actividad-alineada-2026-04-24.md`.
- **Mitigación previa interim (2026-04-23):** disclaimer role-aware en Tema Urgente · sigue vigente como contexto secundario.
- **Disenso D-23-G' resuelto:** la propuesta 4-fases con disenso CEO 2026-04-23 queda disuelta porque el reframe no requiere matriz v2/v3 ni clasificación humana.
- **Deuda residual:** backfill IA del catálogo histórico (~3,800 posts) en curso · piloto activo arranca con backfill parcial (30d window).

### B-23-04 · F-23-10/11 rewrite estructural diferido · 🟡 DEUDA POST-PILOTO

- **Origen:** CEO feedback 2026-04-23: *"F-23-10/11 dice CALIB pero el texto mismo reconoce patrón estructural pendiente. Eso no es cerrado, es cerrado-a-nivel-título."*
- **Status:** 🟡 **DEUDA POST-PILOTO 2026-05-17.** Cross-validación CEO + Gemini + Claude: NO entrar a backlog activo durante piloto. Sprint 23-D cerró renames de títulos (13 de 18 bloques). El patrón "qué mide / cómo te fue / qué hacer" queda pendiente para cuando el engagement loop esté estabilizado y se quiera escalar sin acompañamiento consultivo MD. Dirigentes piloto reciben acompañamiento que cubre el gap UX.
- **Re-activar SOLO si:** (a) cliente piloto reporta fatiga cognitiva grave con cards actuales, (b) onboarding sin acompañamiento se vuelve requisito.
- **Plan documentado:** `frontend-review-2026-04-23/BACKLOG-SPRINT-24.md` con 4 fases + 3 preguntas de arquitectura para sesión dedicada cuando llegue el momento.

### ~~B-23-06~~ · DESCARTADO 2026-05-12 · Máynez no nos ocupa

CEO clarificó 2026-05-12 noche: Máynez (id=7) no es prioridad para el piloto. No requiere scraping ni Plan IA. Queda como referencia rival (`competidor_directo_ids`) pero no se trabaja activamente.

### B-23-05 · Cloudflared tunnel rotatorio vs piloto activo · fragilidad del producto

- **Origen:** Diálogo CEO + Claude Code 2026-04-23 durante diagnóstico F0.1.
- **Status:** ⏸️ **DIFERIDO INDEFINIDO 2026-05-17 (CEO).** Decisión: "lo aguantamos. No tenemos cuenta de paga en CF y siempre es un retroceso el tema." Named tunnel requiere Cloudflare Zero Trust (gratis hasta 50 usuarios pero pidió tarjeta en evaluación previa) y CEO no quiere abrir esa puerta hoy. Convivimos con microcortes ~N segundos / hora del tunnel rotatorio.
- **Texto histórico:** El backend CRECE corre en `localhost:8002` del Mac Mini M4 expuesto vía `cloudflared tunnel --url http://localhost:8002 --no-autoupdate` (ad-hoc, URL rotatoria ~1h). LaunchAgent `com.mdconsultoria.crece-tunnel.plist` rota URL y auto-updatea `NEXT_PUBLIC_API_URL` en Vercel env vars.
- **Mitigación propuesta (diferida):** migrar a **named tunnel con hostname estable** (p.ej. `api-crece-dev.mdconsultoria-ti.org`). Requiere (1) CNAME en Cloudflare DNS hacia tunnel UUID, (2) config.yml + credentials JSON en Mac Mini, (3) modificar LaunchAgent para apuntar a named, (4) fijar `NEXT_PUBLIC_API_URL` en Vercel a nuevo hostname estable. Estimado 30-45 min.
- **Re-evaluar SOLO si:** (a) CEO acepta cuenta paga CF, (b) microcortes generan reclamos concretos del piloto, (c) Better Stack monitor externo se vuelve obligatorio.
---

### B-26-01 · Plan IA timeout en Coolify CPU · DEMO BLOCKER

- **Origen:** sprint-implement Sprint 1.3 ejecutado 2026-04-26 04:57 UTC.
- **Status:** 🔴 **ABIERTO · CRÍTICO.** Task `bf41a412` `plan_ia_generate_async` para `dirigente_id=8` con prompt 13438 chars → **SoftTimeLimitExceeded en 540s** (9 min) sin completar la generación. Coolify CPU-only no termina un plan completo dentro del time_limit.
- **Trade-off comprometido:** la decisión CEO 2026-04-25 de migrar Ollama a Coolify para "liberar RAM Mac Mini" sacrifica performance al punto de **romper la generación de planes**. El comentario en docker-compose decía "~3-7 min plan completo" pero la realidad medida es ≥9 min sin terminar.
- **Implicación demo:** sin Plan IA generable, la feature principal del piloto Ballesteros queda inoperante. Los 2 planes existentes (id=19 del 2026-04-25 18:33 y id=20 del 2026-04-26 01:54) son del runtime anterior — no se pueden generar nuevos sin resolver esto.
- **Opciones (decisión CEO requerida):**
  1. ~~Revertir backend a Mac local~~ · ❌ **NO viable** · Claude borró `gemma3:12b` del Mac en sesión previa · Mac local no tiene el modelo.
  2. **Modelo más pequeño en Coolify** · `gemma3:4b` (~2.5GB) procesa más rápido, sacrificando calidad de plan
  3. **Comprimir prompt** · 13438 → ≤5000 chars (reducir contexto de posts/historial). Investigar qué se puede quitar sin degradar calidad.
  4. **Subir time_limit a >1h** · CEO 2026-04-26 OK con esperar · plan toma ~30-60 min en Coolify CPU. Workaround inmediato: ejecutar pipeline directo via `docker exec` (sin time_limit Celery). Ya en curso 2026-04-26 05:15 UTC.
  5. **Re-instalar gemma3:12b en Mac** · CEO decisión explícita necesaria · trade-off RAM Mac Mini.
  6. **Híbrido** · planes pre-gen + Coolify para queries on-demand más cortas.

- **Acción inmediata 2026-04-26 05:15 UTC:** Plan IA Ballesteros lanzado vía `docker exec ... default_pipeline.generate(...)` sin time_limit · CEO autorizó esperar >1h. Background task `bxqiorqi0` monitoreado. Si termina con éxito, valida opción 4 (Coolify CPU paciente) sin necesidad de cambiar arquitectura.
- **Bloquea:** demo piloto Ballesteros · Sprint 1.3 cierre · feature Plan IA en general.

---

## Resueltos

### B-VIOLENCIA-TAGS-1 · Categorización tipos violencia política · ❌ DESCARTADO 2026-05-17

Cross-validación CEO + Gemini + Claude: `severity_dist` LOW/MEDIUM/HIGH + lista top comments violentos ya implementados en `CardB18` (`frontend/src/components/diagnostico_tier2/cards.tsx:808-870`) y `violencia_politica_service.compute()` cubren ~80% del valor estratégico — equipo legal puede detonar protocolos de contención con la información actual. Sub-clasificar por tipo (insultos vs amenazas vs violencia de género) sería perfeccionismo NLP sin demanda explícita del cliente piloto. CEO no recordaba haberlo solicitado al revisar el blocker.

### B-26-03 · yt-dlp + Playwright no instalados en container · ✅ CERRADO 2026-05-16

Vía Q-5 sprint-implement. yt-dlp 2026.03.17 en `/install/bin/yt-dlp`, Chromium SO en `/usr/bin/chromium`, `CHROME_BIN` correcto, `tiktok.py:200-211` reusa Chromium SO (ahorra 973MB). 7/7 regression guards en `tests/scrapers/test_container_binaries.py`.

### B-26-02 · `get_scraper(platform)` lowercase mismatch · ✅ CERRADO 2026-05-16

Vía Q-1 sprint-implement. `app/scrapers/base.py:94` → `scrapers.get(platform.lower())`. 19/19 tests `tests/scrapers/test_base.py`.

### B-ONBOARDING-FE-BE-MISMATCH-1 · Endpoints onboarding path-scoped · ✅ CERRADO 2026-05-16

Vía Q-4 sprint-implement. 5 endpoints `POST /api/v1/onboarding/{dirigente_id}/...` con `assert_dirigente_access`. Legacy preservados como alias (recom Gemini). 6/6 tests `tests/onboarding/test_onboarding_path_scoped.py`. Pendiente menor: wizard FE no implementado actualmente.

### B-FOLLOWERS-BOT-1 · Hook bot_detection en followers · ✅ CERRADO 2026-05-16

Vía Sprint B sprint-implement. `score_follower(handle, platform, profile)` en `app/services/bot_detection.py` threshold 0.70. Integrado en `youtube_privileged.upsert_subscribers`. Endpoint `POST /dirigentes/{id}/followers/rescan-bots` + query `only_real`. E2E Benjamin Jimenez (id=1, YT): bot_score=0.05, is_real=True. 6/6 tests.

### B-OAUTH-YT-CRYPTO-1 · Tokens OAuth cifrados pgcrypto · ✅ CERRADO 2026-05-16

Vía Q-3 sprint-implement. Migration `oc1_oauth_token_encryption.py` agrega `token_enc/refresh_token_enc BYTEA + crypto_version INT + encrypted_at TIMESTAMPTZ`. Helper `app/services/oauth_crypto.py` wrap `pii.encrypt_value/decrypt_value` (mismo precedente que `ciudadanos_legacy` D-DATA-02). Script standalone `scripts/encrypt_existing_oauth_tokens.py` migró 3/3 filas existentes. Pendiente menor: NULL-out `token_hash`/`refresh_token_hash` legacy (SQL provisto en script output).

### B-OAUTH-YT-STATE-1 · State OAuth firmado HMAC · ✅ CERRADO 2026-05-16

Vía Q-2 sprint-implement. `app/services/oauth_state.py` con `sign_state/verify_state` HMAC-SHA256 sobre `JWT_SECRET`. Payload `did + nonce(32B) + ts (max_age 600s)`. Callback `onboarding.py` rechaza state inválido con 302 + `?oauth_error=invalid_state:<reason>`. 10/10 tests cubren roundtrip, tampering, malformed, expirado.

### B-OAUTH-YT-GCP-1 · YT OAuth GCP setup · ✅ CERRADO 2026-05-13

CEO completó GCP project `crece-496212` + YouTube Data API v3 + OAuth client web + scopes `youtube.readonly` + `yt-analytics.readonly`. E2E validado: token id=2 `is_stub=False`, 1 sub real (`benjamin jimenez`) en social_followers.

### B-APIFY-CREDIT-EXHAUSTED-1 · Apify segunda cuenta · ✅ CERRADO 2026-05-14

CEO proveyó cuenta `Rafael Personal` (`emotional_tables` · `AhTBMXghtRWWD0kye` · email `raf.ramos.personal@gmail.com`). Token rotado en `.env` root, validado contra `/v2/users/me` HTTP 200. Token viejo (cuenta original agotada) queda comentado en `backend/.env.scraping-keys` para auditoría.

### B-23-07 · Refrescar scraping rezagados · ✅ CERRADO 2026-04-26

Vía sprint-implement Sprint 1.2 · 156 nuevos posts · `MAX(published_at)=2026-04-25 22:43`. Hero KPI "Actividad Alineada" deja de estar vacío Ballesteros + Piña (TW/IG actualizado).
