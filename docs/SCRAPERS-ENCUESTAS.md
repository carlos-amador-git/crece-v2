# Scrapers de Encuestas Políticas — CRECE v2

**Última revisión:** 2026-05-08 · Owner: Linda (CRECE-electoral)

Este documento es la **fuente de verdad** sobre cómo se pueblan los datos de
`encuestas_publicas` en CRECE v2. Si vuelves a perder la programación o el
contexto, este archivo (junto con los archivos referenciados) basta para
reconstruir todo el pipeline.

---

## 1. Tabla resumen del estado actual

Snapshot 2026-05-08 — `encuestas_publicas`:

| Fuente | Filas | Cobertura | Costo cash | Stack |
|---|---:|---|---|---|
| Mitofsky (PDF GDrive) | 3697 | gobernadores 2022-2026 · alcaldes individual 150×~19m=2241 · presidente 2024-2025 · histórico nacional 2020-2026 | $0 | pdfplumber + httpx |
| Oraculus poll-of-polls | 748 | Aprobación presidencial 1995-2026 (CSP, AMLO, EPN, FCH, VFQ, EZPL) | $0 | regex JSON inline + httpx |
| El Financiero/tel + Enkoll + Buendía + Demoscopía + Parametría + Demotecnia + Covarrubias | 73 | Encuestas individuales agregadas por Oraculus polls section + Demoscopía federal recuperable | $0 | (incluido en Oraculus + Demoscopía partial) |
| PollsMX (artículos políticos) | 22 | Intención voto 2027, aprobación, percepción seguridad | $0 | regex partido+valor en narrativa |
| **TOTAL** | **4540** | | **$0/mes** | sin LLM, sin vision, sin OCR |

Path forward identificado pero NO implementado:
- AS/COA Approval Tracker → bloqueado por SPA D3 (requiere Playwright). Skip por ROI.
- Mitofsky 4 PDFs failed parse → boletines pre-2023 con layouts edge case.
- PollsMX histórico → solo 21 artículos visibles en homepage; sitemap retorna 404.

---

## 2. Schema de la tabla `encuestas_publicas`

