# Exploratorio · Stack gratuito para extracción de LIKERS · 2026-05-14

## Objetivo

Validar si el stack gratuito existente (Scweet, ensta+instaloader+instagrapi,
yt-dlp, Playwright con cookies CEO) puede extraer **lista nominal de usuarios
que dieron like/reaction a un post** en cada red social donde los dirigentes
de CRECE tienen presencia. Si sí: eliminamos dependencia recurrente de Apify
para FB reactions ($5-50/mes hoy escalable a >$50/mes con más dirigentes).

## Resumen ejecutivo · 1 párrafo

**Stack gratuito SÍ funciona para FB e IG con login**, los dos casos de
mayor valor. **X, TT y YT no son técnicamente accesibles** para listar
likers — no por limitación de stack sino por **decisión de plataforma**
(privacy/API design). Por lo tanto Apify para FB reactions es **opcional,
no obligatorio**, en producción · podemos usar Playwright + sesión CEO
para FB y `instagrapi` con cuenta soporte para IG, ambos a $0/mes.

## Resultados por fase

### Fase 0 · Setup ✅

| Item | Status |
|---|---|
| ensta · instaloader 4.15.1 · Scweet 5.3 · yt-dlp · scrapetube 2.6.0 instalados | ✓ |
| TWITTER_AUTH_TOKEN configurado (cuenta burner) | ✓ |
| INSTAGRAM_USERNAME=`soporte@consultoriamd.com.mx` configurado | ✓ |
| Posts target identificados por red | ✓ |

### Fase 1 · X / Twitter ❌

**Veredicto**: **X removió el endpoint público `Favoriters`/`Likers` en 2023**
(decisión Elon Musk). Ningún scraper público (gratis o pago) puede listar
quién dio like a un tweet específico desde fuera. Solo `retweeters` está
accesible vía `twscrape` (con auth).

| Test | Resultado |
|---|---|
| `Scweet.get_likers` o método similar | ❌ no expuesto en API · solo `favorite_count` agregado |
| `twscrape` métodos relacionados | ✓ tiene `retweeters` (retweet list) · ❌ NO tiene `liking_users` |
| Endpoint `https://twitter.com/i/api/graphql/.../Favoriters` directo | ❌ removido por X en 2023 |

### Fase 2 · Instagram ✅

**Veredicto**: **Funciona con `instagrapi` autenticado**. Mejor que Apify
para volumen: `media_likers(media_pk)` retorna `pk` numérico estable +
`username` + `full_name`. Con cuenta soporte logueada captura hasta 100
likers/post sin rate-limit visible.

| Test | Resultado |
|---|---|
| ensta Guest mode | ❌ no expone likers (solo perfil/posts/stats) |
| ensta Host mode | ❌ clase `Host` no disponible en versión instalada |
| `instaloader.Post.get_likes()` | ❌ 401 Unauthorized "Please wait" · query_hash hardcoded deprecated |
| `instagrapi.Client.media_likers()` con login | ✅ **100 likers** del post Saymi `DXZtWo1jhNF` (253 totales) · pk estable + username |
| `/embed/captioned/<shortcode>` HTML | ⏸️ no probado (instagrapi resolvió la pregunta) |

**Output sample**:
```
@nelly.danett   · Nelly Zorrilla    · pk=7125658372
@merarygijon    · Merary Gijon      · pk=65889187336
@pazlopezgomez  · Paz López Gómez   · pk=7078415122
@win_santiago   · Win Santiago      · pk=636350236
```

### Fase 3 · TikTok ❌

**Veredicto**: **TT no expone lista de likers a nadie**. Ni TT API oficial
ni scrapers públicos exponen quién dio like a un video. yt-dlp captura solo
`like_count` agregado.

| Test | Resultado |
|---|---|
| `yt-dlp --dump-json` de post TT | ⚠️ container IP bloqueada · pero el JSON nunca incluye liker list según docs |
| `yt-dlp` perfil TT (entries) | ❌ "Your IP address is blocked from accessing this post" |
| `TikTok-Api` con Playwright host | ❌ no tiene método `get_likers_of_video` |
| Endpoint TT público con cookies CEO | ❌ TT no expone liker list endpoint público |

### Fase 4 · YouTube ❌

**Veredicto**: **YouTube nunca expuso lista de likers** (privacy decision
desde 2010). yt-dlp captura `like_count`. YouTube Data API v3
`videos.list?part=statistics` retorna stats agregadas pero NO lista de
usuarios que dieron like. Único acceso: `commentThreads` (quién comenta,
ya implementado en `youtube_privileged.py` vía OAuth).

| Test | Resultado |
|---|---|
| `yt-dlp --dump-json` video YT | ⚠️ trae `like_count` solo · sin lista |
| YouTube Data API `videos.list` | ❌ stats agregadas, no liker list |
| YouTube Data API `videos.getRating` | ⚠️ solo retorna el rating del propio usuario logueado |

### Fase 5 · Facebook ✅ (con caveats)

**Veredicto**: **Playwright + storage_state capturado de tu sesión CEO
funciona**. Extrae reactors del post con `reaction_type` por tab del popup.
Limitaciones operativas:
- Solo capta los públicos (~25-40% del total por privacy FB)
- Orden depende de relevancia al viewer logueado (CEO Marx)
- Scroll necesita refinamiento para llegar a todos los visibles
- storage_state expira ~30 días · re-captura manual o auto-relogin

