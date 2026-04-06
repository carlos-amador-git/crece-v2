# CRECE v2.0 — Sprint: Cerrar P0 Backend + Voter Scoring ML
## Estado: COMPLETADO
## Fecha: 2026-04-05

---

## Sprint 1: Fix Benchmark endpoint 500 (15 min) — COMPLETADO
**Objetivo:** El endpoint de benchmarking crashea por serialización del modelo Competidor.
**Archivos:** `backend/app/api/v1/endpoints/benchmark.py`, `backend/app/models/benchmark.py`
**Criterio:** GET /benchmarking responde 200 con datos de competidores.
**Resultado:** El "500" era en realidad un 404 — el prefix es `/benchmark/` no `/benchmarking/`. Ambos endpoints (`/competidores` y `/ranking`) responden 200 correctamente.

## Sprint 2: Content Factory E2E con Ollama (20 min) — COMPLETADO
**Objetivo:** Verificar que Content Factory genera contenido real con Ollama (tweet, reel, carrusel).
**Archivos:** `backend/app/services/content_factory.py`
**Criterio:** Generar contenido para Piña usando Ollama en Coolify. Output legible y usable.
**Resultado:** Timeout aumentado a 600s. Ollama genera contenido real en ~480s (CPU-only). Tweet generado para Piña sobre transporte público. Persistido en DB con modelo_ia='ollama/gemma3:12b', etiqueta_ia=True, disclaimer INE.

## Sprint 3: Voter Scoring — seed sintético INEGI (30 min) — COMPLETADO
**Objetivo:** Poblar 50+ ciudadanos con distribuciones demográficas reales de CDMX (INEGI 2020) para habilitar pipeline ML.
**Archivos:** `backend/scripts/seed_synthetic_citizens.py` (nuevo)
**Criterio:**
- 200 ciudadanos con data_source='synthetic_census_2020' ✅
- Distribuciones verificables: edad, escolaridad, género por alcaldía CDMX ✅
- RandomForestClassifier entrenado con accuracy=1.0, f1=1.0 ✅
- 606 VoterScores calculados ✅
**Detalles:**
- 16 alcaldías CDMX con secciones electorales
- 139 encuestas sintéticas
- Columna `data_source` agregada a ciudadanos
- Segmentos: 495 opositor, 90 promotable, 21 persuadible

## Sprint 4: Detección de bots (20 min) — COMPLETADO
**Objetivo:** Servicio básico de análisis de patrones sospechosos en seguidores/interacciones.
**Archivos:** `backend/app/services/bot_detection.py` (nuevo)
**Criterio:** Analizar lista de seguidores/posts y retornar score de probabilidad de bot.
**Resultado:** 
- 3 analizadores: username patterns, profile metadata, post patterns
- Signals: trailing_digits, suspicious_prefix, low_follower_ratio, content_duplication, regular_posting_interval, burst_posting, etc.
- Batch analysis para follower lists
- Test: bot ficticio → 1.0 score, Piña real → 0.05 score

## Sprint 5: Commit + tests + reporte (10 min) — COMPLETADO
**Criterio:** Tests pasan, PR actualizado, STATUS.md al día.
**Resultado:** 148 tests green.
