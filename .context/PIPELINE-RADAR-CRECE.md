# Pipeline RADAR → CRECE — Documento operacional

**Última actualización:** 2026-05-28
**Autores:** Hugo (radar-side, verificado contra payloads reales) · Linda (crece-side, verificado contra adapters + DB)
**Propósito:** inventario completo del flujo de datos radar → crece. Sirve para responder sin invenciones: "para feature X, qué tenemos hoy, qué falta y de qué lado se resuelve".

---

## 0. Flujo end-to-end

```
[Plataforma social] → [Engine RADAR scrape] → [radar_db :5453 scrape_results]
                                                    ↓
                              [Export JSON shape v2 {export_meta, items[]}]
                                                    ↓
                           [Adapter CRECE ingest_radar_*.py --commit]
                                                    ↓
            [Tablas destino crece :5438: social_posts/comments/profiles/snapshots, watched_profiles/like_events]
                                                    ↓
                            [Endpoints/Cards FE leen agregados de las tablas]
```

Triggers manuales hoy (Linda/CEO piden a Hugo) — NO hay sync automático radar→crece todavía.

---

## 1. RADAR-side (Hugo · ground-truth verificado vs payloads y código de engines)

### 1.1 Engines disponibles por plataforma y tipo

**Facebook**
- post: `claude_extension_v1` (762), `cdp_discover` (288, deep), `pepe_hybrid` (135, shallow), `linda_apify_backfill` (53), `apify_fb_posts` (51)
- comment: `playwright_storage_state` (2,395)
- reactor: **`cdp_chrome_v1` (141,414 = 95%)**, `graphql_reactors` (7,417 = 5%), `cdp_http_v1` (132)
- profile (followers): `fb_og_logged_out`, `playwright_storage_state`

**Instagram** (CONGELADO — cuenta `chatmx_oficial` en flag, riesgo shadow-ban)
- post/comment/reactor/profile: `instagrapi_2.x` — alternativa: Apify (gated por costo $50/mes hard).

**TikTok**
- post: `ytdlp_tiktok` (636)
- comment: `tt_browser_session` (1,191)
- profile (followers): `tt_browser_session` (browser-session autenticado) y/o `ytdlp_tiktok`
- reactor: **no existe** — TT no expone likers (POR DISEÑO, no es gap)

**X (Twitter)**
- post/comment/profile: `scweet_5.3`
- reactor: no existe (X no expone likers públicos)

**YouTube**
- post: `ytdlp_youtube`
- comment: `youtube_data_api_v3`
- reactor: no existe (YT no expone likers)

### 1.2 Campos verificados que cada engine extrae

**FB post (claude_extension_v1, cdp_discover, pepe_hybrid, apify_fb_posts)**
```
post_id (pfbid o numeric), post_url, text, time_iso,
reactions_count, comments_count, shares_count, by_reaction_type,
author_username, feedback_id_b64, typename
```

**FB comment (playwright_storage_state)**
```
author_display_name, author_username, comment_id_surrogate, is_surrogate_id,
post_id, text, time_iso
```

**FB reactor — `cdp_chrome_v1` (95% del volumen)**
```
post_id, post_url, reaction_type_id,
reactor_username (id numérico, NO handle bonito), reactor_display_name
```
NO viene: `profile_url`, `avatar_url`, `mutual_friends_count`. Lee del **overlay del post**, no visita perfil.

**FB reactor — `graphql_reactors` (5% del volumen)**
```
(todo lo anterior de cdp_chrome_v1) +
reactor_profile_url (formato /profile.php?id=NNN, NO el handle bonito),
mutual_friends_count,
feedback_target_id
```
`avatar_url` por confirmar (Hugo verifica si el código tira el campo o si no viene en la respuesta).

**IG post**
```
post_id, post_code, post_url, caption, like_count, comment_count,
view_count, play_count, media_type, product_type, author_username, time_iso
```

**IG comment**
```
comment_id_ig, author_id, author_username, author_display_name,
like_count, post_id, post_url, text, time_iso
```

**IG reactor** (instagrapi)
```
reactor_id, reactor_username, reactor_display_name, reaction_type,
post_id, post_url
```
NO viene: profile_url, avatar_url, mutuals.

**TT post (ytdlp)**
```
post_id, post_url, description, title,
view_count, like_count, comment_count, repost_count, save_count,
duration, channel, uploader, time_iso, thumbnail, track
```