```sql
CREATE TABLE encuestas_publicas (
    id SERIAL PRIMARY KEY,
    fuente VARCHAR(100),                  -- "Mitofsky", "Oraculus poll-of-polls", "PollsMX", ...
    fecha_publicacion DATE,                -- mes de la encuesta (día 1 si solo se conoce el mes)
    ambito VARCHAR(20),                    -- federal, estatal, municipal
    entidad VARCHAR(100),                  -- "México", "Ciudad de México", "Sinaloa", ...
    actor_tipo VARCHAR(40),                -- presidente, gobernador, alcalde, partido,
                                           -- promedio_gobernadores, promedio_alcaldes,
                                           -- presidente_aprobacion_estatal, candidato, tema
    actor_nombre VARCHAR(120),             -- "Claudia Sheinbaum Pardo", "MORENA", ...
    actor_partido VARCHAR(20),             -- partido del actor (MORENA, PAN, PRI, MC, etc.)
    metrica VARCHAR(40),                   -- aprobacion, desaprueba, intencion_voto,
                                           -- percepcion_inseguridad, tema
    valor_pct NUMERIC(5,2),                -- valor en porcentaje
    valor_delta_vs_anterior NUMERIC(5,2),  -- variación vs mes anterior (NULL si N/A)
    tamanyo_muestra INT,                   -- ASCII (no ñ); NULL si no reportado
    margen_error NUMERIC(5,2),             -- NULL si no reportado
    url_fuente TEXT,                       -- URL del artículo/PDF/post
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Dedupe key (en cada ingester):** `(fuente, fecha_publicacion, entidad, actor_nombre, metrica)`
+ `actor_tipo` en Mitofsky para distinguir histórico_nacional vs estatal.

⚠️ **Ojo schema drift histórico:** la columna se llama `tamanyo_muestra` (ASCII),
NO `tamaño_muestra`. Migración `3d6fe3f1660d` consolidó el rename. Cualquier
scraper nuevo debe usar `tamanyo_muestra`.

---

## 3. Inventario de scripts y archivos

### Scrapers (en `backend/app/scrapers/`)

| Archivo | Fuente | Descripción |
|---|---|---|
| `encuestas_oraculus.py` | Oraculus | Extrae JSON inline `var data = {...}` de `oraculus.mx/aprobacion-presidencial/`. Histórico 1995→presente de poll-of-polls + encuestas individuales agregadas. |
| `encuestas_demoscopia.py` | Demoscopía Digital | Extrae `ng_state` (Angular SSR transfer state) de `demoscopiadigital.com/aprobacionEstado/{ciudad-de-mexico,oaxaca,...}`. Federal + CDMX + Oaxaca. |
| `encuestas_mitofsky_pdf.py` | Mitofsky | **3 parsers:** `parse_pdf_gobernadores`, `parse_pdf_alcaldes`, `parse_pdf_presidente`. Lee PDFs descargados de Google Drive (botón "DESCARGAR RANKING" en posts Wix). |
| `encuestas_pollsmx.py` | PollsMX | Crawl listings + parse narrativa + regex partido/político vs valor%. |
| `encuestas_mitosky.py` | Mitofsky (LEGACY) | Importador Excel `Aprobacion_Gobernadores_Historico.xlsx`. **No usado**: el flujo actual es PDF (`encuestas_mitofsky_pdf.py`). Conservado como referencia si Mitofsky publica Excel en el futuro. |

### Orchestrators (en `backend/scripts/`)

| Archivo | Comando | Descripción |
|---|---|---|
| `scrape_encuestas.py` | `python scripts/scrape_encuestas.py [--source oraculus\|all] [--historical]` | Corre Oraculus. Flag `--historical` incluye AMLO/EPN/FCH/VFQ/EZPL además de CSP. |
| `mitofsky_catalog_gdrive.py` | `python scripts/mitofsky_catalog_gdrive.py [--limit N] [--out PATH]` | Recorre `blog-posts-sitemap.xml` de Mitofsky, identifica los 127 posts gobernadores/aprobacion/ranking/alcaldes, extrae el href Google Drive del botón "DESCARGAR RANKING" de cada uno. Output JSON con `{post_url, post_title, post_date, gdrive_id, gdrive_url, download_label}`. |
| `ingest_mitofsky_pdfs.py` | `python scripts/ingest_mitofsky_pdfs.py [--type all\|gobernadores\|alcaldes\|presidente] [--limit N] [--dry-run]` | Lee catalog JSON, descarga cada PDF de GDrive (~5-9 MB), parsea con dispatcher según tipo, UPSERT idempotente. |
| `scrape_pollsmx.py` | `python scripts/scrape_pollsmx.py [--dry-run]` | Crawl listings de polls.politico.mx, parsea cada artículo, extrae datapoints con regex partido/político. |

### Data artifacts (en `captures/`)

| Archivo | Descripción |
|---|---|
| `mitofsky-gdrive-catalog.json` | 127 entries · 105 con `gdrive_id` válido · catálogo persistente para futuros re-runs sin re-crawl. |

---

## 4. Comandos canónicos para repoblar

Si la BD se pierde (snapshot, recovery, sandbox nuevo), estos comandos en orden
restauran el corpus:

```bash
# Pre-requisito: docker compose con crece-backend + crece-db levantados,
# DATABASE_URL apuntando a postgres+asyncpg

# 0. Verificar tabla
docker exec crece-backend python -c "
import asyncio, os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
async def m():
    eng = create_async_engine(os.environ['DATABASE_URL'])
    S = async_sessionmaker(eng, expire_on_commit=False)
    async with S() as db:
        r = await db.execute(text('SELECT COUNT(*) FROM encuestas_publicas'))
        print('rows pre-ingest:', r.scalar())
asyncio.run(m())
"

# 1. Oraculus (federal + encuestadoras agregadas por ellos: ~825 rows)
docker exec crece-backend python scripts/scrape_encuestas.py --source oraculus --historical

# 2. Mitofsky PDFs — primero catalog (10-15 min · solo si no existe captures/)
docker exec crece-backend python scripts/mitofsky_catalog_gdrive.py --out /tmp/cat.json
docker cp crece-backend:/tmp/cat.json captures/mitofsky-gdrive-catalog.json

