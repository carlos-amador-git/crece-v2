# CRECE v2.0 — Sprint: Cerrar Gaps del Plan Original
## Estado: EN EJECUCIÓN
## Fecha: 2026-04-05
## Contexto: 5 scrapers + NLP + Voter Scoring ya funcionan. Cerramos lo que falta.

---

## Sprint 1: Bluesky scraper (20 min)
**Objetivo:** Scraper para AT Protocol (API pública, sin auth)
**Archivos:** `backend/app/scrapers/bluesky.py`, `backend/app/scrapers/base.py`
**Criterio:** fetch_raw + parse + update_profile_stats funcionan contra perfil real
**Dependencias:** Ninguna — AT Protocol es REST abierto
**Plan:**
1. Crear bluesky.py con httpx contra api.bsky.app
2. Registrar en base.py get_scraper()
3. Probar contra algún perfil político mexicano en Bluesky

## Sprint 2: sentiment-spanish + modelo propaganda (20 min)
**Objetivo:** Agregar validación cruzada NB + detección de propaganda al pipeline NLP
**Archivos:** `backend/app/nlp/analyzer.py`, `backend/app/nlp/huggingface_models.py`
**Criterio:** analyze_full() retorna campos adicionales (sentiment_cross_validation, propaganda_labels)
**Dependencias:** sentiment-analysis-spanish ya en pyproject.toml
**Plan:**
1. Instalar sentiment-analysis-spanish
2. Agregar al analyze_full() como campo de validación cruzada
3. Buscar modelo de propaganda en HuggingFace, agregar al registry
4. Probar con posts reales de Piña

## Sprint 3: pgvector búsqueda semántica (30 min)
**Objetivo:** Habilitar búsqueda por similitud semántica de posts
**Archivos:** nuevo migration, `backend/app/services/embeddings.py`
**Criterio:** Buscar posts similares a un texto dado retorna resultados relevantes
**Dependencias:** PostgreSQL con extensión pgvector (verificar si está en PostGIS image)
**Plan:**
1. Verificar que pgvector está disponible en la imagen PostGIS
2. Crear migration para agregar columna embedding a SocialPost
3. Servicio de embeddings con sentence-transformers (modelo español)
4. Endpoint de búsqueda semántica

## Sprint 4: Commit + actualizar contexto (10 min)
**Objetivo:** Commit, push, actualizar STATUS.md y DECISIONS.md
**Criterio:** PR actualizado, contexto al día
