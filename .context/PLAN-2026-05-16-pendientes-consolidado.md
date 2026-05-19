# PLAN · 2026-05-16 · Pendientes CRECE v2 (consolidado · todo lo abierto)

## Origen

CEO pidió `/plan` exhaustivo de TODO lo pendiente para atender eficientemente sin perderse. Filosofía aplicada: **calidad > tiempo · eficiencia > tiempo**. Items agrupados por dominio técnico para minimizar context-switching, ordenados por riesgo al piloto.

Fuentes verificadas:
- `.context/PLAN-current.md` (NEXT-1/NEXT-2/NEXT-3)
- `.context/BLOCKERS.md` (16 blockers activos)
- `.context/PLAN-2026-05-14-watchlist-saymi.md` (Fase 1+2 pendientes)
- `.context/PLAN-2026-05-14-tier2-ux-followers-ig.md` (Sprint A+B+C pendientes)
- `.context/STATUS.md` (sprints dedicados S1/S3/S6 diferidos honestamente)
- Coordinación peer 2026-05-16 madrugada (gate endpoint Juan)

## Glosario de prefijos

- **D-x.x** · Decisión abierta (acción CEO antes que código)
- **S-x.x** · Sprint codificable (acción Linda)
- **B-XXX** · Blocker registrado (ver BLOCKERS.md)

---

## BLOQUE 1 — Decisiones abiertas (CEO action)

### D-1.1 · Gate endpoint `ingest-reactions-bulk` (helper Juan FB)
- **Origen:** coordinación peer 2026-05-16. Juan @ md-research entregó helper `fb_extract_reactors_for_crece(post_url)` validado 149/149 contra post Saymi.
- **Decisión:** luz verde / diferir / declinar el sprint endpoint.
- **Si luz verde:** S-8.1 (BLOQUE 8) se desbloquea.
- **Si declinas:** archivar helper Juan como "available, no consumer activo" — no se pierde, queda disponible.
- **Estimado decisión:** 5 min de tu lado.
- **Caveat empírico Juan 2026-05-16 07:37Z (importante para evaluar valor):**
  - Distribución posts Saymi (sample 25): **~80% sin reactors visibles** (text/video) · **~16% low-engagement** (2-4 reactors, FB no abre modal por threshold ≥5) · **~4% extraíble completo** (5+ reactors).
  - **Avatar URL siempre null** (restricción FB, no bug · no salvable sin follow-up request 149× por post = flag risk alto).
  - **Reaction timestamp no expuesto en modal** (FB no lo guarda en este surface).
  - **Implicación piloto:** valor real del endpoint depende de qué % de posts del corpus Saymi/Ivette/Susana cae en el ~4% extraíble. Si piloto muestra >30% low-engagement, re-evaluar (B2/B3 reverse-engineering GraphQL, hoy descartado).

### D-1.2 · Activación Reels Groq
- **Origen:** cierre 2026-05-15 (FASE 2 Reels).
- **Acción CEO:** (1) registrar console.groq.com (gratuito), (2) generar key `gsk_...`, (3) agregar `GROQ_API_KEY=gsk_...` a root `.env`, (4) `docker compose restart backend`.
- **Estimado:** 5 min · costo $0.
- **Verificación:** visitar `/dashboard/reels` → generar guión → 200 OK.

### D-1.3 · Decisión Meta App Review (B-META-APPREVIEW-1)
- **Origen:** Sprint OAuth 2026-05-13.
- **Acción CEO:** iniciar Meta Business Manager verification (4-6 sem).
- **Desbloquea:** scrapers IG/FB privilegiados con Graph API (alternativa a Brightdata proxy).
- **Sin urgencia:** Apify cubre interim.

### D-1.4 · Decisión modelo `competidores` (B-COMPETIDORES-MODELO-1)
- **Origen:** Audit 2026-05-14.
- **Decisión:** (a) migrar Ivette+Susana a `dirigentes` con `partido='COMPETIDOR_OAX'`, o (b) renombrar `competidores` a "directorio extendido" para metadata no-scrape, o (c) deprecar tabla.
- **Estimado decisión:** 15 min con `/gemini analyze`.