**TT comment (tt_browser_session)**
```
comment_id, author_username, author_display_name, text,
digg_count, create_time_iso, reply_comment_total, is_author_digged
```

**X post / comment (scweet_5.3)**
```
post: author_username, author_display_name, text, embedded_text,
      likes_count, retweets_count, replies_count, media_urls, permalink, timestamp
comment: author_username, in_reply_to_post_id, text, timestamp
```

**YT post / comment**
```
post: post_id, post_url, title, channel, uploader, view_count, duration, thumbnail
comment: comment_id, author_display_name, author_channel_id, channel_handle,
         like_count, reply_count, text, published_at, video_id
```

### 1.3 Topes / cooldowns / decisiones permanentes

- **FB reactor cap D-006** ~25-40% (privacy de cuentas). El resto está bloqueado en origen, no se puede scrapear sin OAuth/Graph API del dueño del post.
- **FB rate-limit** ~60 posts por sesión deep — fuerza cooldowns entre lotes.
- **TT/X/YT reactor = 0 POR DISEÑO** (la plataforma no expone). NO contar como gap; la audiencia de esas redes sale exclusivamente de los comments.
- **IG congelado** hasta luz verde CEO (cuenta `chatmx_oficial` con flag de Instagram). Alternativa: Apify.
- **Apify costo $50/mes hard cap** (decisión CEO). No se exceden los créditos.
- **`avatar_url` = 0 en TODOS los engines** (a confirmar tras verif de código graphql_reactors).
- **`handle real bonito` del fan FB** (ej. `@nombre.persona` en vez de `id num`) no se captura sin visita al perfil = pase costoso.
- **Señales profundas del perfil del fan** (`friends_count`, `bio`, `posts_visible_count`, `last_visible_post_at`, `account_created`) = TODAS requieren visitar el perfil del fan = pase nuevo costoso + huella FB alta. Decisión separada (muestreado vs Apify, gated).

---

## 2. CRECE-side (Linda · verificado contra adapters y schema DB)

### 2.1 Adapters de ingest (todos en `backend/scripts/`)

| Adapter | Lee de | Escribe a | Patrón UPSERT |
|---|---|---|---|
| `ingest_radar_yt_x_posts.py` | JSON `{export_meta, posts[]}` shape Hugo | `social_posts` | `ON CONFLICT (platform_post_id) DO NOTHING` |
| `ingest_radar_ig.py` | JSON con posts + comments IG | `social_posts` (UPDATE en re-ingest), `social_comments` (DO NOTHING) | `DO UPDATE SET likes,comments,...` para posts; `DO NOTHING` para comments |
| `ingest_radar_comments_payload.py` | JSON `{export_meta, comments[]}` | `social_comments` | `ON CONFLICT (platform_comment_id) DO NOTHING` |
| `ingest_radar_reactors_v2.py` | JSON `{export_meta, reactors[]}` | `watched_profiles` (UPSERT por dirigente+platform+external_id), `watched_like_events` (`DO NOTHING`) | dual |
| `ingest_radar_captions_v2.py`, `ingest_radar_posts_v3.py`, `ingest_radar_comments_v2.py`, `ingest_radar_ig_posts.py`, `ingest_radar_comments.py`, `ingest_radar_reactors.py` | legacy/variantes — no usados activamente hoy | — | — |

### 2.2 Tablas destino — schemas reales

**`social_posts`** (34 columnas)
- Identidad: `id`, `profile_id`, `platform_post_id`
- Contenido: `content`, `post_type`, `published_at`, `media_urls`
- Métricas crudas: `likes`, `comments`, `shares`, `views`
- Métricas derivadas: `engagement_rate` (calculado por `engagement.py`)
- NLP texto LLM: `tono_discurso`, `nlp_target`, `topics_extracted`, `topics_jsonb`, `emotions`, `target_politico`, `nlp_model_version`, `llm_razon`, `llm_modelo`, `llm_processed_at`
- NLP sentiment numérico (pysentimiento worker): `sentiment_score`, `sentiment_label`, `controversy_score`, `toxicity_score`, `platform_adjusted_sentiment`, `sentimiento_politico_ajustado`
- Meta: `is_political`, `clasificacion_origen`, `raw_data` (jsonb del payload original), `scraped_at`
- Auditoría: `last_reviewed_by`, `last_reviewed_at`, `review_status`

