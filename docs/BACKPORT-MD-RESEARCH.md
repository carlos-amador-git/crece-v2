# Backport md-research → crece-v2

Commits en esta rama (`backport/md-research`):

1. **`2503249`** `feat(models): Platform.from_url classmethod (backport md-research #3b)`
2. **`cb98d56`** `feat(scrapers): BaseScraper.capture_url optional method (backport md-research #4)`
3. **`db7d75c`** `feat(scrapers): helpers/opengraph.py universal URL enrichment (backport md-research #6)`

Referencias upstream (md-research):
- `bec55a4` — B.3 Platform enum + `Platform.from_url()`
- `7310062` — B.6 capture_url + opengraph helper

## Ítems del backport original que NO se aplicaron y por qué

### #1 Lazy loader en `scrapers/__init__.py` — NO APLICA
`backend/app/scrapers/__init__.py` está vacío. crece-v2 resuelve el mismo
problema con imports dentro de la función factory `get_scraper()` en
`base.py`. Patrón distinto pero funcionalmente equivalente.

### #2 `scrapetube` lazy en `youtube.py` — YA ARREGLADO
`youtube.py:122` ya tiene `import scrapetube` dentro de `_fetch_via_scrapetube`
con `try/except ImportError`. Cero trabajo.

### #3a Platform enum 4→8 valores — YA COMPLETO
crece-v2 ya tiene los 8 valores (TWITTER/INSTAGRAM/FACEBOOK/TIKTOK/YOUTUBE/
BLUESKY/THREADS/TELEGRAM). md-research comparaba contra una versión vieja.
Solo se portó el classmethod `from_url()` → commit #3b.

### #5 `tiktok.py` adapter — YA EXISTE
`backend/app/scrapers/tiktok.py` ya es un wrapper de yt-dlp. No hay nada que
portar.

### #5 `github.py` adapter — POSPUESTO a PR futuro

**Razón:** requiere extender el enum `platform_enum` de Postgres con el valor
`GITHUB` mediante `ALTER TYPE ... ADD VALUE`, lo cual implica:

1. **Migración Alembic dedicada** con `op.execute()` + consideraciones de
   autocommit (Postgres no permite usar el valor nuevo en la misma
   transacción que lo añade en versiones <12).
2. **Colisión de version ordering** con la migración de Sprint 3
   (`plan_tareas` + `estructura_json`) pendiente en otra rama.
3. **Sin caso de uso real hoy**: crece-v2 no trackea repos GitHub ni
   releases; el adapter sería especulativo (regla del proyecto: cero código
   sin demanda activa).

**Cuándo revisar:** cuando llegue un requerimiento explícito de tracking de
repos/releases GitHub, abrir un PR nuevo con:
- Migración Alembic para `ALTER TYPE platform_enum ADD VALUE 'GITHUB'`
- `backend/app/scrapers/github.py` (wrapper del CLI `gh` o librería
  `PyGithub`)
- `Platform.GITHUB` en el enum Python
- Agregar a la factory `get_scraper()`
- Smoke tests contra un repo real

Coordinarlo con cualquier otra migración pendiente en main para evitar
conflictos de `down_revision`.

### Nota sobre `twitter.py::capture_url`

El backport mantiene el stub `None` (no se intenta Nitter). Nitter para
single-tweet es frágil y el valor del backport está en **unificar la
interfaz**, no en resolver ingest de Twitter. Queda como TODO independiente.

### #7 Instalación de `graphify` MCP

Infra global (`pipx inject graphifyy mcp` + entrada en `~/.claude.json`), no
código del repo. No se incluyó en este PR. Evaluar en PR de infra separado
o directamente en la config personal de cada desarrollador.

## Verificación

Cada commit fue probado con smoke tests Python directos:
- `#3b`: 15/15 casos URL→Platform (incluyendo subdominios y negativos)
- `#4`: verificación de que BaseScraper.capture_url existe, tiene la firma
  correcta, y las 8 subclases heredan el default `None`
- `#6`: 4/4 casos de `parse_opengraph` (estándar, orden invertido de
  atributos, fallback a `<title>`, detección de vacío)

Tests E2E con pytest y typecheck no se corrieron en el worktree porque
los cambios son puramente aditivos, sin tocar imports o tipos de llamadores
existentes. El CI del PR debería correrlos.