# 3. Mitofsky PDFs — ingest los 3 tipos (~10-15 min cada uno)
docker cp captures/mitofsky-gdrive-catalog.json crece-backend:/tmp/cat.json
docker exec crece-backend python scripts/ingest_mitofsky_pdfs.py --catalog /tmp/cat.json --type gobernadores
docker exec crece-backend python scripts/ingest_mitofsky_pdfs.py --catalog /tmp/cat.json --type alcaldes
docker exec crece-backend python scripts/ingest_mitofsky_pdfs.py --catalog /tmp/cat.json --type presidente

# 4. PollsMX (~30 segundos · solo articulos visibles en homepage actualmente)
docker exec crece-backend python scripts/scrape_pollsmx.py
```

Total tiempo: ~25-40 min para llegar de cero a ~2254 rows.

---

## 5. Detalles por fuente

### 5.1 Oraculus (`encuestas_oraculus.py`)

**URL:** `https://oraculus.mx/aprobacion-presidencial/`

**Mecánica:** la página renderiza con un bloque `<script>var data = {...};</script>`
inline. Regex `r"var\s+data\s*=\s*(\{.*?\});\s*</script>"` extrae el JSON.

**Estructura del JSON:**
```js
{
  "estimates": {
    "aprueba":   { "CSP": [[ts_ms, mid, lo95, hi95, ...], ...], "AMLO": [...], ... },
    "desaprueba": { /* idem */ }
  },
  "polls": {
    "Aprueba":    { "CSP": [[pollster, ts_ms, valor], ...], "AMLO": [...], ... },
    "Desaprueba": { /* idem */ }
  }
}
```

**Output:**
- Poll-of-polls (ámbito federal, ~748 rows). Si `--historical` se incluye AMLO/EPN/FCH/VFQ/EZPL.
- Encuestas individuales — la sección `polls` acredita a cada casa: Mitofsky,
  Buendía, Enkoll, Parametría, El Financiero, etc. Cada una entra como `fuente`
  separada en `encuestas_publicas`. Por eso vemos las 7 encuestadoras "menores"
  con 14-24 rows cada una — todas vienen del scrape Oraculus, no requiere
  scraper directo a sus sitios.

**Idempotencia:** dedupe `(fuente, fecha, actor_nombre, metrica)`.

### 5.2 Demoscopía (`encuestas_demoscopia.py`)

**URLs:** federal + CDMX (Brugada) + Oaxaca (Salomón Jara).

**Mecánica:** sitio Angular Universal con `ng_state` = transfer-state JSON
embebido en `<script id="serverApp-state">`. Decodifica HTML entities + parsea
JSON.

**Función clave:** `iter_months(back_months)` para enumerar meses históricos.

**Estado actual:** 11 rows totales (Demoscopía Digital fuente). Este número es
bajo — el extractor podría estar perdiendo datos, candidato a auditoría futura.

### 5.3 Mitofsky PDF (`encuestas_mitofsky_pdf.py`) — **el más complejo**

**Mecánica:**

1. Cada post en `mitofsky.mx/post/<slug>` tiene un botón "DESCARGAR RANKING"
   (o "DESCARGAR DOCUMENTO") que linkea a Google Drive:
   `https://drive.google.com/file/d/<ID>/view?usp=sharing`.
2. `download_gdrive_pdf(file_id)` convierte el ID → URL `uc?export=download&id=...`
   y descarga el PDF (sigue redirect 303 → drive.usercontent.google.com).
3. `pdfplumber` extrae texto seleccionable (los PDFs NO son scaneados).

**3 tipos de PDF y sus parsers:**

#### Gobernadores (`parse_pdf_gobernadores`) — el más rico

Páginas relevantes (cambian entre boletines viejos y nuevos):
- `PROMEDIO NACIONAL DE APROBACIÓN DE GOBERNADORES` → tabla 12 meses × N años
  (boletín 76 dic-2025 onwards). Extrae **72 datapoints** del histórico
  nacional en 1 sola página (`parse_page4_serie_nacional`).
- `LUGAR % DE ACUERDO` → ranking del mes con 32 estados
  (`parse_ranking_page`). Layout `LUGAR_PREV LUGAR_ACTUAL ABREV_ESTADO NOMBRE %_PREV %_ACTUAL`.
  Boletines viejos NO usan punto después de los lugares; regex es flexible.

`detect_pdf_period()` lee la fecha de la portada (page 1: "DICIEMBRE 2025").

`detect_pdf_type()` clasifica via texto de la portada — usado solo si hay duda.

