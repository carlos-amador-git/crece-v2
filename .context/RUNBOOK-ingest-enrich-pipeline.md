# RUNBOOK — Pipeline RADAR → CRECE (ingest + enrich NLP)

**Creado 2026-05-27.** Propósito: NO re-adivinar qué funciona. Todo aquí está verificado contra datos reales esta sesión.

## Arquitectura (qué vive dónde)
- **RADAR** scrapea → `radar_db` :5453 (container `radar-postgres-1`, user `md_scraper`, db `radar_db`). Tablas: `scrape_results` (col `payload` jsonb, `entity_type` ∈ post/comment/reactor/profile, `target_id`), `targets`. **Es el ORIGEN crudo, NO destino de NLP.**
- **Adapters (corren en HOST)** extraen de :5453 → JSON → escriben a `crece_db` :5438.
- **crece_db** :5438 (container `crece-db`, user `crece` / pass `crece_dev` / db `crece`). Destino del ingest Y del enrich NLP.
- App (Vercel `frontend-zeta-sepia-46`) lee de :5438 vía túnel cloudflared (auto-gestionado, `scripts/mac-local/start-crece-tunnel.sh` + LaunchAgent).

## Acceso
- crece: `PGPASSWORD=crece_dev psql -h localhost -p 5438 -U crece -d crece`
- radar: `docker exec -i radar-postgres-1 psql -U md_scraper -d radar_db` — **`-i` OBLIGATORIO** para heredocs (sin `-i` el heredoc no llega → output vacío, NO es "0 filas").

## Tablas crece y JOINS CORRECTOS (⚠️ error que costó esta sesión)
- `social_profiles` (id, dirigente_id, platform, handle, followers_count…) = **perfil PROPIO del dirigente**.
- `social_posts.profile_id` → **`social_profiles.id`** (NO watched_profiles).
- `social_comments.parent_post_id` → `social_posts.id`.
- `watched_profiles.dirigente_observador_id` = **audiencia/likers observados, NO los posts del dirigente**.
- **NUNCA** joinear `social_posts.profile_id` contra `watched_profiles` — da 0 o falsos matches por IDs que coinciden entre tablas distintas (esto produjo el falso "data 3 MC perdida" el 2026-05-27).
- **Coverage correcto:**
  ```sql
  SELECT spr.dirigente_id, COUNT(sp.tono_discurso)||'/'||COUNT(*) AS tono,
         COUNT(sp.emotions) emo, COUNT(sp.topics_extracted) top
  FROM social_profiles spr JOIN social_posts sp ON sp.profile_id=spr.id
  WHERE spr.dirigente_id=N GROUP BY 1;
  -- comments: JOIN social_comments sc ON sc.parent_post_id=sp.id ; COUNT(sc.nlp_tono)
  ```

## Onboarding dirigente NUEVO (playbook verificado con Felipe = dir 60)
1. **Org** (si es cliente nuevo): `INSERT INTO organizaciones (nombre, slug, tipo, estado, is_active, config, created_at, updated_at)`. `tipo` ∈ {PARTIDO, GOBIERNO, ONG}. id autoincrementa. (Felipe → org 5 "Gobierno Nicolás Romero", GOBIERNO.)
2. **Dirigente**: `INSERT INTO dirigentes (...)`. NOT NULL: `full_name, cargo, partido, estado, sync_status, competidor_directo_ids, data_origin, pesos_target_politico` (+ created/updated). Enums/valores:
   - `sync_status` (enum `dirigente_sync_status`): pending | scraping | analyzing | calculating_ipd | ready | error. Nuevo → `pending`; tras enrich → `ready`.
   - `rol_politico`: `oposicion` (ej. MC) | `oficialismo` (ej. MORENA).
   - `competidor_directo_ids` = `'{}'` si no tiene.
   - `data_origin` = `'T3'` (radar).
   - `pesos_target_politico` = `'{"propio": 1.0, "personal": 1.0, "oposicion": 1.0, "oficialismo": 1.0}'` (default).
   - `data_fidelity_tier` por red, ej. `'{"X":"N-A","TikTok":"T3","YouTube":"N-A","Facebook":"T3","Instagram":"T3"}'`.
   - id autoincrementa (sequence). **NO inventar** cargo/partido/estado/rol — pedirlos al CEO.
3. **Profiles**: `INSERT INTO social_profiles (dirigente_id, platform, handle, url, followers_count, following_count, posts_count, data_source, is_confirmed)` por red.
   - `platform` UPPER: FACEBOOK | INSTAGRAM | TIKTOK | TWITTER | YOUTUBE.
   - `data_source` (enum `data_source_enum`): automated_scraper | manual_host_ingest | official_api | manual_onboarding → usar `manual_host_ingest`.
   - NOT NULL incluye `following_count` y `posts_count` (=0 si desconocido).

