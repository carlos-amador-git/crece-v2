# Scraping Máynez (id=7) · ejecución 2026-04-24

**Plan origen:** `.context/PLAN-recuperacion-post-incidente-2026-04-21.md`
**Contract de output:** no aplica · los scrapers internos escriben directo al ORM `SocialPost` (18 columnas, limpio post-3d6fe3f).

## Contexto

Jorge Álvarez Máynez (id=7) · Coordinador Nacional Movimiento Ciudadano · ex-candidato presidencial 2024. Entró al piloto sin datos scrapeados · todos los demás dirigentes activos + shadow ya tienen histórico.

Handles oficiales verificados 2/2 fuentes en `.context/HANDLES-MAYNEZ-2026-04-23.md` para 4 de 5 plataformas. YouTube marcado `is_confirmed=false` por solo 1/2 fuentes (canal legacy `JorgeAlvarezMaynez`).

## Paso 1 · Bootstrap social_profiles (completado 2026-04-24)

```sql
INSERT INTO social_profiles (dirigente_id, platform, handle, url, ..., is_confirmed)
VALUES
  (7, 'TWITTER',   'AlvarezMaynez',      'https://x.com/AlvarezMaynez',                  ..., true),
  (7, 'INSTAGRAM', 'alvarezmaynez',      'https://instagram.com/alvarezmaynez',          ..., true),
  (7, 'FACEBOOK',  'AlvarezMaynez',      'https://facebook.com/AlvarezMaynez',           ..., true),
  (7, 'TIKTOK',    'alvarezmaynez',      'https://tiktok.com/@alvarezmaynez',            ..., true),
  (7, 'YOUTUBE',   'JorgeAlvarezMaynez', 'https://youtube.com/user/JorgeAlvarezMaynez',  ..., false);
```

Ids insertados: 32 (X) · 33 (IG) · 34 (FB) · 35 (TT) · 36 (YT). `data_source='manual_onboarding'`.

## Paso 2 · Adaptación `scripts/scrape_new_dirigentes.py` (completado · timebox 5 min cumplido)

Parametrizado con dos args nuevos:
- `--dirigente-id INT` · modo single dirigente (override de legacy TARGET_DIRIGENTES)
- `--skip-nlp` · **OBLIGATORIO** post-3d6fe3f hasta que F1.1 corra

Backward compat preservado: sin args corre legacy (4 shadow MORENA por nombre).

### Razón de `--skip-nlp` obligatorio (D-OPS-07 contexto)

`scripts/reprocess_nlp` invoca código NLP que lee/escribe columnas dropeadas por la migración destructiva `3d6fe3f1660d_add_resultados_electorales_seccion_2024.py` (2026-04-18):

- `social_posts.tono_discurso`
- `social_posts.target_politico`
- `social_posts.sentimiento_politico_ajustado`
- `social_posts.nlp_model_version`
- `social_posts.controversy_score`
- `social_posts.toxicity_score`
- `social_posts.llm_*` (razon, modelo, processed_at)
- `dirigentes.rol_politico`

**Post-F1.1 (cuando Joy + revisor §9.8 restauren schema):** correr el paso NLP faltante con:

```bash
docker exec crece-backend python -m scripts.reprocess_nlp
```

Esto procesará los posts de Máynez ingestados en esta sesión + todos los posts acumulados sin NLP desde 2026-04-18.

## Paso 3 · Scraping incremental · _(en ejecución)_

Comando:
```bash
docker exec crece-backend python -m scripts.scrape_new_dirigentes --dirigente-id 7 --skip-nlp
```

Target mínimo: 50 posts totales · 20 por plataforma como umbral FODA suficiente (reporte flag `⚠️ INSUFICIENTE FODA (<20)` implementado en Summary del script).

### Resultado · FALLIDO · 0 posts ingestados · exit code 1

Ejecución: `2026-04-24T05:22:54Z` · duración ~4 min hasta crash · `bg task bq0bvw941`.

