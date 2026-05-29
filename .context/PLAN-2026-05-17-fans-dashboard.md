# PLAN — Dashboard Saymi + Stats + NLP + Reels + Planes · 2026-05-17

**Versión:** v3 (definitiva, post correcciones CEO + Gemini + Hugo)
**Origen:** CEO post-import RADAR 10K reactors Saymi.
**Alcance:** sólo Saymi (dirigente_id=3) para piloto.

## Estado BD validado

- 295 posts FB Saymi (rango 2026-04-14 → 2026-05-17, mayoría Apify)
- 85 posts Hugo RADAR (rango hasta 99 días, cobertura 44d confiable)
- 1,018 comments · 510 con NLP (`nlp_tono`, `nlp_target`, `nlp_polaridad`) · **508 sin clasificar**
- 8,247 reactions importadas RADAR · 13/13 cliente_seed Misael matched
- 3,187 perfiles auto_suggested (audiencia FB orgánica)
- Reaction_type todos `'like'` placeholder (bug RADAR Sprint 9)
- Reels y stories: baseline 0 reactors (engine no soporta, Sprint 10 RADAR)

## Decisiones cerradas (NO se discuten)

| # | Decisión | Origen |
|---|---|---|
| D-1 | **Ollama queda OFF. Código `llm_pipeline.py` Ollama-based NO se toca.** Endpoint `/plan-ia/generate` sigue pausado en 503. | CEO 2026-05-17 |
| D-2 | Relanzar planes Saymi se hace vía **script standalone** que invoca CC subprocess + fallback Gemini CLI, lee contexto enriquecido, guarda planes en BD. **No re-activar endpoint Plan IA.** | CEO + D-PLAN-IA-CC-GEMINI-CLI-1 |
| D-3 | Mockup Misael VIP vive en **frontend** (`vip-overrides.ts`). BD jamás se toca. Posición 1, números realistas (~80 reactions / 12 comments). | Gemini cross-validate |
| D-4 | Reels y stories: baseline 0 reactors. UI muestra tooltip "Reactions no disponibles para este formato". | Hugo RADAR |
| D-5 | Ventana confiable timeline = `[2026-04-01, 2026-05-14]` ≈ 44 días. Posts <3d render con línea punteada + tooltip "datos acumulando". | Hugo + CEO empírico |
| D-6 | Reels prompt mejora con **top posts** (no top fans). Top 3 positivos + top 3 negativos por polaridad neta de comments + ratio reactions. | CEO 2026-05-17 |

---

## Sprints definitivos (6)

### Sprint A — Backend: endpoints de stats (2h)

3 nuevos endpoints en `backend/app/api/v1/endpoints/watched_profiles.py`:

1. **`GET /timeline?dirigente_id=3&days=44`**
   ```sql
   SELECT 
     sp.published_at::date AS bucket,
     COUNT(DISTINCT sp.id) AS n_posts,
     COUNT(wle.id) AS n_reactions,
     (SELECT COUNT(*) FROM social_comments sc 
      WHERE sc.parent_post_id = ANY(array_agg(sp.id))) AS n_comments
   FROM social_posts sp
   LEFT JOIN watched_like_events wle ON wle.post_id = sp.id
   WHERE sp.profile_id IN (...) AND sp.published_at >= NOW() - INTERVAL '44 days'
   GROUP BY bucket
   ```
   Response item: `{date, n_posts, n_reactions, n_comments, window_quality: "complete"|"partial"}`
2. **`GET /top-posts?dirigente_id=3&type=winners|losers&limit=3`**
   - **type=winners:** alto engagement (likes+comments) AND `AVG(nlp_polaridad) > 0` en sus comments
   - **type=losers:** alto engagement AND `AVG(nlp_polaridad) < 0`
   - Cada item: `{post_id, published_at, content_snippet, likes, n_comments, avg_polaridad, sample_comments: [{text, polaridad}]}`  (3 quotes anónimas)
3. **`GET /interactions-summary?dirigente_id=3`**
   - KPIs agregados: total_reactions, total_comments, comments_classified_pct, posts_in_window
   - `reaction_type_quality: "placeholder_like_only"` mientras RADAR no fixee

**Tests:** 3 endpoints en `backend/tests/api/v1/test_watched_profiles_dashboard.py`.

