# PLAN · 2026-05-14 · Watchlist Saymi (Excel + competidoras FB)

## Origen

CEO entregó:
- `Perfilles 2026.xlsx` con 13 perfiles FB (lista de la Lic. Saymi).
- 2 URLs FB de competidoras directas (resueltas a `IvetteMoranDeMurat` + `susanaharpiturribarria`).

Pregunta de la Lic.: ¿cómo participan estos 13 (+2 competidoras) en redes? — comentarios, fechas, frecuencia. FB primario, luego donde Saymi tenga más presencia.

## Pivot vs PLAN-2026-05-14-tier2-ux-followers-ig.md

Este plan **no reemplaza** el de Tier 2 + IG followers — lo **interrumpe** porque la solicitud de la Lic. es nueva y vino con datos concretos. El plan original sigue activo después.

## Hechos verificados en BD (audit 2026-05-14)

- Saymi = `dirigente_id=3`, MORENA, Oaxaca, `org_id=2`.
- 5 social_profiles registrados: FB `saymipinedavelasco` (114K), IG `@saymipinedavelasco` (12.4K), TT `@saymipineda` (20.1K), X `@saymipinedav` (8.9K), YT 581.
- Posts scrapeados (al 2026-05-08): TIKTOK 1157, TWITTER 119, INSTAGRAM 80, FACEBOOK 62, YOUTUBE 30.
- Comments: TIKTOK 80, INSTAGRAM 80, FACEBOOK 14, TWITTER 5, YOUTUBE 0.
- `social_comments.author_hash` = `SHA256(f"{platform}:{commenter_id}:{SALT}")` (one-way; commenter_id es ID numérico de la plataforma, no handle).
- `social_followers` para Saymi: 0 filas.
- Competidoras Ivette + Susana: NO existen en `competidores`.
- Los 13 handles del Excel: NO están en `social_followers`.

## Fase 0 — Match diagnóstico (HOY · sin código nuevo · sin Apify)

**Objetivo:** responder "¿cuántos del Excel + competidoras ya aparecen comentando en lo scrapeado de Saymi?". Es solo diagnóstico — no concluye sobre audiencia, solo sobre cobertura del scraping actual.

### Pasos

1. **Resolver 15 handles → FB user IDs (numéricos).**
   - 13 handles del Excel + `IvetteMoranDeMurat` + `susanaharpiturribarria`.
   - Método: `curl https://www.facebook.com/{handle}` con cookies del CEO (`FACEBOOK_C_USER`, `FACEBOOK_XS` ya en `.env`). Parsear `entity_id` del HTML.
   - Fallback si curl falla: usar `mcp__brightdata__scrape_as_html` o Apify minimalista.
   - **Criterio done:** tabla con 15 filas `(handle, fb_user_id, display_name, status: ok/blocked/private)`.

2. **Hashear cada user ID + match contra BD.**
   - Para cada user ID resuelto: `SHA256(f"FACEBOOK:{user_id}:{SALT}")`.
   - SQL: `SELECT * FROM social_comments WHERE author_hash IN (...) AND parent_post_id IN (posts de Saymi FB)`.
   - **Criterio done:** lista de matches `(handle, post_id, post_url, comment_published_at, comment_content)`.

3. **Reporte breve al CEO.**
   - Tabla: `handle | fb_user_id | found | n_comments | last_comment`.
   - Guardado en `.context/AUDIT-WATCHLIST-SAYMI-FB-2026-05-14.md`.
   - **Criterio done:** CEO ve el resultado y decide si pasamos a Fase 1.

### Tiempo: ~20 min · Costo: $0

### Riesgos

- FB puede bloquear curl masivo → mitigar con delay 2s entre requests + cookies.
- Algún perfil puede ser privado / borrado → marcar `status=private` y seguir.
- 13/14 IDs pueden NO estar en los 14 author_hashes scrapeados → **eso no es conclusión**, solo diagnóstico de cobertura.

---

## Fase 1 — Setup datos (solo si CEO da luz verde post-Fase 0)

**Decisión a tomar después de Fase 0:** ¿el sistema ya tiene "lo suficiente" o necesitamos scrape ampliado de Saymi + scrape nuevo de Ivette/Susana?

### Pasos tentativos (no ejecutar sin OK)

1. Crear competidoras Ivette + Susana en `competidores` + `competidor_social_profiles`.
2. Scrape FB de Ivette + Susana via Apify actor (`apify/facebook-pages-scraper` para posts, `apify/facebook-posts-scraper` para comments). Cuenta `Rafael Personal` con $5 free.
3. Re-scrape FB de Saymi solo si Fase 0 muestra cobertura insuficiente (e.g., posts viejos sin todos los comments).

### Tiempo estimado: ~1.5h · Costo: <$1

---

## Fase 2 — Modelo + UI (solo si CEO confirma post-Fase 1)

**Decisión arquitectural pendiente:** tabla nueva `watched_profile` vs columna `is_watched` + `watch_tags` en `social_followers`. Decidir post-Fase 1 con `/gemini` cross-audit.

### Pasos tentativos

1. Migration + modelo + endpoints CRUD watched profiles.
2. Endpoint analytics: `/api/v1/aceptacion/watched/{id}/engagement`.
3. UI tab "Perfiles Observados" en `/dashboard/aceptacion/fantasmas`.
4. CTA "Sugerencias auto" (autores frecuentes no observados).

### Tiempo estimado: ~3-4h

---

## Lo que NO hacemos en este plan

- NO crear modelos sin haber visto el resultado de Fase 0.
- NO scrape de Ivette/Susana hasta saber si vale la pena ampliar.
- NO modificar el plan de Tier 2 UX — sigue después de cerrar este.
- NO inventar interpretaciones sobre "audiencia de Saymi" o "engagement" — solo reportar hechos verificables.

## Próximo paso inmediato

Esperar luz verde del CEO para ejecutar Fase 0 paso 1 (resolver 15 handles → FB user IDs).