| Plataforma | Posts | Duración | Estado | Razón |
|---|---:|---|---|---|
| TWITTER | 0 | ~2 min | ❌ | asyncio nested loop bug |
| INSTAGRAM | 0 | ~1 min | ❌ | ensta 3× + fallback instaloader sin creds |
| FACEBOOK | 0 (1 extraído pero no persistido) | ~1 min | ❌ abort | chromedriver crash |
| TIKTOK | — | — | ⏭ skipped | nunca ejecutado · abort por FB |
| YOUTUBE | — | — | ⏭ skipped | idem |

**Ninguna plataforma cumple umbral FODA (≥20 posts).** Máynez plan IA bloqueado hasta re-scraping exitoso.

---

## Stack traces completos por plataforma

### Twitter · bug nested asyncio

**Versiones relevantes:** `Scweet 5.2`, `twscrape 0.17.0`

**Síntoma:** 4 intentos Scweet + 4 intentos twscrape · todos fallan idéntico:
```
WARNING app.scrapers.twitter: Scweet attempt 0 failed for @AlvarezMaynez: 
  asyncio.run() cannot be called from a running event loop
/app/app/scrapers/twitter.py:164: RuntimeWarning: coroutine 'Scweet.aget_profile_tweets' 
  was never awaited
WARNING app.scrapers.twitter: Scweet attempt 1 failed: asyncio.run() cannot be called from a running event loop
WARNING app.scrapers.twitter: Scweet attempt 2 failed: asyncio.run() cannot be called from a running event loop
WARNING app.scrapers.twitter: Scweet attempt 3 failed: asyncio.run() cannot be called from a running event loop
WARNING app.scrapers.twitter: Scweet exhausted retries for @AlvarezMaynez
INFO app.scrapers.twitter: Scweet returned 0 tweets for @AlvarezMaynez (account may be empty)
```

Luego profile info · mismo patrón en `twitter.py:201` y `twitter.py:613`:
```
/app/app/scrapers/twitter.py:613: RuntimeWarning: coroutine 
  'TwitterScraper._fetch_profile_twscrape' was never awaited
```

**Hipótesis causa raíz:**
El outer runner del script es `asyncio.run(main(...))` (línea final de `scripts/scrape_new_dirigentes.py`). Dentro de `main()` async se llama `scraper.scrape(profile_id=...)` que es un wrapper sync que internamente invoca `asyncio.run(self.ascrape(...))`. Python 3.12+ lanza `RuntimeError: asyncio.run() cannot be called from a running event loop` cuando se intenta nested.

El script funcionó en 2026-04-11 con los 4 shadow MORENA · posible que el container tenía Python 3.11 en ese momento y se actualizó silenciosamente a 3.12+ en rebuild.

**Fix propuesto (post-F1.1 con Joy):**
Opción A: refactorizar `scraper.scrape()` para exponer `ascrape()` async nativo · main.py awaits directo.
Opción B: en `scripts/scrape_new_dirigentes.py` reemplazar `asyncio.run(main())` por orquestación sync tradicional.

---

### Instagram · `ensta` rompió + credenciales `instaloader` ausentes

**Versiones relevantes:** `ensta 5.2.9`, `instaloader 4.15.1`

**Síntoma:**
```
WARNING app.scrapers.instagram: ensta failed for @alvarezmaynez (attempt 1/3): 
  'NoneType' object has no attribute 'follower_count'
WARNING app.scrapers.instagram: ensta failed (attempt 2/3): 'NoneType' object has no attribute 'follower_count'
WARNING app.scrapers.instagram: ensta failed (attempt 3/3): 'NoneType' object has no attribute 'follower_count'
INFO app.scrapers.instagram: Falling back to instaloader for @alvarezmaynez
ERROR app.scrapers.instagram: instaloader fallback also failed for @alvarezmaynez: 
  instaloader fallback requires INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD environment variables
ERROR app.scrapers.instagram: Failed to fetch stats for @alvarezmaynez: 
  'NoneType' object has no attribute 'follower_count'
```

**Config env del container (confirmado):**
```
INSTAGRAM_USERNAME: NOT_SET
INSTAGRAM_PASSWORD: (empty)
```

**Hipótesis causa raíz:**
- `ensta` devuelve `None` cuando Instagram sirve login-wall (no rate-limit · no 404 · devuelve HTML sin JSON embedido) → `None.follower_count` → AttributeError
- `instaloader` fallback requiere auth que nunca se configuró en `.env` del container
- `@alvarezmaynez` es perfil público verificado de Máynez · debería ser scrapable

