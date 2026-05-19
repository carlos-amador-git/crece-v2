# Content Intelligence — Research 2026-05-15

> Investigación profunda para módulo **Content Intelligence** de CRECE v2.
> Tiempo invertido: ~2h. Premisa CEO: **calidad > tiempo**. Reporta riesgos antes de optimismos.
> Autor: Deep Research Agent (dispatched por SuperClaude Agent en CRECE v2).

---

## Resumen ejecutivo (10 líneas)

1. **Topic extraction:** BERTopic con `paraphrase-multilingual-MiniLM-L12-v2` + representación con Claude vía LiteLLM. ~5 min sobre 5000 posts en M-series. Alternativa rápida: KeyBERT puro (sin clustering).
2. **Recommendation engine:** híbrido **feature-engineered (gradient boosting) + RAG (pgvector) + LLM re-ranking con Claude**. No reinventar — usar Surprise/LightFM solo si añadimos colaborativo (no aplica al caso CRECE).
3. **Stack LLM:** **Gemini 2.5 Pro para análisis batch de patrones** (1M context, batch API −90% costo) + **Claude para generación creativa** (post final, brand voice). Prompt caching en Anthropic ahora **TTL = 5 min default** → diseñar burst en lugar de spread.
4. **Reuso MD:** `md-design-system/StatCard + BentoGrid + ChartContainer`, `md-research/scrapers` (ya integrados), `last-30-days` skill como benchmark UX, `pgvector` skill para embeddings store. CRECE ya tiene `embeddings.py` y `content_factory.py` (599 LOC) — extender, **no reemplazar**.
5. **Estimación realista:** 5–7 sprints (10–14 días) si premisa es calidad. Topic mining (1.5 días), feature mining temporal (1 día), recommendation MV+API (2 días), generador con brand voice (2 días), UI con heatmap+top cards (2 días), evals (1 día), compliance/etiquetado (1 día). NO comprimir.
6. **Riesgos top 3:**
   - **R1 (alto):** "Best time to post" sobre <500 posts/plataforma/dirigente es **ruido estadístico**. Saymi (1157 TT) sí cumple; Solano (77 IG) NO. Hay que rechazar el patrón cuando n<200 con UI explícita.
   - **R2 (alto):** Reforma LFPDPPP 2026 exige aviso de privacidad detallado sobre algoritmos + derecho a oposición a decisiones automatizadas. Sugerencias de contenido son borderline — bloquearlas si el dirigente no consintió.
   - **R3 (medio):** Veda electoral INE — sugerencias DEBEN suspenderse 3 días antes del día E. Etiquetado IA obligatorio (ya cumplido vía `modelo_ia` + `ia_content_registry`).

**Contraindicación crítica al CEO:** Saymi y Ballesteros tienen volúmenes muy distintos. Un único umbral global de "patrón confiable" no funciona. Recomendación: **scoring de confianza por dirigente×plataforma** mostrado en UI ("patrón débil n=23 vs robusto n=1157").

---

## Bloque 1 · Topic extraction & recommendation engines

### 1.1 Topic extraction — comparativa para CRECE

| Lib | Estrellas | Setup MX-ES | Velocidad 5K posts | Salida | Recomendación |
|---|---|---|---|---|---|
| **BERTopic** | 6.7K | Excelente — `language="multilingual"` activa MiniLM ES por default | 3–5 min en M4 (CPU). 88% del tiempo es encoding | Topics + scores + reps LLM | ★★★★★ **Primary** |
| **KeyBERT** | 3.5K | Excelente — usa mismos embeddings | <1 min | Keywords ranked por similaridad | ★★★★ Fallback / complemento |
| **Top2Vec** | 3.0K | Bueno | 4–6 min | Topics + jerarquía | ★★★ Trade-off no compensa vs BERTopic |
| **LDA (gensim)** | — | Pobre — requiere tokenización ES manual | <1 min | Topics word-based | ★★ Solo si necesitamos baseline interpretable |

**Decisión recomendada:** **BERTopic con LiteLLM→Anthropic** para etiquetas humanas. Pipeline:
1. `SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")` para embeddings (CRECE ya usa el mismo modelo en `services/embeddings.py`).
2. UMAP + HDBSCAN default.
3. `representation_model = LiteLLM(model="claude-haiku-4-5")` para labels en español.
4. Persistir topic_id, topic_label, top_keywords, prob, embedding en tabla nueva.

