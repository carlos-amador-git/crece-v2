# Exploratorio Multi-Herramienta · 2026-05-13

## Objetivo

Re-evaluar todas las herramientas de scraping probadas con las **credenciales completas del CEO** (5 cuentas: YT/IG/FB/X/TT) para identificar qué combinaciones funcionan HOY desde container Docker y desde host Mac Mini.

## Cuentas de prueba (todas del CEO · 2026-05-13)

| Red | Handle/identidad | Auth disponible |
|-----|------------------|-----------------|
| YouTube | `mdsamca2025@gmail.com` | OAuth real (token id=2 BD) |
| Instagram | `chatmx_oficial` (login `soporte@consultoriamd.com.mx`) + `marxitoc` (personal) | user+password |
| Facebook | `marx.chavez.1` (perfil personal) | cookies `c_user` + `xs` |
| Twitter/X | `@marxito_123` | `TWITTER_AUTH_TOKEN` (cookie) |
| TikTok | `flowey_md` | user+password |

## Matriz consolidada (22+ herramientas)

Status legend: ✅ funciona · ❌ no · ⚠️ parcial · ⏸️ diferido · 🔍 a probar HOY

| # | Herramienta | Plataforma | Auth | Status histórico | Hoy con creds CEO | Costo |
|---|-------------|-----------|------|------------------|-------------------|-------|
| 1 | scrapetube v2.6 | YT | ❌ ninguna | ✅ | 🔍 | $0 |
| 2 | yt-dlp v2026.3.17 | YT | ❌ | ✅ | 🔍 | $0 |
| 3 | OAuth real Google | YT | ✅ | ✅ HOY | ✅ Token id=2 + 1 sub real | $0 |
| 4 | ensta v5.2.9 Guest | IG | ❌ | ✅ (Piña test 2026-04-05) | 🔍 contra `marxitoc` | $0 |
| 5 | instaloader v4.15 sin login | IG | ❌ | ❌ 403 | ❌ confirmado HOY | $0 |
| 6 | instaloader v4.15 con login | IG | ✅ user+pass | ❌ datacenter IP block (HOY) | 🔍 desde host Mac Mini | $0 |
| 7 | OAuth Meta IG | IG | ✅ App Review | ⏸️ 4-6 sem | ⏸️ | $0 |
| 8 | IG /embed/captioned/{shortcode} | IG | ❌ | ✅ posts individuales | 🔍 | $0 |
| 9 | facebook_page_scraper v5 | FB | ❌ | ❌ bug selenium-wire | ❌ no fix disponible | $0 |
| 10 | facebook-scraper (kevinzg) | FB | ❌ | ❌ abandonado | ❌ | $0 |
| 11 | Brightdata Dataset FB posts | FB | ✅ token BRD | ✅ scripts en archive | 🔍 contra `marx.chavez.1` | bandwidth |
| 12 | OAuth Meta FB Pages | FB | ✅ App Review | ⏸️ 4-6 sem | ⏸️ | $0 |
| 13 | Scweet v5.2 | X | ✅ auth_token | ✅ Piña validado | 🔍 contra `@marxito_123` | $0 |
| 14 | twscrape v0.13 | X | ✅ pool de cuentas | ⚠️ requiere setup | 🔍 con `TWITTER_AUTH_TOKEN` | $0 |
| 15 | twikit v2.3.3 | X | ✅ user+pass+email | ❌ KEY_BYTE error | ❌ | $0 |
| 16 | httpx syndication X | X | ❌ | ❌ 429 | ❌ | $0 |
| 17 | X publish.x.com/oembed | X | ❌ | ✅ tweets individuales | 🔍 contra tweets propios | $0 |
| 18 | TikTok-Api v7.3.2 (Playwright) | TT | ❌ | ⚠️ Playwright bloqueado Docker | 🔍 desde host con login `flowey_md` | $0 |
| 19 | ScraperAPI TikTok comments | TT | ✅ API key (¿hay?) | Script existe | 🔍 verificar API key | $$$ |
| 20 | yt-dlp TikTok | TT | ❌ | Sin probar | 🔍 | $0 |
| 21 | Apify (todos los actors) | Multi | ✅ token | ⚠️ SIN CRÉDITO (B-APIFY-CREDIT-EXHAUSTED-1) | ⏸️ hasta renovación | $5/mes free |
| 22 | Brightdata Dataset API | Multi | ✅ token | ✅ varios scripts | 🔍 | bandwidth |
| 23 | Brightdata Web Unlocker | Multi proxy | ✅ token | Sin probar | 🔍 con instaloader desde container | bandwidth |
| 24 | Playwright local Mac Mini | Multi | varía | Sin usar | 🔍 (MANUAL_HOST_INGEST pattern) | $0 |

## Tests en ejecución (sprint 2026-05-13)

### Ronda 1 · Container Docker (rápidos, $0, baja invasividad)