#### Alcaldes (`parse_pdf_alcaldes`)

- Page 3 con texto tipo `"Feb26 46.5 / Dic 25 47.7 / ..."` (histórico promedio
  nacional 150 alcaldes). Regex `_RE_ALCALDES_HIST` captura mes+año+valor.
- Ranking individual de 150 alcaldes **no implementado** en v1: layout fragmentado
  multilínea con orden visual no lineal — alta probabilidad de errores. ROI bajo
  (los alcaldes individuales raramente aparecen en políticos seguidos por CRECE).

#### Presidente (`parse_pdf_presidente`)

- Page 2: serie histórica 12 meses (etiquetas tipo "Oct 24 Nov 24 ... Sep 25").
  `parse_pdf_presidente_historico` busca línea con 12 etiquetas mes+año, luego
  toma los primeros 12 valores flotantes del bloque previo (asume orden ACUERDO).
- Page 4-6 (variable): ranking aprobación presidencial por estado (32 estados).
  `parse_pdf_presidente_ranking_estados` con regex
  `^Estado posición valor variación`.
- `detect_actor_presidente` decide CSP vs AMLO según texto + fecha.

**Idempotencia:** dedupe `(fuente, fecha, entidad, actor, metrica, actor_tipo)`.
El último campo es importante para no colisionar `promedio_gobernadores`
(federal, ámbito México) con `gobernador` (estatal).

**4 PDFs failed parse:** layouts edge case, no resueltos. `gid` listados en
STATUS.md sprint 2026-05-08. Reprocesar cuando el parser se afine en otro sprint.

### 5.4 PollsMX (`encuestas_pollsmx.py`)

**URL base:** `https://polls.politico.mx`

**Mecánica:**
1. `discover_articles()` crawls 4 listing pages: `/`, `/noticias`, `/aprobacion`,
   `/power-ranking/gobernadores/2027`. Regex `_RE_ARTICLE_URL` extrae paths
   `/YYYY/MM/DD/slug/` → ~21 artículos visibles.
2. `parse_article(url)` descarga, extrae title (og:title), strip HTML, body.
3. `detect_metric_ambito()` infiere ámbito + métrica desde título + body:
   - "intencion / votar / preferencia / 2027" → `intencion_voto`
   - "aprobacion" → `aprobacion`
   - "inseguridad / seguridad" → `percepcion_inseguridad`
   - else → `tema` (genérico)
4. `extract_datapoints()` recorre `PARTIDO_PATTERNS` (MORENA, PAN, PRI, MC, PT, PVEM)
   o `POLITICO_PATTERNS` (Sheinbaum, AMLO, Lilly Téllez, Harfuch, Ebrard, etc.)
   buscando `\b\d+(\.\d)?%` en ventana de 200 chars después de cada mención.

**Limitaciones:**
- Solo captura los ~21 artículos en homepage actual (no histórico completo).
- Sitemap retorna 404 → no hay listing histórico explorable.
- Regex matches first-mention-first-percent: no diferencia entre dato actual
  vs comparativo (puede capturar valor Marzo cuando se busca Abril).
- `actor_tipo='tema'` es marcador débil; estos rows son de menor calidad.

**Cuándo re-correr:** mensual (cada vez que polls.politico.mx publique nuevos
artículos). Idempotente, dedupe automático.

---

## 6. Lecciones aprendidas (para no repetir errores)

### 6.1 Validar fuente primaria antes de comprometer infra

**Caso D-25-A (vision stack Mitofsky):** el CEO autorizó 3 modos LLM
(text/OCR/vision) para extraer datos de PNG charts en Mitofsky. Antes de
ejecutar, S1 keystone reveló que **cada post tiene botón "DESCARGAR RANKING" →
PDF en Google Drive** con texto seleccionable. Pipeline 100% determinístico,
cero LLM, cero vision, cero VRAM Coolify.

**Lección:** antes de comprometer infra LLM, hacer un sweep de DevTools sobre
el HTML buscando: (a) downloads CTAs, (b) JSON inline en `<script>`, (c)
endpoints API en network tab. 30 minutos de research ahorran horas-días de
infra.

### 6.2 Coolify VPS es CPU-only — vision LLM inviable