**Justificación contra reinventar:** la regla del CLAUDE.md prohíbe escribir parsing custom de NLP cuando existe lib. BERTopic = 6.7K★, mantenido, soporta Claude oficialmente.

Fuentes:
- BERTopic Multilingual: https://maartengr.github.io/BERTopic/getting_started/embeddings/embeddings.html
- BERTopic LLM Representation: https://maartengr.github.io/BERTopic/getting_started/representation/llm.html
- Scalability con LightLLM/Anthropic: https://bertopic.com/how-scalable-is-bertopic-for-large-datasets/
- Benchmark BERTopic vs LDA/Top2Vec: https://www.researchgate.net/publication/377129120

### 1.2 Recommendation engine — enfoque

Tres approaches considerados:

| Approach | Cómo modela | Pro | Con | Aplica a CRECE? |
|---|---|---|---|---|
| **Feature-engineered + gradient boosting** | Features: hora, día, longitud, hashtags, tema, tipo media, sentimiento. Target: engagement_rate normalizado. Modelo: LightGBM | Interpretable. Funciona con <5K rows. SHAP para explicar "por qué este post". | No genera contenido; solo predice. | ★★★★★ |
| **RAG embedding-based** | Embeddings de posts históricos top-decile. Para sugerir, busca k-NN del prompt del dirigente y compone con Claude. | Captura "estilo del dirigente". CRECE ya tiene `embeddings.py` + pgvector. | Sesgo al pasado — no innova. | ★★★★ (complemento) |
| **Colaborativo (LightFM, Surprise)** | Matriz dirigente×topic×engagement | — | **NO aplica** — n=6–10 dirigentes es muy pequeño. | ★ Descartar |

**Decisión:** **híbrido feature-engineered (LightGBM) para "qué características funcionan" + RAG con pgvector para "ejemplos similares" + Claude para "redacta el post final basado en estas señales"**.

Refs:
- `Social-Media-Capstone/Social-Media-Engagement-Forecasting` (GitHub): https://github.com/Social-Media-Capstone/Social-Media-Engagement-Forecasting — usa NLP + time series, validamos enfoque.
- `anujeshify/Social-Media-Engagement-Analyzer`: Random Forest sobre features sentimiento+likes+retweets.
- LightFM: https://github.com/lyst/lightfm (descartado para CRECE — pero referencia útil).

### 1.3 Optimal posting time — análisis serio

**Hallazgo crítico:** Buffer analizó 9.6M posts IG (200K cuentas) para su State of Engagement 2026. Sprout analizó 2B engagements / 307K perfiles. **CRECE tiene 4895 posts total, ~800 por dirigente máximo (Saymi).** Para "best time" con confianza estadística por dirigente×plataforma×hora-del-día, necesitamos por lo menos ~200 posts en esa celda (10 buckets × 7 días × 24h = 1680 buckets — claramente n insuficiente).

**Approach realista:**
1. **No** "predecir mejor hora" con un modelo. Sí **describir percentil 75 de engagement** por (day_of_week × bucket_3h) con CI bootstrap.
2. Cuando n<50 en celda → marcar como "datos insuficientes" en UI.
3. Usar **Prophet** para detectar tendencia + estacionalidad semanal sobre el agregado del dirigente. NO sobre buckets pequeños.
4. Reusar **last-30-days** skill como inspiración de presentación temporal.

Fuentes:
- Buffer 2026 (9.6M posts metodología): https://buffer.com/resources/when-is-the-best-time-to-post-on-instagram/
- Sprout 2026 (2B engagements): https://sproutsocial.com/insights/best-times-to-post-on-social-media/
- Hootsuite "Best Time to Publish" usa 30 días: https://www.hootsuite.com/platform/best-time-to-post-on-social-media
- Prophet docs: https://facebook.github.io/prophet/

---

## Bloque 2 · Cookbooks Anthropic + Gemini

### 2.1 Anthropic claude-cookbooks (https://github.com/anthropics/claude-cookbooks)

Cookbooks directamente aplicables:

| Cookbook | Path | Aplicación CRECE |
|---|---|---|
| `capabilities/classification/` | clasificar tópicos políticos | Reusar para refinar `political_framework.py` |
| `capabilities/summarization/` | multi-shot, chunking, multi-doc | Resúmenes "qué funcionó este mes para X dirigente" |
| `capabilities/retrieval_augmented_generation/` | contextual embeddings | **Patrón base del sugeridor de posts** |
| `misc/prompt_caching.ipynb` | cache 5min ephemeral | **Crítico** — para batch de generación post |
| `misc/how_to_enable_json_mode.ipynb` | output estructurado | Output de "5 razones por las que este post funcionará" |
| `misc/building_evals.ipynb` | evals automatizados | **Necesario** para validar calidad antes de mostrar al usuario |
| `multimodal/using_sub_agents.ipynb` | sub-agentes | Dividir: extractor de patrón → generador → validador |

