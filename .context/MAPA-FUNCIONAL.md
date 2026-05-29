# MAPA FUNCIONAL — CRECE v2 (Manual de Operaciones de la app)

**Última actualización:** 2026-05-28
**Propósito:** referencia única de qué hace cada función, qué endpoint la sirve, qué service la computa, qué tablas lee, y qué deuda tiene. Antes de proponer cambio/feature, consultar este doc. Si algo no está acá, agregarlo antes de implementar.

**Convención de estado:**
- ✅ **Completo:** documentado a fondo, data real, FE renderiza.
- ⚠️ **Parcial:** existe pero con deuda conocida o data incompleta.
- ❌ **Placeholder:** existe en código pero no entrega valor real.
- 📝 **A documentar:** función identificada, falta profundidad en este doc.

---

## Índice

1. **Aceptación + Fans y Perfiles** — ✅ Documentado
2. **Recepción / Diagnóstico Tier 1 (B01-B10)** — ✅ Documentado
3. **FODA** — ✅ Documentado
4. **Planes IA (Diagnóstico + Estrategia + Contenido)** — ✅ Documentado
5. **Clima Político** — ✅ Documentado
6. **Recomendaciones · Mi Evaluación · Reels** — ✅ Documentado
7. **Overview + Dirigentes** — ✅ Documentado
8. **Diagnóstico Tier 2 (B11-B18)** — ✅ Documentado
9. **Configuración + Sistema** — ✅ Documentado
10. **Admin (no-cliente)** — ✅ Documentado

---

## 1. Aceptación + Fans y Perfiles ✅

**Concepto:** módulo que cuantifica la recepción real del público hacia el dirigente, distingue audiencia activa (comenta) de pasiva ("fantasmas" = follower que nunca comenta), y permite curar perfiles de fans para monitoreo continuo.

### 1.1 Vistas FE del sidebar

#### `/dashboard/aceptacion/` (Aceptación · lista dirigentes)
- **Archivo:** `frontend/src/app/dashboard/aceptacion/page.tsx`
- **Función:** muestra lista de dirigentes scoped a rol (admin = todos; viewer = su dirigente; analyst/viewer = org) con tarjeta de overview por cada uno (% activados, % fantasmas, polaridad).
- **Hook:** `useAceptacionOverview()` de `use-aceptacion.ts`
- **Endpoint backend:** `GET /api/v1/social/aceptacion/overview`
- **Response type:** `AceptacionOverview` — agregado por dirigente.

#### `/dashboard/aceptacion/[dirigente_id]/` (Detalle dirigente)
- **Archivo:** `frontend/src/app/dashboard/aceptacion/[dirigente_id]/page.tsx`
- **Función:** vista profunda de un dirigente. Pestañas con cards B0x específicos de aceptación.
- **Componente principal:** `components/aceptacion/dirigente-detail-content.tsx`
- **Cards visibles:** InteractionsKPIs (`reacciones`, `comments`, `% clasificados NLP`, `posts (histórico)`), TimelineChart (interacción diaria), Recepción del público (más favorable + más rechazo en comments).
- **Hooks usados:** `useIADirigenteSummary` (resumen IA por dirigente), `useWatchedTimeline` (serie temporal), `useWatchedSummary`.
- **Endpoints:** `GET /api/v1/social/dirigentes/{dirigente_id}/ia-summary`, `GET /api/v1/aceptacion/watched-profiles/timeline`, `GET /api/v1/aceptacion/watched-profiles/summary`.

#### `/dashboard/aceptacion/fans-y-perfiles/` (Fans y Perfiles)
- **Archivo:** `frontend/src/app/dashboard/aceptacion/fans-y-perfiles/page.tsx`
- **Función:** sub-vista donde se ven los Top Fans (ranking), perfiles observados curados, y sugerencias de comentaristas frecuentes para agregar a la lista.
- **Componentes principales:**
  - `top-fans-ranking.tsx` (ranking con score)
  - `watched-profiles-tab.tsx` (lista observados + tabs)
- **Hooks:** `useTopFans`, `useWatchedProfiles`, `useWatchedSummary`, `useWatchedEngagement`, `useWatchedSuggestions`, `useCompetitors`.
- **Endpoints involucrados:** ver tabla 1.2.

### 1.2 Endpoints backend del módulo

#### Índice de Aceptación (`backend/app/api/v1/endpoints/indice_aceptacion.py`)

| Endpoint | Response | Función | Hook FE |
|---|---|---|---|
| `GET /social/posts/{post_id}/ia` | `IAScores` | Índice IA para un post individual (% aprobación / rechazo / neutral basado en comments clasificados) | `useIAPost(post_id)` |
| `GET /social/dirigentes/{dirigente_id}/ia-summary` | `IADirigenteSummary` | Resumen IA agregado por dirigente (top posts aprobación + top rechazo) | `useIADirigenteSummary(dirigente_id)` |
| `GET /social/aceptacion/overview` | `AceptacionOverview` | Overview agregado por dirigente: activación, fantasmas, polaridad | `useAceptacionOverview()` |
| `GET /social/aceptacion/fantasmas-por-plataforma` | `list[DirigentePlatformFantasmas]` | **Fantasmas desglosado por (dirigente, plataforma)** | `useFantasmasPorPlataforma()` |

**Fórmula real de fantasmas** (verificado en código líneas 311-345 + 394-450):
```sql
unique_commenters = COUNT(DISTINCT social_comments.author_hash WHERE nlp_model_version IS NOT NULL)
pct_activados    = 100 × unique_commenters / followers_count
pct_fantasma     = 100 - pct_activados
                = % de followers que NO han comentado
```

Por plataforma: el mismo cálculo pero filtrando por `social_profiles.platform`. El "fantasma" se calcula sobre la audiencia (followers_count) que NO interactúa textualmente. NO requiere enrichment del perfil del fan (avatar/bio/etc.) — la métrica usa solo lo que ya tenemos.

Scope RBAC:
- `admin` → ve todos los dirigentes (sin filtro).
- `viewer` con `dirigente_id` → solo SU dirigente.
- `analyst` / `viewer sin dirigente` → todos los de su `org_id`.

#### Watched Profiles (`backend/app/api/v1/endpoints/watched_profiles.py`)

| Endpoint | Función | Hook FE |
|---|---|---|
| `GET /aceptacion/watched-profiles/` | Lista watched_profiles con filtros (source, platform, etc.) | `useWatchedProfiles(params)` |
| `POST /aceptacion/watched-profiles/` | Crear perfil observado manualmente (backend `watched_profiles.py:241`) | ⚠️ **Sin hook FE — deuda detectada por auditoría Gemini 2026-05-28** (no hay `useMutation` POST en `use-watched-profiles.ts`). |
| `PATCH /aceptacion/watched-profiles/{id}` | Editar tags / notes / source / is_active | `useUpdateWatched()` |
| `DELETE /aceptacion/watched-profiles/{id}` | Eliminar (soft o hard) | `useDeleteWatched()` |
| `GET /aceptacion/watched-profiles/summary` | Resumen por dirigente (counts agregados) | `useWatchedSummary(dirigente_id)` |
| `GET /aceptacion/watched-profiles/{id}/engagement` | Historial de likes + comments del fan a posts del dirigente | `useWatchedEngagement(id)` |
| `GET /aceptacion/watched-profiles/suggestions` | Comentaristas frecuentes (≥2 comments) sugeridos para agregar a lista | `useWatchedSuggestions(dirigente_id, min_comments, limit)` |
| `GET /aceptacion/watched-profiles/top-fans` | Ranking top fans por score = reactions×1 + comments×2.5 | `useTopFans(params)` |
| `GET /aceptacion/watched-profiles/timeline` | Serie temporal `interactions/day` por ventana de N días | `useWatchedTimeline(dirigente_id, days, platform)` |
| `GET /aceptacion/watched-profiles/top-posts` | Top posts por engagement de la audiencia observada | (vía componente) |
| `GET /aceptacion/watched-profiles/interactions-summary` | KPIs agregados (reactions/comments/posts histórico) | (vía `InteractionsKPIs`) |
| `POST /aceptacion/watched-profiles/ingest-reactions-bulk` | **Bulk ingest de reactions externas** (scrapers Juan FB browser-harness, etc.) (`watched_profiles.py:949-950`, comentario S-8.1) | ⚠️ Sin hook FE — usado por scripts externos, no consumido por dashboard. |

### 1.3 Tablas DB que el módulo lee/escribe

| Tabla | Uso |
|---|---|
| `dirigentes` | Identidad + rol_politico + scope org |
| `social_profiles` | `followers_count` (denominador de % activados/fantasmas) por dirigente × plataforma |
| `social_posts` | Posts del dirigente para timeline + top-posts |
| `social_comments` | `nlp_polaridad` (1/0/-1) + `author_hash` (unique_commenters) + `nlp_model_version` (clasificados only) |
| `watched_profiles` | Audiencia observada (fans). Schema: 17 cols — ver `PIPELINE-RADAR-CRECE.md` §2.2. |
| `watched_like_events` | Reactions de fans → posts del dirigente (link via `url_to_post` fallback) |

### 1.4 Deuda y estado real conocido

| Item | Estado | Notas |
|---|---|---|
| Endpoint `/fantasmas-por-plataforma` | ✅ Funcional | Fórmula clara, no requiere enrichment |
| `useFantasmasPorPlataforma` hook | ✅ Existe | **Pendiente verificar:** ¿se renderiza en alguna vista FE actualmente? No vi llamada en las páginas inspeccionadas. Posible deuda de FE sin consumir hook ya disponible. |
| Top Fans ranking (FE) | ✅ Renderiza | Score = `reactions × 1 + comments × 2.5`. Categorías "Cliente / Competidor / Sugeridos". |
| watched_profiles cobertura columnas | ⚠️ Parcial | `avatar_url` = 0% siempre; `profile_url` = 0-13% (solo cliente_seed manual); `profile_handle` = 0-13%. Ver §3 de `PIPELINE-RADAR-CRECE.md` para gap analysis. |
| Reacciones tipo placeholder | ⚠️ Conocido | Banner FE: "Reacciones marcadas como 'like' son placeholder — los tipos detallados llegan con el fix RADAR Sprint 9." |
| Cobertura watched_profiles por dirigente | ⚠️ Asimétrica | Saymi 28,649 / Pepe 30,995 ✅ · Piña 4,769 + IG 2,598 (resuelto hoy) · Solano 222 IG · Gaby 2,105 · Balles 15,324 · Felipe 66 (todos hoy 2026-05-28). Reel Piña 3982 = 495 rx pendientes en FASE B (handoff). |
| VIP overrides | ⚠️ Documentado en código | `frontend/src/lib/api/utils/vip-overrides.ts` aplica overrides client-side (Misael VIP per memoria histórica). BD jamás se toca (D-3 decisión). |
| Sugerencias de fans frecuentes | ✅ Funcional | Detecta on-the-fly comentaristas ≥2 comments que NO están en watched_profiles. Visible en sub-card "comentaristas frecuentes sin observar". |
| Métrica "HISTÓRICO" en KPIs | ⚠️ Label confuso | Significa "todo lo capturado por RADAR sin filtro de fecha" — NO es total real del perfil en plataforma. Para Felipe FB: 25 capturados vs 562 reales en FB. Label deuda de UI (`interactions-kpis.tsx`). |

### 1.5 Cómo responder preguntas comunes

| Pregunta CEO | Dónde está la respuesta |
|---|---|
| "¿Qué es un fantasma?" | Endpoint `/social/aceptacion/fantasmas-por-plataforma` líneas 290-450 de `indice_aceptacion.py`. Fórmula: follower que no ha comentado. |
| "¿Cuál es el % de fantasmas por dirigente?" | `useAceptacionOverview()` retorna `pct_fantasma` por dirigente. Por plataforma: `useFantasmasPorPlataforma()`. |
| "¿Por qué Felipe muestra solo 25 posts en HISTÓRICO?" | Label "HISTÓRICO" significa "lo capturado por RADAR". 25 ≠ total real (562). Causa: Felipe onboarded 2026-05-27 (1 día), solo pase shallow de pepe_hybrid. Ver §1.4. |
| "¿Cómo se calcula el score Top Fans?" | `reactions × 1 + comments × 2.5`. Endpoint `/aceptacion/watched-profiles/top-fans`. |

### 1.6 Auditoría

- **2026-05-28** · Auditor: Gemini · Veredicto inicial: ⚠️ Pasa con ajustes (reporte: `.context/audits/2026-05-28-mapa-funcional-seccion-1.md`).
- **Hallazgos corregidos:**
  - Hook inventado `useCreateWatched()` → reemplazado por "⚠️ Sin hook FE — deuda detectada por auditoría". Lección: sesgo CRUD simétrico (asumí que porque hay POST endpoint hay hook FE de creación). Sub-regla #6 agregada al MODELO.
  - Endpoint omitido `POST /aceptacion/watched-profiles/ingest-reactions-bulk` (`watched_profiles.py:949-950`) → agregado a tabla §1.2.
- **Falso positivo del auditor:** Gemini señaló `useIAPost` como omitido pero ya estaba en §1.2 línea 1. Sin acción.
- **Sesgo declarado:** §1.4 ya declaraba verificación solo para dirigentes 1,2,3,5,8,57,60. Dirigentes 4 (Yesenia), 6 (Cravioto), 7 (Máynez), 58 (Ivette), 59 (Susana) existen en DB pero NO se auditaron en este pase.

---

## 2. Recepción / Diagnóstico Tier 1 (B01-B10) ✅

**Concepto:** primer panel de diagnóstico cuantitativo del dirigente. 10 bloques (B01-B10) que miden conexión con la audiencia, alcance, salud de publicaciones, comparativa vs rivales, emociones, alertas de crisis, crecimiento, voz, profundidad de movilización y humanización. **B11-B18 NO están aquí** — son Tier 2 (ver §8).

> **Corrección 2026-05-28:** versión previa del MAPA decía "B01-B18 dentro de Tier 1". Verificado contra `diagnostico.py:213-226` (1 service por bloque B01-B10) y `diagnostico_tier2.py:45-130` (B11-B18 en endpoints separados). Los bloques son disjuntos.

### 2.1 Vistas FE del sidebar

#### `/dashboard/diagnostico/` (lista dirigentes con diagnóstico)
- **Archivo:** `frontend/src/app/dashboard/diagnostico/page.tsx`
- **Función:** lista dirigentes scoped a rol con tarjeta resumen "X/10 bloques OK".
- **Hook:** depende de `useDirigentes()` + `useDiagnosticoTier1()` por entrada (ver detalle).

