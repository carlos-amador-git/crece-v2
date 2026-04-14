# Plan Sprint NLP+Charts — 2026-04-13 tarde

**Origen:** `/sprint-review` sobre 4 acciones derivadas de auditoría sentiment + charts lab
**Branch:** `feat/sprint-c-hardening`
**Docs fuente:** `docs/AUDITORIA-SENTIMENT-2026-04-13.md`, `docs/NLP-MODELOS-INVESTIGACION.md`, `docs/CHARTS-LAB-DECISIONES.md`
**Estado:** CEO dio luz verde, ejecutando

---

## Las 4 acciones originales (del CEO)

1. Re-procesar 3,709 posts con `analyze_full()` (controversy + toxicity + topics + platform-adjusted)
2. LLM contextualizado Gemma3:12b con prompt tono+target+imagen por rol político
3. Reconstruir charts-lab persistente (Treemap, Stream, Sunburst) con datos reales
4. Fix RTs exclusion + dedup cross-platform en endpoints dashboard

---

## División en fases (revisada)

Re-ordené por **impacto/tiempo** y **paralelización**. La fase 4 del CEO (endpoints fix) va primero porque es rápida y desbloquea UI inmediatamente. La re-procesada de NLP va en background mientras se hace lo demás.

### FASE A — Preparación (10 min)
- **A.1** Verificar Ollama up + `gemma3:12b` cargado localmente
- **A.2** Smoke test `analyze_full()` sobre 3 posts variados (validar que HF models cargan)
- **A.3** Verificar versión de pysentimiento/torch en venv Python

**Criterio:** los 3 modelos HF cargan sin error, analyze_full devuelve dict completo para 3 posts.

### FASE B — Endpoints fix RTs + dedup (1h, PRIMERO por impacto/tiempo)
Ataca las anomalías #2 y #3 de la auditoría sin esperar al re-proceso NLP.

- **B.1** `dashboard.py /overview` — excluir RTs (`content NOT LIKE 'RT @%'`) + dedup `DISTINCT ON (content LEFT 100)` en agregación de avg_sentiment
- **B.2** `social.py /sentiment-timeline` — mismo filtro RT + dedup
- **B.3** `social.py /posts` — filtro `?exclude_rts=true` opcional
- **B.4** Excluir posts < 20 chars del avg_sentiment (nueva regla `length >= 20`)
- **B.5** Frontend: renombrar KPI "Sentimiento" → "Tono discursivo" con tooltip explicando
- **B.6** Verificación visual con Chrome DevTools: antes/después para MC-CDMX + GOB-OAXACA

**Criterio:** Piña avg cambia de -0.295 a ~-0.165, Solano cambia signo (-0.090 → +0.071). Tooltip explica.

### FASE C — Re-proceso analyze_full (background, 2-4h)
Desbloquea los 4 campos faltantes (controversy, toxicity, topics, platform-adjusted).

- **C.1** Migration Alembic: agregar columnas a `social_posts`:
  - `controversy_score FLOAT`
  - `toxicity_score FLOAT`
  - `topics JSONB` (lista de `{label, score}`)
  - `platform_adjusted_sentiment FLOAT`
  - `nlp_model_version VARCHAR(50)` ("multi-model-v1")
- **C.2** Script `backend/scripts/reprocess_nlp_full.py`:
  - Query posts con `nlp_model_version IS NULL OR != 'multi-model-v1'`
  - Llama `analyze_full(content, platform=sp.platform.lower())`
  - Persiste 5 nuevos campos
  - Idempotente (skip si ya procesado con v1)
- **C.3** Smoke test con 50 posts primero, validar output
- **C.4** Batch full 3,709 posts en background, log cada 100
- **C.5** Query verificación: distribución topics, toxicity media, controversy media

**Criterio:** 3,709 posts con los 4 campos nuevos poblados, topics cubren 8 categorías, ≥ 80% posts con al menos 1 topic.