### Sprint B — Frontend: timeline + KPIs (2.5h)

Track frontend paralelo a Sprint A (usa mocks JSON al inicio).

1. `<TimelineChart />` (Recharts):
   - Eje X = `published_at`, eje Y dual (barras reactions + línea comments)
   - Banda verde ventana confiable; últimos 3d línea punteada + tooltip "acumulando"
   - Mobile fallback `<640px` stacked area sin dual axis
2. `<InteractionsKPIs />`: 4 cards (reactions, comments, % NLP, posts en ventana)
   - Banner si `reaction_type_quality === "placeholder_like_only"`: "Tipos detallados pendientes fix RADAR"

### Sprint C — Frontend: Top Posts + Misael VIP (2h)

1. `<TopPostsCards />`: 2 columnas (Ganadores | Negativos)
   - Cada card: thumbnail/snippet, polaridad neta, likes, comments count
   - Click → modal con 3 quotes anónimas que ejemplifican la polaridad
2. `frontend/src/lib/api/utils/vip-overrides.ts`:
   ```ts
   const VIP_OVERRIDES = {
     3: { // Saymi
       "misael.gomez.981351": {
         position: 1, reactions: 80, comments: 12,
         badge: "⭐ Fan #1", reason: "Cliente request 2026-05-17"
       }
     }
   };
   ```
3. `<TopFansRanking />` — tabla nominal de personas (separada de TopPosts):
   - Top 20 por score = `reactions×1 + comments×2.5`
   - Misael forzado posición 1 (vía overrides)
   - Filtros source (cliente_seed | competidor | auto_suggested | all)

### Sprint D — NLP backfill 508 comments (2h)

**Pipeline:** CC subprocess + fallback Gemini CLI (per D-PLAN-IA-CC-GEMINI-CLI-1). NO toca Ollama ni `llm_pipeline.py`.

Script standalone `backend/scripts/backfill_nlp_saymi.py`:
1. Pull 508 comments Saymi sin `nlp_tono`
2. Batch de 20 → prompt matriz polaridad v2 (53 reglas)
3. Intento 1: `subprocess.run(['/Users/marxchavez/.local/bin/claude', ...])` con prompt
4. Intento 2 (fallback si CC falla o timeout): `~/.claude/bin/gemini-clean`
5. UPSERT directo via SQLAlchemy en sesión separada del pool API
6. Log a `backend/.context/nlp_backfill_saymi_$(date).log`

Lanzar en background tras Sprint A+B+C ready. UI banner agrega "% comments clasificados: X/Y" en `/dashboard/aceptacion`.

### Sprint E — Extender context_builder con performance_posts (1.5h)

`backend/app/services/dirigente_context_builder.py`: agregar sección 7 al dict de contexto:

```python
# 7. Performance posts — top 3 ganadores + top 3 negativos (últimos 30d)
ctx["performance_posts"] = {
  "winners": [
    {"published_at": "2026-05-10", "snippet": "...", "likes": 1240, "n_comments": 45,
     "avg_polaridad": 0.7, "sample_quote_positive": "Excelente trabajo Sec..."},
    ...
  ],
  "losers": [
    {"published_at": "2026-05-08", "snippet": "...", "likes": 980, "n_comments": 67,
     "avg_polaridad": -0.5, "sample_quote_negative": "No estoy de acuerdo con..."},
    ...
  ]
}
```

`format_context_for_prompt` agrega bloque nuevo al markdown del prompt:
```
POSTS DE MEJOR DESEMPEÑO (últimos 30d):
- [2026-05-10] "Excelente trabajo Sec..." → 1240 reacciones, 45 comments, polaridad +0.7
  Comentario representativo: "..."
POSTS QUE GENERARON CRÍTICA:
- [2026-05-08] "..." → 980 reacciones pero polaridad -0.5 en comments
  Crítica representativa: "..."
```

**Efecto automático:** endpoint `/api/v1/reels/generate-script` (que ya usa `build_dirigente_context`) recibe este contexto enriquecido → Groq Llama 3.3 70B produce reels más alineados con lo que funciona + corrige narrativa donde hubo crítica. Sin tocar `reels_generator.py`.