---

## BLOQUE 2 — Riesgo piloto operativo (mitigar primero)

### S-2.1 · B-23-05 · Named tunnel Cloudflare estable
- **Asignado CEO directo** (config UI Cloudflare + LaunchAgent · no es trabajo del agente).
- **Estimado:** 30-45 min CEO.
- **Pre-requisito de:** F0.1 Better Stack monitor externo.
- **Criterio aceptación:** `api-crece-dev.mdconsultoria-ti.org` resuelve 200 desde fuera del Mac · `NEXT_PUBLIC_API_URL` Vercel fija al hostname estable.

### S-2.2 · B-23-07 · Refresh scraping rezagados (mantenimiento)
- **Naturaleza:** sprint dedicado, no atomizable.
- **Pasos:** (1) lanzar scrapers de 8 dirigentes, (2) re-clasificar posts nuevos vía classifier `target_politico`, (3) actualizar snapshots `social_followers`.
- **Estimado:** 1-2h supervisado.
- **Criterio aceptación:** `MAX(published_at)` ≤7 días por dirigente para TW/IG/FB.

### S-2.3 · B-23-02 · Comments/shares ambigüedad 0 vs no-recolectado
- **Diferido §9.8 del 2026-05-20.**
- **Naturaleza:** requiere migration nullable counters + revisión scrapers (frágil contra piloto activo).
- **Estimado:** 2-3h + ventana mantenimiento.
- **Criterio aceptación:** UI distingue `0 reales` vs `no recolectado` con badge distinto.

---

## BLOQUE 3 — OAuth & Seguridad (preparación pre-piloto público)

### S-3.1 · B-OAUTH-YT-STATE-1 · HMAC firma state
- **Estimado:** 30 min.
- **Cambios:** `app/api/v1/endpoints/onboarding.py` (sign state con `JWT_SECRET` antes de redirect, verify en callback).
- **Criterio aceptación:** intentar modificar state suffix manualmente → callback rechaza con 400.
- **Test:** unit test que valida HMAC roundtrip + curl con state manipulado → 400.

### S-3.2 · B-OAUTH-YT-CRYPTO-1 · Tokens OAuth cifrados
- **Estimado:** 1h.
- **Cambios:** integrar `app.services.pii.encrypt_value` (pgcrypto) en `OAuthTokenByPlatform.token_hash` + `refresh_token_hash`. Precedente: `ciudadanos_legacy` (D-DATA-02).
- **Criterio aceptación:** SELECT directo a la tabla muestra `\x...` encriptado · `decrypt_value(token)` retorna plain.
- **Pre-requisito de:** primera fila `is_stub=False` en producción (hoy CEO ya tiene 1 fila real, riesgo bajo pero abierto).

### S-3.3 · B-ONBOARDING-FE-BE-MISMATCH-1 · Alinear endpoints onboarding
- **Estimado:** 1.5h (revisión + cambios bilaterales + smoke test).
- **Diagnóstico:** FE llama `POST /onboarding/{dirigenteId}/profile`, BE define ruta sin `{dirigenteId}` en URL (va en body). 5 endpoints divergentes total.
- **Decisión recomendada:** mantener `dirigente_id` en URL (más RESTful), refactor BE para aceptar como path param.
- **Criterio aceptación:** smoke test E2E del wizard onboarding desde frontend → BD upserts esperados.

### Batch S-3 total: ~3h en sesión propia (mismo dominio: auth + permisos).

---

## BLOQUE 4 — UI sistémica (alto valor UX · batch día completo)

Filosofía: estos 4 sprints comparten stack (Next.js + shadcn + Tailwind + tipografía). Batchear en sesión propia con energía fresca, no fragmentar.

