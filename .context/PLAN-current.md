# CRECE v2.0 — Plan de Implementación Fase 1 (Completar Gaps)

## Estado: EN EJECUCIÓN
## Fecha: 2026-04-03
## Clasificación: ESTRATÉGICA (ST aplicado)

---

## Resumen Ejecutivo
Completar los gaps identificados en la auditoría de Fase 1 para tener un sistema funcional end-to-end.

## Sprints

### BATCH 1 — Ejecución Paralela (4 agentes)

#### Sprint 1A: Scrapers Twitter + Instagram
- **Agente**: python-expert
- **Archivos**: `backend/app/scrapers/twitter.py`, `backend/app/scrapers/instagram.py`
- **Entregable**: Scrapers funcionales con twscrape e instaloader
- **Criterio**: fetch_raw() retorna datos parseados, store persiste en DB

#### Sprint 1B: Scrapers Facebook + TikTok + YouTube
- **Agente**: python-expert
- **Archivos**: `backend/app/scrapers/facebook.py`, `backend/app/scrapers/tiktok.py`, `backend/app/scrapers/youtube.py`
- **Entregable**: Scrapers funcionales con facebook-scraper, TikTok-Api, YouTube Data API v3
- **Criterio**: fetch_raw() retorna datos, parse() normaliza a SocialPost schema

#### Sprint 1C: Nuevos Modelos de Datos + Migración
- **Agente**: backend-architect
- **Archivos nuevos**:
  - `backend/app/models/ciudadano.py` — Padrón de ciudadanos por sección
  - `backend/app/models/evento.py` — Eventos y actividades
  - `backend/app/models/programa_social.py` — Programas sociales por sección
- **Entregable**: Modelos SQLAlchemy, schemas Pydantic, endpoints CRUD, migración Alembic, seed actualizado

#### Sprint 1D: Test Suite Backend
- **Agente**: quality-engineer
- **Archivos**: `backend/tests/`
- **Entregable**: Tests para auth, dirigentes CRUD, diagnostico IPD, sentiment service, electoral endpoints
- **Criterio**: pytest pasa con >80% de endpoints cubiertos

### BATCH 2 — Ejecución Paralela (2 agentes, post-Batch 1)

#### Sprint 2A: NLP Pipeline Upgrade
- **Agente**: python-expert
- **Archivos**: `backend/app/nlp/analyzer.py`, nuevo `backend/app/nlp/huggingface_models.py`
- **Entregable**: Integrar PlanTL-GOB-ES controversy detection, toxic political tweets classifier
- **Criterio**: analyze() retorna controversy_score y toxicity de múltiples modelos

#### Sprint 2B: Validación Visual con Playwright
- **Agente**: quality-engineer (Playwright)
- **Archivos**: `frontend/tests/` (e2e)
- **Entregable**: Screenshots de login, dashboard, dirigentes, electoral, planes
- **Criterio**: Todas las páginas renderizan sin errores de consola

---

## Verificación Interna
1. Post-Batch 1: `pytest` backend + `next build` frontend
2. Post-Batch 2: Playwright screenshots + review visual
3. Final: Commit consolidado + status update

## Asignación de Recursos
| Agente | Tipo | Sprint |
|--------|------|--------|
| Agent A | python-expert | 1A (scrapers TW+IG) |
| Agent B | python-expert | 1B (scrapers FB+TT+YT) |
| Agent C | backend-architect | 1C (modelos + migración) |
| Agent D | quality-engineer | 1D (tests) |
| Agent E | python-expert | 2A (NLP upgrade) |
| Agent F | quality-engineer | 2B (Playwright) |