| # | Test | Cmd | Resultado | Findings |
|---|------|-----|-----------|----------|
| R1.1 | Scweet 5.3 contra `@marxito_123` | `Scweet(auth_token).get_user_info + get_profile_tweets + get_followers` | ✅ **PERFECT** | Trae perfil completo, tweets reales (`"alchoholimetro"`), **lista granular de followers (@pabsito · 142)**. **Es lo que Saymi necesita.** $0. |
| R1.2 | ensta Guest contra `marxitoc` + `chatmx_oficial` | `Guest().profile(handle)` + `posts(handle)` | ✅ **YES** | Profile completo (87 followers `marxitoc`, posts con likes/comments). **NO follower list** (eso requiere login). $0. |
| R1.3 | scrapetube + yt-dlp canal CEO | — | ⏭️ Skip · CEO dijo no tiene YT activo | — |
| R1.4 | IG /embed/captioned contra post `C28ukenL-8o` | `curl /embed/captioned/` | ✅ 200 OK, 91KB HTML con post embed | Útil para posts individuales · parsing HTML necesario para extraer caption/likes |
| R1.5 | X oEmbed contra `@marxito_123` | `publish.twitter.com/oembed` | ⚠️ Solo widget HTML, no contenido | Cubre Scweet · descartar para CRECE |
| R1.6 | Brightdata Dataset FB perfil CEO | `gd_lkaxegm826bjpoo9m5` + URL `marx.chavez.1` | ⚠️ `error_code: dead_page` | Dataset BRD requiere **Pages**, no perfiles personales. FB personal sigue gateado · Meta App Review único path real. |
| R1.7 | twscrape | _no probado · Scweet ya cubre_ | — | — |
| R1.8 | TikTok-Api con `flowey_md` desde container | Playwright launch | ❌ Chromium not installed in container | Confirma B-26-03 · necesita host o instalar Chromium en image |
| R1.9 | **yt-dlp TikTok** contra `@flowey_md` | `yt-dlp --skip-download --print-json` | ✅ Trae JSON con video IDs + formats + metadata | **REVELACIÓN:** path $0 sin auth sin Playwright, funciona en container. Cubre TT públicos sin tocar host. |

### Ronda 2 · Host Mac Mini (requiere reorganizar arquitectura — IP residencial)

| # | Test | Notas |
|---|------|-------|
| R2.1 | instaloader login `chatmx_oficial` desde host | Esperamos IG no bloquee IP residencial CEO |
| R2.2 | TikTok-Api con Playwright host + login `flowey_md` | Requiere Chromium en host |
| R2.3 | Brightdata Web Unlocker proxy desde container | Si R2.1 falla, usar BRD proxy en instaloader |

### Ronda 3 · OAuth real

| # | Test | Estado |
|---|------|--------|
| R3.1 | OAuth YouTube + scrape subs/comments | ✅ Hoy 2026-05-13 · benjamin jimenez capturado |
| R3.2 | OAuth Meta IG | ⏸️ gateado App Review |
| R3.3 | OAuth Meta FB Pages | ⏸️ gateado App Review |

---

## Veredicto consolidado del exploratorio 2026-05-13

| Red | Stack ganador $0 hoy desde container | Cubre caso Saymi? |
|-----|--------------------------------------|-------------------|
| **YouTube** | OAuth real + scraper privilegiado (validado HOY) | ✅ followers + commenters cross-reference (visible privacy) |
| **Twitter/X** | **Scweet 5.3** con `TWITTER_AUTH_TOKEN` (validado en R1.1) | ✅ followers + tweets + reply tree |
| **Instagram** | ensta Guest (profile + posts) + IG /embed/captioned (post individual) | ⚠️ Posts/comments públicos · NO follower list. Para followers necesita auth + IP residencial (B-IG-DATACENTER-IP-1) |
| **TikTok** | **yt-dlp** sin auth (revelación R1.9) | ⚠️ Posts públicos · sin auth no hay follower list. Con auth requiere host (B-26-03) |
| **Facebook** | Brightdata Dataset solo funciona en **Pages**, no perfiles | ❌ Personal gateado · espera Meta App Review |

### Hallazgos sorpresa

1. **`yt-dlp` cubre TikTok desde container** sin auth ni Playwright. No estaba documentado en ningún veredicto previo del proyecto. Falta validar comments depth.
2. **`Scweet 5.3` API cambió** vs versión que usaba `Scweet/user.py:get_user_information` — ahora es `Scweet(auth_token=...).get_user_info(['handle'])`. Hay que adaptar `backend/app/scrapers/twitter.py` (que usa `Scweet(auth_token=...)` pero llama `client.user_info` que probablemente no existe en 5.3).
3. **Brightdata FB requiere Pages** — para perfil personal del CEO, no aplica. Saymi sí tiene Page Diputada, sí debería funcionar.
4. **`env_file` del container solo lee root `.env`** — `backend/.env` no se carga. Sincronización requerida cada vez que se agregan creds (corregido en commit final del día).

### Stack recomendado por red (post-exploratorio)

| Red | Producción | Fallback |
|-----|-----------|----------|
| YT | OAuth real (dirigente conecta) | scrapetube + yt-dlp (sin auth, públicos) |
| X | Scweet 5.3 con auth_token CEO/burner | publish.twitter.com/oembed (tweets individuales) |
| IG | ensta Guest (posts/comments) + futuro Meta App Review (followers) | IG /embed/captioned (post individual) |
| TikTok | yt-dlp (sin auth) | TikTok-Api desde host con flowey_md (followers, futuro) |
| FB | Brightdata Pages para Pages reales · Apify cuando regrese crédito | Selenium host con cookies CEO (FB personal) |

### Próximos pasos

- Adaptar `backend/app/scrapers/twitter.py` a la API nueva de Scweet 5.3.
- Documentar `yt-dlp TikTok` como path canónico en `_archive` o crear `tiktok_yt_dlp.py`.
- Plan IG follower list: probar `ensta` Authenticated mode (con login) desde container — si IG no banea (cuenta nueva en datacenter IP), tendríamos path $0 sin proxy. Si banea, escalar a Brightdata Web Unlocker.
- Crear nuevo dirigente CEO de prueba en BD para mezclar OAuth YT + Scweet X sin contaminar dirigente Piña.