### S-4.1 · S1 · Unificación 4 implementaciones KPI cards
- **Origen:** PLAN-2026-05-15 diferido honestamente.
- **Estimado:** 5-6h con CEO presente (revisar cada KPI antes de unificar).
- **Pre-requisito:** auditar las 4 implementaciones existentes con grep antes de proponer abstracción.
- **Criterio aceptación:** 1 componente `<KPICard>` consume 100% de los lugares · tsc clean · `npm run check:no-mocks` verde · screenshots before/after Playwright.

### S-4.2 · Sprint A · Tier 2 UX refactor (cards B11-B18)
- **Origen:** PLAN-2026-05-14-tier2-ux-followers-ig.md Sprint A.
- **Estimado:** ~3h.
- **Items concretos:** notas técnicas → tooltip · B14 disabled cuando calibrando · grid B14 con leyenda · botón "Activar Filtro" → switch global · empty state B16 → CTA "Registrar primera promesa" · B17 veda con borde animado · agrupación 3 zonas (Autenticidad / Narrativa / Legal-Riesgo).
- **Criterio aceptación:** screenshot before/after por card · CEO valida Vercel staging.

### S-4.3 · S3 · Mobile audit completo
- **Origen:** PLAN-2026-05-15 diferido honestamente.
- **Estimado:** 6-8h sprint propio.
- **Naturaleza:** audit todas las vistas en breakpoints sm/md → fixes Tailwind responsive.
- **Criterio aceptación:** Lighthouse mobile score ≥85 en /dashboard principal + /dashboard/aceptacion + /dashboard/seguidores.

### S-4.4 · S6 · Onboarding UI admin competidores
- **Origen:** PLAN-2026-05-15 diferido honestamente.
- **Estimado:** ~4h.
- **Depende de:** D-1.4 (modelo `competidores`) resuelto antes.
- **Criterio aceptación:** admin puede crear/editar/eliminar competidores desde UI sin tocar BD.

### Batch S-4 total: ~17-20h · 2-3 sesiones dedicadas.

---

## BLOQUE 5 — Infra scrapers

### S-5.1 · Sprint B · Followers IG vía Brightdata proxy
- **Origen:** PLAN-2026-05-14-tier2-ux-followers-ig.md Sprint B.
- **Estimado:** 2.5h.
- **Cambios:** `instaloader.context._session.proxies` → `brd.superproxy.io:22225` · `instagram_privileged.py` scaffold paralelo a `youtube_privileged.py`.
- **Criterio aceptación:** `Profile.from_username(L.context, 'instagram')` retorna >0 followers · `chatmx_oficial.get_followers(limit=50)` ≥1 fila real · UI `/dashboard/seguidores` muestra IG.

### S-5.2 · B-26-02 · `get_scraper(platform)` lowercase fix
- **Estimado:** 5 min sprint nuevo.
- **Cambio:** `app/scrapers/base.py:97` `scrapers.get(platform)` → `scrapers.get(platform.lower())`.
- **Criterio aceptación:** `scrape_all_profiles()` no falla con `ValueError: No scraper available for platform: TWITTER`.
- **Test:** unit test del registry con uppercase + lowercase.

### S-5.3 · B-26-03 · yt-dlp + Playwright en container backend
- **Estimado:** 30 min sprint setup.
- **Cambios:** Dockerfile backend agregar `pip install yt-dlp playwright && playwright install chromium`.
- **Criterio aceptación:** `docker exec backend yt-dlp --version` OK · `playwright launch chromium` OK.
- **Desbloquea:** scrapers YT + TT vía container (hoy `MANUAL_HOST_INGEST` los esquiva).

### S-5.4 · Sprint C · Vercel deploy + UI validación followers YT
- **Origen:** PLAN-2026-05-14-tier2-ux-followers-ig.md Sprint C.
- **Estimado:** 30 min.
- **Pasos:** `cd frontend && vercel deploy --prod` · validación visual login Piña → `/dashboard/seguidores` → `benjamin jimenez · YouTube`.
- **Estado:** desfasado · ya hubo deploy Vercel 2026-05-15 con Reels · revisar si sigue pendiente o se hizo en paralelo.