### 2.2 Anthropic knowledge-work-plugins/marketing (https://github.com/anthropics/knowledge-work-plugins/tree/main/marketing)

**Hallazgo importante:** Anthropic publicó un plugin oficial de marketing con skills equivalentes a casi todo lo que CRECE Content Intelligence va a construir:
- `/draft-content` → genera blog/social/email/landing
- `/campaign-plan` → calendarios + canales + métricas
- `/brand-review` → valida contra voice/style/messaging
- `/performance-report` → métricas + tendencias + recomendaciones

**Recomendación:** **NO reimplementar — leer los skills oficiales y adaptar los prompts del plugin** a contexto político MX. Esto reduce el sprint de generador de posts de 3 días a ~1 día.

### 2.3 Gemini cookbook (https://github.com/google-gemini/cookbook)

Notebooks aplicables:

| Notebook | Path | Aplicación |
|---|---|---|
| File Search RAG | `quickstarts/File_Search.ipynb` | Multi-doc grounding |
| Batch API (−90% costo) | `quickstarts/Batch_mode.ipynb` | **Procesar todos los 4895 posts en batch único** |
| Logs/Datasets | `examples/Datasets.ipynb` | Análisis de engagement masivo |
| Long-context patterns | https://gemilab.net/en/articles/gemini-advanced/gemini-long-context-practical-patterns | "lost-in-the-middle" + structured output |

### 2.4 Patrón híbrido Claude + Gemini recomendado

```
[Análisis batch trimestral con Gemini 2.5 Pro Batch API]
  ↓ extrae patrones de 4895 posts (1M context lo permite)
  ↓ output: JSON con "estos 12 patrones funcionan para Saymi en TT"
  ↓ costo: ~$0.50 por análisis (Batch −90% sobre Gemini Pro)

[Cache prompt en Anthropic 5 min]
  ↓ system prompt con brand voice + patrones detectados
  ↓ user input: "post sobre tema X"
  ↓ Claude Haiku 4.5 para variaciones
  ↓ Claude Opus solo si HITL pide rewrite premium
  ↓ etiqueta ia_content_registry.modelo_ia obligatoria
```

**Anti-patrón a evitar:** invocar Claude Opus para cada sugerencia. Usar Haiku 4.5 para draft + Opus para refine final si HITL lo pide.

Fuentes:
- Anthropic prompt caching 5-min TTL: https://dev.to/whoffagents/anthropic-silently-dropped-prompt-cache-ttl-from-1-hour-to-5-minutes-16ao
- Gemini Batch API: https://github.com/google-gemini/cookbook/blob/main/quickstarts/Batch_mode.ipynb
- Gemini long-context patterns: https://gemilab.net/en/articles/gemini-advanced/gemini-long-context-practical-patterns

---

## Bloque 3 · Reuso MD-ecosystem

### 3.1 Inventario aplicable

| Repo / skill | Componente | Cómo aplica a Content Intelligence | Esfuerzo integración |
|---|---|---|---|
| `crece-v2/backend/app/services/content_factory.py` | 599 LOC existentes. Tiene `ContentFactory.generate` + `_generate_with_ollama` + Anthropic + `list_temas_sugeridos` | **Extender, NO reemplazar.** Añadir `suggest_post_from_patterns(dirigente, platform, tema)`. | Bajo (extensión) |
| `crece-v2/backend/app/services/embeddings.py` | Pgvector setup | Reusar para RAG sobre posts históricos top-decile | Trivial |
| `crece-v2/backend/app/services/political_framework.py` | Marco 53 reglas (Sprint B) | Como categorizador secundario a topics BERTopic | Bajo |
| `crece-v2/backend/app/models/contenido.py` + `ia_content_registry.py` | Modelos ContenidoGenerado y trazabilidad IA | Cumplimiento INE/LFPDPPP ya resuelto. **No tocar.** | — |
| `md-research/scrapers/{twitter,instagram,facebook,tiktok,youtube}.py` | Scrapers maduros | Ya integrados a CRECE. No re-pegar. | — |
| `md-design-system/components/dashboard/StatCard.tsx` | Card métrica + delta | Top posts cards | Trivial |
| `md-design-system/components/dashboard/BentoGrid.tsx` | Layout bento | Layout dashboard Content Intel | Trivial |
| `md-design-system/components/dashboard/ChartContainer.tsx + ChartPalette.ts` | Wrapper Recharts | Heatmap hora×día | Bajo |
| `md-design-system/docs-kit/` | Generación de one-pagers/decks | "Exportar reporte de Content Intelligence a PDF" feature | Medio |
| `~/.claude/skills/pgvector/SKILL.md` | Patterns embeddings | RAG setup | Leer antes de codear |
| `~/.claude/skills/last-30-days/` | Investigación temporal | UX inspiración temporal | Mirar UI |
| `~/.claude/skills/kpi-dashboard-design/` | KPI design | Layout cards | Leer antes UI |
| `~/.claude/skills/fastapi/SKILL.md` | Endpoint patterns | Endpoints `/content-intel/*` | Leer antes codear |