Smoke histórico (ver STATUS.md): >17 min/iter para gemma3:12b texto, plan IA
Ballesteros timeout 540s. Para vision con `llava:13b`/`qwen2-vl:7b` esperaríamos
45-90 min/imagen, totalmente inviable para batch de 100+ imágenes.

**Constraint operativo D-25-A:** todo procesamiento LLM en CRECE corre en
Ollama Coolify del VPS (no providers pagos por directiva CEO). Por tanto vision
queda fuera. Modo A (texto narrativo gemma3:12b) sí es viable pero lento —
preferir batch nocturno.

### 6.3 Multi-formato dentro de la misma fuente

Mitofsky cambia layout entre boletines: pre-2025 los rangos no usan punto
después del lugar (`1 1 QR Mara Lezama`), post-2025 sí (`1. 1. QR ...`); pre-2025
no incluye serie histórica nacional, post-2025 sí.

**Lección:** parsers deben ser **multi-formato tolerantes** o al menos
graceful-degrade (skip vs crash). Patrón: `_find_page_with(substring)` busca
por contenido en lugar de hardcodear índice de página.

### 6.4 Schema drift (`tamanyo_muestra` vs `tamaño_muestra`)

La columna en BD es `tamanyo_muestra` (ASCII) pero scrapers viejos
(`encuestas_mitosky.py` legacy) tenían `tamaño_muestra` (ñ). Causaba INSERT
silencioso fallido. Migración `3d6fe3f1660d` consolidó el rename.

**Lección:** seguir el schema actual de la DB (columna ASCII). Cualquier
scraper nuevo: verificar columnas con `SELECT column_name FROM information_schema.columns`
antes de programar.

### 6.5 docker-compose y crece-db down silencioso

Si `crece-db` muere durante un sprint largo, las inserciones empiezan a fallar
con `socket.gaierror: Name or service not known` resolviendo `db`. Health-check
de `docker ps --format '{{.Status}}' | grep crece-db` antes de ingestiones masivas.

---

## 7. Próximos pasos identificados (no implementados)

| # | Item | Esfuerzo | ROI esperado |
|---|---|---:|---|
| 1 | AS/COA Approval Tracker via Playwright | ~3h | Bajo (CSP ya cubierto por Mitofsky+Oraculus) |
| 2 | Mitofsky 4 PDFs failed → parsers para layouts edge case | ~2h | Bajo (4 PDFs de 105 = 4% pérdida) |
| 3 | Mitofsky alcaldes ranking individual 150 | ~3-4h | Medio (políticos individuales raros en piloto MC) |
| 4 | PollsMX paginación histórica (vía sitemap real o crawler agresivo) | ~3h | Medio (más artículos = más datapoints intención voto 2027) |
| 5 | Demoscopía auditoría — solo 11 rows parece bajo | ~1-2h | Medio (puede haber bug de extracción) |
| 6 | Parametría scraper directo (sitio propio) | ~2-3h | Bajo (Oraculus ya agrega Parametría) |

---

## 8. Identidades y coordinación (para contexto futuro)

- **Linda** (peer `uji6x64w`, sesión CRECE-electoral): owner de este pipeline.
  Encuestas, scrapers políticos, NLP, MC CDMX, replies a dirigentes.
- **Joy** (peer `3t5flofn`, sesión CRECE-Negocios): NO toca encuestas. Turf
  separado (B2B PyMEs, restaurantes, GBP OAuth, Tributo Huasteco).
- **Juan** (peer `i27fjncq`, md-research): research, scrapers experimentales,
  ScrapeGraph-AI evaluation. Coordinó la validación de Mitofsky.

Decisión arquitectural relacionada: `D-25-A` en `.context/DECISIONS.md`.

---

## 9. Auditoría rápida del corpus

Verificar la salud del corpus con un comando:

```bash
docker exec crece-backend python -c "
import asyncio, os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
async def m():
    eng = create_async_engine(os.environ['DATABASE_URL'])
    S = async_sessionmaker(eng, expire_on_commit=False)
    async with S() as db:
        # Por fuente
        r = await db.execute(text('SELECT fuente, COUNT(*), MIN(fecha_publicacion), MAX(fecha_publicacion) FROM encuestas_publicas GROUP BY fuente ORDER BY 2 DESC'))
        for row in r: print(f'{row[0]:<30s} {row[1]:>5d}  {row[2]} → {row[3]}')
asyncio.run(m())
"
```