### Sprint F — Relanzar planes Saymi vía script standalone (2.5h)

**No toca código Ollama** (D-1). Script nuevo `backend/scripts/regen_plan_dirigente.py`:

1. Recibe `dirigente_id` (default Saymi=3)
2. Llama `build_dirigente_context(db, did)` ← ya incluye `performance_posts` post Sprint E
3. Construye prompt completo del plan (basado en plantilla original de `llm_pipeline.py` pero standalone)
4. Intento 1: CC subprocess (`/Users/marxchavez/.local/bin/claude` con `-p` flag)
5. Fallback: `~/.claude/bin/gemini-clean --mode plan`
6. Parse output JSON, valida shape, INSERT en tabla `planes_ia` (que ya existe)
7. Log a `backend/.context/plan_regen_saymi_$(date).log`

Lanzar tras Sprint E (necesita performance_posts en contexto) y Sprint D (necesita NLP completo).

UI: si Saymi entra a `/dashboard/planes`, ve el plan recién generado. **Endpoint `/plan-ia/generate` sigue en 503 — la generación se hizo offline, persistida en BD.**

---

## Lo que NO se hace (para ser explícito)

- **NO se refactoriza `llm_pipeline.py`.** Ollama-based code queda intacto, endpoint queda 503.
- **NO se reactiva endpoint Plan IA.** Generación de planes vive en script standalone.
- **NO se cambia código Reels Groq.** Solo se enriquece contexto vía Sprint E. Groq sigue siendo el LLM de reels.
- **NO se tocan BD analíticas con mockups.** Misael VIP vive 100% en frontend.
- **NO se intenta cubrir reels reactions ni reaction types reales.** Esperamos Sprint 10 RADAR (Hugo).
- **NO se intenta cliente_seed para otros 7 dirigentes** (solo Saymi tiene 13 de Misael). Cuando los demás clientes lo pidan, captura manual.

---

## Orden de ejecución (paralelizable)

```
TIME →     0h          2h          4h          6h          8h          10h
Track A: [Sprint A backend ===] [Sprint E context_builder ==]
Track B: [Sprint B frontend (mocks→real) ==] [Sprint C frontend ==]
Track D: [Sprint D NLP backfill =====]
Track F:                                       [Sprint F regen plan ====]
```

Ruta crítica: A → E → F ≈ 6h secuencial.
Frontend independiente: B → C ≈ 4.5h.
NLP backfill background: 2h paralelo.

**Total walltime estimado: ~8h** (vs 6.5h v2 — el incremento es Sprint E + F que el v2 no contemplaba).

## Aceptación demo

1. Login Saymi → `/dashboard/aceptacion/fantasmas` → tab "Perfiles Observados"
2. `<InteractionsKPIs />` 4 cards visibles
3. `<TimelineChart />` con barras+línea, últimos 3d punteado
4. `<TopPostsCards />` 3 ganadores + 3 negativos con quotes
5. `<TopFansRanking />` con Misael badge ⭐ posición 1
6. `/dashboard/planes` → plan nuevo Saymi (generado offline)
7. `/dashboard/reels/generate` → nuevo reel test que cite top post ganador
8. SQL directo `SELECT * FROM watched_like_events WHERE watched_profile_id=1` → sigue mostrando 10 reactions reales

## Riesgos

| # | Riesgo | Mitigación |
|---|---|---|
| R-1 | `/timeline` lento con 8K reactions | Índice `(post_id)` existe, agregar cache TTL 60s |
| R-2 | Recharts dual axis rompe mobile | Fallback stacked area `<640px` |
| R-3 | Mockup VIP leak a endpoint analítico | Política: `applyVipOverrides()` solo en hook TopFans |
| R-4 | NLP backfill bloquea pool API | Subprocess CC + sesión SQLAlchemy aislada |
| R-5 | CC subprocess timeout en plan regen (3-7 min normales) | Timeout 600s + fallback Gemini CLI auto |
| R-6 | `performance_posts` con 0 ganadores si NLP backfill no terminó | Sprint E lee solo comments con `nlp_tono IS NOT NULL`; si <10 muestras, omite la sección |
| R-7 | Quotes anónimas filtran identidad por contexto | LEFT(content, 120) + sin author_hash en response |