### Batch S-5 total: ~3.5h (Sprint B carga el peso).

---

## BLOQUE 6 — NLP & Data quality (diferidos largos)

### S-6.1 · B-VIOLENCIA-TAGS-1 · Categorización violencia política
- **Diferido a sprint NLP dedicado.**
- **Naturaleza:** clasificador adicional sobre comments ya marcados · reuso framework 3-capas existente.
- **Estimado:** 2-3h.
- **Criterio aceptación:** card B18 muestra desagregado por tag (insultos / amenazas / violencia de género) cuando % sube.

### S-6.2 · B-FOLLOWERS-BOT-1 · Hook bot_detection
- **Naturaleza:** integrar scraper inicial a `app/api/v1/endpoints/bot_detection.py` para poblar `social_followers.bot_score`.
- **Estimado:** 1-1.5h.
- **Criterio aceptación:** filtro "Solo seguidores reales" funcional en frontend.

### S-6.3 · B-CALENDARIO-PLANES-IA-1 · Efemérides → planes_ia
- **Estado:** diferido, requiere diseño previo (qué efemerides priorizar, qué frecuencia).
- **Mitigación actual:** dirigentes ven "Próximas fechas" en `/dashboard/calendario` y generan post on-demand.
- **Naturaleza:** cron mensual + modelo plan_tareas type `efemeride_sugerida`.
- **Estimado:** 2-3h + decisión arquitectural previa.

### S-6.4 · B-23-04 · F-23-10/11 rewrite estructural
- **Origen:** PARCIAL desde sprint 23-D (sólo renames cerrados).
- **Diferido a:** sesión dedicada con 3 preguntas arquitectura.
- **Documentado en:** `frontend-review-2026-04-23/BACKLOG-SPRINT-24.md`.

---

## BLOQUE 7 — Plan IA refactor (cuando se prenda)

### S-7.1 · Refactor `_call_ollama` → subprocess CC + Gemini CLI
- **Origen:** D-PLAN-IA-CC-GEMINI-CLI-1 (DECISIONS.md 2026-05-15).
- **Estado hoy:** plan_ia HTTP 503 honesto · button disabled · code preservado con `DEAD MODULE` header.
- **Naturaleza:** sprint propio · reemplazar `_call_ollama` en `llm_pipeline.py` por subprocess CC + Gemini CLI según mandato CEO (NO API external · Ollama off hasta VPS mejor).
- **Estimado:** 3-4h sprint propio.
- **Criterio aceptación:** `POST /api/v1/plan-ia/generate` retorna 200 con plan generado · timeout configurable · costo monitoreado.
- **Cerrado vía pause:** B-26-01 (timeout Coolify CPU) queda mitigado mientras paused.

---

## BLOQUE 8 — Watchlist Saymi (depende D-1.1)

### S-8.1 · Endpoint `ingest-reactions-bulk` + ingesta E2E
- **Pre-requisito:** D-1.1 luz verde.
- **Estimado:** 1-2h.
- **Cambios:** (1) migration JSONB `evidence_metadata` en `watched_like_events`, (2) endpoint `POST /api/v1/aceptacion/watched-profiles/ingest-reactions-bulk` que hashea con `COMMENT_AUTHOR_SALT` local, upsert WatchedProfile + insert WatchedLikeEvent, (3) test E2E con `high.json` de Juan (149 reactors Saymi reales).
- **Criterio aceptación:** POST array Juan-format → BD muestra 149 reactors upserted · WatchedLikeEvent count = 149 · author_hash format consistente con scrapers existentes.

### S-8.2 · Fase 1 watchlist Saymi · scrape ampliado Ivette + Susana
- **Pre-requisito:** D-1.4 (modelo `competidores`) resuelto.
- **Estimado:** 1.5h.
- **Pasos:** crear competidoras en directorio elegido + scrape FB Apify (cuenta `Rafael Personal`, $5 free).