### FASE D — LLM contextualizado Gemma (background + foreground iterativo, 3-5h)
Ataca la anomalía #1 (sentimiento técnico ≠ imagen política).

- **D.1** Diseño prompt v1 con el CEO en este chat (tono + target + imagen_dirigente + relevancia)
- **D.2** Script piloto `backend/scripts/llm_contextual_pilot.py` sobre 20 posts mezcla (5 Piña + 5 Cravioto + 5 Pineda + 5 RTs)
- **D.3** Revisar output, iterar prompt con el CEO (2-3 rondas)
- **D.4** Migration: `social_posts` agrega columnas `tono_discurso`, `target_politico`, `imagen_dirigente`, `relevancia_politica`, `llm_razon`, `llm_modelo`
- **D.5** Script batch full `backend/scripts/llm_contextual_batch.py`:
  - Recibe rol del dirigente (oficialismo/oposición/independiente) de `dirigentes.partido` + heurística
  - Llama Ollama local vía HTTP POST
  - Parsea JSON response, persiste
  - Reintentos con backoff
- **D.6** Batch en background sobre 3,709 posts (estimado 4-5h Mac M-series)
- **D.7** Agregado: por dirigente, distribución de tonos + target más frecuente + avg imagen_dirigente

**Criterio:** 3,709 posts con tono clasificado, 95%+ con target coherente, CEO valida 20 posts pilot.

### FASE E — Charts lab persistente (2h)
Reconstruye el HTML perdido con datos reales.

- **E.1** Crear `tools/charts-lab/index.html` con Plotly CDN
- **E.2** Fetch a API local para traer:
  - Engagement por plataforma por dirigente (para Treemap)
  - Sentiment timeline con nuevas métricas (para Stream)
  - Jerarquía dirigente→plataforma→post_type (para Sunburst)
- **E.3** 3 gráficos renderizados, interactivos (filtros, toggle leyenda, tooltip)
- **E.4** Control: selector de org + período + dirigente
- **E.5** README explica cómo correrlo (servir con `python -m http.server`)

**Criterio:** `tools/charts-lab/index.html` persiste en repo, abre en navegador, datos reales de la DB.

### FASE F — Dashboard integration (foreground, 2-3h)
Mueve los 3 gráficos del lab al dashboard donde corresponda.

- **F.1** Componente `<EngagementTreemap />` en `frontend/src/components/charts/`
- **F.2** Componente `<SentimentStream />` con toggle global + por plataforma
- **F.3** Componente `<DirigenteSunburst />` jerarquía
- **F.4** Asignación a páginas según el mapeo de `docs/CHARTS-LAB-DECISIONES.md`:
  - Treemap → `/dashboard` (overview)
  - Stream → `/dashboard/social`
  - Sunburst → `/dashboard/dirigentes` (o `/dashboard/radiografia` nuevo)
- **F.5** Verificación visual Chrome, screenshots antes/después

**Criterio:** los 3 gráficos montados, usan hooks de react-query con org scoping, screenshots guardados.

### FASE G — Documentación + Cierre (30 min)
- **G.1** Actualizar `.context/STATUS.md` con resultados
- **G.2** Registrar decisiones en `.context/DECISIONS.md` (prompt LLM, rol política heurística)
- **G.3** Commit final con granularidad por fase
- **G.4** Reporte al CEO

---

## Dependencias y paralelización

```
FASE A (setup 10min)
  │
  ├──> FASE B (endpoints fix 1h) ──> listo para UI
  │
  └──> FASE C (re-proceso NLP 2-4h background) ──┐
                                                 │
          FASE D (LLM Gemma 3-5h background) ────┤
                                                 │
                  FASE E (charts lab 2h) ────────┤
                                                 │
                 FASE F (dashboard 2-3h) ────────┘
                                                 │
                                       FASE G (cierre 30min)
```