#### `/dashboard/diagnostico/[dirigenteId]/` (detalle Tier 1)
- **Archivo:** `frontend/src/app/dashboard/diagnostico/[dirigenteId]/page.tsx`
- **Función:** renderiza las 10 cards B01-B10 con datos del bloque + skeleton mientras carga + estado de error.
- **Hook principal:** `useDiagnosticoTier1(dirigenteId)` → llama `GET /diagnostico/{dirigenteId}` (1 request, 10 bloques).
- **Hook drill-down:** `useHumanizacionExamples(dirigenteId, limit)` → llama `/diagnostico/{dirigenteId}/humanizacion/examples`.
- **Componentes:** `CardB01..CardB10` (de `components/diagnostico/cards.tsx`), `CardB10WithDrilldown` (humanización con ejemplos), `CardSkeleton`.

### 2.2 Endpoint backend del módulo

Archivo único: `backend/app/api/v1/endpoints/diagnostico.py`. Todos los handlers requieren `current_user` autenticado y resuelven `org_id` vía `_resolve_org_id()` para scope multi-tenant.

| Endpoint | Línea | Service invocado | Función |
|---|---|---|---|
| `GET /diagnostico/{dirigente_id}` | `diagnostico.py:196` | **agregado: invoca los 10 services secuencialmente** | Devuelve `{dirigente_id, bloques: {B01..B10}, resumen: {ok, insufficient_data, total}, bloque_version}` en 1 request. Acepta query `dias_a_comicio` para modulador temporal de B01. Secuencial (no `asyncio.gather`) para evitar contention de DB session. |
| `GET /diagnostico/{dirigente_id}/er_normalizado` | `diagnostico.py:47` | `er_service.compute()` | B01 individual |
| `GET /diagnostico/{dirigente_id}/breakout_scale` | `diagnostico.py:60` | `breakout_service.compute()` | B02 individual |
| `GET /diagnostico/{dirigente_id}/matriz_2x2` | `diagnostico.py:72` | `matrix_2x2_service.compute()` | B03 individual |
| `GET /diagnostico/{dirigente_id}/benchmark` | `diagnostico.py:84` | `benchmark_service.compute()` | B04 individual |
| `GET /diagnostico/{dirigente_id}/sentiment_plutchik` | `diagnostico.py:96` | `sentiment_plutchik_service.compute()` | B05 individual |
| `GET /diagnostico/{dirigente_id}/crisis_spike` | `diagnostico.py:108` | `crisis_spike_service.compute()` | B06 individual |
| `GET /diagnostico/{dirigente_id}/growth_attribution` | `diagnostico.py:120` | `growth_attribution_service.compute()` | B07 individual |
| `GET /diagnostico/{dirigente_id}/sov` | `diagnostico.py:132` | `sov_service.compute()` | B08 individual |
| `GET /diagnostico/{dirigente_id}/share_like_ratio` | `diagnostico.py:145` | `share_like_ratio_service.compute()` | B09 individual |
| `GET /diagnostico/{dirigente_id}/humanizacion` | `diagnostico.py:157` | `humanizacion_service.compute()` | B10 individual |
| `GET /diagnostico/{dirigente_id}/humanizacion/examples` | `diagnostico.py:169` | `humanizacion_service.get_examples()` | Drill-down B10: top posts institucionales + humanizantes + keywords + n_posts_analizados |
| `GET /diagnostico/foda/{dirigente_id}` | `diagnostico.py:442` | — (lee `planes_ia`) | Pertenece a §3 FODA |

**Hook FE:** `frontend/src/lib/api/hooks/use-diagnostico-tier1.ts:212 export function useDiagnosticoTier1()` con `staleTime: 60_000` (1 min). Drill-down humanización en `:222 useHumanizacionExamples()` con `staleTime: 120_000`. NO existe `useDiagnostico<Bloque>` por bloque individual — el endpoint agregado cubre el caso de uso del dashboard. Los endpoints individuales por bloque están disponibles backend pero NO consumidos por hook FE actual (deuda intencional: 1 request es más eficiente que 10).

### 2.3 Catálogo de bloques B01-B10

Cada service expone `async def compute(db, dirigente_id, org_id, ...) -> dict` con shape `{status, bloque, bloque_version, computed_at, missing?, warnings?, data?}` (ver `_common.py::build_insufficient()` y `BloqueBase` en `use-diagnostico-tier1.ts:8`).

| Bloque | Service | Card FE | Concepto | Data shape (`use-diagnostico-tier1.ts`) |
|---|---|---|---|---|
| **B01 ER Normalizado** | `er_service.py:1 "B01 — Engagement Rate normalizado por estrato político"` | `CardB01` (`cards.tsx:81`) | ER actual vs rango esperado por estrato político + ventana electoral. Por plataforma. Usa matriz validada Zenodo. | `B01Data{er_por_plataforma, estrato, modificador_temporal, ventana_electoral_activa, dias_a_comicio, ventana_dias_analizada, n_posts_total, matriz_version}` |
| **B02 Breakout Scale** | `breakout_service.py:1 "B02 — Breakout Scale Brookings (Categorías 1-6)"` | `CardB02` (`cards.tsx:196`) | Posts que rompen burbuja (views/followers ratio en escala Brookings 1-6). | `B02Data{max_categoria, posts_por_categoria, posts_breakout[], views_breakout_pct, n_posts_evaluados, fidelity, nota}` |
| **B03 Matriz 2×2** | `matrix_2x2_service.py:1 "B03 — Matriz 2×2 de contenido (4 cuadrantes)"` | `CardB03` (`cards.tsx:254`) | Cada post posicionado por engagement vs sentiment → cuadrante INSIGNIA / CRISIS / VANIDAD / MUERTA. | `B03Data{posts[], conteo_cuadrantes, umbral_engagement, umbral_sentiment, n_posts, leyenda}` |
| **B04 Benchmark** | `benchmark_service.py:1 "B04 — Benchmark vs competidores directos (proxies D-22)"` | `CardB04` (`cards.tsx:329`) | Comparativa vs `dirigentes.competidor_directo_ids`. ⚠️ **Deuda:** S2 los 8 dirigentes piloto tienen `competidor_directo_ids=[]` (ver `benchmark_service.py` docstring) → bloque insufficient para mayoría. |
| **B05 Plutchik** | `sentiment_plutchik_service.py:1 "B05 — Sentiment composition Plutchik 6 emociones"` | `CardB05` (`cards.tsx:437`) | Distribución 6 emociones Plutchik (alegría/confianza/miedo/sorpresa/tristeza/disgusto) desde `social_posts.emotions` JSONB. | `B05Data` |
| **B06 Crisis Spike** | `crisis_spike_service.py:1 "B06 — Crisis Spike detector (ventana móvil 2h vs baseline)"` | `CardB06` (`cards.tsx:501`) | Detección de picos atípicos de actividad (comments + reactions) vs baseline 7d. Ventana móvil 2h. | `B06Data` |
| **B07 Growth Attribution** | `growth_attribution_service.py:1 "B07 — Growth Attribution Time-Decay (scikit-learn)"` | `CardB07` (`cards.tsx:544`) | Qué posts atribuibles al crecimiento de followers (time-decay regression). Requiere timeseries followers (depende RADAR — ver `memory/project_b07_radar_follower_dependency.md`). | `B07Data` |
| **B08 SoV** | `sov_service.py:1 "B08 — Share of Voice (SoV) por tema clave"` | `CardB08` (`cards.tsx:627`) | Cuota de conversación del dirigente vs competidores sobre temas extraídos por topic extractor (modelo `cc-topics-v1-2026-05-21` en DB · Gemma 3:12b configurado vía OLLAMA_MODEL). En `social_posts.topics_extracted`. | `B08Data` |
| **B09 Share/Like Ratio** | `share_like_ratio_service.py:1 "B09 — Share-to-Like Ratio (movilización profunda)"` | `CardB09` (`cards.tsx:681`) | Ratio shares/likes como proxy de "movilización profunda" (compartir > liker). | `B09Data` |
| **B10 Humanización** | `humanizacion_service.py:1 "B10 — Humanización Score (0-100)"` | `CardB10` (`cards.tsx:726`) + `CardB10WithDrilldown` (`cards.tsx:840`) | Heurística léxica sobre `social_posts.content` (últimos 90d) con 4 factores: primera persona, emojis humanos, institucional, longitud. Score 0-100. Drill-down con top posts. | `B10Data` |

### 2.4 Tablas DB que el módulo lee

| Tabla | Columnas usadas | Verificado en |
|---|---|---|
| `social_profiles` | `id`, `followers_count`, `platform`, `dirigente_id` | `er_service`, `_common.py` (precondición "social_profiles=0 → insufficient_data"). Verificado en `_common.py::build_insufficient(BLOQUE, missing=["social_profiles=0"])` invocado por 8 de 10 services. |
| `social_posts` | `id`, `engagement_rate`, `sentiment_score`, `emotions` (JSONB Plutchik), `content`, `topics_extracted` (JSONB), `views`, `likes`, `shares`, `comments`, `published_at`, `profile_id` | B01 (engagement_rate), B02 (views), B03 (engagement+sentiment), B05 (emotions), B08 (topics_extracted), B09 (likes+shares), B10 (content) |
| `social_comments` | `published_at`, `parent_post_id` | B06 (crisis spike volumen) |
| `dirigentes` | `id`, `competidor_directo_ids`, `org_id`, `estrato_politico` | B04 (competidores), B01 (estrato) |

### 2.5 Cobertura DB actual (2026-05-28 noche)

Query ejecutada contra `crece-db :5438`:

```sql
SELECT COUNT(*) AS total,
       COUNT(*) FILTER (WHERE engagement_rate > 0) AS er,
       COUNT(*) FILTER (WHERE sentiment_score IS NOT NULL) AS sentiment,
       COUNT(*) FILTER (WHERE emotions IS NOT NULL) AS emotions,
       COUNT(*) FILTER (WHERE topics_extracted IS NOT NULL) AS topics
FROM social_posts;
```

| Métrica | Cobertura | % | Bloques afectados si bajo |
|---|---|---|---|
| Total posts | 7,169 | — | — |
| `engagement_rate > 0` | 6,707 | **93%** | B01, B03, B09 |
| `sentiment_score` populated | 5,178 | **72%** | B03, B05 (parcial) |
| `emotions` JSONB populated | 6,390 | **89%** | B05 (principal) |
| `topics_extracted` populated | 5,773 | **81%** | B08 |

Por dirigente reciente (post-ingest Felipe + NLP + DUP-9 cleanup + Hugo backfill):

| Dirigente | Posts | ER>0 | Sentiment | Emotions |
|---|---|---|---|---|
| **Felipe (60) post-NLP** | **188** (76 FB + 12 IG + 100 TT) | 188 | **188 (100%)** ✅ | 188 (100%) ✅ |
| Saymi (3) | 2,173 | 2,109 | 1,335 (61%) | 2,023 (93%) |

✅ Felipe NLP COMPLETO 2026-05-29:
- 46 FB posts clasificados inline por Claude Opus 4.7 (texto del scrape inicial).
- 14 FB posts clasificados tras `fb_text_backfill.py` de Hugo (recuperación via json_message regex post-ingest).
- 2 TT posts clasificados via **transcripción de audio con `supadata_transcript`** (audio→texto→NLP) — patrón reusable para videos sin caption.
- 9 FB duplicados cross-scheme eliminados (B-FELIPE-FB-DUP-9 cerrado).
- **0 posts pendientes** — cobertura 100% completa.

### 2.5.1 Opciones de enrichment NLP para contenido faltante (descubiertas 2026-05-28)

Cuando un post tiene `content=''` o NULL (videos/imágenes sin caption), opciones de enriquecer ANTES de pasar a NLP:

| Opción | Cobertura | Costo | Cuándo aplicar |
|---|---|---|---|
| **supadata_transcript** | TT, YT, IG, Twitter video | API call (tier supadata) | Video con audio hablado · funciona para TT verificado 2026-05-28 |
| Hugo `fb_text_backfill.py` | FB posts/reels | Run radar-side | FB posts no scrapeados completos por engine inicial · recupera body via regex |
| OCR/Vision sobre media | FB/IG reels/images | Vision API + download media | Último recurso si las 2 anteriores fallan |
| Aceptar `NULL` permanente | — | Cero | Si claramente no hay caption ni audio (imagen sin texto, video sin audio) |

### 2.6 Deuda y estado real conocido

| Item | Estado | Notas |
|---|---|---|
| Endpoint agregado `/diagnostico/{id}` | ✅ Funcional | 10 services en 1 request, secuencial sobre misma session. |
| Endpoints individuales por bloque | ⚠️ Existen sin hook FE | B01..B10 cada uno tiene endpoint `/diagnostico/{id}/<bloque>` pero NO se consume desde FE. Decisión intencional (1 request agregado más eficiente). Documentar en ADR si se quiere formalizar el contrato "use endpoints individuales para tests/admin, agregado para dashboard". |
| B04 Benchmark | ⚠️ Insufficient_data en mayoría | `competidor_directo_ids=[]` en 8/10 dirigentes piloto S2 (cita: `benchmark_service.py` docstring "S2 los 8 dirigentes piloto tienen `competidor_directo_ids=[]`"). Solución: cargar competidores manual o via `competidores_directos` propuesta abierta. |
| B05 emotions cobertura | ⚠️ 89% global / 69% Felipe | NLP pendiente +62 Felipe FB nuevos. Saymi 93% sólido. |
| B07 Growth Attribution | ⚠️ Dependencia RADAR | Necesita timeseries `followers_count` para regression. Contrato acordado con Marx, pendiente ejecución (ver `memory/project_b07_radar_follower_dependency.md`). |
| B08 SoV topics | ⚠️ 81% cobertura | topic extractor Gemma 3:12b ya extraído por Sprint S1 T5 pero no en todos los posts. Pendiente backfill. |
| `CardB10WithDrilldown` | ✅ Renderiza | Único bloque Tier 1 con drill-down a ejemplos (endpoint `/humanizacion/examples`). |
| Scope multi-tenant | ✅ Implementado | Cada handler resuelve `org_id` con `_resolve_org_id(current_user, request)` antes de invocar service. Service filtra por `org_id` en queries. |
| Versionado | ✅ `bloque_version: "tier1-v1"` | Cada bloque también versiona su data (ej. `B01.matriz_version`). |
| `dias_a_comicio` modulador | ✅ Funcional | Query param del endpoint agregado modula B01 (rampa temporal — ver `memory/feedback_ramp_temporal_methodology.md`). |
| Cards FE B01-B10 | ✅ Renderiza | Todos exportan en `cards.tsx`. Skeleton + estado error cubiertos. |
| Tier 2 (B11-B18) | 📝 Existe separado | `diagnostico_tier2.py` + `use-diagnostico-tier2.ts` + `/dashboard/diagnostico-tier2/[dirigenteId]/`. Ver §8. |

