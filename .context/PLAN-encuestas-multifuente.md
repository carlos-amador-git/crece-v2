# Plan · Encuestas Multi-Fuente para Alcaldías CDMX

**Created:** 2026-05-09 · **Status:** Sprint 1+2A done · 5 fuentes pendientes

## Estado actual (post-Sprint 1+2A)

| Fuente | Cobertura | Mediciones | Histórico | Estado |
|---|---|---:|---|---|
| Demoscopía Digital | 15/16 alcaldías | ~2,400 (aprobación + desaprobación) | 2024-10 → 2026-04 (4 alcaldías desde 2022) | ✅ ingestado |
| Mitofsky | 16/16 alcaldías | ~600 | 2022-01 → 2026-04 | ✅ ingestado (post-Sprint 1 con municipios mapeados) |
| **GobernArte** | 9/16 alcaldías (top ranking) | 9 (1 snapshot ago-2025) | Mensual público | ⚠️ MVP — solo 1 fecha · scraper multi-fecha pendiente |
| FactoMétrica (Monitor Capitalino) | 16/16 mensual | 0 | 2025+ disponible | 🔴 pendiente |
| Massive Caller | 16/16 mensual | 0 | PDF público | 🔴 pendiente |
| PollsMX (Político.mx) | Agregador 16/16 | 0 | Mensual | 🔴 pendiente |
| El Financiero (Bloomberg) | Trimestral CDMX | 0 | 2025+ | 🔴 pendiente |
| El Universal | Trimestral 16/16 | 0 | 2025+ | 🔴 pendiente |
| SRC (Statistical Research Corp) | 16/16 mensual | 0 | 2025+ | 🔴 pendiente |
| RUBRUM | Parcial (top alcaldías) | 0 | Mensual | 🔴 pendiente (low priority) |

## Sprint 2B · GobernArte multi-fecha (4-6 hrs)

**Objetivo:** scrape histórico GobernArte mensual desde marzo 2025.

**Endpoints:**
- `https://gobernarte.com.mx/ranking-de-aprobacion-de-alcaldes-de-la-ciudad-de-mexico-resultado-de-{N}-de-{mes}-{año}/`
- Listing: `https://gobernarte.com.mx/category/cdmx-alcaldias/` (probar)

**Implementación:**
1. `backend/app/scrapers/encuestas_gobernarte.py` siguiendo patrón de `encuestas_demoscopia.py`
2. Listar URLs mensuales del listado category → BeautifulSoup parse
3. Para cada URL:
   - regex extracción narrativa (probado: `([Nombre]+) ([Alcaldía], [Partido]) – [pct]`)
   - 9 top alcaldías por mes, suficiente para demostración
4. Insertar con `fuente='GobernArte'` en `encuestas_publicas`
5. Test: comparar mes vs mes 2 alcaldías misma fuente

**Caveats:**
- GobernArte solo publica top ranking (no las 16). Acceptable para MVP.
- Formato narrativo (no tablas) → regex frágil ante cambios de redacción.
- Sin desaprobación.

## Sprint 2C · FactoMétrica (4-6 hrs)

**Endpoint:** `https://factometrica.com/post/monitorcapitalino-ranking-de-alcaldes-cdmx-{mes}-{año}`

**Implementación:**
1. Probar listing `https://factometrica.com/category/monitor-capitalino/`
2. Cada post tiene tablas o imágenes con ranking — investigar formato
3. Scraper similar a GobernArte
4. **Posible blocker:** si datos están en imagen (gráfico) → necesitamos OCR (tesseract) o tabla embebida
5. Si el sitio tiene JSON estructurado en `<script type="application/ld+json">` → parsear ahí

**Métrica posible:** aprobación + desaprobación + tendencia (delta mensual).

## Sprint 3A · Massive Caller PDF (6-10 hrs)

**Endpoint:** `https://www.massivecaller.com/files/alcaldias_cdmx.pdf` (URL única, se actualiza)

**Implementación:**
1. Listing de PDFs: `https://www.massivecaller.com/category/encuestas/cdmx/` (validar)
2. Por cada PDF:
   - Download local
   - Parse con `pdfplumber` o `pypdf` — extraer tablas
   - Mapear filas a alcaldía + métrica
3. Hash del PDF para idempotencia (no reingestar el mismo archivo)
4. **Caveat:** PDFs varían en estructura mes a mes. Necesita parser tolerante a layouts.

**Recomendación:** empezar con 1 PDF reciente, validar parser, luego batch.

## Sprint 3B · PollsMX (Político.mx) (3-5 hrs)

**Endpoint:** `https://polls.politico.mx/2026/04/26/ranking-de-alcaldes-coyoacan-lidera-aprobacion-en-la-ciudad-de-mexico/`

**Implementación:**
1. Listing por fecha de publicación
2. Parsear cada post — usualmente HTML con tablas
3. **Ventaja:** PollsMX es **agregador** de otras casas, su data ya viene cruzada. Útil para validar Demoscopía/Mitofsky/GobernArte.

**Caveat:** algunos posts solo citan top 5 con resumen narrativo, otros tienen tabla completa. Parser debe distinguir.

## Sprint 4 · El Financiero + El Universal (4-6 hrs)

**El Financiero:**
- URL: `https://www.elfinanciero.com.mx/cdmx/{año}/{mes}/{día}/{slug}/`
- Listing por categoría CDMX
- Datos en HTML (tablas + texto narrativo)
- Trimestral (4-6 publicaciones/año)

**El Universal:**
- URL interactivo: `https://interactivos.eluniversal.com.mx/2025/encuesta-evaluacion-gobcdmx_dic/`
- **Embed Flourish** o D3.js → datos en JSON embebido (`<script>` tags)
- Trimestral

**Caveat:** El Universal puede requerir Playwright si es renderizado JS. Probar primero con curl simple.

## Política operativa post-implementación

1. **Cron Celery** para actualizar mensual:
   - `gobernarte_scraper.refresh_monthly` (día 5 de cada mes)
   - `factometrica_scraper.refresh_monthly` (día 10)
   - `massive_caller_scraper.refresh_monthly` (día 15)
   - `pollsmx_scraper.refresh_weekly` (cada lunes)
   - `el_financiero_scraper.refresh_quarterly` (1 de mes nuevo trimestre)
   - `el_universal_scraper.refresh_quarterly` (15 de mes nuevo trimestre)
2. **Frontend `/clima-politico`**: agregar filtro "Fuente" (multi-select) al tab Alcaldes
3. **Tabla comparativa** que muestre todas las fuentes para una alcaldía/fecha en un solo chart
4. **Alertas**: si dos fuentes difieren >15 puntos en mismo mes/alcaldía → flag para revisión humana

## Estimación total honesta

- Sprint 2B (GobernArte multi-fecha): 4-6 hrs
- Sprint 2C (FactoMétrica): 4-6 hrs
- Sprint 3A (Massive Caller PDF): 6-10 hrs
- Sprint 3B (PollsMX): 3-5 hrs
- Sprint 4 (El Financiero + El Universal): 4-6 hrs
- Frontend (filtro fuente + tabla comparativa): 4-6 hrs
- Cron schedules: 2-3 hrs

**Total: 27-42 hrs · 4-6 días dedicados.**

## Recomendación estratégica

**Si MC presiona** → priorizar Sprint 2B (GobernArte completo) + Sprint 2C (FactoMétrica) para tener 4 fuentes activas. Cubre 80% del valor con 30% del esfuerzo.

**Si MC no presiona** → ejecutar la ola completa post-piloto, con foco en cron automation desde el día 1 (no hacer scrapes one-shot que se queden congelados).