| Test | Resultado |
|---|---|
| `facebook_scraper.get_reactors` | ❌ lib deprecada · FB cambió endpoint `m.facebook.com/ufi/reaction/profile/browser` |
| Playwright + perfil Chrome (copia) | ⚠️ falla por SingletonLock + cookies stale |
| Playwright + storage_state (login en vivo) | ✅ extrae reactors visibles · 10/27 capturados con scroll de 8 iter |
| Selector con tabs (Me gusta/Me encanta/Me divierte) | ✅ identifica reaction_type por tab |

**Output sample**:
```
Kevin Ausencio Jiménez Zarate  · profile.php?id=61571339841713 · reaction=like
Carlos Fernandez                · profile.php?id=61583936147305 · reaction=like
Jonathan Miguel Aquinbo Martinez · /ven.tengodulces                · reaction=like
Josh FG                         · /FriasCardiel                   · reaction=like
Andréé López                    · /edd.soe                        · reaction=like
[...]
```

### Fase 6 · Veredicto consolidado

| Red social | Likers gratis? | Lib/método | Calidad |
|---|---|---|---|
| **FB** | ✅ con login CEO | Playwright + storage_state | Parcial (público + ordenado por viewer) |
| **IG** | ✅ con login burner | `instagrapi.media_likers()` | **Mejor que Apify** (100 likers + pk estable) |
| **X** | ❌ no path | — | Plataforma removió endpoint 2023 |
| **TT** | ❌ no path | — | Plataforma no expone |
| **YT** | ❌ no path | — | Plataforma nunca expuso |

## Decisión arquitectural

### Para producción · CRECE Electoral

**Recomendación inmediata**: **stack mixto**

| Red | Path productivo | Costo | Fallback |
|---|---|---|---|
| **FB** | Apify (`scraper_one/facebook-reactions-scraper`) primario · Playwright Nivel 1 complemento gratuito | $0-50/mes Apify pool · $0 Playwright | Si Apify cambia pricing → Playwright queda |
| **IG** | `instagrapi` con cuenta soporte | **$0** (sustituye necesidad de Apify IG) | Si IG bloquea la cuenta → cuenta burner secundaria |
| **X** | Apify Scweet ya cubre posts + followers · likers NO ACCESIBLES | $0 | Aceptar limitación de plataforma |
| **TT** | yt-dlp (posts + transcripción) · likers NO ACCESIBLES | $0 | Aceptar limitación |
| **YT** | youtube_privileged + OAuth (subscribers visible + comments) · likers NO ACCESIBLES | $0 | Aceptar limitación |

### Implicaciones para CRECE Negocios

Fuera de scope de esta exploración, pero hallazgos útiles:
- `instagrapi` puede aplicar a scraping de clientes potenciales por hashtag
  local (zona Saymi + hashtags de turismo, gastronomía, etc.)
- Playwright + login flow del CEO sirve para acceder a páginas FB de
  competencia (con consentimiento del dueño del negocio cliente, vía
  cuenta de admin de la página)
- Para reviews de Google Maps, Tripadvisor, etc. usar Apify
  `apify/google-maps-reviews-scraper` o equivalentes (fuera de scope)

## Próximas acciones recomendadas

| # | Acción | Esfuerzo | Valor |
|---|---|---|---|
| 1 | Migrar pipeline IG de Apify→`instagrapi` con cuenta soporte (ahorra ~$0-5/mes por dirigente) | 1 día | Alto · $0 recurrente IG |
| 2 | Refinar scroll de Playwright FB para capturar 100% de reactors públicos visibles | 2-3h | Alto · complemento gratuito a Apify FB |
| 3 | Implementar auto-relogin de FB para storage_state cuando expira (cada 30 días) | 1 día | Medio · evita intervención manual |
| 4 | Documentar veredicto X/TT/YT en `.context/DECISIONS.md` para evitar re-exploración | 30 min | Bajo · evita perder tiempo en limitaciones de plataforma |
| 5 | Esperar respuesta de claude.ai con prompt enviado (estrategia scraper propio Nivel 2/3) antes de decidir mayor inversión | — | — |

## Costos finales del exploratorio

- **$0** en stack gratuito (validación Fase 1-4 + Playwright Fase 5)
- **$0.0103** en Apify (pruebas easyapi/scrapio fallidas)
- **Tiempo**: ~3h (objetivo cumplido dentro de presupuesto del plan)

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| Cuenta `soporte@consultoriamd.com.mx` se banea de IG | Crear 2-3 cuentas burner como pool · rotar |
| FB detecta automation en Playwright y banea cuenta CEO | Usar cuenta secundaria distinta · NO la personal del CEO |
| storage_state expira → producción cae | Auto-relogin headless · monitoring de last_successful_run |
| `instagrapi` queda deprecada como instaloader.get_likes | Mantenimiento ocasional · 1-2 forks alternativos disponibles |

## Memoria persistente actualizada

- `reference_apify_trials_humano.md` (existente · validado)
- `reference_fb_likes_public_ceiling.md` (existente · actualizado con corrección de hipótesis privacy)
- **Nuevo**: `reference_stack_gratuito_likers_2026_05_14.md` (a crear)