### 3.2 Componente clave a reusar: `content_factory.py`

CRECE ya tiene 599 LOC en `services/content_factory.py` con:
- `_gather_dirigente_context()` — pull top posts del dirigente
- `_build_prompt()` — composición con constraints por plataforma
- `ContentFactory.generate()` + `generate_stream()` — Anthropic streaming SSE
- `list_temas_sugeridos()` — sugerencia de temas
- Soporte Ollama+Anthropic con fallback

**Implicación:** Content Intelligence NO es greenfield. Es **extender content_factory con un nuevo entry point `generate_from_patterns(dirigente_id, plataforma, tema, ventana)`** que primero consulta la materialized view de patrones, luego compone prompt con brand voice + patrones detectados, luego invoca Claude.

### 3.3 Lo que NO existe y hay que crear

- Tabla `content_patterns` (output BERTopic + agregados temporales)
- Materialized view `top_posts_by_dirigente_plataforma_ventana`
- Endpoint `/api/v1/content-intel/{top-posts,patterns,suggest,heatmap}`
- Celery beat task `compute_content_patterns` (cron diario 03:00)
- Frontend page `/dashboard/content-intel/[dirigente_id]`

---

## Bloque 4 · UX/UI benchmarks

### 4.1 Comparativa Sprout / Buffer / Hootsuite

| Patrón | Sprout | Buffer | Hootsuite | Recomendación CRECE |
|---|---|---|---|---|
| **Top posts** | Lista con thumbnail, métricas inline, tag plataforma, filtros (window/platform/format) | Cards con engagement bar, sort por métrica | Tabla con sort, "boost" badge | **Cards (estilo Buffer)** — más visual, mejor para dirigentes no técnicos |
| **Best time heatmap** | 7×24 heatmap calendario, hover muestra engagement | Heatmap con bandas de "ok/good/best" | Heatmap "best time to publish" basado en últimos 30 días | **Heatmap 7×8** (días × buckets 3h) con flag de "datos suficientes/insuficientes" |
| **Suggestion UI** | "Optimal Send Times" badge, AI suggestions inline | OwlyWriter modal con prompt + tone | OwlyWriter inline w/ "post ideas" | **Modal stepper:** patrón detectado → preview prompt → variaciones → editar → guardar borrador |
| **Content patterns** | "Top performing categories" donut | "Top hashtags" + "Avg engagement per format" | Reporte custom builder | **Cards apiladas:** Tema top + Formato top + Hora top + Longitud top (con n y confianza) |

### 4.2 Componentes shadcn / lucide / md-design-system mapeados

