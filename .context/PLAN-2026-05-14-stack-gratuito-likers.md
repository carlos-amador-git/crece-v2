# PLAN · Re-validación stack gratuito para LIKERS · 2026-05-14

## Contexto

En sesión 2026-05-13 (`EXPLORATORIO-MULTI-HERRAMIENTA-2026-05-13.md`) validamos
que `ensta`, `Scweet`, `yt-dlp`, `instaloader` son scrapers gratuitos con cobertura
de **POSTS y métricas agregadas** de perfil. Stack documentado en
`memory/reference_scraper_stack_2026_05_13.md`.

Pero NO probamos exhaustivamente si esos mismos scrapers exponen también
**LIKERS / REACTORS de un post específico** (lista nominal de quién dio like).

Hoy (2026-05-14) gastamos ~$11 en Apify para validar 8/13 watched de Saymi.
Si el stack gratuito ya puede dar esos likers, **Apify deja de ser necesario para
producción** (ahorro ~$50/mes en piloto + escalable a más dirigentes).

## Pregunta de investigación

> ¿El stack gratuito existente (Scweet, ensta+instaloader, yt-dlp, IG embed, FB cookies)
> puede extraer la **lista de usuarios que dieron like a un post específico**
> para cada red social donde Saymi tiene presencia?

## Criterio de éxito

Para cada red social ∈ {FB, IG, X, TT, YT}:
- ✅ ÉXITO: scraper gratuito retorna ≥1 reactor con (name + ID/url estable + reaction_type)
- ⚠️ PARCIAL: retorna nombres pero no IDs estables (igual que pfbid problem)
- ❌ FALLO: no expone likers / requiere auth no disponible / API bloqueada

## Plan — 5 fases secuenciales

### Fase 0 · Setup (15 min)

| Paso | Acción | Output |
|---|---|---|
| 0.1 | Confirmar versiones libs: `ensta`, `Scweet`, `instaloader`, `yt-dlp` en container | versiones logged |
| 0.2 | Inventariar credenciales gratuitas disponibles: `TWITTER_AUTH_TOKEN`, IG cookies CEO, FB cookies CEO Chrome profile | tabla de auth disponible |
| 0.3 | Elegir **1 post conocido por red** con reactors verificados (post 5057 FB tiene Guadalupe+Itzel+Mariel) | URLs target |

### Fase 1 · X / Twitter (Scweet 5.3) · 30 min

Hoy Scweet sólo expone `get_user_info`, `get_profile_tweets`, `get_followers`,
`get_following`, `search`. **No tiene método `get_likers` público.**

| R | Test | Cómo | Hipótesis |
|---|---|---|---|
| X.1 | Inspeccionar código fuente Scweet para endpoint `Favoriters` o `Likers` | `python -c "import inspect; from Scweet import Scweet; print(inspect.getsourcefile(Scweet))"` + grep | quizá tenga método interno no documentado |
| X.2 | Si X.1 falla: hit directo a `twitter.com/i/api/graphql/.../Favoriters` con `auth_token` cookie | curl/httpx con el auth_token de `@RafaRamos72` | el endpoint público existe pero requiere autorización; auth_token podría servir |
| X.3 | Validar contra 1 tweet conocido de Saymi en X (si tiene) o tweet propio | json output con liker IDs | ✅/❌ |

### Fase 2 · Instagram (ensta + instaloader) · 30 min

Memoria dice: `ensta Guest no follower list`. Pero ensta tiene modo `Host`
(con session) y instaloader tiene método `Post.get_likes()`.

| R | Test | Cómo | Hipótesis |
|---|---|---|---|
| IG.1 | Verificar si ensta v6+ tiene clase `Host` con `post.likers()` o similar | `dir(ensta)` post-upgrade si necesario | quizás expuesto en versión nueva |
| IG.2 | `instaloader.Post.from_shortcode(L, shortcode).get_likes()` con sesión guardada | requiere `INSTAGRAM_USERNAME/PASSWORD` env vars | método público de instaloader; bloqueado para no-amigos pero vale probar |
| IG.3 | IG `/embed/captioned/<shortcode>` HTML — parsear si embed expone IDs de likers o solo count | `curl https://www.instagram.com/p/<code>/embed/captioned/` + grep | likely solo count agregado |
| IG.4 | `instagram-private-api` lib alterna (más agresiva) — pip install + test | con credenciales burner | si las otras 3 fallan |