### 2.7 Cómo responder preguntas comunes

| Pregunta CEO | Dónde está la respuesta |
|---|---|
| "¿Qué bloques tiene Tier 1?" | 10 bloques B01-B10. Lista en §2.3. Tier 2 = B11-B18 (§8). |
| "¿Por qué B04 sale `insufficient_data` para casi todos?" | `competidor_directo_ids=[]` en piloto S2. Necesita curaduría manual de competidores por dirigente. |
| "¿Felipe ya tiene su diagnóstico?" | Posts: ✅ 197. ER: ✅ 183. Sentiment/emotions: ⚠️ 135 (los 62 FB nuevos sin NLP). B01-B04 OK, B05 parcial, B07 pendiente followers timeseries. |
| "¿Por qué el endpoint agregado es 1 request y no 10?" | `useDiagnosticoTier1` consume `/diagnostico/{id}` agregado para evitar 10 round-trips desde el dashboard. Endpoints individuales existen para tests/admin sin hook FE. |
| "¿Cómo se decide el estrato político?" | `dirigentes.estrato_politico` directo, con fallback en `er_service`. `estrato_inferido: boolean` en response. |
| "¿Por qué los bloques tienen `bloque_version`?" | Permite cambiar fórmula sin romper UI antigua. Cards leen `bloque_version` para mostrar warning si está desfasado de su tipo TS. |

### 2.8 Auditoría

- **2026-05-28** · Auditor: Gemini · Veredicto: ✅ **Pasa** (reporte: `.context/audits/2026-05-28-mapa-funcional-seccion-2.md`).
- **Citas verificadas:** 12 afirmaciones (endpoints, hooks, cards, services, cobertura DB global + Felipe/Saymi, precondiciones, deuda B04/B07). 0 sin verificar. 0 inventadas. 0 omisiones.
- **Sesgo declarado:**
  - Cobertura solo verificada para dirigentes 1,2,3,5,8,57,60. Dirigentes 4 (Yesenia), 6 (Cravioto), 7 (Máynez), 58 (Ivette), 59 (Susana) NO auditados en este pase.
  - Aclaración aplicada §2.3 B08: modelo NLP en DB es `cc-topics-v1-2026-05-21`. Gemma 3:12b es config OLLAMA_MODEL, no se etiqueta así en `nlp_model_version`.

## 3. FODA ✅

**Concepto:** vista que muestra el último análisis FODA (Fortalezas / Oportunidades / Debilidades / Amenazas) generado por IA para el dirigente, persistido en la tabla `planes_ia` con `tipo='DIAGNOSTICO'`. Sirve como insumo previo a generar planes de Estrategia (`tipo='CONSOLIDACION'`) y Contenido (`tipo='CONTENIDO'`).

### 3.1 Vistas FE del sidebar

#### `/dashboard/diagnostico/foda/` (dispatcher)
- **Archivo:** `frontend/src/app/dashboard/diagnostico/foda/page.tsx`
- **Función:** Server Component (`force-dynamic`) que decodea el JWT `crece_access_token` cookie y redirige:
  - Si `payload.dirigente_id` existe → `/dashboard/diagnostico/{dirigente_id}/foda`
  - Si no → `/dashboard/dirigentes` (selector)
- **Sin hook:** redirect puro, ningún fetch.

#### `/dashboard/diagnostico/[dirigenteId]/foda/` (vista FODA)
- **Archivo:** `frontend/src/app/dashboard/diagnostico/[dirigenteId]/foda/page.tsx`
- **Función:** renderiza 4 cuadrantes (Fortalezas / Oportunidades / Debilidades / Amenazas) con cada item mostrando `titulo`, `evidencia`, y opcionalmente `implicacion` / `tactica` / `riesgo` / `mitigacion`. Botón hacia el plan derivado si existe (`plan_derivado_id`).
- **Hook:** `useFoda(dirigenteId)` (líneas 36-44 de la misma página — **definido inline, no exportado a archivo central**).
  ```ts
  useQuery<FodaResponse>({
    queryKey: ["diagnostico-foda", dirigenteId],
    queryFn: () => api.get(`/diagnostico/foda/${dirigenteId}`),
    staleTime: 1000 * 60 * 5,  // 5 min
  });
  ```
- **Endpoint backend:** `GET /diagnostico/foda/{dirigente_id}`
- **Response type:** `FodaResponse` (inline, líneas 24-34 de la página)

### 3.2 Endpoint backend

Archivo: `backend/app/api/v1/endpoints/diagnostico.py`

| Endpoint | Línea | Función |
|---|---|---|
| `GET /diagnostico/foda/{dirigente_id}` | `diagnostico.py:442` | Devuelve último FODA estructurado del dirigente |

**Lógica del handler `get_diagnostico_foda` (`diagnostico.py:442-520`):**

1. **Scope check** (`diagnostico.py:454-457`):
   - `admin` → cualquier dirigente
   - `viewer` con su propio `dirigente_id` → solo SU dirigente, sino 403
   - Resto (`analyst`, `viewer` sin dirigente) → cualquier dirigente de su org
2. **Lookup último DIAGNOSTICO:**
   ```sql
   SELECT id, contenido, created_at, estructura_json
   FROM planes_ia
   WHERE dirigente_id = :did AND tipo = 'DIAGNOSTICO'
   ORDER BY created_at DESC LIMIT 1
   ```
3. **Si no hay registro:** devuelve `{fortalezas:[], oportunidades:[], debilidades:[], amenazas:[], diagnostico_id: null, generado_at: null, plan_derivado_id: null}`. NO 404 — la vista FE muestra empty state.
4. **Dual fallback de parsing** (`diagnostico.py:481-493`):
   - Primero: si `estructura_json` tiene key `fortalezas`, leer directo de keys `fortalezas`, `oportunidades`, `debilidades`. Para `amenazas` usa fallback `estructura_json.get("amenazas", estructura_json.get("riesgos", []))` (legacy generadores usaron `riesgos`).
   - Fallback: si no hay `estructura_json` bien formada, invocar `_parse_foda(contenido)` (`diagnostico.py:291`) que parsea markdown de `contenido` buscando headers `## Fortalezas` / `## F1` etc.
5. **Plan derivado:** segunda query busca último `CONSOLIDACION` del mismo dirigente; devuelve su `id` como `plan_derivado_id` (link en FE "ir al plan").

**Response shape (`diagnostico.py:511-520`):**
```python
{
    "dirigente_id": int,
    "fortalezas": [{"titulo": str, "evidencia": str, "implicacion"?: str, ...}],
    "oportunidades": [...],
    "debilidades": [...],
    "amenazas": [...],
    "diagnostico_id": int | None,
    "generado_at": ISO8601 | None,
    "plan_derivado_id": int | None,
}
```

### 3.3 Tablas DB que el módulo lee

| Tabla | Columnas usadas |
|---|---|
| `planes_ia` | `id`, `dirigente_id`, `tipo` (enum: `DIAGNOSTICO` / `CONSOLIDACION` / `CONTENIDO`), `contenido` (text markdown), `estructura_json` (jsonb), `created_at` |
| `dirigentes` | `id` (FK validation) |

**Schema relevante (verificado vía `\d planes_ia`):**
- `tipo tipo_plan_enum NOT NULL` — enum con valores `DIAGNOSTICO`, `CONSOLIDACION`, `CONTENIDO`
- `contenido text NOT NULL` — markdown del FODA generado por LLM
- `estructura_json jsonb` — parsed structured version (preferida)
- `aprobado boolean NOT NULL`, `modelo_ia varchar(100)`, `generado_por_id` FK users
- Index btree en `dirigente_id`, FK CASCADE a `dirigentes`, FK RESTRICT a `users`

### 3.4 Cobertura DB actual (2026-05-28)

Query: `SELECT tipo, COUNT(*) FROM planes_ia GROUP BY tipo`

| tipo | count |
|---|---|
| `DIAGNOSTICO` | **35** |
| `CONTENIDO` | 15 |
| `CONSOLIDACION` | **46** |

**Cobertura `estructura_json` (crítico para parsing):**

```sql
SELECT COUNT(*), COUNT(*) FILTER (WHERE estructura_json IS NULL) AS sin_estructura
FROM planes_ia WHERE tipo='DIAGNOSTICO';
-- total=35, sin_estructura=14 (40%), con_estructura=21 (60%)
```

⚠️ **40% de DIAGNOSTICOs (14/35) tienen `estructura_json` NULL.** El fallback `_parse_foda(contenido)` NO es legacy safety net — es load-bearing para 40% de los registros actuales. Si el parser regex se rompe, esos 14 dirigentes pierden FODA. Hallazgo de auditoría Gemini 2026-05-28.

Por dirigente (último DIAGNOSTICO 2026-05-27 23:37 batch):

| Dirigente | n_diagnosticos | last |
|---|---|---|
| Saymi (3) | 8 | 2026-05-27 |
| Pepe Monroy (57) | 5 | 2026-05-27 |
| Piña (1) | 4 | 2026-05-27 |
| Gaby Jiménez Godoy (5) | 4 | 2026-05-27 |
| Solano (2) | 4 | 2026-05-27 |
| Balles (8) | 3 | 2026-05-27 |
| César Cravioto (6) | 3 | 2026-05-10 |
| Yesenia Nolasco (4) | 3 | 2026-05-10 |
| **Felipe (60)** | **1** | 2026-05-27 |

**Dirigentes SIN ningún DIAGNOSTICO** (verificado SQL `NOT IN (SELECT dirigente_id FROM planes_ia WHERE tipo='DIAGNOSTICO')`):
- 7 — Jorge Álvarez Máynez
- 56 — RSS News Bot (cuenta sistema, no esperado tener FODA)
- 58 — Ivette Morán de Murat
- 59 — Susana Harp Iturribarría

3 dirigentes reales (Máynez, Ivette, Susana) pendientes de primera generación de FODA.

⚠️ Felipe tiene 1 DIAGNOSTICO pre-ingest de hoy. Regenerar tras NLP +60 FB nuevos.

### 3.5 Generadores de FODA (escriben `planes_ia`)

**Vía 1 — API endpoints (`planes.py`):**

| Endpoint | Línea | Acepta `tipo` | Notas |
|---|---|---|---|
| `POST /planes/generar` | `planes.py:72` | DIAGNOSTICO / CONSOLIDACION / CONTENIDO | Endpoint principal. Rate-limit `5/hour` por usuario. Roles `ADMIN`, `ANALYST`. Flag `payload.estructurado` (bool) decide entre `generate_structured_plan` o `generate_plan` (legacy). |
| `POST /planes/generar/stream` | `planes.py:107` | DIAGNOSTICO / CONSOLIDACION / CONTENIDO | Variante SSE streaming, misma rate-limit + roles. |

**Vía 2 — Scripts batch:**

| Generador | Tipo | Notas |
|---|---|---|
| `backend/scripts/generate_diagnostico_dirigentes.py` | DIAGNOSTICO | Batch generación inicial |
| `backend/scripts/regen_diagnostico_enriched.py` | DIAGNOSTICO | Re-genera con dataset enriquecido |
| `backend/scripts/regen_diagnostico_enriched_host.py` | DIAGNOSTICO | Variante host-side (CC RAM-safe) |
| `backend/scripts/regen_diagnostico_v2.py` | DIAGNOSTICO | Variante v2 |
| `backend/scripts/regen_diagnostico_gemini.py` | DIAGNOSTICO | Usa Gemini en vez de Claude |
| `backend/scripts/generate_planes_v3_from_diagnostico.py` | CONSOLIDACION | Deriva plan estratégico desde FODA existente |
| `backend/scripts/regen_consolidacion_v2.py` | CONSOLIDACION | Valida `fortalezas`, `debilidades`, `riesgos` en `estructura_json` (`regen_consolidacion_v2.py:153`) antes de generar el plan |
| `backend/scripts/regen_contenido_v2.py` | CONTENIDO | Genera plan de contenido |
| `backend/scripts/regen_plan_dirigente.py` | (variado) | Genera plan completo por dirigente individual |
| `backend/app/services/plan_generator.py` | (módulo común) | Lógica compartida invocada por `planes.py` endpoints |

**Convención `estructura_json` keys observada (verificada con query `jsonb_object_keys`):**
- `fortalezas` ✅ (consistente)
- `debilidades` ✅
- `riesgos` ⚠️ (algunos generadores legacy) o `amenazas` (consumidores modernos)
- Adicionales: `ipd_score`, `ipd_bucket` (cuando vienen del pipeline IPD)

El endpoint `get_diagnostico_foda` resuelve ambos via `.get("amenazas", .get("riesgos", []))` — los generadores nuevos deberían unificar a `amenazas`, no `riesgos`.

### 3.6 Deuda y estado real conocido

| Item | Estado | Notas |
|---|---|---|
| Endpoint `/diagnostico/foda/{id}` | ✅ Funcional | Scope RBAC implementado. Empty-state retorna 200 con arrays vacíos (no 404). |
| Hook `useFoda` exportado a archivo central | ❌ NO existe | Hook está inline en `[dirigenteId]/foda/page.tsx:36`. Si otra página necesita FODA → refactor a `frontend/src/lib/api/hooks/use-foda.ts`. Deuda menor (single-consumer hoy). |
| `estructura_json.amenazas` vs `.riesgos` | ⚠️ Inconsistencia legacy | Endpoint mitiga via fallback. Migrar generadores legacy a `amenazas` resolvería la deuda. ADR candidato. |
| `plan_derivado_id` link | ✅ Funcional | Devuelve último `CONSOLIDACION` (no necesariamente derivado del MISMO DIAGNOSTICO — convención "último de cada tipo"). Documentar la asunción. |
| Felipe (60) cobertura | ⚠️ Solo 1 DIAGNOSTICO pre-ingest hoy | Regenerar tras NLP +60 FB nuevos para reflejar audiencia ampliada. |
| Dispatcher FODA | ✅ Funcional | Server Component, decodea JWT cookie, redirect correcto. |
| `_parse_foda(contenido)` fallback | ⚠️ **Load-bearing, no safety net** | Parser regex markdown. **40% de DIAGNOSTICOs actuales (14/35) tienen `estructura_json=NULL`** → dependen 100% de este parser. Si se rompe regex, esos dirigentes pierden FODA. Pendiente backfill de `estructura_json` para los 14 registros. Hallazgo audit Gemini 2026-05-28. |