| UI element | Componente recomendado |
|---|---|
| Layout bento | `md-design-system/BentoGrid` |
| Top post card | `shadcn/Card` + `md-design-system/StatCard` (delta vs mediana) |
| Heatmap 7×8 | `shadcn-calendar-heatmap` (https://www.shadcn.io/template/gurbaaz27-shadcn-calendar-heatmap) — adaptar de 365×7 a 7×8 |
| Time series engagement | `shadcn/charts` (Recharts AreaChart) wrapped in `ChartContainer` |
| Filtros (window/platform) | `shadcn/Select` + `shadcn/Tabs` |
| Tabla patrones | `shadcn/DataTable` (tanstack) |
| Generador modal | `shadcn/Sheet` + `shadcn/Stepper` |
| Tag plataforma | `lucide-icons` (twitter, instagram, facebook, tiktok, youtube) + `shadcn/Badge` |
| Trazabilidad IA badge | `shadcn/Badge` "Generado por Claude Haiku 4.5" |

### 4.3 Anti-patrones del proyecto MD a evitar

Del `design-standards.md` global:
- No Inter/Roboto/Arial.
- No gradientes púrpura/blanco.
- Hover/focus/disabled obligatorios.
- Estados loading/empty/error obligatorios.
- WCAG AA mínimo.

Fuentes:
- Sprout vs Hootsuite UI 2026: https://sociality.io/blog/sprout-social-vs-hootsuite/
- Buffer best-time IG 2026: https://buffer.com/resources/when-is-the-best-time-to-post-on-instagram/
- shadcn calendar heatmap: https://allshadcn.com/tools/calendar-heatmap/
- shadcn charts (53 componentes): https://www.shadcn.io/charts

---

## Bloque 5 · Compliance México

### 5.1 LFPDPPP — reforma 2026

**Cambios relevantes (Executrain 2026 guide):**
1. **Aviso de privacidad ahora distingue Simplified vs Comprehensive.** El Comprehensive **debe explicar en lenguaje simple cómo funciona el algoritmo**.
2. **Derecho a oposición a decisiones automatizadas.** Si CRECE sugiere contenido al dirigente automáticamente, el dirigente puede pedir revisión humana.
3. **Transparencia algorítmica.** "Conocer si un humano intervino" es ahora derecho ARCO+.

**Aplicación a Content Intelligence:**
- ✅ El dirigente es **usuario operador**, no titular de datos terceros — el algoritmo opera sobre **sus propios posts públicos** + comentarios públicos. Bajo riesgo LFPDPPP de su lado.
- ⚠️ Si analizamos **comentarios ciudadanos** para extraer patrones (sentimiento de comentarios → ajustar sugerencia), **estamos procesando PII de terceros**. El aviso de privacidad de CRECE debe declararlo.
- ⚠️ Si en el futuro hay un módulo "sugiere a qué ciudadanos targetear" → entonces sí aplica decisión automatizada sobre PII.

**Recomendación:** módulo Content Intelligence v1 **NO debe usar comentarios ciudadanos directamente** (usar solo posts del dirigente). Si v2 los incorpora, añadir flag de consentimiento en aviso de privacidad.

### 5.2 INE veda electoral + IA

**Hallazgos:**
- INE aún consolidando lineamientos formales sobre IA en procesos electorales (acuerdo INE/CG334/2025).
- Contenido modificado/alterado por IA **debe etiquetarse** por su emisor. CRECE ya cumple vía `ia_content_registry` y campo `modelo_ia` (regla del proyecto).
- Durante **veda (3 días antes E + día E)**: no nueva propaganda. Las "sugerencias" automáticas de Content Intelligence **deben pausarse durante veda** si el dirigente está en proceso electoral.

**Aplicación:**
1. Endpoint `/content-intel/suggest` debe **rechazar con 403** si `dirigente.organizacion.veda_activa = true`.
2. UI debe mostrar banner "Veda activa — sugerencias deshabilitadas. Solo lectura."
3. Todo borrador generado debe tener flag `requiere_etiquetado_ia = true` (cumplimiento INE).

### 5.3 Trazabilidad IA — checklist obligatorio CRECE

| Campo | Tabla | Obligatorio? |
|---|---|---|
| `modelo_ia` (claude-haiku-4-5 etc) | ContenidoGenerado | Sí — regla CLAUDE.md |
| `prompt_hash` | ia_content_registry | Sí |
| `version_modelo` | ia_content_registry | Sí |
| `patrones_usados` (FK a content_patterns) | nuevo en ContenidoGenerado | **Recomendado nuevo** |
| `requiere_etiquetado_publico` | ContenidoGenerado | Sí — INE |
| `revisado_por_humano` + `revisor_user_id` | hitl_audit | Sí cuando aplica (HITL) |

Fuentes:
- Executrain LFPDPPP 2026 guide: https://executrain.com.mx/nueva-lfpdppp-2026-guia-cumplimiento-empresas-mexico/
- LFPDPPP texto: http://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf
- INE protocolos IA: https://centralelectoral.ine.mx/2025/07/18/ine-activa-protocolos-para-el-uso-responsable-de-inteligencia-artificial/
- INE acuerdo CG334/2025: https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/181780/CGex202503-29-ap-6.pdf

---

## Recomendación arquitectural concreta

### Stack final propuesto

```
NLP layer:
  - BERTopic + paraphrase-multilingual-MiniLM-L12-v2 (reusa embeddings.py)
  - Representación: LiteLLM → claude-haiku-4-5
  - KeyBERT como fallback rápido

Pattern mining layer:
  - Feature engineering: hora, día, longitud, hashtags, media_type, topic_id, sentimiento
  - LightGBM regressor → engagement_rate (interpretable con SHAP)
  - Estacionalidad: Prophet sobre serie agregada del dirigente (NO sobre buckets pequeños)

Recommendation layer:
  - Top-K patterns from materialized view
  - RAG: pgvector k-NN sobre top-decile históricos
  - Generación: Claude Haiku 4.5 (draft) + Claude Opus (refine on demand)
  - System prompt cached (TTL 5 min) — diseñar en bursts

Analysis batch:
  - Gemini 2.5 Pro Batch API trimestral para análisis profundo de N posts en 1M context

Backend:
  - FastAPI endpoints /api/v1/content-intel/*
  - Celery beat: compute_content_patterns 03:00 diario
  - Materialized view top_posts_window_view refresh 06:00

Frontend:
  - Next.js 14 App Router
  - md-design-system: BentoGrid, StatCard, ChartContainer
  - shadcn: Card, Sheet, Select, Tabs, DataTable, Badge
  - shadcn-calendar-heatmap (adaptado 7×8)
  - Recharts (vía ChartContainer)

Compliance:
  - ia_content_registry sigue siendo source of truth IA
  - Veda check antes de cualquier suggest
  - Aviso privacidad: actualizar si v2 usa comentarios ciudadanos
```

### Esquema BD propuesto

```sql
-- 1. Topics extraídos por BERTopic
CREATE TABLE content_topics (
  id SERIAL PRIMARY KEY,
  topic_label TEXT NOT NULL,            -- "Seguridad pública", "Movilidad"
  top_keywords TEXT[],
  embedding vector(384),                 -- centroide
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  computed_run_id UUID NOT NULL          -- agrupador del batch
);

-- 2. Asignación post → topic
CREATE TABLE social_post_topics (
  post_id BIGINT REFERENCES social_posts(id) ON DELETE CASCADE,
  topic_id INT REFERENCES content_topics(id),
  probability FLOAT,                     -- 0-1
  PRIMARY KEY (post_id, topic_id)
);

-- 3. Patrones detectados (output mining)
CREATE TABLE content_patterns (
  id SERIAL PRIMARY KEY,
  dirigente_id INT REFERENCES dirigentes(id),
  plataforma platform_enum NOT NULL,
  window_start DATE,
  window_end DATE,
  pattern_type pattern_type_enum,        -- 'hour', 'day', 'topic', 'length', 'hashtag', 'media_type'
  pattern_value JSONB,                   -- {"hour_bucket": "18-21", "median_eng": 0.045, "n": 234, "p_value": 0.012}
  confidence FLOAT,                      -- 0-1
  sample_size INT,                       -- crítico para UI "datos suficientes"
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. Materialized view top posts (refresh diario)
CREATE MATERIALIZED VIEW mv_top_posts_window AS
SELECT
  sp.dirigente_id,
  sp.plataforma,
  sp.id AS post_id,
  sp.content,
  sp.media_urls,
  sp.likes, sp.shares, sp.comments,
  sp.engagement_rate,
  sp.published_at,
  spt.topic_id,
  ROW_NUMBER() OVER (
    PARTITION BY sp.dirigente_id, sp.plataforma, date_trunc('week', sp.published_at)
    ORDER BY sp.engagement_rate DESC
  ) AS rank_in_week
FROM social_posts sp
LEFT JOIN social_post_topics spt ON spt.post_id = sp.id
WHERE sp.published_at >= now() - interval '12 months';

CREATE UNIQUE INDEX ON mv_top_posts_window (post_id, plataforma);
CREATE INDEX ON mv_top_posts_window (dirigente_id, plataforma, published_at DESC);

-- 5. Sugerencias generadas (extiende ContenidoGenerado existente)
ALTER TABLE contenidos_generados
  ADD COLUMN content_patterns_used INT[],   -- FK array a content_patterns
  ADD COLUMN sugerencia_origen TEXT;         -- 'content_intel' | 'manual' | 'plan_ia'
```

### Pipeline Celery propuesto

```python
# backend/app/workers/tasks.py (NUEVO bloque)

@celery_app.task(name="content_intel.compute_topics")
def compute_content_topics():
    """Diario 03:00 — corre BERTopic sobre posts últimos 90 días."""
    # 1. Pull posts (4895 actualmente, crece)
    # 2. BERTopic fit_transform con representación Claude
    # 3. Persiste content_topics + social_post_topics
    # 4. Emit metric: topics_count, avg_size

@celery_app.task(name="content_intel.mine_patterns")
def mine_content_patterns():
    """Diario 04:00 — extrae patrones por dirigente×plataforma×ventana."""
    # Por cada (dirigente, plataforma):
    #   - if n_posts < 50: skip y registra "insufficient_data"
    #   - else: agregados por hora/día/tema/formato/longitud
    #   - bootstrap CI para median engagement
    #   - persist content_patterns

@celery_app.task(name="content_intel.refresh_top_view")
def refresh_top_posts_view():
    """Diario 06:00 — refresh materialized view."""
    # REFRESH MATERIALIZED VIEW CONCURRENTLY mv_top_posts_window
```

### 3 alternativas con trade-offs

#### **Alternativa A — Stack completo recomendado** (BERTopic + LightGBM + RAG + Claude/Gemini híbrido)
- Pros: máxima calidad, interpretable, escala bien, reusa CRECE.
- Cons: 10–14 días setup, requiere Celery beat + materialized views.
- **Recomendada si la premisa CEO es calidad > tiempo.**

#### **Alternativa B — Lean (sin LightGBM, sin Gemini)**
- Solo BERTopic + agregados SQL + Claude para generación.
- Pros: 5–7 días setup, simple, suficiente para demo.
- Cons: no predicción de engagement, no SHAP, depende solo de patrones descriptivos.
- **Recomendada si hay piloto urgente.**

#### **Alternativa C — LLM-first (descartar BERTopic)**
- Pasar todo a Gemini 2.5 Pro 1M context: "estos son 4895 posts, extrae patrones y sugiere".
- Pros: 2–3 días setup, sin pipeline NLP.
- Cons: caro recurrente (1M context cada vez), poco interpretable, sin estado entre runs, ruptura de cache. Anthropic 5-min TTL agrava.
- **Descartada como primary. Útil para sanity-check trimestral.**

---

## Riesgos y mitigaciones

| ID | Riesgo | Severidad | Mitigación |
|---|---|---|---|
| R1 | "Best time" sobre n<200 = ruido | Alta | UI muestra n y confidence. Si n<50 → "datos insuficientes, sigue posteando". |
| R2 | LFPDPPP 2026 exige transparencia algoritmo | Alta | Aviso privacidad simple+comprehensive. Si v2 usa comentarios ciudadanos → consentimiento. |
| R3 | Veda INE pausa sugerencias | Media | Middleware checa `veda_activa` antes de suggest. UI banner. |
| R4 | Cache Anthropic 5min vs uso bursty | Media | Diseñar generador en bursts (batch de 10 sugerencias en <5min) en lugar de spread durante día. |
| R5 | BERTopic UMAP no determinístico | Baja | Fijar `random_state=42`. Versionar topic_id con `computed_run_id` para auditar. |
| R6 | Re-implementación de content_factory | Alta | Extender, NO reescribir. PR debe mostrar diff sobre el archivo existente. |
| R7 | Saymi (MORENA) vs MC dirigentes — sesgos | Media | Modelar **por dirigente**, NO global. No transferir patrones entre dirigentes diferentes partidos sin opt-in. |
| R8 | Quitar contenido sin etiquetado IA | Alta | `requiere_etiquetado_publico=true` por default. Toda sugerencia trae footer "Generado con asistencia de Claude". |

---

## Cosas que descarté y por qué

1. **Top2Vec** — comparable a BERTopic pero menos comunidad MX y peor integración con LLM. Sin razón para preferirlo.
2. **LDA puro** — interpretabilidad débil sin sentence-embeddings. Solo si necesitamos baseline auditable de 5 años atrás.
3. **LightFM / Surprise (colaborativo)** — requiere matriz user-item densa. n=6–10 dirigentes es absurdo para colaborativo. Descartado completamente.
4. **Implementar best-time sin gating de n** — produce recomendaciones falsas. Inaceptable según regla CLAUDE.md "no inventar datos".
5. **Gemini 1M context como motor primario** — caro, no determinístico, ruptura de cache. Solo úsalo en batch trimestral.
6. **Brand voice plugin de Anthropic full integration con Notion/Slack/Confluence** — overkill para CRECE. Adoptar **solo los prompts** del plugin, no la integración MCP completa.
7. **Reescribir content_factory.py** — 599 LOC funcionales. Sería violación de la regla "surgical changes" de Karpathy. Extender.
8. **NVTabular para feature engineering** — necesario solo a escala TB. Pandas + scikit basta para CRECE.
9. **Reentrenar embeddings con corpus político MX** — caro y de ROI dudoso con n=4895. `paraphrase-multilingual` ya funciona aceptablemente en ES.
10. **Generación con Ollama local como primary** — Ollama está OUT del stack CRECE según memoria reciente. Mantener solo como fallback dev.

---

## Próximos pasos sugeridos (para SuperClaude Agent / CEO)

1. **Decisión CEO:** Alternativa A (calidad, 10–14d) o B (lean, 5–7d).
2. Si A → crear `PLAN-2026-05-15-content-intelligence-sprint.md` con 6 fases:
   - F1 Topic extraction (BERTopic + Celery beat) — 1.5d
   - F2 Pattern mining (LightGBM + Prophet) — 2d
   - F3 Recommendation API (FastAPI + pgvector RAG) — 2d
   - F4 Generador con brand voice (extiende content_factory) — 2d
   - F5 Frontend dashboard (Next.js + shadcn + md-design-system) — 2d
   - F6 Compliance, evals, etiquetado IA, veda check — 1.5d
3. Antes de F1: leer skills oficiales `pgvector`, `fastapi`, `kpi-dashboard-design`, `nextjs15`, y plugin Anthropic marketing skills.
4. Validar contra Saymi (1157 TT) **y** Solano (77 IG) — el patrón Solano debe quedar con flag "insuficiente".

---

## Apéndice — fuentes consolidadas

### NLP / Topic
- BERTopic docs: https://maartengr.github.io/BERTopic/
- BERTopic LLM Representation: https://maartengr.github.io/BERTopic/getting_started/representation/llm.html
- BERTopic Scalability: https://bertopic.com/how-scalable-is-bertopic-for-large-datasets/
- KeyBERT: https://github.com/MaartenGr/KeyBERT
- Multilingual transformers + BERTopic short text: https://arxiv.org/pdf/2402.03067
- Top2Vec vs BERTopic vs LDA: https://www.researchgate.net/publication/377129120

### LLM cookbooks
- Anthropic claude-cookbooks: https://github.com/anthropics/claude-cookbooks
- Anthropic knowledge-work-plugins/marketing: https://github.com/anthropics/knowledge-work-plugins/tree/main/marketing
- Anthropic Brand Voice plugin: https://claude.com/plugins/brand-voice
- Google Gemini cookbook: https://github.com/google-gemini/cookbook
- Gemini long-context patterns: https://gemilab.net/en/articles/gemini-advanced/gemini-long-context-practical-patterns
- Anthropic prompt caching guide: https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- Anthropic 5-min TTL change: https://dev.to/whoffagents/anthropic-silently-dropped-prompt-cache-ttl-from-1-hour-to-5-minutes-16ao

### Engagement / time-series
- Buffer 2026 IG analysis (9.6M posts): https://buffer.com/resources/when-is-the-best-time-to-post-on-instagram/
- Sprout 2026 (2B engagements): https://sproutsocial.com/insights/best-times-to-post-on-social-media/
- Hootsuite Best Time tool: https://www.hootsuite.com/platform/best-time-to-post-on-social-media
- Prophet: https://facebook.github.io/prophet/
- Social Media Engagement Forecasting (GitHub): https://github.com/Social-Media-Capstone/Social-Media-Engagement-Forecasting

### UI / Components
- shadcn charts (53 componentes): https://www.shadcn.io/charts
- shadcn calendar heatmap: https://allshadcn.com/tools/calendar-heatmap/
- Social media dashboard kit shadcn: https://thefrontkit.com/apps/social-media-dashboard-kit

### Compliance MX
- LFPDPPP texto: http://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf
- Executrain LFPDPPP 2026 guide: https://executrain.com.mx/nueva-lfpdppp-2026-guia-cumplimiento-empresas-mexico/
- INE acuerdo CG334/2025 (uso IA): https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/181780/CGex202503-29-ap-6.pdf
- INE protocolos IA: https://centralelectoral.ine.mx/2025/07/18/ine-activa-protocolos-para-el-uso-responsable-de-inteligencia-artificial/
- INE lineamientos veda: https://centralelectoral.ine.mx/wp-content/uploads/2023/01/Lineamientos-en-materia-electoral-1.pdf

---

**Fin del reporte.** Total ~2h de research. Reporte cubre los 5 bloques solicitados + arquitectura concreta + 3 alternativas + 10 descartes justificados.