**Estrategia:** FASE B primero (rápido, alto impacto). FASE C y D corren en background mientras yo hago FASE E foreground. FASE F depende de C (para tener los datos) y E (para tener los componentes). FASE G al final.

---

## Recursos asignados

| Fase | Skill/Agent | Herramientas |
|---|---|---|
| A | python-expert, systematic-debugging | Bash, Ollama HTTP |
| B | backend, nextjs15, frontend | Edit, Bash, Chrome DevTools |
| C | pgvector, fastapi, python-expert | Alembic, psycopg2, analyze_full |
| D | ollama skill, claude-api, bullmq-specialist | Ollama HTTP, JSON parsing |
| E | frontend-design, ui-ux-pro-max | Plotly CDN, HTML |
| F | frontend, tailwindcss4, nextjs15 | Recharts/Plotly, shadcn-ui |
| G | technical-writer | Edit, git |

---

## Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| HF models no cargan (memoria/red) | Media | graceful degradation — skip campo específico, no bloquear batch |
| Ollama Mac local se congela con 3,709 prompts | Media | Batch con retries + checkpoint cada 100 posts |
| Prompt LLM produce JSON malformado | Alta | regex recovery + fallback neutral, log todos los fallos |
| Charts lab Plotly CDN offline | Baja | fallback a versión local en node_modules |
| Dashboard chart F.1 rompe existing page | Media | feature flag, deploy gradual |

---

## Cross-audit Gemini (aplicado 2026-04-13)

Gemini identificó 4 mejoras válidas, todas integradas:

### G1: Schema de C y D debe estar finalizado ANTES de empezar E
**Fix:** Agregar sub-tarea "C.0 DEFINIR SCHEMA" al inicio de C. El schema exacto se documenta en el PLAN antes de ejecutar migration, así E puede diseñar fetch con ese contrato.

### G2: Migration C debe ser robusta con rollback
**Fix:** Alembic auto-genera rollback. Añadir test: correr upgrade → downgrade → upgrade en DB de prueba antes de producción.

### G3: D necesita criterio de calidad medible (validación humana)
**Fix:** Nuevo criterio en D: 20 posts piloto validados por CEO (acepta/rechaza tono y target). Umbral: ≥ 16/20 correctos para aprobar prompt y ejecutar batch full.

### G4: Resiliencia Ollama batch 8h + consumo Mac
**Fix:**
- Script `llm_contextual_batch.py` con checkpoints cada 50 posts en DB
- Resume desde último procesado al reiniciar
- Correr con `nice -n 15` para baja prioridad CPU
- Monitor cada 15 min: si Mac load_avg > 6.0, pausar batch

### G5 (extra): E con mock data para desacoplar
**Fix:** E.1-E.3 pueden arrancar con `/tools/charts-lab/mock-data.json` (generado de schema C/D). Validar gráficos independientemente, luego conectar a API real en E.4.

---

## Schema nuevo de columnas — social_posts (final, post-Gemini)

```sql
-- FASE C
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS controversy_score FLOAT;
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS toxicity_score FLOAT;
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS topics JSONB;  -- [{label, score}, ...]
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS platform_adjusted_sentiment FLOAT;
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS nlp_model_version VARCHAR(50);

-- FASE D
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS tono_discurso VARCHAR(20);
  -- enum: 'critico', 'propositivo', 'celebratorio', 'informativo', 'solidario', 'ataque', 'personal'
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS target_politico VARCHAR(50);
  -- enum: 'gobierno', 'oposicion', 'ciudadania', 'medios', 'autopromocion', 'tema_especifico', 'otro'
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS imagen_dirigente SMALLINT;
  -- -2 a +2: proyección de imagen política
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS relevancia_politica SMALLINT;
  -- 0 a 10
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS llm_razon TEXT;
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS llm_modelo VARCHAR(50);
  -- 'gemma3:12b-v1', etc.
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS llm_processed_at TIMESTAMP;
```