### 3.7 Cómo responder preguntas comunes

| Pregunta CEO | Dónde está la respuesta |
|---|---|
| "¿Felipe ya tiene FODA?" | Sí, 1 DIAGNOSTICO en `planes_ia` (creado 2026-05-27, pre-ingest). Recomendar regenerar. |
| "¿Cómo se conecta FODA con el plan?" | El endpoint devuelve `plan_derivado_id` = último `tipo='CONSOLIDACION'` del dirigente. FE muestra link "ir al plan". |
| "¿Por qué algunos FODAs traen `riesgos` y otros `amenazas`?" | Generadores legacy escribieron `riesgos`. El endpoint resuelve ambos con `.get("amenazas", .get("riesgos", []))`. Pendiente migrar. |
| "¿Qué pasa si el dirigente no tiene FODA aún?" | Endpoint retorna 200 con arrays vacíos. FE muestra empty state, no error. |
| "¿Quién puede ver el FODA de quién?" | Admin: todos. Viewer con `dirigente_id` propio: solo su dirigente. Viewer/analyst sin dirigente: todos los de su org. |

### 3.8 Auditoría

- **2026-05-28** · Auditor: Gemini · Veredicto: ⚠️ **Pasa con ajustes** (reporte: `.context/audits/2026-05-28-mapa-funcional-seccion-3.md`).
- **Citas verificadas:** todos los endpoints, hooks inline, shapes, queries DB.
- **Hallazgos sustantivos aplicados:**
  1. Agregado §3.5 Vía 1 API: `POST /planes/generar` (`planes.py:72`) y `POST /planes/generar/stream` (`planes.py:107`) faltaban como vía de generación FODA (solo mencioné scripts).
  2. Corregido §3.4 y §3.6: `_parse_foda` es **load-bearing 40%** (14/35 DIAGNOSTICOs con `estructura_json=NULL`), NO legacy safety net como afirmé inicialmente.
  3. Agregado §3.4: dirigentes SIN DIAGNOSTICO listados explícitamente (Máynez 7, RSS Bot 56, Ivette 58, Susana 59).
- **Sesgo declarado y corregido:** sub-regla §5 absolutos — la afirmación "generadores modernos siempre populan estructura_json" era inválida sin SQL. SQL ejecutada (40% NULL) refuta la afirmación. Corregida.

## 4. Planes IA (Diagnóstico + Estrategia + Contenido) ✅

**Concepto:** módulo que gestiona el ciclo de vida de planes generados por IA. 3 tipos (`DIAGNOSTICO`, `CONSOLIDACION`, `CONTENIDO`) persistidos en `planes_ia` con su sub-tabla `plan_tareas` para tracking de tareas accionables. Rediseño D-PLANES-CONCEPTO-3 aprobado por CEO 2026-05-21: 3 tabs visuales independientes en una sola página.

### 4.1 Vistas FE del sidebar

#### `/dashboard/planes/` (página principal · 2 tabs)
- **Archivo:** `frontend/src/app/dashboard/planes/page.tsx`
- **Función:** rediseño Concepto 3 (D-PLANES-CONCEPTO-3 · 2026-05-21). **Tab Diagnóstico fue eliminado 2026-05-22** (`D-PLANES-DIAGNOSTICO-REMOVED-2026-05-22`, `page.tsx:57`). Quedan **2 tabs:**
  - **Estrategia** — Plan 90 días (próximamente · empty state · Fase 2).
  - **Contenido** — Calendario editorial (próximamente · empty state).
- Bookmarks viejos con `?tab=diagnostico` caen silenciosamente a `estrategia` (`page.tsx:74-76`).
- El módulo Diagnóstico (B01-B18) sigue accesible vía `/dashboard/diagnostico/[dirigenteId]/` (§2).
- **Hooks:** `usePlanes(status, page)`, `useDirigentes()`.
- **RBAC:** backend `_check_org` + endpoint filtra auto por `user.dirigente_id`. Multi-dirigente selector solo admin/analyst (D-ACEPTACION-DEDUPE).
- **Sin CTA "Generar Plan"** en header (D-CTA-GENERATE-REMOVED 2026-05-21).

#### `/dashboard/planes/[id]/` (detalle plan)
- **Archivo:** `frontend/src/app/dashboard/planes/[id]/page.tsx`
- **Función:** renderiza markdown del `contenido` con `react-markdown` + `remark-gfm`, badges por tipo (DIAGNOSTICO azul · CONSOLIDACION emerald · CRISIS rojo), lista `PlanTareasList`.
- **Hooks:** `usePlan(id)`.
- **Acciones:** botones Approve / Reject (admin only).

#### `/dashboard/planes/[id]/kanban/` (kanban deprecado · redirect)
- **Archivo:** `frontend/src/app/dashboard/planes/[id]/kanban/page.tsx`
- **Función:** **redirect** según `plan.tipo`:
  - `CONSOLIDACION` → `/dashboard/planes?dirigente={id}&tab=estrategia`
  - `CONTENIDO` → `/dashboard/planes?dirigente={id}&tab=contenido`
  - `DIAGNOSTICO` → `/dashboard/diagnostico/{id}/foda`
  - Default → `/dashboard/planes?dirigente={id}`
- Mantenido con `?noRedirect=true` query para debug. **Ruta legacy.**

### 4.2 Endpoints backend

Archivo: `backend/app/api/v1/endpoints/planes.py`

| Endpoint | Línea | Auth/Rate | Función | Hook FE | Hook ruta llamada |
|---|---|---|---|---|---|
| `POST /planes/generar` | `planes.py:72` | ADMIN, ANALYST · `5/hour` | Generar plan (DIAGNOSTICO/CONSOLIDACION/CONTENIDO). `payload.estructurado` (bool) decide `generate_structured_plan` vs `generate_plan` (legacy). | ⚠️ `useGeneratePlan` (`use-planes.ts:23`) llama `/planes/generate` (path incorrecto). |
| `POST /planes/generar/stream` | `planes.py:107` | ADMIN, ANALYST · `5/hour` | Variante SSE streaming. | — (no hay hook stream) |
| `GET /planes/` | `planes.py:132` | autenticado | Lista paginada con `?status=&page=` | ✅ `usePlanes(status, page)` (`use-planes.ts:5`) → `/planes?...` ✅ match |
| `GET /planes/{plan_id}` | `planes.py:186` | autenticado | Detalle | ✅ `usePlan(id)` (`use-planes.ts:15`) → `/planes/{id}` ✅ match |
| `PATCH /planes/{plan_id}/aprobar` | `planes.py:196` | ADMIN only | Aprobar plan | ⚠️ `useApprovePlan` (`use-planes.ts:34`) llama `/planes/{id}/approve` (path incorrecto). |
| `PATCH /planes/{plan_id}/rechazar` (asumido) | (en `planes.py:196` bloque) | ADMIN | Rechazar plan | ⚠️ `useRejectPlan` (`use-planes.ts:45`) llama `/planes/{id}/reject` |
| `GET /planes/{plan_id}/tareas` | `planes.py:228` | autenticado | Lista tareas | ✅ `usePlanTareas(planId)` (`use-planes.ts:91`) → `/planes/{id}/tareas` ✅ match |
| `PATCH /planes/{plan_id}/tareas/{task_id}` | `planes.py:241` | ADMIN, ANALYST | Actualizar tarea (estado, deadline, métricas) | ✅ `useUpdateTarea(planId)` (`use-planes.ts:107`) → match |
| `POST /planes/{plan_id}/tareas/{task_id}/complete` | `planes.py:278` | ADMIN, ANALYST | Marcar tarea completada | ✅ `useCompleteTarea(planId)` (`use-planes.ts:119`) → match |
| `GET /planes/{plan_id}/progreso` | `planes.py:316` | autenticado | KPIs de progreso del plan | ✅ `usePlanProgreso(planId)` (`use-planes.ts:99`) → match |

### 4.3 Tablas DB que el módulo lee/escribe

#### `planes_ia` (ya documentada en §3.3)
- `tipo` enum (`tipo_plan_enum`, 4 valores verificados SQL): **`DIAGNOSTICO`, `CONSOLIDACION`, `CRISIS`, `CONTENIDO`**
- `contenido` text (markdown), `estructura_json` jsonb (preferido)
- `aprobado` boolean, `modelo_ia` varchar(100), `prompt_usado` text
- Tipo `CRISIS` definido en `app/models/plan_ia.py:16`. Su UI específica vive en este módulo pero sin UI dedicada actualmente (deuda).

#### `plan_tareas`
| Columna | Tipo | Notas |
|---|---|---|
| `plan_id` | int FK CASCADE | → planes_ia |
| `orden` | int | Orden de ejecución |
| `titulo`, `descripcion` | varchar(200), text | |
| `plataforma`, `formato`, `frecuencia`, `responsable` | varchar | Metadatos accionables |
| `deadline`, `completado_at` | timestamptz | |
| `metrica_objetivo`, `metrica_valor_objetivo`, `metrica_valor_real` | varchar/float | KPI por tarea |
| `estado` | `estado_tarea_enum` | Default `'TODO'`. Valores verificados SQL: `TODO`, `IN_PROGRESS`, `DONE`. |
| `cambios_historial` | jsonb | Audit trail de cambios |

#### `recomendaciones_plan_ia`
- FK CASCADE a `planes_ia.id`. Referenciado por endpoint `/recomendaciones/...` (ver §6).

### 4.4 Cobertura DB actual (2026-05-28)

```sql
SELECT tipo, COUNT(*), COUNT(*) FILTER (WHERE estructura_json IS NOT NULL) AS con_struct,
       COUNT(DISTINCT modelo_ia) AS modelos
FROM planes_ia GROUP BY tipo;
```

| tipo | count | con `estructura_json` | modelos únicos |
|---|---|---|---|
| `DIAGNOSTICO` | 35 | 21 (60%) | 7 |
| `CONSOLIDACION` | **46** | 46 (**100%** ✅) | 7 |
| `CONTENIDO` | 15 | 15 (**100%** ✅) | 2 |

**Top modelos IA usados** (16 total):
- `foda-derived-v3` — 20
- `cc-contenido-v2-2026-05-21` — 11
- `cc-consolidacion-v2-2026-05-21` — 11
- `claude-code-2026-05-12` — 8
- `cc-claude-inline-2026-05-27` — 7
- `data-driven-v1` — 7
- `claude-2way-enriched-2026-05-10` / `gemini-cli-2way-enriched-2026-05-10` — 6 cada uno
- otros 8 modelos con counts 1-5

⚠️ CONSOLIDACION y CONTENIDO siempre traen `estructura_json` (100%). DIAGNOSTICO solo 60% (ver §3.4 — deuda load-bearing del fallback `_parse_foda`).

### 4.5 Generadores (escriben `planes_ia`)

Ver §3.5. Resumen aplicable a §4:

| Tipo | Endpoint API | Scripts batch |
|---|---|---|
| DIAGNOSTICO | `POST /planes/generar` con `tipo=DIAGNOSTICO` | `generate_diagnostico_dirigentes.py`, `regen_diagnostico_v2.py`, `regen_diagnostico_enriched*.py`, `regen_diagnostico_gemini.py` |
| CONSOLIDACION | `POST /planes/generar` con `tipo=CONSOLIDACION` | `regen_consolidacion_v2.py`, `generate_planes_v3_from_diagnostico.py` |
| CONTENIDO | `POST /planes/generar` con `tipo=CONTENIDO` | `regen_contenido_v2.py` |

### 4.6 Deuda y estado real conocido

| Item | Estado | Notas |
|---|---|---|
| ⚠️ **FE-BE mismatch `useGeneratePlan`** | ❌ Broken | `use-planes.ts:27` llama `POST /planes/generate` pero backend es `POST /planes/generar` (`planes.py:72`). Resultado: hook tira 404. **Verificar si se usa actualmente — D-CTA-GENERATE-REMOVED 2026-05-21 quitó el CTA de la UI, posible muerto.** |
| ⚠️ **FE-BE mismatch `useApprovePlan`** | ❌ Broken | `use-planes.ts:37` llama `PATCH /planes/{id}/approve` pero backend es `PATCH /planes/{id}/aprobar` (`planes.py:196`). |
| ⚠️ **FE-BE mismatch `useRejectPlan`** | ❌ Broken | `use-planes.ts:48` llama `PATCH /planes/{id}/reject`. Endpoint backend `/rechazar` no confirmado (mismo bloque línea 196 pero no verificado nombre). |
| Endpoint listing `/planes` paginated | ✅ Funcional | Hook + path coinciden. |
| Endpoint detalle `/planes/{id}` | ✅ Funcional | Hook + path coinciden. |
| Endpoints `/tareas` y `/progreso` | ✅ Funcionales | Hooks + paths coinciden. |
| Tab Estrategia + Tab Contenido | 📝 Empty state | "Próximamente · Fase 2" según D-PLANES-CONCEPTO-3. UI lista, generación operativa via scripts batch. |
| Rate limit `5/hour` generación | ✅ Aplicado | `@limiter.limit("5/hour")` en ambos endpoints generación. |
| Kanban page deprecada | ⚠️ Redirect | `[id]/kanban/page.tsx` redirige según tipo. Mantener mientras existan links externos. |
| Botones Aprobar/Rechazar en `[id]/page.tsx` | ❌ **Placeholders sin handler** | Líneas 242 (`Rechazar`) y 246 (`Aprobar Plan`) renderizan pero NO tienen `onClick` (verificado con grep). Los hooks `useApprovePlan` / `useRejectPlan` existen pero el wiring FE→handler está roto. Deuda visible al usuario. Combinada con el mismatch FE-BE (`/approve` vs `/aprobar`) son 2 fallas serializadas en esta acción. |
| Tipo `CRISIS` sin UI dedicada | ⚠️ Existe en modelo | `app/models/plan_ia.py:16` define CRISIS pero la vista `[id]/page.tsx` solo etiqueta colores (`TIPO_LABELS.CRISIS`). No hay tab ni generación específica. ADR pendiente: o se documenta como "preparado para futuro" o se elimina del enum. |
| Cobertura modelos IA | ⚠️ 16 modelos distintos | Inconsistencia. ADR pendiente: estandarizar etiquetado `modelo_ia` (ej. solo `cc-{tipo}-v2-{fecha}` o `claude-{model}-{fecha}`). |
| Stream endpoint | ⚠️ Sin hook FE | `POST /planes/generar/stream` SSE existe pero no consumido. Posible uso futuro para UI con feedback en vivo. |