**`social_comments`** (21 columnas)
- Identidad: `id`, `parent_post_id`, `parent_comment_id`, `platform_comment_id`
- Contenido: `content`, `author_hash` (sha256 pseudonimizado, LFPDPPP), `commenter_handle`, `likes`, `published_at`
- Estructura: `is_reply_to_comment`, `es_follower`
- NLP comments: `nlp_tono`, `nlp_target`, `nlp_polaridad`, `nlp_model_version`
- Meta: `data_source`, `created_at`, `updated_at`
- Auditoría: `last_reviewed_by`, `last_reviewed_at`, `review_status`

**`watched_profiles`** (17 columnas) — la lista nominada de fans
- Identidad: `id`, `dirigente_observador_id`, `org_id`, `platform`, `profile_external_id`
- Metadata del fan: `profile_handle`, `profile_url`, `display_name`, `avatar_url`, `notes`
- Clasificación: `source` (`auto_suggested` / `cliente_seed` / etc.), `tags` (jsonb), `is_active`
- PII: `author_hash` (sha256)
- Auditoría: `created_at`, `updated_at`, `created_by`

**`watched_like_events`** (6 columnas)
- `id`, `watched_profile_id`, `post_id`, `reaction_type`, `detected_at`, `source`

**`social_profiles`** (12 columnas) — el perfil del dirigente (no del fan)
- Identidad: `id`, `dirigente_id`, `platform`, `handle`, `url`
- Audiencia: `followers_count`, `following_count`, `posts_count`
- Meta: `last_scraped_at`, `data_source` (`automated_scraper`/`manual_host_ingest`), `last_manual_update`, `is_confirmed`

**`social_profile_snapshots`** (9 columnas) — series temporales del perfil del dirigente
- `id`, `profile_id`, `dirigente_id`, `org_id`, `platform`, `followers_count`, `posts_count`, `taken_at`, `data_origin_checkpoint`

### 2.3 Cobertura real por columna (qué adapters SÍ pueblan y a qué %)

**`watched_profiles` para Saymi (28,649) y Pepe (30,995) — los únicos dirigentes con reactors ingestados al cierre 2026-05-28:**

| Columna | Saymi cobertura | Pepe cobertura | Origen del dato |
|---|---|---|---|
| `profile_external_id` | 100% | 100% | export Hugo (`author_hash` o `reactor_username`) |
| `display_name` | 99.8% | 97.6% | export Hugo (`author_display_name`) |
| `profile_handle` | **13%** | **0%** | el INSERT del adapter NO setea esta columna |
| `profile_url` | **0.05%** (13 filas) | **0%** | solo lo trae el seed manual `cliente_seed`, no el ingest automático |
| `avatar_url` | **0%** | **0%** | el ingest no la pobla; Hugo confirma el engine no la captura |
| `notes` | 0% | 0% | reservada para anotaciones manuales |
| `tags` | siempre `[]` por default, algunas con tags manuales | igual | el INSERT default es `'[]'::jsonb` |

**`social_posts` (Piña/Solano/Saymi/Gaby/Balles/Pepe/Felipe = 7 dirigentes in-scope, total ~6K posts al 2026-05-28):**

| Bloque de columnas | Cobertura aprox | Origen |
|---|---|---|
| Identidad + content + métricas crudas + `raw_data` | ~100% (lo que el adapter ingesta del payload Hugo) | Hugo via adapter |
| `engagement_rate` | ~85% (todos menos los que no tienen denominador: views=0 y followers=0) | Calculado CRECE-side por `engagement.py` |
| `tono_discurso` / `nlp_target` / `topics_extracted` / `emotions` (LLM texto) | ~95-100% en in-scope (los vacíos son posts con content vacío, NULL legítimo) | CRECE-side via Claude CC subprocess o /gemini inline |
| `sentiment_score` (pysentimiento numérico) | varía: Saymi 61%, Gaby 78%, Felipe/Balles/Pepe los re-ingestados 100% post-backfill 2026-05-27 | CRECE-side via celery worker `analyze_sentiment` task (pysentimiento + secondary model) |
| `target_politico`, `topics_jsonb`, `platform_adjusted_sentiment`, `controversy_score`, `toxicity_score` | parcial; algunos los pone el worker NLP, otros endpoints específicos | CRECE-side |
| Auditoría (`last_reviewed_*`) | manual via "Mi Evaluación" en FE | usuario |

**`social_profiles` (perfiles del dirigente):**