## Ingest (extracción :5453 → adapter → :5438)
Base: `docker exec -i radar-postgres-1 psql -U md_scraper -d radar_db -tA -c "<query json>" > /tmp/x.json`
Filtrar por `t.display_name='<Nombre>' AND t.platform='<lower>' AND sr.entity_type='<post|comment>'`.

| Red / entidad | Adapter | Shape JSON | Comando |
|---|---|---|---|
| **FB/TT/X/YT posts** | `ingest_radar_yt_x_posts.py` | `{"posts":[{"platform_post_id": payload->>'post_id', "payload": <raw payload>}]}` (X: id desde permalink) | `--json F --platform {FACEBOOK,TIKTOK,TWITTER,YOUTUBE} --dirigente-id N --commit` · **pasar `DATABASE_URL_RAW=postgresql://crece:crece_dev@localhost:5438/crece`** (default usa crece-db:5432, no resuelve en host) |
| **IG posts** | `ingest_radar_ig.py` | APLANADO: `{"posts":[{platform_post_id(=post_id), caption, like_count, comment_count, play_count, media_type, product_type, post_url, post_code, time_iso}]}` | `--dirigente-id N --profile-id M --posts F --commit` |
| **FB/TT comments** | `ingest_radar_comments_payload.py` | `{"comments":[{"payload": <raw comment payload>}]}` | `--dirigente-id N --profile-id M --comments F --commit` |
| **IG comments** | `ingest_radar_ig.py` | `{"comments":[{platform_post_id, comment_id, comment_text, author_display_name, time_iso}]}` | `... --comments F` |

- Todos los adapters: **idempotentes** (ON CONFLICT), computan ER + `author_hash` (LFPDPPP) automáticamente.
- TT comments: `payload.post_id` matchea limpio. FB comments: depende del join key (pfbid puede quedar huérfano; verificar `huérfanos=0` en el output).

## Enrich NLP
- **`post_ingest_enrich.py --dirigente-id N [--limit M]`** — cadena 4 pasos: posts tono/target → comments tono/target/polaridad → emotions posts → topics. **Idempotente** (`WHERE col IS NULL` → solo el delta sin enriquecer).
- **Modelo (OBLIGATORIO): `CC_MODEL=sonnet CC_EFFORT=medium`.** NUNCA Opus 4.7 ni effort high para clasificar. `low` NO (subestima críticas 34%, audit D3). Sonnet ~6x más rápido que Opus, sólido para clasificación.
- **RAM-SAFE:** los 4 sub-scripts invocan `claude --print --strict-mcp-config` → **0 procesos MCP por llamada** (sin el flag arrancan ~26 → agotan RAM). **NO usar `--bare`** (apaga MCP pero rompe auth de suscripción → "Not logged in" sin ANTHROPIC_API_KEY).
- Rate medido: ~1.7s/item (~0.5-0.6/s) serial.
- **Paralelismo seguro** (sin deadlock): dirigentes DISTINTOS en paralelo (filas disjuntas), o por dirigente: posts-chain (tono→emo→topics, MISMA tabla `social_posts` → SERIAL entre sí) ‖ comments (`social_comments`, aparte). Probado: 3 claude concurrentes, RAM estable/sube.
- **Gate RAM:** `memory_pressure | grep "free percentage"` → sano >40%. El crash 2026-05-27 NO fue la flota MCP per se sino presión ACUMULATIVA (máquina al borde + browsers de radar concurrentes + jobs solapados). El flag MCP + no correr concurrente con scraping pesado de radar lo previenen.
- Comando: `cd backend && CC_MODEL=sonnet CC_EFFORT=medium PYTHONPATH=. .venv/bin/python scripts/post_ingest_enrich.py --dirigente-id N`
- Background tracked: lanzar con `run_in_background` SIN `nohup` (nohup lo desacopla del tracking → no notifica).

## Verificación — qué pedir SIEMPRE antes de decir "funciona"
1. Coverage posts (join social_profiles): tono/emotions/topics. **Faltantes con texto vacío/emoji = legítimo** (scripts saltan sub-threshold).
2. Coverage comments: nlp_tono. Faltantes = comments sin texto.
3. Query de "faltante CON texto" debe ser ~0:
   ```sql
   SELECT COUNT(*) FILTER (WHERE sp.emotions IS NULL AND length(trim(COALESCE(sp.content,'')))>3)
   FROM social_profiles spr JOIN social_posts sp ON sp.profile_id=spr.id WHERE spr.dirigente_id=N;
   ```