### S-8.3 · Fase 2 watchlist Saymi · UI tab "Perfiles Observados"
- **Pre-requisito:** S-8.1 + S-8.2 completos.
- **Estimado:** 3-4h.
- **Cambios:** endpoints CRUD watched profiles · analytics `/api/v1/aceptacion/watched/{id}/engagement` · UI tab + CTA sugerencias auto.
- **Criterio aceptación:** CEO ve perfiles observados de Saymi con engagement comparativo vs lista cliente_seed.

---

## Orden recomendado de ejecución (eficiencia primero)

### Orden por riesgo + dependencias:

1. **Decisiones CEO (BLOQUE 1)** — 5-15 min cada una · NADA depende de código nuestro · CEO decide en cualquier momento.
2. **BLOQUE 2 piloto operativo** — quitar riesgo activo del piloto antes que features nuevas.
   - S-2.1 (CEO directo) + S-2.2 (Linda 1-2h) → sesión corta.
3. **BLOQUE 3 OAuth/Seguridad** — batch día completo (~3h) · pre-piloto público.
   - S-3.1 + S-3.2 + S-3.3 misma sesión.
4. **BLOQUE 5 Infra scrapers críticos** — items pequeños primero (S-5.2 5 min · S-5.3 30 min) · luego S-5.1 si IG es prioridad.
5. **BLOQUE 4 UI sistémica** — 2-3 sesiones dedicadas · NO atomizar.
   - Sesión A: S-4.1 KPI cards (5-6h).
   - Sesión B: S-4.2 Tier 2 UX refactor (3h).
   - Sesión C: S-4.3 Mobile audit (6-8h).
   - Sesión D (post-D-1.4): S-4.4 Onboarding admin (4h).
6. **BLOQUE 8 Watchlist Saymi** (post-D-1.1 + post-D-1.4) — sesión propia ~6h total.
7. **BLOQUE 7 Plan IA refactor** — sprint propio cuando CEO marque prioridad.
8. **BLOQUE 6 NLP diferidos largos** — al final · no urgentes.

### Total estimado por bloque:

| Bloque | Sprints | Estimado Linda | Estimado CEO |
|---|---|---|---|
| 1 Decisiones | D-1.1 a D-1.4 | 0 | ~30 min total |
| 2 Piloto | S-2.1, S-2.2, S-2.3 | 3-5h | 45 min |
| 3 OAuth | S-3.1, S-3.2, S-3.3 | ~3h | 0 |
| 4 UI sistémica | S-4.1 a S-4.4 | 17-20h | presencia validación |
| 5 Infra scrapers | S-5.1 a S-5.4 | ~3.5h | 0 |
| 6 NLP diferidos | S-6.1 a S-6.4 | 7-10h | 0 |
| 7 Plan IA refactor | S-7.1 | 3-4h | 0 |
| 8 Watchlist Saymi | S-8.1 a S-8.3 | 5-7h | 0 |
| **TOTAL** | **22 items** | **~45-55h** | **~75 min** |

---

## Lo que NO está en este plan (out of scope explícito)

- Features nuevas no listadas (ej: WhatsApp Campaign Manager, Smart Canvassing, CRM Político de Fase 2).
- Refactor estructural BD sin §9.8.
- Cualquier item descartado en BLOCKERS (~~B-TWITTER-COMMENTS-1~~, ~~B-FB-SCRAPER-1~~, ~~B-IG-SCRAPER-1~~, etc.).
- Coordinación con peers distintos a Juan (helper FB).

## Próximo paso inmediato

**Esperando decisión CEO sobre BLOQUE 1** (D-1.1, D-1.2, D-1.3, D-1.4). Cada una desbloquea trabajo distinto sin overlap. Pueden decidirse en paralelo.

Sin decisión CEO, Linda queda en standby — no procede a código por la regla "decisiones que comprometen trabajo" (memoria proyecto).