| Columna | Cobertura | Origen |
|---|---|---|
| Identidad (`handle`, `url`) | 100% | onboarding manual + ingest |
| `followers_count`, `posts_count` | 100% para los 7 in-scope | Hugo o manual update (Piña TT era `manual_host_ingest`) |
| `last_scraped_at` | depende de última corrida Hugo o snapshot | mixto |
| `data_source` | `automated_scraper` casi siempre, salvo Piña TT (`manual_host_ingest`) | adapter |

### 2.4 Pipelines auxiliares (no son ingest pero alimentan o transforman)

| Script | Función |
|---|---|
| `backfill_engagement_rate.py` | Recalcula `social_posts.engagement_rate` global (helper canónico `engagement.py`). Idempotente. |
| `post_ingest_enrich.py --dirigente-id N` | Cadena post-ingest: NLP posts tono/target → comments tono/target/polaridad → emotions → topics. Usa Claude CC subprocess. |
| `backfill_nlp_posts.py`, `backfill_nlp_saymi.py`, `backfill_emotions_cc.py`, `extract_topics_saymi_cc.py` | Sub-pasos del enrich. Soportan fallback Gemini si `CLAUDE_BIN=/nonexistent`. Usan `--strict-mcp-config` (RAM-safe post-crash 2026-05-27). |
| `regen_diagnostico_enriched_host.py`, `regen_diagnostico_gemini.py` | Generan FODA en `planes_ia` tipo DIAGNOSTICO. |
| `seed_foda_cc_2026_05_27.py` | Seed manual de FODA (hecho inline por CC esta sesión). |
| `regen_consolidacion_v2.py` | Genera Plan estratégico tipo CONSOLIDACION (`ConsolidacionEstructura`). |
| `regen_contenido_v2.py` | Genera Plan de contenido tipo CONTENIDO (`ContenidoEstructura`). |
| Celery task `analyze_sentiment(post_id)` | Calcula `sentiment_score` con pysentimiento. Disparada vía `analyze_sentiment.delay(pid)` por cada post nuevo. Worker `crece-celery-worker` tiene el modelo cargado. |

---

## 3. Gap analysis por feature

### 3.1 Feature: "Fans enriquecidos" (Top fans con identidad clara)

**Qué necesita el FE para ser útil:**
- `display_name` ✅ ya viene
- `profile_url` (link clickeable al perfil del fan)
- `profile_handle` (handle bonito tipo `@nombre`)
- `avatar_url` (foto)
- (opcional) badge "verificado" o "creator"

**Qué tenemos hoy:**
- `display_name` ✅ 99%
- `profile_url`: solo 0-0.05% (13 filas seed) — la inmensa mayoría vacía
- `profile_handle`: 0-13% (el INSERT no lo setea)
- `avatar_url`: 0%

**Qué falta y de qué lado se resuelve:**
- `profile_url`: ✅ RADAR ya tiene en `graphql_reactors` (7,417 reactores). **Acción Hugo:** hacer `graphql_reactors` engine default + re-exportar con `reactor_profile_url`. **Acción Linda:** actualizar el INSERT de `ingest_radar_reactors_v2.py` para poblar `profile_url` desde el campo del export. ~30 min ambas mitades.
- `profile_handle`: ❌ no disponible vía overlay. Requiere visitar el perfil = pase costoso. Fase futura gated.
- `avatar_url`: ⚠️ Hugo verificó código estático: engine `graphql_reactors` lee solo `id`, `name`, `mutual_friends.count` del `user_node`; NO extrae avatar. La respuesta cruda de FB **probablemente** trae `profile_picture` (la UI lo muestra), pero requiere 1 corrida de `fb_graphql_recon.py` para confirmar. Hugo lo correrá cuando FB enfríe (rate-limit hoy en deep walk). Si la respuesta sí lo trae = fix barato de parser (1 campo). Si no = pase nuevo costoso. **ETA confirmación: 1-2 días.**

### 3.2 Feature: "Estimar fantasmas" (% de fans inactivos / no-humanos)

**Qué señales discriminan real-activo vs fantasma:**
1. ¿Tiene foto de perfil? (`avatar_url` presente)
2. ¿Tiene amigos en común con el dirigente? (`mutual_friends_count > 0`)
3. ¿Cuenta llena vs vacía? (friends total, posts visibles, bio, edad cuenta)
4. ¿Ha hecho algún comment además del like? (CRECE-side: hay match con `social_comments.author_hash`)

**Qué tenemos hoy / qué falta:**