## B07 (crecimiento de seguidores / "publicaciones que atraen gente")
- Necesita **time-series REAL de `followers_count`**: ≥2 `social_profile_snapshots` con `taken_at` distintos **y valores que cambien**. Si los snapshots copian el count estático → Δ=0 → card "en proceso de integración".
- RADAR debe correr `get_profile` periódico (entity_type='profile', `followers_count` en payload) → sembrar la serie. (Backfill pedido a Hugo 2026-05-27.)
- **Lista de followers NO es scrapeable** (FB privacidad, X cerrado, TT/YT no exponen, IG rate-limit/shadow-ban). → La idea "comentaristas que no siguen" está bloqueada de raíz.
- Proxy viable (radar lo computa): "engagers nuevos por ventana" = reactors/commenters que aparecen ahora y no en la ventana previa.

## Downstream tras NLP: B0x → FODA → Planes (verificado contra código 2026-05-27)
Orden real una vez que el enrich NLP terminó:
1. **B0x bloques (B01-B18): auto-update ON-READ.** `app/api/v1/endpoints/diagnostico.py` computa cada bloque en vivo (`await <service>.compute(db, dirigente_id, org_id)`: er/breakout/matrix_2x2/benchmark/plutchik/growth_attribution…). Reflejan la data NLP nueva al instante. **NO hay paso que correr.**
2. **FODA: REGENERAR (paso, LLM).** NO es on-read — `get_diagnostico_foda` lo lee de `planes_ia WHERE tipo='DIAGNOSTICO'` (último, `estructura_json` = fortalezas/oportunidades/debilidades/amenazas). Artefacto almacenado. Regenerar por dirigente con la data enriquecida:
   - `scripts/regen_diagnostico_enriched_host.py` (host) · `scripts/regen_diagnostico_gemini.py` (variante Gemini, sin CC). Confirmar args (`--dirigente-id N`) en el header del script.
3. **Planes: GENERAR desde el FODA (paso).** Endpoint live `/plan-ia/generate` = 503/disabled (D-1 Ollama OFF · blocker B-26-01 timeout Coolify). Usar scripts standalone:
   - `scripts/generate_planes_v3_from_diagnostico.py` — determinista: deriva tareas del FODA (cada D/A → tarea, cada O → tarea de explotación), v3 supersedes v2.
   - `scripts/regen_plan_dirigente.py --dirigente-id N [--skip-cc]` — plan IA vía `claude --print --effort high` + fallback `gemini-clean --mode plan` (D-2). `--skip-cc` fuerza Gemini (cero CC).

**Resumen del flujo completo:** ingest (RADAR→crece) → enrich NLP → **B0x libre (on-read)** → **regen FODA** → **generar planes**. FODA y planes tienen variante Gemini → se pueden correr sin CC.

## Gotchas registrados (no repetir)
- `docker exec` sin `-i` → heredoc no corre (output vacío ≠ 0 filas).
- Join social_posts → social_profiles (NO watched_profiles).
- `claude --print` carga 26 MCP sin `--strict-mcp-config`; `--bare` rompe auth.
- Medir ANTES de afirmar causa raíz / "data perdida" / duración (esta sesión: 3 diagnósticos erróneos por no medir).
- **Re-ingest de posts ya existentes vacíos NO actualiza content:** `ingest_radar_yt_x_posts.py` (FB/TT/X/YT) usa `ON CONFLICT (platform_post_id) DO NOTHING`. Si un post ya está en CRECE con content vacío (ej. los FB discovery-only de pepe_hybrid) y luego RADAR re-captura la versión CON texto, re-ingestar NO rellena el texto. Fix: `DELETE FROM social_posts WHERE content='' AND profile_id=X` antes de re-ingestar, o UPDATE targeted. (El adapter `ingest_radar_ig.py` SÍ hace `DO UPDATE ... content=COALESCE(NULLIF(content,''),EXCLUDED.content)`; el yt_x NO.)
- **FB posts sin `text` de `pepe_full_hybrid_run`:** el payload trae `discovery_source='engagement_links'` + post_id/URL/counts pero SIN `text`. **Causa real (Hugo, leyendo el script — NO es "discovery-only" como inferí del payload):** el engine SÍ extrae meta+reactors+comments y `extract_post_meta` baja el HTML completo (`page.content()`), pero el **parser nunca saca el cuerpo/mensaje** → hueco de PARSER, no incapacidad. Fix radar-side: agregar el parse del mensaje + re-run Phase 1; NO requiere apify/gasto. Afectó 135 posts FB (Gaby 74, Felipe 49, Piña 9, Yesenia 2, Pepe 1). `apify_fb_posts` y `claude_extension_v1` sí traen `text`. **Lección:** la ausencia de un campo en el payload dice QUÉ falta, no POR QUÉ — la causa se confirma leyendo el engine, no infiriendo del payload.
