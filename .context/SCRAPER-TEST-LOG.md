# CRECE v2.0 — Log de Pruebas de Scrapers
## Fecha: 2026-04-05
## Objetivo: Probar herramientas reales contra perfiles de Piña/Solano
## Regla: ZERO mocks. Si no funciona, se documenta y se pasa a la siguiente.

---

## Perfiles de prueba
- Alejandro Piña: Twitter @Alejandro_Pinha, IG @alejandro.pinha, FB alejandropinamedina
- Rafael Solano: IG @rafasolanoperez, LinkedIn rafael-solano-perez

## Resultados

| # | Herramienta | Plataforma | Funciona? | Datos obtenidos | Notas |
|---|------------|------------|-----------|-----------------|-------|
| 1 | scrapetube v2.6 | YouTube | SI | 5 videos reales Piña | Sin API key, gratis |
| 2 | instaloader v4.15 | Instagram | NO | 0 | 403 Forbidden, requiere auth en 2026 |
| 3 | twscrape v0.13 | Twitter | NO | 0 | 0 cuentas en pool, requiere auth |
| 4 | httpx syndication | Twitter | NO | 0 | 429 Rate limit |
| 5 | facebook_page_scraper v5 | Facebook | NO | 0 | Bug selenium-wire (blinker._saferef) |
| 6 | Advanced-Twitter-Scraper | Twitter | NO | 0 | Clonado. CSS selectors de 2018 (.js-stream-item), X migró a React. DESCARTADO |
| 7 | instagram-media-scraper (ahmedrangel) | Instagram | N/A | — | Node.js, requiere cookies IG. No Python. DESCARTADO |
| 8 | yt-dlp v2026.3.17 | YouTube | SI | 2/3 videos con metadata completa | Views, likes, comments, description, duration |
| 9 | media-scraper (elvisyjlin) | Multi | NO | 0 | Clonado. Último commit 2019. Selenium + selectors obsoletos. DESCARTADO |
| 10 | youtube-scrapy-scraper | YouTube | N/A | — | Clonado. Scrapy + proxy SDK. Más pesado que scrapetube+yt-dlp. Sin valor agregado |
| 11 | scraping_media | Multi | N/A | — | No encontrado como repo público, referencia de Reddit |
| 12 | twikit v2.3.3 | Twitter | NO | 0 | "Couldn't get KEY_BYTE indices", requiere auth |
| 13 | **ensta v5.2.9** | **Instagram** | **SI** | **Profile + 5 posts reales** | **SIN AUTH, modo Guest, datos completos** |

---

## GANADORES (funcionan hoy, sin auth, sin API key)

### 1. scrapetube (YouTube)
- pip install scrapetube
- Busca videos por keyword, extrae IDs
- Gratis, sin API key

### 2. yt-dlp (YouTube metadata)
- pip install yt-dlp
- Metadata completa: views, likes, comments, description, duration, channel
- Complementa scrapetube (IDs → metadata)

### 3. ensta (Instagram) *** DESCUBRIMIENTO CLAVE ***
- pip install ensta (+ moviepy<2 para fix)
- Modo Guest: perfil completo + posts SIN AUTENTICACIÓN
- Datos reales obtenidos de @alejandro.pinha:
  - Full name: Alejandro Piña Medina
  - Followers: 3,290
  - Following: 666
  - Total posts: 668
  - Category: Politician
  - Posts con: caption, likes, comments, timestamp, shortcode

---

## BLOQUEADOS (requieren auth o tienen bugs)

### Twitter/X — Todas las opciones requieren auth
- twscrape: necesita cuentas en pool
- twikit: necesita username+password+email
- httpx syndication: rate-limited (429)
- Advanced-Twitter-Scraper: no es pip, solo repo Selenium
- Conclusión: Twitter en 2026 NO se puede scrapear sin auth. Opciones: X API Pay-Per-Use ($10/mes) o crear cuenta dedicada.

### Facebook — Librería principal rota
- facebook_page_scraper: bug de dependencia selenium-wire/blinker
- facebook-scraper (kevinzg): abandonado
- Conclusión: Facebook requiere Apify o fix del bug de selenium-wire.

---

## Repos clonados — Ronda 2 (Twitter)

| # | Repo | Lenguaje | Último commit | Resultado |
|---|------|----------|--------------|-----------|
| 14 | **Scweet v5.2** | Python (pip) | **2026-04-03** | **FUNCIONA — tweets + perfil + followers** |
| 15 | x-twitter-scraper (Xquik) | Skill/API | 2026-04-06 | API de pago ($20/mes), no scraper |
| 16 | twitter-scraper (convocation) | Node.js | 2026-03-31 | Descartado — no es Python |
| 17 | selenium-twitter-scraper | Python | 2025-04-12 | Descartado — Selenium pesado, Scweet es mejor |
| 18 | TweetScraperR | R | — | Descartado — no es Python |
| 19 | imperatrona/twitter-scraper | Go | — | Descartado — no es Python |
| 20 | bakimane/Twitter-scrapper | Python | 2024-07-22 | Descartado — wrapper de twscrape |
| 21 | gmellini/twitter-scraper | Python | 2023-02-14 | Descartado — 3 años sin update |
| 22 | actor-twitter-scraper | Node.js | 2019-12-02 | Descartado — 7 años sin update |

### Scweet — datos reales obtenidos de @Alejandro_Pinha:
- Followers: 3,674 | Following: 1,616 | Tweets: 9,185
- Blue verified: True | Location: Distrito Federal, México
- Tweets con: text, timestamp, likes, retweets, comments, media, URL
- Requiere: auth_token de cookie de X.com (NO API key, NO cuenta dedicada)

---

## Stack FINAL post-pruebas (22 herramientas probadas)

| Plataforma | Herramienta ganadora | Auth necesaria | Costo |
|------------|---------------------|----------------|-------|
| **Instagram** | **ensta v5.2.9** (Guest mode) | Ninguna | $0 |
| **YouTube** | **scrapetube + yt-dlp** | Ninguna | $0 |
| **Twitter/X** | **Scweet v5.2** | Cookie auth_token | $0 |
| Facebook | Apify free tier (pendiente) | Token Apify | $0-5/mes |
| TikTok | TikTok-Api v7.3.2 (pendiente) | Playwright | $0 |