**Fix propuesto (post-F1.1):**
A. Agregar `INSTAGRAM_USERNAME` + `INSTAGRAM_PASSWORD` a `.env` (account burner · no personal)
B. Evaluar si `ensta` tiene bug contra perfiles verificados recientes · upgrade lib o switch a Apify/Brightdata
C. Validar que el manejo de `None` en `ensta` levante excepción semántica (no `AttributeError` silencioso)

---

### Facebook · chromedriver crash (Selenium)

**Versiones relevantes:** `selenium 4.8.3`, `selenium-wire 5.1.0`, `webdriver-manager 4.0.2`, `facebook-page-info-scraper` (version no exhibido)

**Síntoma:**
```
INFO app.scrapers.facebook: curl-cffi extracted 1 posts for handle=AlvarezMaynez
WARNING facebook_page_info_scraper.facebook_page_info_scraper: retrying to scrape link...
INFO WDM: ====== WebDriver manager ======
INFO WDM: Get LATEST chromedriver version for google-chrome
INFO WDM: About to download new driver from https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip
INFO WDM: Driver has been saved in cache [/app/.wdm/drivers/chromedriver/linux64/114.0.5735.90]
Error setting up webdriver. Message: Service /app/.wdm/drivers/chromedriver/linux64/114.0.5735.90/chromedriver unexpectedly exited. Status code was: -5
```

**Config container:**
- Chromedriver descargado: `114.0.5735.90` (release 2023) · cache en `/app/.wdm/drivers/chromedriver/linux64/114.0.5735.90/`
- Chrome/Chromium instalado: `/usr/bin/chromium` (versión actual 2026 probablemente v120+)
- **Mismatch mayor versiones:** chromedriver v114 vs chromium v120+ → signal SIGBUS/SIGSEGV (status code -5 en macOS/linux mapea a SIGKILL o similar)

**Hipótesis causa raíz:**
`webdriver-manager 4.0.2` tiene URL hardcoded `https://chromedriver.storage.googleapis.com/114.0.5735.90/` (storage legacy Google deprecado · ahora usa `chromefordevtesting`). Siempre baja v114 viejo sin importar qué versión de Chromium tiene el container.

**Fix propuesto (post-F1.1):**
A. Upgrade `webdriver-manager` a versión que soporta Chrome for Testing API (>= 4.5.x)
B. O fijar chromedriver manualmente compat con chromium del container (override WDM)
C. O cambiar `facebook-page-info-scraper` por puro `curl-cffi` (que SÍ extrajo 1 post · evidencia que el parser básico funciona sin Selenium)

---

### TikTok + YouTube · no ejecutados

El script aborta con exit 1 tras el crash del webdriver FB · TT + YT nunca se intentaron. Bugs potenciales no evaluados.

---

## Versiones completas del stack (para referencia del fix post-F1.1)

```
ensta                      5.2.9
instaloader                4.15.1
playwright                 1.58.0
Scweet                     5.2
selenium                   4.8.3
selenium-wire              5.1.0
TikTokApi                  7.3.3
twscrape                   0.17.0
webdriver-manager          4.0.2
yt-dlp                     2026.3.17
```

Container: `crece-backend` · bind mount `/Users/marxchavez/Projects/crece-v2/backend → /app`.

## Siguiente paso (post-scraping exitoso · dependiente de F1.1 + fix stack)

1. **F1.1 Schema restauración** (pendiente Joy + revisor §9.8)
2. **Fix stack scrapers** (ver BACKLOG ticket dedicado · requiere Joy)
3. **Re-ejecutar** `docker exec crece-backend python -m scripts.scrape_new_dirigentes --dirigente-id 7 --skip-nlp`
4. **Correr `reprocess_nlp`** sobre posts Máynez
5. **Generar FODA** (`generate_diagnostico_dirigentes.py --dirigente-id 7 --provider ollama`)
6. **Generar Plan v3** (`generate_planes_v3_from_diagnostico.py --dirigente-id 7`)

Referencia completa en `.context/PLAN-recuperacion-post-incidente-2026-04-21.md` F1.1.