### 4.7 Cómo responder preguntas comunes

| Pregunta CEO | Dónde está la respuesta |
|---|---|
| "¿Por qué el botón Generar Plan no aparece?" | D-CTA-GENERATE-REMOVED 2026-05-21. Generación ahora vía scripts batch o API direct. UI rediseñada Concepto 3. |
| "¿Por qué useGeneratePlan / useApprovePlan están rotos?" | Mismatch en rutas FE→BE (`generate` vs `generar`, `approve` vs `aprobar`). Deuda detectada por audit 2026-05-28 en §4.6. Fix: cambiar el path en hook FE. |
| "¿Cuál es el estado de cada tab del Concepto 3?" | Diagnóstico ✅ funcional. Estrategia 📝 empty state. Contenido 📝 empty state. Fase 2 desbloqueable cuando se decida UI. |
| "¿Cómo se generan los planes hoy?" | Scripts batch (`regen_*_v2.py`) corriendo en host con Claude Code subprocess o Gemini CLI. Endpoint `POST /planes/generar` existe pero el hook FE está roto. |
| "¿Cuántos modelos IA distintos se usan?" | 16 etiquetas distintas en `modelo_ia`. Inconsistencia (algunos `cc-...`, otros `claude-...`, `gemini-...`, `gemma3:12b`, `data-driven-v1`). |

### 4.8 Auditoría

- **2026-05-28** · Auditor: Gemini · Veredicto: ⚠️ **Pasa con ajustes** (reporte: `.context/audits/2026-05-28-mapa-funcional-seccion-4.md`).
- **Hallazgos sustantivos aplicados:**
  1. **Tab Diagnóstico eliminado 2026-05-22** (`D-PLANES-DIAGNOSTICO-REMOVED-2026-05-22`, `page.tsx:57`). Corregido §4.1: 2 tabs reales, no 3.
  2. **Tipo `CRISIS` en `tipo_plan_enum`** verificado SQL (4 valores: DIAGNOSTICO/CONSOLIDACION/CRISIS/CONTENIDO). Agregado a §4.3.
  3. **Enum `estado_tarea_enum`** valores reales `TODO/IN_PROGRESS/DONE` (no `DOING` como asumí). Corregido §4.3.
  4. **Botones Aprobar/Rechazar son placeholders sin onClick** (`[id]/page.tsx:242,246`). Combinado con FE-BE mismatch en hooks. Agregado a §4.6.
- **Falso positivo del auditor:** Gemini afirmó "líneas planes.py desplazadas (list_tareas en 214 vs 228 citado)". Verificado: `planes.py:228` es `@router.get` decorator, `:229` es `async def list_tareas`. Mi cita al decorator es correcta. Sin acción.
- **Sesgo declarado:** modelos IA legacy vs activos no diferenciados. RBAC verificado por código, no probado empíricamente.

## 5. Clima Político ✅

**Concepto:** vista de contexto comparativo nacional con series temporales de aprobación/desaprobación pública de gobernadores, alcaldes y presidente (datos de encuestas públicas Mitofsky, Oraculus, Demoscopía Digital). Permite al cliente ver "cómo está mi gobernador vs otros del mismo partido" sin scope multi-tenant (es dato público).

### 5.1 Vistas FE

#### `/dashboard/social/clima/` (página única)
- **Archivo:** `frontend/src/app/dashboard/social/clima/page.tsx`
- **Función:** dashboard con series temporales de aprobación gubernamental. Filtros: métrica (aprobación / desaprobación / ambas), búsqueda por actor, ámbito (federal / estatal / municipal). Visualización con Recharts `LineChart`. Detección de expresidentes para color especial (Sheinbaum, Brugada, Salomón Jara hardcoded).
- **Hook:** `useClimaPolitico(metrica)` (`use-clima-politico.ts:19`)
- **Endpoint:** `GET /social/clima-politico?metrica=aprobacion|desaprobacion|ambas`
- **Response type:** `ClimaPoliticoSerie[]` con `{actor_nombre, actor_tipo, ambito, entidad, municipio, puntos: [{fecha, valor_pct, metrica}]}`

### 5.2 Endpoint backend

Archivo: `backend/app/api/v1/endpoints/social.py`

| Endpoint | Línea | Función |
|---|---|---|
| `GET /social/clima-politico` | `social.py:473` | Series temporales aprobación gubernamental. Query param `metrica` (default `aprobacion`). Sin multi-tenant scoping (dato público desde 2026-05-12). |

**Lógica clave (`social.py:474-547`):**

1. **Filtro de fuentes hardcoded:** SQL filtra solo `fuente IN ('Demoscopía Digital', 'Oraculus poll-of-polls', 'Mitofsky')` (línea 503). Las otras 12 fuentes en BD se ignoran.
2. **Filtro métrica condicional:** si `metrica != "ambas"`, agrega `AND metrica = :metrica`.
3. **Agregación:** `AVG(valor_pct)` agrupado por `(actor_nombre, actor_tipo, ambito, entidad, municipio, metrica, fecha_publicacion)`.
4. **Dedup en código (Python):** se construye `seen` dict con clave `(nombre, ambito, municipio)` para alcaldes (homonimia política conocida) o `(nombre, ambito)` para gobernadores/presidente.
5. **Sort final:** por `(ambito, actor_nombre)`.

### 5.3 Tabla DB que el módulo lee

`encuestas_publicas` (NO `encuestas` ni `encuestas_resultados`).

Cobertura 2026-05-28 (filtrando solo fuentes usadas por endpoint):

```sql
SELECT fuente, ambito, COUNT(*), COUNT(DISTINCT actor_nombre) AS actores,
       MIN(fecha_publicacion), MAX(fecha_publicacion)
FROM encuestas_publicas WHERE fuente IN ('Demoscopía Digital','Oraculus poll-of-polls','Mitofsky')
GROUP BY fuente, ambito;
```

| Fuente | Ámbito | rows | actores | desde | hasta |
|---|---|---|---|---|---|
| Demoscopía Digital | estatal | 2,167 | 31 | 2022-10 | 2026-04 |
| Demoscopía Digital | federal | 106 | 1 | 2024-10 | 2026-04 |
| Demoscopía Digital | municipal | **12,610** | 242 | 2021-03 | 2026-04 |
| Mitofsky | estatal | 1,334 | 55 | 2022-10 | 2026-03 |
| Mitofsky | federal | 122 | 3 | 2020-01 | 2026-04 |
| Mitofsky | municipal | 2,241 | **579** | 2023-02 | 2026-04 |
| Oraculus poll-of-polls | federal | 748 | 6 | 1995-02 | 2025-09 |

**Total usable: ~19,328 rows** (de 15 fuentes y ~33,000 rows en `encuestas_publicas`).

### 5.4 Deuda y estado real conocido

| Item | Estado | Notas |
|---|---|---|
| Endpoint `/social/clima-politico` | ✅ Funcional | Query SQL directa, sin service intermedio. |
| Filtro estatal removido 2026-05-12 | ✅ Decisión documentada | "Aprobación pública es 100% DATO PÚBLICO" (`social.py:484-487`). Cliente ve contexto nacional comparativo. |
| **Hardcoded 3 fuentes** | ⚠️ Asume canon | `Mitofsky`, `Oraculus`, `Demoscopía Digital` son las 3 admitidas. Las otras 12 fuentes (Buendía y Márquez, El Financiero, Enkoll, GobernArte, PollsMX, etc.) tienen datos pero NO se exponen al cliente. ADR pendiente: o se documenta la decisión de canon o se permite override por config. |
| Filtros municipio para alcaldes | ✅ Implementado | Clave de dedup incluye `municipio` por homonimia política conocida. |
| Sin paginación | ⚠️ Por diseño | El endpoint devuelve TODAS las series (potencialmente cientos de actores × cientos de puntos). Si vol crece se necesitará paginación o filtro por actor desde query. |
| Cache `staleTime: 5 min` (FE) | ✅ Razonable | Datos públicos no cambian frecuente. |
| Sin scope multi-tenant | ✅ Por diseño | Dato público — `_ = current_user` línea 491. |
| Detección expresidentes hardcoded | ⚠️ Frontend-side | `EXPRESIDENTES` Set en `page.tsx:46` con 5 nombres verificados: AMLO, EPN, FCH, Vicente Fox Quesada, Ernesto Zedillo Ponce de León. Mantener cuando aparezca el siguiente expresidente. |
| Métrica `ambas` retorna 2× rows | ⚠️ Posible perf | Si metrica=ambas, se agregan aprobacion + desaprobacion en un GROUP BY. Si actor tiene 200 puntos × 2 = 400. ResponseType lista de series. |

### 5.5 Cómo responder preguntas comunes

| Pregunta CEO | Dónde está la respuesta |
|---|---|
| "¿De dónde salen los números de aprobación?" | 3 fuentes hardcoded en endpoint: Mitofsky, Oraculus, Demoscopía Digital. Las otras 12 en BD no se muestran. |
| "¿Por qué Felipe NO aparece aquí?" | Felipe (60) es legislador, no gobernador/alcalde/presidente. `encuestas_publicas` solo cubre cargos ejecutivos. |
| "¿Por qué un gobernador aparece varias veces con misma fecha?" | El endpoint agrega `AVG(valor_pct)` sobre encuestadoras y fechas. Si misma fecha tiene 2+ encuestas, se promedia. |
| "¿Cómo agrego una encuesta?" | Insertar en `encuestas_publicas` (no expuesto por API actual). Si la `fuente` no está en el whitelist, no aparecerá en FE. |
| "¿Se ve histórico desde cuándo?" | Oraculus federal desde **1995** (40 años). Demoscopía municipal desde 2021. Mitofsky federal desde 2020. |

### 5.6 Auditoría

- **2026-05-28** · Auditor: Gemini · Veredicto: ✅ **Pasa** (reporte: `.context/audits/2026-05-28-mapa-funcional-seccion-5.md`).
- **Citas verificadas:** 8 afirmaciones (vista FE, hook, endpoint, filtro fuentes SQL, agregación, dedup, cobertura DB, CRUD asimétrico). 0 inventos. 0 omisiones.
- **Sesgo declarado y corregido:** `EXPRESIDENTES` Set tiene 5 nombres (no 3) — corregido §5.4 con lista completa.

## 6. Recomendaciones · Mi Evaluación · Reels ✅

**Concepto:** 3 sub-módulos accionables del cliente. **Recomendaciones** entregan acciones priorizadas (start/stop/continue) derivadas del análisis IA con ciclo de estados 5 fases (D-17). **Mi Evaluación** permite al dirigente ajustar pesos del cálculo de Actividad Política Alineada para personalizar el KPI. **Reels** genera guiones para video corto vía Groq Llama 3.3 70B.

### 6A. Recomendaciones

#### 6A.1 Vista FE
- **Archivo:** `frontend/src/app/dashboard/recomendaciones/page.tsx`
- **Hooks:** `useRecomendaciones(filters)`, `useTransicionarEstado()`, `useVincularPostEjecutor()` (declarados en `use-recomendaciones.ts`)
- **Ciclo de estados (D-17 · 5 fases):** `propuesta` → (admin pass) → `aprobada` | `rechazada` | `modificada` → (cliente ejecuta) → `ejecutada` → `completada` | `fallida`. Veredicto cliente: `exitosa` | `parcial` | `fallida`.

#### 6A.2 Endpoints backend (`backend/app/api/v1/endpoints/plan_ia.py`)

| Endpoint | Línea | Función |
|---|---|---|
| `POST /plan-ia/generate/{dirigente_id}` | `plan_ia.py:69` | ⚠️ **FEATURE PAUSADA 2026-05-15** — Genera batch de recomendaciones IA. Quote del docstring (línea 78). Argumento `force` admin-only bypass del rate limit 24h. |
| `GET /plan-ia/generate/status/{task_id}` | `plan_ia.py:474` | Polling del status de generación async (Celery task). |
| `GET /plan-ia/recomendaciones` | `plan_ia.py:272` | Lista con filtros `estado` (multi), `dirigente_id`, `tipo`, `limit`. RBAC: viewer solo ve `aprobada/modificada/ejecutada/completada` (NO `propuesta` ni `rechazada`). |
| `PUT /plan-ia/{recomendacion_id}/estado` | `plan_ia.py:364` | Transición de estado del ciclo D-17 |
| `PUT /plan-ia/{recomendacion_id}/post-ejecutor` | `plan_ia.py:424` | Vincula recomendación a `social_posts.id` ejecutor (T7) |

**Endpoint NO existe** (hallazgo audit Gemini 2026-05-28): el header del hook `use-recomendaciones.ts:5-10` menciona `GET /plan-ia/{id}/seguimiento` pero NO está implementado en backend. Verificado: 0 matches en `grep "seguimiento" plan_ia.py`. Si la UI lo consume → degrada a empty state (defensiva del hook).

#### 6A.3 Tabla DB · `recomendaciones_plan_ia`

Schema esperado (basado en `Recomendacion` interface en `use-recomendaciones.ts:65`):
- `id`, `plan_ia_id` FK, `dirigente_id`, `org_id`
- `tipo` enum (`start`/`stop`/`continue`)
- `accion_texto` text
- `ventana_inicio`, `ventana_fin`, `ventana_duracion_dias`
- `criterio_exito` jsonb, `principio_conductual` text, `evidencia_respaldo` jsonb
- `estado` enum 7 valores
- `post_ejecutor_id` FK → `social_posts.id`
- `metricas_predichas` jsonb, `metricas_observadas` jsonb
- `veredicto`, `veredicto_editado_por_cliente`, `veredicto_original`
- `notas_cliente` text

#### 6A.4 Cobertura

```sql
SELECT estado, COUNT(*) FROM recomendaciones_plan_ia GROUP BY estado;
-- 0 rows (tabla vacía)
```

