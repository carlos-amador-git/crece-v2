# Comparativo de Herramientas de Scraping — Enfoque Facebook

**Fecha:** 2026-04-13
**Contexto:** CRECE v2 necesita extraer posts de paginas publicas de Facebook para 6 dirigentes politicos.
**Problema:** Las librerias open-source (kevinzg/facebook-scraper, facebook-page-scraper) estan rotas en 2026. Nuestro scraper Playwright+GraphQL intercept saca 4-10 posts por pagina. Necesitamos mas volumen.

## Cuadro Comparativo

| # | Herramienta | FB Dedicado | Datos FB | Free Tier | Python | Precio Min | Headless | Veredicto |
|---|------------|-------------|----------|-----------|--------|-----------|----------|-----------|
| 1 | **Apify** | SI — actor FB Pages Scraper | Posts, likes, comments, shares, timestamps, imagenes | $5/mo credito | `apify-client` (pip) | $49/mo o pay-per-use | SI (cloud) | **RECOMENDADO #1** — plan original, SDK listo |
| 2 | **Crawlbase** | SI — endpoint dedicado FB, JSON estructurado | Posts, likes, comments, shares, followers, page info | 1,000 requests | `crawlbase` (pip) | $29/mo | SI (API) | **RECOMENDADO #2** — mejor relacion precio/valor |
| 3 | **Brightdata** | SI — collectors FB Pages, Posts, Marketplace | Posts, likes, shares, author, timestamps, imagenes | Trial (match deposit) | `brightdata` (pip) | $1.50/1K records | SI (cloud) | **RECOMENDADO #3** — mas completo, pay-per-use |
| 4 | **PhantomBuster** | SI — Phantom FB Profile + Post Likers | Profile info, about, FB ID, engagement via Phantoms | 14 dias trial | REST API (no SDK) | $69/mo | SI (cloud) | Caro. Requiere cookie FB. Free plan inutil (10 rows CSV) |
| 5 | **ScraperAPI** | NO — solo proxy+render HTML | Raw HTML (parser custom necesario) | 5,000 requests | `scraperapi-sdk` (pip) | $49/mo | SI (proxy) | No sirve para FB — solo proxy, sin parser |
| 6 | **ScrapingBee** | NO — solo proxy+render HTML | Solo titulo, timestamp, link publico | 1,000 credits | `scrapingbee` (pip) | $49/mo | SI (proxy) | No sirve para FB — proxy sin datos estructurados |
| 7 | **Diffbot** | NO — articulos/noticias, no social media | N/A | 14 dias trial | REST API | $299/mo | SI | No sirve — enfocado en noticias, no FB feeds |
| 8 | **ScrapeStorm** | PARCIAL — AI visual, FB dificil | Depende de config manual | Version gratis limitada | NO | $49.99/mo | Desktop app | No sirve — requiere app desktop, sin API |
| 9 | **ParseHub** | PARCIAL — visual scraper, FB rompe frecuente | Depende de config manual | 200 pags/run, 5 runs | REST API | $189/mo | Desktop app | Caro, manual, fragil contra FB |
| 10 | **Mozenda** | ? — enterprise | N/A | NO | REST API | Enterprise (contactar) | SI (cloud) | Overkill — Fortune 500, pricing opaco |
| 11 | **Sequentum** | NO — sin templates FB | N/A | Trial enterprise | NO (C#/visual) | $5,500/yr | Windows desktop | Descartado — Windows only, enterprise, sin FB |
| 12 | **WebHarvy** | PARCIAL — point-and-click | Depende de config manual | 15 dias trial | NO | $139 one-time | Windows desktop | Descartado — Windows only, sin API |

## Resumen Ejecutivo

**Solo 3 de las 12 herramientas tienen soporte REAL de Facebook con datos estructurados:**

### Tier 1: Recomendados

| Criterio | Apify | Crawlbase | Brightdata |
|----------|-------|-----------|-----------|
| Actor/endpoint FB dedicado | SI | SI | SI |
| JSON estructurado | SI | SI | SI |
| Posts + engagement | SI | SI | SI |
| Python SDK | `apify-client` | `crawlbase` | `brightdata` |
| Free tier util | $5/mo (~500 scrapes) | 1,000 requests | Trial con deposito |
| Precio produccion | $49/mo | $29/mo | $1.50/1K records |
| Sin browser local | SI (cloud) | SI (API) | SI (cloud) |
| Riesgo cuenta FB | NO (ellos manejan) | NO | NO |

### Tier 2: Funcionan pero con limitaciones

| Criterio | PhantomBuster |
|----------|---------------|
| FB dedicado | SI (Phantoms) |
| Requiere cookie FB | SI (riesgo suspension) |
| Free plan | Inutil (10 rows) |
| Precio | $69/mo (mas caro) |

### Tier 3: No sirven para Facebook

ScraperAPI, ScrapingBee, Diffbot, ScrapeStorm, ParseHub, Mozenda, Sequentum, WebHarvy — son proxies genericos, enterprise, o desktop-only. Ninguno tiene parser FB dedicado.

## Decision para CRECE v2

**Opcion A (recomendada): Apify**
- Ya estaba en el plan original (SCRAPER-TEST-LOG.md)
- SDK instalado en el proyecto (`apify-client`)
- $5/mo free tier alcanza para 6 dirigentes x ~50 posts = 300 scrapes/mes
- Actor: `apify/facebook-pages-scraper`

**Opcion B (alternativa si Apify falla): Crawlbase**
- $29/mo, JSON estructurado
- Endpoint: `api.crawlbase.com/?token=JS_TOKEN&url=facebook.com/PAGE`
- Devuelve posts con likes, comments, shares directamente

**Opcion C (alto volumen futuro): Brightdata**
- Pay-per-use $1.50/1K records
- Ideal cuando escalemos a 50+ dirigentes
- Collectors dedicados por tipo de dato FB

## Stack de resiliencia Facebook (actualizado)

```
Intento 1: Apify FB Pages Scraper (cloud, sin browser)
    ↓ si falla (rate limit, creditos agotados)
Intento 2: Crawlbase FB endpoint (API, JSON)
    ↓ si falla
Intento 3: Playwright GraphQL intercept (nuestro scraper actual, 4-10 posts)
    ↓ si falla
Intento 4: curl-cffi HTML parsing (1-5 posts del JSON embebido)
```