### Fase 3 · TikTok (yt-dlp + TikTok-Api) · 20 min

Memoria 2026-05-13 dice: yt-dlp da metadata + transcripción pero **sin
follower/liker list** (sin auth).

| R | Test | Cómo | Hipótesis |
|---|---|---|---|
| TT.1 | `yt-dlp --dump-json <post_url>` — revisar si JSON incluye `likes_count_user_ids` o similar | yt-dlp en container | solo conteo agregado, no lista |
| TT.2 | `TikTok-Api` lib con Playwright host + cookies | requiere host (B-26-03) | hay método `video.related_videos` pero no `liked_users` público |
| TT.3 | Endpoint TT público con cookies CEO | http GET con cookies | TT bloquea aggressive, descartable |

### Fase 4 · YouTube (yt-dlp + youtube_privileged) · 15 min

| R | Test | Cómo | Hipótesis |
|---|---|---|---|
| YT.1 | `yt-dlp --dump-json` de video — revisar si trae likers | yt-dlp | YT nunca expuso quién dio like (privacy desde 2010) |
| YT.2 | YouTube Data API v3 `videos.list?part=statistics` — count pero no lista | OAuth Saymi ya tenemos | confirma agregado-only |
| YT.3 | commentThreads ya validado — DA quién comenta (no quién likeó pero es engagement) | ya implementado en `youtube_privileged.py` | reuso, no nueva validación |

### Fase 5 · Facebook (cookies CEO + librerías custom) · 30 min

| R | Test | Cómo | Hipótesis |
|---|---|---|---|
| FB.1 | `facebook-graphql-scraper` con cookies de Chrome profile CEO | extract `cookies.txt`, pasar a la lib | la lib usa GraphQL endpoint; con cookies de cuenta amiga de Saymi sí trae lista |
| FB.2 | Playwright headless con cookies CEO → navegar post Saymi → scrollear modal "Reactions" | usar `chromium.launchPersistentContext` con Chrome profile | manual pero confiable; lento |
| FB.3 | Brightdata Web Unlocker proxy + cookies CEO | descartado por R1.6 en exploratorio 2026-05-13 (pages only) | NO |

### Fase 6 · Veredicto y decisión (30 min)

Output: `.context/EXPLORATORIO-LIKERS-STACK-GRATUITO-2026-05-14.md` con:
- Tabla resumen por red: lib · método · funcionó · output sample · costo
- Comparativa final stack-gratuito vs Apify-actual:
  - Si gratuito cubre 3+ redes: **migrar pipeline production**, declarar Apify deprecado para likers
  - Si gratuito cubre 1-2 redes: stack mixto (gratuito donde funcione, Apify donde no)
  - Si gratuito cubre 0 redes: Apify único path, documentar y dejar de explorar
- Decisión arquitectural en `.context/DECISIONS.md`

## Costo total estimado

- **$0** (stack gratuito + credenciales ya disponibles)
- **2-3 horas** de exploración focalizada
- Riesgo: tokens caducos (Scweet auth_token, IG cookies) — mitigación: pedir CEO refresh si necesario

## Salida concreta

Cuando termine cada fase, reporte breve con:
1. ¿Se obtuvo lista de likers? sí / no / parcial
2. Si sí: cuántos items, IDs estables sí/no, ejemplo de output
3. Si no: razón técnica (auth blocked, API removed, deprecation, etc.)
4. Recomendación: usar / no usar para producción

## Riesgos identificados

| R | Mitigación |
|---|---|
| auth_token Twitter expirado | pedir CEO refresh, validar al inicio Fase 1 |
| IG cookies CEO expiradas | usar burner account si existe, sino skip IG |
| FB cookies bloqueadas por session_check | Playwright headed con perfil Chrome real (lento pero funcional) |
| Libs deprecadas (ensta no actualizado en 6m) | tener fallback instaloader y registrar deprecation |

## Orden de ejecución sugerido

1. **Fase 1 (X)** primero — auth_token activo, alto valor para piloto
2. **Fase 5 (FB)** segundo — donde más pagamos hoy, mayor impacto si encuentra path gratuito
3. **Fase 2 (IG)** tercero — Saymi también tiene IG con engagement
4. **Fase 3 (TT)** y **Fase 4 (YT)** últimas — likely fail por privacy / API design

## ¿Procedemos? CEO confirma antes de empezar Fase 1.