| Señal | Origen | Status | Costo |
|---|---|---|---|
| Comment match (`author_hash` en social_comments) | CRECE-side | ✅ disponible YA, sin Hugo | 0 (query) |
| `mutual_friends_count` | RADAR (`graphql_reactors`) | ✅ ya capturado, solo falta exportar | Bajo (hacer engine default) |
| `avatar_url s/n` | RADAR (`graphql_reactors`) | ⚠️ pendiente verificación Hugo | Bajo (fix parser) o medio (pase nuevo) |
| `friends_count`, `bio`, `posts_visible`, `last_post`, `account_created` | RADAR pase nuevo | ❌ no disponible | **Alto** — requiere visita al perfil de cada fan. Decisión separada (muestreado vs Apify gated). |

**Propuesta `ghost_score v1` (sin pase nuevo):**
```
ghost_score = w1 * (avatar_url IS NULL) +
              w2 * (mutual_friends_count = 0) +
              w3 * (author_hash NO aparece en social_comments del dirigente)
```
Con `w1 + w2 + w3 = 1`. Aplica solo a los fans con engine `graphql_reactors` (5% del total hoy, creciente cuando Hugo lo haga default). Para el 95% restante (`cdp_chrome_v1`), no hay señal — quedan sin score.

### 3.3 Feature: "B05 Plutchik real" (emociones detalladas en reactions)

**Qué necesita:** `reaction_type` por reactor con valor real (love/wow/haha/sad/angry/care/support), no placeholder `like`.

**Qué tenemos:**
- En `watched_like_events.reaction_type`: el adapter NORMALIZA a valores válidos del constraint DB. Si el engine reporta `unknown` (6-7% de cdp_chrome_v1), el adapter lo mapea a `'like'` por default.
- En el FE banner: "Reacciones marcadas como 'like' son placeholder — los tipos detallados llegan con el fix RADAR Sprint 9."

**Qué falta:** que Hugo capture el `reaction_type` real en el 100% de los casos, no solo el agregado por categoría.

**De qué lado se resuelve:** RADAR — Hugo Sprint 9 (mencionado en su sumario; no he visto detalles del scope aún).

### 3.4 Feature: "Cobertura RADAR continua" (sin zonas vacías en gráfico de Interacción diaria)

**Qué pasa hoy:** el gráfico de Felipe muestra días vacíos (`zonas vacías = sin cobertura RADAR`). El backend marca esos días como "no captured" cuando no hay post + reaction en esa fecha.

**Causa:** RADAR no scrape diario sobre todos los dirigentes. Algunas corridas son por demanda (handoffs Linda↔Hugo), otras programadas (Hugo Beat).

**De qué lado se resuelve:** RADAR — Hugo decide cadencia automática por dirigente (Hugo Beat schedule).

### 3.5 Feature: "B07 Crecimiento real" (timeseries followers)

**Qué necesita:** `social_profile_snapshots` con `followers_count` capturado periódicamente (mínimo semanal).

**Qué tenemos:** 2 snapshots por dirigente in-scope (2026-05-12 y 2026-05-25) **con valores estáticos idénticos** (el snapshot del 25 copió el del 12 — bug B07 documentado). Plus TT followers frescos 2026-05-27 vía `tt_browser_session`. Felipe TT 2026-03-29 ← 2026-05-28 = sin historial.

**Qué falta:** Hugo programar captura periódica de followers por dirigente × plataforma → exportar → CRECE ingesta a `social_profile_snapshots`. Y limpiar los 2 puntos basura del 05-12 = 05-25.

**De qué lado se resuelve:** RADAR setup recurrente. Linda ingesta los snapshots cuando Hugo entregue.

---

## 4. Coordinación y handoffs

- Peers `claude-peers`: Hugo (radar, cwd `~/Projects/radar`, ID dinámico — usar `mcp__claude-peers__list_peers`). Linda (crece-v2, esta sesión).
- Handoffs activos hoy 2026-05-28: HANDOFF-2026-05-28-radar-ingest-pendiente.md (495 rx Piña reel 3982 — requiere FASE B con cookies CEO).
- Memoria persistente: `~/.claude/projects/-Users-marxchavez-Projects-crece-v2/memory/handoff-radar-ingest-residual-2026-05-28.md` (SessionStart hook la detecta).

## 5. Reglas de mantenimiento de este doc

- Cuando Hugo lance un engine nuevo o cambie campos: actualiza sección 1.
- Cuando Linda agregue/cambie un adapter: actualiza sección 2.
- Cuando un feature nuevo del FE necesite datos: agrega su gap analysis a sección 3.
- Verificar coberturas reales con queries antes de afirmar (no inventar).