⚠️ **0 recomendaciones generadas hoy.** Feature pausada desde 2026-05-15. FE renderiza empty state cuando la lista está vacía.

### 6B. Mi Evaluación

#### 6B.1 Vista FE
- **Archivo:** `frontend/src/app/dashboard/evaluacion/[id]/page.tsx`
- **Concepto (D-23-H Phase B · 2026-04-25):** dirigente ajusta pesos por categoría `target_politico` para personalizar el KPI **Actividad Política Alineada**. Doble métrica siempre visible: Análisis IA (pesos default) + Tu Lectura (pesos del dirigente).
- **Decisiones consolidadas:**
  - Solo Palanca 1 (pesos por categoría). Palanca 2 (override per-post) → Phase C futura.
  - 3 presets políticos + Personalizado, sin sliders abstractos.
  - `last_modified` stamp en columna, sin tabla `history` MVP.
  - Comparativas inter-dirigentes usan SIEMPRE default (no manipulable por ranking).
- **Hooks:** `useDirigente(id)` (`use-dirigentes.ts:35`), `useUpdateDirigentePesos()` (`use-dirigentes.ts:101`). NO existe `use-evaluacion.ts` — todo vive en `use-dirigentes.ts`.

#### 6B.2 Endpoint backend

| Endpoint | Línea | Función |
|---|---|---|
| `PATCH /dirigentes/{dirigente_id}/pesos` | `dirigentes.py:365` | Actualiza `dirigentes.pesos_target_politico` (jsonb). Devuelve dirigente actualizado con los pesos en línea 398 + 413. |

**Nota:** el endpoint `hitl_evaluation.py` (con prefijo `/hitl/`) **NO es Mi Evaluación** — es para HITL de **comments y posts** (review/confirm de clasificaciones NLP). Las rutas son: `/hitl/sample`, `/hitl/comments/{id}`, `/hitl/posts/{id}`, `/hitl/audit/{id}`. Pertenece a §10 Admin.

#### 6B.3 Columna DB

`dirigentes.pesos_target_politico` jsonb. Default null → usa preset por defecto (ver `components/evaluacion/presets.ts`).

### 6C. Reels

#### 6C.1 Vista FE
- **Archivo:** `frontend/src/app/dashboard/reels/page.tsx`
- **Hooks (`use-reels.ts`):**
  - `useGenerateReelScript()` (línea 57) → `POST /reels/generate-script`
  - `useRecentReelScripts()` (línea 70) → `GET /reels/recent`

#### 6C.2 Endpoints backend (`backend/app/api/v1/endpoints/reels.py`)

| Endpoint | Línea | Función |
|---|---|---|
| `POST /reels/generate-script` | `reels.py:58` | Genera UN guión vía **Groq Llama 3.3 70B (tier gratuito)**. Latencia 1-2s. Scope multi-tenant via `assert_dirigente_access`. |
| `GET /reels/recent` | `reels.py:182` | Lista guiones recientes para el dirigente |

#### 6C.3 Pipeline de generación (`reels.py:58-100`)

1. Scope check: `assert_dirigente_access(db, current_user, dirigente_id)`
2. Fetch metadata: `_fetch_dirigente_meta()` → nombre + cargo
3. **Builder de contexto determinista (Feature 2 · 2026-05-17):** `build_dirigente_context(db, dirigente_id)` extrae tono dominante, target predominante, posts recientes, promesas, efemérides. ~50ms, sin LLM.
4. Si builder falla → fallback "modo genérico" sin contexto (no bloquea la generación).
5. Llamada a Groq con `generate_reel_script()` (service `reels_generator.py`).
6. **Persistencia:** en `contenido_piezas` (NO en `reel_scripts` — la tabla `reel_scripts` no existe en DB), con `variantes` jsonb `{duracion_segundos, incluir_cta, script, metadata}`.

#### 6C.4 Cobertura
- Tabla `reel_scripts` **NO existe** en DB (verificado SQL).
- Guiones persistidos en `contenido_piezas.variantes` jsonb.

### 6.D Deuda y estado real conocido

| Item | Estado | Notas |
|---|---|---|
| **Recomendaciones — generación pausada** | ⚠️ FEATURE PAUSADA 2026-05-15 | `plan_ia.py:69` docstring. 0 recomendaciones generadas. Hooks + página + ciclo de estados implementados, esperan reactivación. |
| Recomendaciones endpoints transición | ⚠️ Sin verificación grep | `/estado`, `/post-ejecutor`, `/seguimiento` declarados en hook FE pero no confirmé backend. |
| Mi Evaluación Palanca 1 (pesos) | ✅ Funcional | PATCH `/dirigentes/{id}/pesos` operativo. 3 presets + custom. |
| Mi Evaluación Palanca 2 (per-post) | 📝 Phase C futura | Decisión cerrada D-23-H. Diferido a roadmap. |
| Reels generación | ✅ Funcional | Groq tier gratuito, 1-2s latencia. Persiste en `contenido_piezas`. |
| Reels persistencia | ⚠️ Confuso | Doc previo asumía `reel_scripts` table. Real: `contenido_piezas` con `variantes` jsonb. ADR pendiente: o crear tabla dedicada o documentar la decisión jsonb. |
| HITL Evaluation (comments/posts) | ⚠️ Confusión naming | `hitl_evaluation.py` NO es Mi Evaluación. Mover a §10 Admin. |

### 6.E Cómo responder preguntas comunes

| Pregunta CEO | Dónde está la respuesta |
|---|---|
| "¿Por qué no se generan recomendaciones?" | Feature pausada 2026-05-15 (`plan_ia.py:69`). Esperan reactivación. |
| "¿Cómo personalizo el cálculo del Actividad Política Alineada?" | Página `/dashboard/evaluacion/{id}/` con 3 presets + Personalizado. PATCH `/dirigentes/{id}/pesos`. |
| "¿Por qué el ranking sigue usando pesos default si yo personalicé?" | Decisión D-23-H 2026-04-25: comparativas inter-dirigentes SIEMPRE usan default. Personalización es vista personal. |
| "¿Cuánto tarda generar un reel?" | 1-2 segundos (Groq Llama 3.3 70B tier gratuito). |
| "¿Por qué `reel_scripts` no existe?" | Diseño: persiste en `contenido_piezas.variantes` jsonb. ADR pendiente formalizar. |

### 6.F Auditoría

- **2026-05-28** · Auditor: Gemini · Veredicto: ⚠️ **Pasa con ajustes** (reporte: `.context/audits/2026-05-28-mapa-funcional-seccion-6.md`).
- **Hallazgos aplicados:**
  1. `GET /plan-ia/{id}/seguimiento` NO existe (eliminado de §6A.2). El comentario del hook FE menciona el endpoint pero backend nunca lo implementó.
  2. `PUT /plan-ia/{recomendacion_id}/post-ejecutor` confirmado en `plan_ia.py:424` (no "asumido").
  3. Precisada ubicación de `useUpdateDirigentePesos` en `use-dirigentes.ts:101`.
  4. Agregado `GET /plan-ia/generate/status/{task_id}` (`plan_ia.py:474`) como endpoint de soporte para polling de la generación async.
- **Sesgo declarado:** validación del ciclo de estados RBAC NO probada empíricamente (0 rows en `recomendaciones_plan_ia`). Documentado en deuda §6.D.

## 7. Overview + Dirigentes ✅

**Concepto:** entrada principal del dashboard. **Overview** muestra KPIs agregados scoped a rol/org, top dirigentes, alertas crisis activas, tono discurso trend. **Dirigentes** lista + CRUD + vista de perfil (`[id]`) con sub-páginas (diagnóstico, evaluación, FODA, perfil social).

### 7A. Overview (dashboard root `/dashboard/`)

#### 7A.1 Vista FE
- **Archivo:** `frontend/src/app/dashboard/page.tsx`
- **Hooks (`use-overview.ts`):**
  - `useKpiOverview(period)` (línea 14) — `period` enum: `today|7d|30d|90d` (default `30d`)
  - `useTopDirigentes(limit)` (línea 31) — usa `/dirigentes/?per_page=limit` reutilizado
  - `useSystemStatus()` (línea 50)
  - `useCrisisAlerts()` (línea 42) — solo `severity=high&type=crisis`
  - `useAlerts(unreadOnly)` (línea 22)
  - `useHealthCheck()` (línea 58)
- **Hooks `use-social.ts`:** `useSocialPosts()`, `useTonoDiscursoTrend()`, `useTonoDiscursoCoverage()`
- **Componentes principales:** `TonoDiscursoChart`, `PostCard`, `CrisisAlertList`
- **Layout:** cards de KPIs arriba-izquierda (regla `~/.claude/rules/design-standards.md`), gráficas centro, alertas a la derecha.

#### 7A.2 Endpoints backend

| Endpoint | Línea | Función |
|---|---|---|
| `GET /dashboard/overview?period=...` | `dashboard.py:60` | KPIs agregados. Scope: dirigente_user → su dirigente; non-admin org → todos los de su org; admin → controla via `X-Org-Id` header. |
| `GET /dashboard/status` | `dashboard.py:269` | ⚠️ **HARDCODED:** `workers_active=2, workers_total=2, scrapers_running=0, last_sync=NOW()`. No consulta Celery real. |
| `GET /alerts/` | `alerts_integration.py:20` | Lista `AlertaCrisisResponse[]`. |

#### 7A.3 Lógica de scoping (KPI Overview)

`dashboard.py:74-87`:
1. Resolve `user_dirigente_id` y `user_org_id` de current_user.
2. Si admin + header `X-Org-Id` → `effective_org_id = int(header)`.
3. Periodo → días (`PERIOD_TO_DAYS["30d"]=30`, etc.).
4. Queries SQL agregadas posts/alerts/sentiment dentro de la ventana.

### 7B. Dirigentes (lista + CRUD)

#### 7B.1 Vista FE
- **Archivo:** `frontend/src/app/dashboard/dirigentes/page.tsx` (lista)
- **Archivo:** `frontend/src/app/dashboard/dirigentes/[id]/page.tsx` (detalle)
- **Hooks (`use-dirigentes.ts`):**
  - `useDirigentes(params)` (línea 12) — paginado
  - `useDirigente(id)` (línea 35)
  - `useDirigenteCrecimiento(id)` (línea 68)
  - `useCreateDirigente()` (línea 77)
  - `useUpdateDirigente()` (línea 88)
  - `useUpdateDirigentePesos()` (línea 101) — usado por §6B Mi Evaluación
  - `useDeleteDirigente()` (línea 112)
- **Hooks Onboarding wizard S5 (`use-onboarding.ts`):**
  - `useOnboardDirigente()` (línea 369) — POST `/dirigentes/onboard`
  - `useOnboardingProgress(dirigenteId)` (línea 376) — polling `/dirigentes/{id}/onboarding-progress`
  - + 10 hooks adicionales para sub-pasos del wizard (`useSaveProfile`, `useSerpSearch`, `useValidateAccount`, `useInitOAuth`, `useSaveCompetidores`, `useSavePromesas`, `useActivate`, etc.)
- **Componente Wizard:** `frontend/src/components/onboarding/onboarding-wizard.tsx` — UI completa del flow S5.

#### 7B.2 Endpoints backend (`backend/app/api/v1/endpoints/dirigentes.py`)

| Endpoint | Línea | Función |
|---|---|---|
| `GET /dirigentes/` | `dirigentes.py:37` | Lista paginada, filtros |
| `GET /dirigentes/{id}` | `dirigentes.py:127` | Detalle |
| `POST /dirigentes/` | `dirigentes.py:301` | Crear |
| `PATCH /dirigentes/{id}` | `dirigentes.py:319` | Update |
| `PATCH /dirigentes/{id}/pesos` | `dirigentes.py:364` | Update pesos (Mi Evaluación · §6B) |
| `DELETE /dirigentes/{id}` | `dirigentes.py:421` | Eliminar |
| `GET /dirigentes/{id}/diagnostico` | `dirigentes.py:438` | Diagnóstico legacy |
| `GET /dirigentes/{id}/flash-analysis` | `dirigentes.py:453` | Flash analysis IA |
| `GET /dirigentes/{id}/social-summary` | `dirigentes.py:591` | Resumen social agregado |
| `POST /dirigentes/onboard` | `dirigentes.py:665` | **S5.3a Onboarding wizard** — Crear User + Dirigente + SocialProfiles en transacción. Retorna 201 con `sync_status='pending'`. Dispara Celery chain `onboard_dirigente_chain` (scrape → NLP → IPD). ADMIN only. |
| `GET /dirigentes/{id}/onboarding-progress` | `dirigentes.py:770` | **S5.4 Poll del estado de onboarding** — devuelve % progreso (0/25/55/85/100) según `dirigente.sync_status`. |
| `GET /dirigentes/{id}/crecimiento` | `dirigentes.py:861` | Crecimiento histórico (denormalized snapshots) |

### 7.C Tablas DB

- `dirigentes` (schema verificado en §1.3 y §2.4)
- `organizations` (referenciado por `org_id` FK)
- `alertas_crisis` (verificar tabla — referenciada por `/alerts`)
- `users` (FK `dirigente_id` en users)

### 7.D Cobertura DB (2026-05-28)

```sql
SELECT COUNT(*), COUNT(DISTINCT org_id) AS orgs FROM dirigentes;
-- 13 dirigentes en 5 orgs
```

| Dirigentes activos | 13 |
| Organizaciones | 5 |
| Con DIAGNOSTICO reciente (último 30d) | 9 (ver §3.4) |

### 7.E Deuda y estado real conocido

| Item | Estado | Notas |
|---|---|---|
| `GET /dashboard/overview` | ✅ Funcional | Scope multi-tenant correcto. |
| `GET /dashboard/status` | ❌ **Hardcoded** | `dashboard.py:269` retorna valores fijos. NO consulta Celery real. Deuda: integrar con flower o redis. |
| `useTopDirigentes` | ✅ Funcional | Reutiliza endpoint `/dirigentes/?per_page=N`. Sin endpoint dedicado. |
| CRUD Dirigentes completo | ✅ Funcional | GET/POST/PATCH/DELETE + pesos + diagnostico legacy + crecimiento. |
| `useDeleteDirigente` | ⚠️ Existe pero ¿usado? | Hook FE existe; verificar si la UI tiene botón. |
| `flash-analysis` endpoint | 📝 No documentado | Devuelve `FlashAnalysisResponse`. Genera análisis flash IA. Pendiente clarificar uso. |
| Mapa electoral (componente comentado en page.tsx) | 📝 Pendiente INE shapefiles | Comentario en línea 30 del page: "Electoral map hidden until INE shapefiles are loaded". |
| `useHealthCheck()` | ✅ Existe | Llama `/health/` (no `/dashboard/health`). |

### 7.F Cómo responder preguntas comunes

| Pregunta CEO | Dónde está la respuesta |
|---|---|
| "¿Por qué `/dashboard/status` siempre muestra 2 workers?" | Endpoint hardcoded (`dashboard.py:269`). No consulta Celery real. Deuda. |
| "¿Por qué admin ve datos de otra org?" | Admin puede setear `X-Org-Id` header para cambiar scope. Sin header → effective_org_id = su propio org_id. |
| "¿Cuál es la diferencia entre `useDirigente` y `useTopDirigentes`?" | `useDirigente` es detalle por id. `useTopDirigentes` es lista paginada del endpoint `/dirigentes/`, no hay endpoint dedicado para "top". |
| "¿Cuándo se ve el mapa electoral?" | Hidden hasta cargar shapefiles INE. Comentado en `dashboard/page.tsx`. |

### 7.G Auditoría

- **2026-05-28** · Auditor: Gemini · Veredicto: ⚠️ **Pasa con ajustes** (reporte: `.context/audits/2026-05-28-mapa-funcional-seccion-7.md`).
- **Hallazgos aplicados:**
  1. Corregido endpoint `POST /dirigentes/{id}/...` (`dirigentes.py:665`) → es realmente `POST /dirigentes/onboard` (sin path param).
  2. Corregido `GET /dirigentes/{id}/...` (`dirigentes.py:770`) → es `GET /dirigentes/{id}/onboarding-progress` (S5.4 polling).
  3. Agregados 12+ hooks de `use-onboarding.ts` que faltaban (incluyendo `useOnboardDirigente` línea 369 y `useOnboardingProgress` línea 376).
  4. Agregado componente `onboarding-wizard.tsx`.
- **Sesgo declarado:** RBAC verificado por lectura de código, no probado empíricamente. Cobertura solo en 13 dirigentes piloto.

## 8. Diagnóstico Tier 2 (B11-B18) ✅

**Concepto:** segunda capa de diagnóstico focalizada en **integridad de la conversación** (CIB, cross-partisan, filtro de realidad), **derivas y riesgos discursivos** (topic drift, rage click, violencia política) y **compliance** (promesas, veda INE). 8 bloques B11-B18.

### 8.1 Vista FE

#### `/dashboard/diagnostico-tier2/[dirigenteId]/`
- **Archivo:** `frontend/src/app/dashboard/diagnostico-tier2/[dirigenteId]/page.tsx`
- **Hooks:** `useDiagnosticoTier2(dirigenteId, filtroCIB)` (`use-diagnostico-tier2.ts:228`) + `useDiagnosticoTier1` (para mostrar baseline + recomputed ER cuando `filtroCIB=true`)
- **Componentes:** `CardB11..CardB18` (`components/diagnostico_tier2/cards.tsx:76,172,276,404,508,620,741,861`), `CardTier2Skeleton` (línea 972)
- **Feature distintiva:** toggle "Filtro de Realidad" (B13). Cuando se activa, `useDiagnosticoTier2` envía `?recompute_tier1=true` y el backend devuelve `tier1_recomputed` con ER excluyendo comments de authors flagged por CIB. **Demuestra el valor del filtro al cliente.**

#### `/dashboard/diagnostico-tier2/` (lista)
- **Archivo:** `frontend/src/app/dashboard/diagnostico-tier2/page.tsx`
- Lista dirigentes (similar a §2.1).

### 8.2 Endpoint backend

Archivo: `backend/app/api/v1/endpoints/diagnostico_tier2.py`. Prefix `/diagnostico_tier2/` (NO `/diagnostico/` — endpoint separado del Tier 1).

| Endpoint | Línea | Service invocado | Función |
|---|---|---|---|
| `GET /diagnostico_tier2/{dirigente_id}` | `diagnostico_tier2.py:142` | **agregado · 8 services + opcional recompute Tier 1** | Devuelve `{bloques: {B11..B18}, tier1_recomputed?, ...}`. Acepta `?recompute_tier1=true&en_veda=true`. **B12 corre primero** porque B13 lo consume (`cib_result` pasado a `filtro_realidad_service.compute()`). |
| `GET /diagnostico_tier2/{dirigente_id}/cross_partisan` | `diagnostico_tier2.py:45` | `cross_partisan_service.compute()` | B11 individual |
| `GET /diagnostico_tier2/{dirigente_id}/cib_detector` | `diagnostico_tier2.py:57` | `cib_detector_service.compute()` | B12 individual (CIB Detector multinivel ITESO/DFRLab) |
| `GET /diagnostico_tier2/{dirigente_id}/filtro_realidad` | `diagnostico_tier2.py:69` | `filtro_realidad_service.compute()` | B13 individual |
| `GET /diagnostico_tier2/{dirigente_id}/topic_drift` | `diagnostico_tier2.py:81` | `topic_drift_service.compute()` | B14 individual (caption vs comments divergence) |
| `GET /diagnostico_tier2/{dirigente_id}/rage_click` | `diagnostico_tier2.py:93` | `rage_click_service.compute()` | B15 individual |
| `GET /diagnostico_tier2/{dirigente_id}/promesas` | `diagnostico_tier2.py:105` | `promesas_service.compute()` | B16 individual |
| `GET /diagnostico_tier2/{dirigente_id}/veda_compliance` | `diagnostico_tier2.py:117` | `veda_compliance_service.compute()` | B17 individual (admite `en_veda` flag) |
| `GET /diagnostico_tier2/{dirigente_id}/violencia_politica` | `diagnostico_tier2.py:130` | `violencia_politica_service.compute()` | B18 individual |

### 8.3 Catálogo de bloques B11-B18

| Bloque | Service (`backend/app/services/diagnostico_tier2/`) | Card FE | Concepto |
|---|---|---|---|
| **B11 Cross-Partisan** | `cross_partisan_service.py` | `CardB11` (`cards.tsx:76`) | Validation Score: cuántos comments del dirigente vienen de cuentas que también comentan a rivales políticos (validación inter-partidaria). |
| **B12 CIB Detector** | `cib_detector_service.py` | `CardB12` (`cards.tsx:172`) | Coordinated Inauthentic Behavior multinivel (metodología ITESO + DFRLab). Flags `author_hashes` sospechosos. |
| **B13 Filtro de Realidad** | `filtro_realidad_service.py` | `CardB13` (`cards.tsx:276`) | ER orgánico **excluyendo authors flagged por B12**. Permite recompute Tier 1 para ver "engagement real". |
| **B14 Topic Drift** | `topic_drift_service.py` | `CardB14` (`cards.tsx:404`) | Divergencia entre tópicos del caption (lo que el dirigente dice) vs tópicos en comments (lo que el público discute). |
| **B15 Rage Click** | `rage_click_service.py` | `CardB15` (`cards.tsx:508`) | Flag de posts cuyo engagement es **outrage-driven** (reacciones angry/sad altas + sentiment muy negativo). |
| **B16 Promesas** | `promesas_service.py` | `CardB16` (`cards.tsx:620`) | Rastreador de promesas de campaña detectadas en posts. Match contra tabla `promesas` (admin §10). |
| **B17 Veda INE** | `veda_compliance_service.py` | `CardB17` (`cards.tsx:741`) | Compliance ventana veda electoral. Flag `en_veda` activa reglas estrictas (sin propaganda, etc.). |
| **B18 Violencia Política** | `violencia_politica_service.py` | `CardB18` (`cards.tsx:861`) | Escaneo de violencia política (verbal, simbólica) en posts y comments. |

### 8.4 Tablas DB que el módulo lee/escribe

| Tabla | Columnas usadas | Uso |
|---|---|---|
| `social_posts` | `content`, `emotions` (JSONB), `engagement_rate`, `topics_extracted` (JSONB), `published_at` | B14 (topics), B15 (engagement+emotions), B17, B18 |
| `social_comments` | `author_hash`, `nlp_polaridad`, `nlp_tono`, `nlp_target`, `content`, `published_at` | B11, B12, B13, B14, B15, B18 |
| `social_profiles` | scope dirigente | todos |
| `dirigentes` | scope org + `competidor_directo_ids` (B11), `estrato_politico` | B11 |
| `promesas_dirigente` | `id`, `dirigente_id`, texto promesa | B16 (admin curaduría §10) |

**NO existe tabla `cib_flags`** (corrección audit Gemini 2026-05-28). El servicio `cib_detector_service.py` realiza el análisis CIB (Maestros, Coro, New authors) **íntegramente en memoria** sobre los comments cargados de la ventana actual. NO hay persistencia. El `cib_result` del B12 se pasa por referencia al `filtro_realidad_service.compute(cib_result=...)` para B13.

**Helper de seguridad:** `_resolve_org_id(current_user, request)` (`diagnostico_tier2.py:37`) — patrón compartido con Tier 1. Resuelve org admin override via `X-Org-Id`.

### 8.5 Deuda y estado real conocido

| Item | Estado | Notas |
|---|---|---|
| Endpoint agregado | ✅ Funcional | B12 corre primero como dependencia explícita (no asyncio.gather completo, secuencial). |
| Recompute Tier 1 opcional | ✅ Funcional | Demo del Filtro de Realidad. Devuelve `tier1_recomputed` con ER post-CIB. |
| `en_veda` toggle | ✅ Funcional | Query param activa reglas estrictas de B17. |
| Endpoints individuales por bloque | ⚠️ Existen sin hook FE | Mismo patrón que §2 — `useDiagnosticoTier2` consume solo el agregado. |
| Cobertura B16 promesas | ⚠️ Solo Piña (id=1) | Verificado SQL: `promesas_dirigente` solo tiene 12 registros para `dirigente_id=1`. Los otros 12 dirigentes darán `insufficient_data` en B16. Acción: curaduría admin masiva (§10 `POST /admin/promesas`). |
| Cobertura B17 veda | 📝 Depende calendario electoral | Sin elecciones próximas → bloque inactivo (`?en_veda=false` default). |
| ⚠️ CIB persistencia | ✅ In-memory (no tabla) | El B12 NO persiste flagged hashes en tabla. Se calcula on-the-fly por request. Aclarado tras audit Gemini 2026-05-28. Si se quisiera audit trail de quién fue flagged y cuándo → ADR pendiente "persistir CIB flags". |

### 8.6 Cómo responder preguntas comunes

| Pregunta CEO | Dónde está la respuesta |
|---|---|
| "¿Qué cambia entre Tier 1 y Tier 2?" | Tier 1 (B01-B10) mide presencia/conexión. Tier 2 (B11-B18) mide integridad/riesgos/compliance. Endpoints separados. |
| "¿Por qué B12 corre antes que B13?" | B13 (Filtro de Realidad) consume el resultado de B12 (CIB Detector) — `filtro_realidad_service.compute(cib_result=...)`. |
| "¿Qué muestra el toggle 'Filtro de Realidad'?" | Recalcula B01 ER excluyendo authors flagged por B12. Compara "ER aparente" vs "ER orgánico". |
| "¿Qué pasa cuando hay veda?" | Endpoint admite `?en_veda=true`. B17 activa reglas estrictas. Sin elecciones cercanas, bloque devuelve `insufficient_data`. |

### 8.7 Auditoría

- **2026-05-28** · Auditor: Gemini · Veredicto: ⚠️ **Pasa con ajustes** (reporte: `.context/audits/2026-05-28-mapa-funcional-seccion-8.md`).
- **Hallazgos sustantivos aplicados:**
  1. **Tabla `cib_flags` no existe** — CIB es in-memory. Cita inventada eliminada de §8.4. Documentada deuda "persistir CIB flags" en §8.5.
  2. **Tabla `promesas` → `promesas_dirigente`** (nombre real). Corregido §8.4.
  3. **Columnas faltantes §8.4:** agregadas `topics_extracted`, `engagement_rate`, `nlp_tono`, `nlp_target`.
  4. **B16 cobertura asimétrica:** solo Piña (1) tiene 12 promesas. 12/13 dirigentes darán `insufficient_data`. Reflejado en §8.5.
  5. Helper `_resolve_org_id` (`diagnostico_tier2.py:37`) agregado.
- **Sesgo declarado:** RBAC validado por lectura de código, no probado empíricamente.

## 9. Configuración + Sistema ✅

**Concepto:** páginas de configuración del producto. **2 de 5 son estáticas** (Metodología, Análisis Político — sin hooks). **3 de 5 son dinámicas**: Settings hub (KPIs), Onboarding (wizard completo), Evaluación NLP (HITL del propio dirigente sobre su actividad).

### 9A. Sistema

#### `/dashboard/sistema/metodologia/`
- **Archivo:** `frontend/src/app/dashboard/sistema/metodologia/page.tsx`
- **Tipo:** vista informativa **estática** (sin hooks, sin endpoints).
- **Función:** documenta cómo se calculan los bloques B01-B18 (Diagnóstico Tier 1 + Diferenciadores Tier 2). Fuentes, supuestos, rangos de referencia para política mexicana.
- **Metadata:** `title: "Metodología · CRECE"`.

#### `/dashboard/sistema/onboarding/`
- **Archivo:** `frontend/src/app/dashboard/sistema/onboarding/page.tsx`
- **Función:** renderiza `<OnboardingWizard />` (componente `frontend/src/components/onboarding/onboarding-wizard.tsx`).
- **Wizard usa:** todos los hooks de `use-onboarding.ts` (ver §7B.1): `useOnboardDirigente`, `useOnboardingProgress`, `useSaveProfile`, `useSerpSearch`, `useValidateAccount`, `useInitOAuth`, `useSaveCompetidores`, `useSavePromesas`, `useActivate`, etc. (12+).
- **Endpoints consumidos:** `POST /dirigentes/onboard`, `GET /dirigentes/{id}/onboarding-progress`, + sub-endpoints S5 (search, validate, oauth-init, etc.).

### 9B. Settings

#### `/dashboard/settings/`
- **Archivo:** `frontend/src/app/dashboard/settings/page.tsx`
- **Función:** hub de configuración. Consume `useSystemStatus()` y `useKpiOverview()` para mostrar estado actual antes de las sub-páginas.

#### `/dashboard/settings/analisis-politico/`
- **Archivo:** `frontend/src/app/dashboard/settings/analisis-politico/page.tsx`
- **Tipo:** vista informativa **estática** con UI gamificada.
- **Función:** muestra los 4 niveles de profundidad de análisis (`rapido`, `enriquecido`, `contextual`, `personalizado`). Lenguaje 100% amigable al político (no menciona modelos LLM).

#### `/dashboard/settings/evaluacion-nlp/`
- **Archivo:** `frontend/src/app/dashboard/settings/evaluacion-nlp/page.tsx`
- **Función:** **Editor HITL del dirigente** sobre SU propia actividad NLP. Renderiza `<EvaluacionNlpClient />` (`frontend/src/components/evaluacion/EvaluacionNlpClient.tsx`).
- **API client:** `frontend/src/lib/api/hitl.ts` con tipos `HitlComment`, `HitlPost`, `HitlSampleResponse`, `TonoV2`, `TargetV2`, `ReviewStatus`, `SampleScope`, `SamplePlatform`.
- **Endpoints consumidos (de `hitl_evaluation.py`):**
  - `GET /hitl/sample` (línea 158)
  - `PATCH /hitl/comments/{id}` (línea 386) + `POST /hitl/comments/{id}/confirm` (línea 463)
  - `PATCH /hitl/posts/{id}` (línea 494) + `POST /hitl/posts/{id}/confirm` (línea 562)
- **Importante:** los mismos endpoints `/hitl/*` se consumen también desde `/dashboard/admin/clasificacion/` (§10) PERO ahí el scope es **toda la flota multi-org**. Aquí es **solo el propio dirigente** (filtrado por RBAC server-side).

### 9.C Endpoints backend consumidos

| Sub-página | Endpoints | Cita |
|---|---|---|
| Metodología | — | estática |
| Análisis Político (niveles) | — | estática |
| Settings hub | `GET /dashboard/status`, `GET /dashboard/overview` | reutilizados de §7A |
| Onboarding wizard | `POST /dirigentes/onboard` + `GET /dirigentes/{id}/onboarding-progress` + sub-endpoints S5 | `dirigentes.py:665, 770` |
| Evaluación NLP (cliente HITL) | `/hitl/sample`, `/hitl/comments/{id}`+`/confirm`, `/hitl/posts/{id}`+`/confirm` | `hitl_evaluation.py:158, 386, 463, 494, 562` |

### 9.D Deuda y estado real conocido

| Item | Estado | Notas |
|---|---|---|
| Metodología (estática) | ✅ Funcional | Cero hooks, cero endpoints. Mantener sincronizada con cambios en B01-B18. |
| Niveles análisis político | ✅ Funcional | UI gamificada, sin lógica backend. |
| Onboarding wizard S5 | ✅ Funcional | 12+ hooks + endpoints completos. |
| Settings hub | ✅ Funcional | Consume status + overview. |
| Evaluación NLP cliente (HITL) | ✅ Funcional | Comparte endpoints `/hitl/*` con §10 admin pero scope filtrado RBAC al propio dirigente. Aclarado cross-doc. |

### 9.E Auditoría

- **2026-05-28** · Auditor: Gemini · Veredicto: ⚠️ **Pasa con ajustes** (reporte: `.context/audits/2026-05-28-mapa-funcional-seccion-9.md`).
- **Hallazgos aplicados:**
  1. Removido placeholder "(pendiente verificar interacciones)" en Evaluación NLP — consumidores `/hitl/*` confirmados.
  2. Corregido absoluto "sin hooks ni endpoints" → solo aplica a 2 de 5 páginas (Metodología + Análisis Político).
  3. Agregado endpoints `/hitl/*` consumidos por Evaluación NLP en §9.C (tabla completa).
  4. Agregado `OnboardingWizard` component + hooks + endpoints S5 en sub-sección Onboarding.
- **Hallazgo cross-doc importante:** contradicción §9 vs §10 detectada y resuelta. HITL es bilateral: cliente (auto-revisión, scope = su dirigente) en §9 + admin (toda la flota) en §10. Corregido §10 también.

---

## 10. Admin (admin/analyst MD scope) ✅

**Concepto:** páginas y endpoints con **scope multi-org / multi-dirigente** (admin/analyst MD). NO son "no-cliente" estrictamente — algunos endpoints (notablemente `/hitl/*`) son compartidos: cliente los usa para validar SU dirigente (§9 Evaluación NLP), admin los usa para revisar TODA la flota. La diferencia es el **scope RBAC server-side**, no la separación de endpoints.

### 10A. Vistas FE

| Página | Archivo | Función |
|---|---|---|
| `/dashboard/admin/overview` | `admin/overview/page.tsx` | Flota multi-org con cobertura framework + NLP + planes + tareas por org. Llama `api.get<Overview>(...)` inline. |
| `/dashboard/admin/clasificacion` | `admin/clasificacion/page.tsx` | Panel HITL de clasificación NLP (posts/comments) |
| `/dashboard/admin/plan-ia-review` | `admin/plan-ia-review/page.tsx` | Revisión y override de recomendaciones IA pre-publicación |
| `/dashboard/admin/ranking` | `admin/ranking/page.tsx` | Ranking interno de dirigentes (admin only) |

### 10B. Endpoints backend

#### Admin Overview (`admin_overview.py`)

| Endpoint | Línea | Función |
|---|---|---|
| `GET /admin/overview` | `admin_overview.py:76` | Flota multi-org con OrgStatus[]: posts_total, posts_clasificados, coverage_framework_pct, coverage_nlp_pct, planes, tareas por org. |

#### Admin Classification HITL (`admin_classification.py`)

| Endpoint | Línea | Función |
|---|---|---|
| `GET /admin/classification/pending` | `admin_classification.py:98` | Cola de posts pendientes de clasificación manual |
| `GET /admin/classification/prompt` | `admin_classification.py:153` | Prompt actual usado para clasificar |
| `POST /admin/classification/batch` | `admin_classification.py:218` | Batch classify (mark multiple posts) |
| `GET /admin/classification/stats` | `admin_classification.py:317` | Estadísticas de clasificación |

#### Admin Compliance (`admin_compliance.py`)

| Endpoint | Línea | Función |
|---|---|---|
| `POST /admin/compliance/purge-by-hash` | `admin_compliance.py:115` (handler `purge_by_hash`) | Borrado LFPDPPP a solicitud del titular del dato — purgar todas las referencias de un `author_hash` en `social_comments`, `watched_profiles`, `watched_like_events`. |
| `GET /admin/compliance/purge-audit` | `admin_compliance.py:205` (handler `list_purge_audit`) | Audit log de purges realizados (cumplimiento LFPDPPP). |

#### Admin Promesas (`admin_promesas.py`)

| Endpoint | Línea | Función |
|---|---|---|
| `POST /admin/promesas` | `admin_promesas.py:56` | Crear promesa (curaduría manual) |
| `GET /admin/promesas/{dirigente_id}` | `admin_promesas.py:86` | Lista promesas por dirigente. Insumo de B16 (§8). |

#### HITL Evaluation (`hitl_evaluation.py`) — **bilateral cliente + admin**

**Importante (corregido 2026-05-28 audit Gemini):** este módulo NO es admin-only. Los mismos endpoints `/hitl/*` se consumen desde 2 frentes:
- **Cliente:** `/dashboard/settings/evaluacion-nlp/` (§9B) — scope `dirigente_id = current_user.dirigente_id`.
- **Admin/analyst:** `/dashboard/admin/clasificacion/` (§10A) — scope = toda la flota multi-org.

La separación es por RBAC server-side, no por endpoint distinto.

| Endpoint | Línea | Función |
|---|---|---|
| `GET /hitl/sample` | `hitl_evaluation.py:158` | Sample para review |
| `PATCH /hitl/comments/{comment_id}` | `hitl_evaluation.py:386` | Actualizar clasificación NLP de un comment |
| `POST /hitl/comments/{comment_id}/confirm` | `hitl_evaluation.py:463` | Confirmar clasificación |
| `PATCH /hitl/posts/{post_id}` | `hitl_evaluation.py:494` | Actualizar clasificación NLP de un post |
| `POST /hitl/posts/{post_id}/confirm` | `hitl_evaluation.py:562` | Confirmar clasificación |
| `GET /hitl/audit/{dirigente_id}` | `hitl_evaluation.py:593` | Audit log de cambios HITL |

### 10C. Hooks FE

**Convención mixta** (corregido tras audit Gemini 2026-05-28): las páginas admin se dividen en 2 grupos según si la lógica de negocio es compartida con cliente o no.

**Inline `api.get<>` (lógica admin-only):**
- `admin/overview/page.tsx` consume `api.get<Overview>("/admin/overview")` directo (`overview/page.tsx:23`).
- `admin/clasificacion/page.tsx` consume `api.get<>` directo para `/admin/classification/...`.

**Hooks centralizados (cuando reutiliza lógica compartida con cliente):**
- `admin/plan-ia-review/page.tsx` usa `useRecomendaciones` y `useTransicionarEstado` de `use-recomendaciones.ts` (líneas 27-28). El mismo hook que `/dashboard/recomendaciones/` (§6A) — la diferencia es scope RBAC server-side.
- `admin/ranking/page.tsx` usa `useAdminCompetitorRankings` de `use-competitors.ts` (línea 23, 35).

**HITL bilateral** (§9B + §10):
- `use-social-comments.ts` consume `/hitl/*` para reviewer panel admin.
- `EvaluacionNlpClient.tsx` (cliente §9B) consume los mismos endpoints `/hitl/*` con scope diferenciado por RBAC server-side.

**Sin `use-admin.ts` central** confirmado vía grep. Patrón actual: usar hook centralizado cuando la lógica es compartida con cliente; inline cuando es admin-only. Convención **no documentada** en código; ADR pendiente formalizar la regla.

### 10D. Tablas DB tocadas

- `social_posts`, `social_comments` (clasificación NLP fields)
- `promesas` (admin curated)
- `recomendaciones_plan_ia` (admin review pre-cliente)
- `users`, `organizations` (admin overview)

### 10E. Deuda y estado real conocido

| Item | Estado | Notas |
|---|---|---|
| Admin overview multi-org | ✅ Funcional | Cobertura framework + NLP por org calculada server-side. |
| Clasificación HITL | ✅ Funcional | Batch + stats + prompt + pending. Pipeline NLP humano. |
| Plan IA Review | 📝 Verificar | Página existe, endpoints no enumerados aquí. |
| Promesas curaduría | ✅ Funcional | POST + GET por dirigente. Insumo B16 §8. |
| Compliance endpoints | 📝 No auditados detalladamente | Solo 2 endpoints identificados (POST línea 115, GET línea 205). |
| Convención mixta hooks admin | ⚠️ Sin documentación | Patrón actual: inline `api.get<>` cuando lógica admin-only (overview, clasificación); hooks centralizados cuando reutiliza lógica compartida con cliente (plan-ia-review usa `useRecomendaciones`; ranking usa `useAdminCompetitorRankings`). NO documentado en código. ADR pendiente formalizar regla. |
| HITL Evaluation naming | ⚠️ Confusión histórica | `hitl_evaluation.py` se confundía con "Mi Evaluación" del dirigente. Aclarado: HITL = clasificación NLP de comments/posts (consumido por cliente §9B y admin §10A). Mi Evaluación = `dirigentes/{id}/pesos` (§6B). Son **3 features distintas** con nombres similares. |

### 10F. Cómo responder preguntas comunes

| Pregunta CEO | Dónde está la respuesta |
|---|---|
| "¿Cómo ve admin todas las orgs?" | `/dashboard/admin/overview` con `GET /admin/overview`. |
| "¿Qué hace la página de clasificación admin?" | HITL panel para revisar y confirmar clasificaciones NLP de posts/comments antes de exponerlas al cliente. |
| "¿Cómo se agregan promesas para B16?" | `POST /admin/promesas` (curaduría manual). Listado por dirigente en `GET /admin/promesas/{id}`. |
| "¿`hitl_evaluation` es lo mismo que Mi Evaluación?" | NO. `hitl_evaluation` = admin de clasificación NLP (§10). Mi Evaluación = pesos personalizables del dirigente (§6B). |

### 10G. Auditoría

- **2026-05-28** · Auditor: Gemini · Veredicto inicial: 🟡 lateral del redactor (Gemini colgó 3× en intentos paralelos).
- **2026-05-28 (re-audit)** · Auditor: Gemini · Veredicto: ⚠️ **Pasa con ajustes** (reporte: `.context/audits/2026-05-28-mapa-funcional-seccion-10.md`).
- **Hallazgos sustantivos aplicados:**
  1. **§10C convención hooks corregida**: el patrón no es "todo inline" — es mixto. `plan-ia-review` usa `useRecomendaciones`/`useTransicionarEstado`; `ranking` usa `useAdminCompetitorRankings`. Solo `overview` y `clasificacion` son inline. Detalle agregado §10C + deuda §10E actualizada.
  2. **admin_compliance endpoints nombrados**: `POST /admin/compliance/purge-by-hash` (`purge_by_hash`) y `GET /admin/compliance/purge-audit` (`list_purge_audit`). Eran placeholders `(verificar)` — agregada función LFPDPPP.
  3. **Bloque duplicado `## 10. Admin (no-cliente) 📝 Pendiente` al final del archivo eliminado** — era residuo de redacción del esqueleto original.
- **Ajuste pre-audit aplicado**: título cambiado de "Admin (no-cliente)" a "Admin (admin/analyst MD scope)" + aclaración HITL bilateral. Detectado por audit Gemini §9 cross-doc.
- **Falso positivo histórico documentado**: el primer audit Gemini falló 3× por timeout (no error del redactor). Re-audit con prompt acotado funcionó.

## Reglas de mantenimiento de este doc

1. **Antes de proponer cualquier feature/cambio:** grep el concepto en backend/+frontend/, consultar este doc. Si la función existe → leer su sección. Si no existe → agregar la sección.
2. **Al cerrar una función:** actualizar la sección correspondiente. Cambios sin doc = deuda inmediata.
3. **Al introducir nueva función:** crear su sección antes del primer commit que la implementa.
4. **Convención de estado** (al inicio del doc) debe usarse en todos los items.
5. **Cross-link** con `PIPELINE-RADAR-CRECE.md` para origen del dato, con `ORGANIZACION.md` para responsables, con `REGLAS.md` para constraints normativos.
