# CRECE v2.0 — Status

**Ultimo update:** 2026-05-27 · CRASH RAM (máquina al borde + factores concurrentes) → reboot. **NADA se perdió.** ⚠️ CORRECCIÓN de un error mío previo: dije "data 3 MC perdida" — FALSO, fue join a tabla equivocada (`watched_profiles`=audiencia/likers en vez de `social_profiles`=perfil propio del dirigente, que es a lo que apunta `social_posts.profile_id`). Join correcto: **data INTACTA en crece-db :5438** — Piña(1) 522 posts/494 tono/2922 comments · Solano(2) 353/234/147 · Ballesteros(8) 685/271/41868. Enrich iba 40-95% al tronar. **Trabajo real (chico, NO re-ingest):** (1) parchear 4 scripts NLP con `--strict-mcp-config` (validado: apaga MCP sin romper auth; `--bare` NO sirve, exige API key); (2) correr `post_ingest_enrich.py --dirigente-id {1,8,2}` attended/lotes/idempotente (solo delta sin enriquecer), CC_MODEL=sonnet medium; (3) verificar app. Enrich target :5438 (NO :5453=radar scraper crudo).

## 2026-05-27 · POSTMORTEM crash RAM (data 3 MC NO perdida — ver corrección al inicio) (sesión Linda)

**Qué pasó:** lancé `post_ingest_enrich.py` en background para dir 1/8/2 (~650 filas, cada una invoca `claude --print`) unattended de noche, sobre una máquina ya saturada y concurrente con la captura de browser de radar.

**Causa raíz — medida 2026-05-27 (Gate A, 3 pasadas):** plain `claude --print` (lo que los 4 scripts NLP hacen) **spawnea 26 procesos MCP por llamada** (medido: delta 69→95 procs durante la llamada; el RSS del padre 448 MB los ocultaba). Mi hipótesis original (flota MCP por llamada) era CORRECTA. **Fix validado: `--strict-mcp-config`** → MCP delta 1 (≈0), mantiene auth de suscripción, output válido; bucle serial de 8 con inferencia real → RAM estable (~1050-1230 MB), 0 procs colgados. **`--bare` descartado:** apaga MCP pero rompe el auth OAuth (exige `ANTHROPIC_API_KEY`, unset → "Not logged in") → violaría `D-PLAN-IA-CC-GEMINI-CLI-1`. **Contribuyente al crash (no único):** presión acumulativa — máquina al borde (~688 MB libres con ambos stacks Docker) + 26-MCP transitorios × 650 llamadas plain unattended + captura browser de radar concurrente. **Fix:** Fase 3 = añadir `--strict-mcp-config` a los 4 scripts (PENDIENTE) + R3 (attended, no concurrente con radar) + R4 (chequear RAM antes).

**Findings verificados (crece-db :5438, 2026-05-27):**
- NLP/enrich target = **:5438** (scripts default `postgresql://crece:crece_dev@localhost:5438/crece`, comentario explícito). `:5453`=radar_db (scrape_results/targets/jobs = scraper crudo de Hugo, NO destino NLP).
- ⚠️ ERROR CORREGIDO: lo de "0 posts para 3 MC" fue join a tabla equivocada. `social_posts.profile_id` → **`social_profiles`** (perfil PROPIO del dirigente), NO `watched_profiles` (audiencia/likers). {3,57,59} en watched_profiles es audiencia, no posts.
- **Join correcto (social_profiles): los 3 MC SÍ tienen data en :5438, intacta** — Piña(1) 522 posts/494 tono/2922 comments · Solano(2) 353/234/147 · Ballesteros(8) 685/271/41868. Enrich parcial (40-95%). Solo falta correr el delta NLP (idempotente). NADA perdido, NO re-ingest.
- 4109 posts orfanos (profile_id sin watched_profile), acumulados semanas, mayoría ya enriquecidos. Batch fresco 2026-05-27 (266, tono=0) = RSS news bot (dir 56), no los 3 MC.

**Trabajo real (data intacta, NO re-ingest):** (1) parchear los 4 sub-scripts NLP con `--strict-mcp-config` (validado: apaga los 26 MCP/llamada sin romper auth de suscripción); (2) correr `post_ingest_enrich.py --dirigente-id {1,8,2}` attended, lotes `--limit`, chequear RAM antes (idempotente → solo delta sin enriquecer); (3) verificar app. CC_MODEL=sonnet CC_EFFORT=medium (confirmado CEO 2026-05-27).

## 2026-05-26 noche tardío · Pipeline ingest RADAR→CRECE E2E (sesión Linda · /sprint-implement A)

**Decisión CEO opción A:** cadena `post_ingest_enrich` + ingest adapters reusables (no backfills manuales). Cross-audit Gemini integrado.

### Adapters construidos (HOST · `cd backend && PYTHONPATH=. DATABASE_URL_RAW=postgresql://crece:crece_dev@localhost:5438/crece .venv/bin/python scripts/...`)
- `ingest_radar_ig.py --dirigente-id N --profile-id M --posts F --comments F --commit` (IG: normaliza ppid media_id_userid→bare, mapea campos, ER+hash).
- `ingest_radar_yt_x_posts.py --json F --platform {YOUTUBE,TWITTER,TIKTOK,FACEBOOK} --dirigente-id N --commit` (payload crudo, profile por BD, ER+hash, +FACEBOOK branch).
- `ingest_radar_comments_payload.py --dirigente-id N --profile-id M --comments F --commit` (comments raw-payload TT + aplanado FB · match exacto + bare fallback).
- `post_ingest_enrich.py --dirigente-id N [--limit M]` (cadena NLP: posts tono/target → comments tono/target/polaridad → emotions posts → topics · idempotente).

### Estado ingest — LOS 3 MC COMPLETOS (3/4)
- **Piña (dir 1):** 5 redes posts (522) + IG/FB/TT comments (917). ER OK. PII 0. Enrich corriendo (PID 1814, ~374/522 tono al persistir).
- **Ballesteros (dir 8):** 5 redes posts (685) + IG/FB/TT comments (1466). CERO código nuevo. ER OK salvo FB (followers=0).
- **Solano (dir 2):** IG 100p/46c + TT + X 19p + FB 1p + TT comments 24. CERO código nuevo. (low-activity FB/X; sin YT profile).
- **Felipe:** pendiente captura Hugo (test del pipeline genérico · FB personal + TT + IG).
- **Enrich NLP de los 3: LANZADO en background** 2026-05-27 ~00:27 (Sonnet 4.6 + effort medium · `CC_MODEL=sonnet CC_EFFORT=medium`). Cadena dir 1→8→2, ~650 llamadas CC, ~1.5-2h. Log `/tmp/enrich_3mc_1827.log`. **Verificar al regresar:** `grep -E "RESUMEN|✓|✗" /tmp/enrich_3mc_*.log` + `SELECT dirigente, COUNT(tono)... ` por dir. Si algún paso falló, re-correr es idempotente. Job viejo Opus (PID 1814) matado.
  - Comando manual si hay que re-correr: `cd backend && CC_MODEL=sonnet CC_EFFORT=medium PYTHONPATH=. .venv/bin/python scripts/post_ingest_enrich.py --dirigente-id N`

### Gaps (RADAR-side, Hugo trackea · no bloquean enrich)
- YT/X comments sin `post_id` en origen → no resuelven (Piña 4, Balles 56). Deuda menor, re-captura post-Felipe.
- FB/TT followers_count=0 → FB ER no computa (followers-based). = req B07 follower timeseries (Hugo arranca post-Solano/Felipe).

### PENDIENTE CRÍTICO
- **Correr enrich NLP** de Piña + Ballesteros: `post_ingest_enrich.py --dirigente-id 1` y `--dirigente-id 8` (slow CC ~horas c/u · idempotente · cubre comments nuevos). Hasta correrlo, B0x/B14/B15/B18/FODA NO tienen NLP de la data nueva. Hubo un background de Piña parcial; correr pass completo.
- Likers IG (Piña 6872, Balles 8473) → script reactors (fans, no bloquea).
- IG comments shape: Hugo manda IG aplanado (comment_id/comment_text top-level) → `ingest_radar_ig` lo come; FB/TT/X/YT comments raw-payload o aplanado → `comments_payload`.


## 2026-05-26 noche · /sprint-implement F0+F1 (plan cierre-pendientes) · sesión Linda

**Plan:** `.context/PLAN-2026-05-26-cierre-pendientes-diagnostico.md` (cross-audit Gemini integrado).

### Post-review (commits tras persistencia 8840ec5)
- **PII author_hash** (`aab8edf`): 257 filas con nombre crudo → pseudonimizadas (242 social_comments + 15 watched_profiles) + guard `ensure_author_hash` en ingest radar. LFPDPPP. 0 PII cruda restante.
- **B11** (`aba8087`): label claro (82.8% = % cruce partidista, NO "% MORENA") + color guinda. Saymi confirmada MORENA (Gobierno Oaxaca), no error.
- **B12 labels** (`bd4a54e`): español + aclara que son cuentas con sospecha 0-1, no posts.

### F0 (`<commit F0>`)
- **F0.2 audit_listeners en Celery worker** (`worker_process_init`) — cierra gap LFPDPPP: ops destructivas en tasks no se auditaban (solo uvicorn). Verificado `after_delete=True` en worker.
- **F0.3 + F3.1 calibración B12 coro:** investigación (Gemini priorizó) → los "coro" eran elogios genéricos ("Excelente"/"Felicidades", 429 autores en 202 grupos), NO coordinación ni dup. Fix `MIN_SHINGLES_CORO=6`. Saymi B12: 8→4 flagged. B13 (downstream) baja % inauténtico solo.

### F1 triage de las 10 cards sin revisar (de-riesgadas)
| Card | Veredicto |
|---|---|
| B01 ER, B02 Breakout, B05 Plutchik, B10 Humaniz, B17 Veda | ✅ OK (B05 ya tiene mapa español emociones D-EKMAN-1) |
| B16 Promesas | vacío legítimo (0 promesas registradas) |
| B04 Benchmark | OK |
| B08 SoV | menor: 660 topics → gap_alert ruidoso (over-granularidad) |
| B09 Share/Like | menor: "viral" sobre números chicos (1 like/4 shares) |

**Hallazgo clave:** a diferencia de las 8 revisadas visualmente (todas con issues reales), las 10 no-revisadas NO tienen errores críticos. Solo 2 calibraciones menores no-cliente-facing.

### A — Cadena `post_ingest_enrich` CONSTRUIDA (opción CEO, commit `769d3fa`)
- `backend/scripts/post_ingest_enrich.py --dirigente-id N`: secuencia 5 pasos NLP (posts tono/target → comments tono/target/polaridad → emotions posts/comments → topics), idempotente, reusa scripts existentes. Generalizó `extract_topics` + `backfill_nlp_saymi` a cualquier dirigente (identidad del prompt desde BD). Wiring probado en host (0 CC). **Subsume F5** (topics es paso 5 + por-dirigente).
- Pendiente E2E real: datos de Piña (Hugo entrega al cerrar captura). Posible gap sentiment_score → confirmar con Piña.

### Pendiente del plan
- **E2E cadena A con Piña** (Hugo entrega JSON al cerrar captura 3 MC + Felipe; CEO priorizó no desviar captura).
- F2 opcional: B08 gap min-posts + B09 floor interacciones (menores, no cliente-facing).
- F3.2: dedup cross-source comments (apify+radar solapan) — dato aparte.
- F4: sprint palabras moderación configurables (plan escrito).
- F6: mobile audit · N+1 BFF · error boundaries · matriz legacy · merge ~62 commits → main.
- B07 ← RADAR (Hugo).

---

## 2026-05-26 · Recuperación post-apagón + review cards diagnóstico + fix ER raíz (sesión Linda)

### Recuperación post-apagón (causa raíz: túnel, no containers)
- Containers Docker nunca cayeron (auto-restart). El problema: el **quick-tunnel cloudflared muere cada 1-3h** (DNS NXDOMAIN); Vercel enruta `/api/v1/*` por `BACKEND_TUNNEL_URL` → frontend cargaba SIN datos (500).
- Fix documentado: `bash scripts/mac-local/start-crece-tunnel.sh` (idempotente: rota túnel, actualiza Vercel env, redeploy). LaunchAgent corre c/hora pero el túnel muere más rápido → ventanas muertas. Considerar túnel nombrado estable (PID 616 ya corre uno).

### Review visual CEO · 6 cards corregidas (todas con el mismo patrón: lógica placeholder nunca calibrada contra datos reales)
| Card | Problema | Fix | Commit |
|---|---|---|---|
| B18 Violencia | "diputado" matcheaba "puta" (substring) | word-boundary `\b` + "cualquiera"→"una cualquiera" + labels español + mostrar todos + texto completo · Saymi 9→2 | `aaba572` |
| B07 Crecimiento | snapshot copia followers estático (delta=0) + mismatch FE↔BE | estado honesto "en integración" + adapter delta_followers/top_posts · dato real depende de RADAR (Hugo) | `aaba572` |
| B14 Topic Drift | bigram-Jaccard saturado (~1.0 a todo) | reframe a **composición** (nlp_target: persona/tema/otro) + topics_extracted · heatmap conservado (CEO lo pidió) · Saymi 55/28/17 | `2b6bc19` |
| B15 Hostilidad | 1 comentario negativo + ER spike → falso rage | exige ≥5 comentarios + ≥3 negativos · evidencia inline · labels español · Saymi 15→7 | `9180052` |
| B03 Salud (matriz 2×2) | ER=0 en 150 posts (default) → mediana 0 → Neutros/Sin eco imposibles | backfill ER global (1973 posts, TODOS los clientes) + umbral sobre ER>0 · Saymi 254/9/0/0→126/5/128/4 | `c773f40` |

### Fix de raíz · engagement_rate en TODAS las rutas de ingest (`a8f8729`)
- Causa: `engagement_rate` default=0.0; ingest (scrapers/RADAR/Apify) no lo calculaba → 35% global en 0 pese a interacción real. Rompía B03/B07/B15.
- Helper canónico `app/services/engagement.py` (views>0: (likes+comments)/views*100; sino (likes+comments+shares)/followers*100) · 6 tests.
- Event listener insert+update en SocialPost, registrado en uvicorn (lifespan) **Y** Celery worker (`worker_process_init` — crítico: scrapers corren en worker).
- 4 scripts SQL crudo (radar posts_v3/yt_x/ig, apify_refresh_all) + backfill usan el helper.

### Dependencias / pendientes abiertos
- **B07 real depende de RADAR (Hugo, peer `exktbbec`)**: contrato acordado — RADAR persiste timeseries follower_count, CRECE lo ingiere a `social_profile_snapshots`. Hugo lo retoma tras cerrar 3 MC + Felipe.
- **Plan palabras moderación configurables**: `.context/PLAN-2026-05-26-palabras-moderacion-config.md` (tabla con categoría+severidad+scope · default exacta · botón Probar). Siguiente sprint.
- **Gap pre-existente:** `audit_listeners` solo registrado en uvicorn, NO en Celery worker → ops destructivas en tasks no se auditan (LFPDPPP). Fix aparte.
- **topics_extracted** per-cliente: Saymi 93%, otros menos → B14 composición parcial en quien tenga menos topics.
- **56 commits** acumulados en `feat/post-ingest-hugo-2026-05-20` sin merge a `main`.
- **Próximo:** análisis B12 (Detector coordinación artificial) + B13 (Filtro de Realidad).

---

## 2026-05-25 noche · F4 matriz polaridad Saymi v1→v2 CERRADO (60 min walltime)

## 2026-05-25 noche · F4 matriz polaridad Saymi v1→v2 CERRADO (60 min walltime)

- 1,155 OK + 5 fails de 1,160 procesados · 99.3% migrado
- RAM 0 aborts · osciló 49-57%
- Distribución v2 final: celebratorio 787 · informativo 716 · personal 482 · propositivo 150 · solidario 29 · defensivo 1 · residuo v1: 8 posts
- Script `backend/scripts/migrate_tono_v1_to_v2_saymi.py` (reusable, RAM-conservador)
- Commit pusheado: `chore(nlp): migrate tono Saymi v1→v2 · 1155/1160 OK · RAM conservador`
- D-MATRIZ-POLARIDAD-V2-SAYMI-CIERRE-2026-05-25 registrada

## PRE-APAGÓN 2026-05-25 noche

CEO reportó apagón eléctrico. Estado al pre-cierre:
- `git status` limpio salvo este STATUS.md (commit ahora)
- Todos los commits previos pusheados a origin/feat/post-ingest-hugo-2026-05-20
- Cero procesos background corriendo (F4 ya terminó normal exit=0)
- Docker containers UP (crece-backend, db, redis, minio, celery-beat, celery-worker, flower, frontend)
- Alias prod `frontend-zeta-sepia-46.vercel.app` apuntando a `frontend-b74yrrywl` (sidebar contrast fix)

### Recuperación post-apagón

Al regresar la luz:
1. Verificar Docker daemon vivo: `docker ps`
2. Si containers caídos: `docker compose up -d` desde raíz repo
3. Cargar contexto: leer `.context/STATUS.md` (este archivo) + `.context/PLAN-current.md`
4. Verificar último push: `git log --oneline origin/feat/post-ingest-hugo-2026-05-20 -5`
5. Cero acción pendiente · sesión cerrada limpia

### Sesión Linda · trabajo del día 2026-05-25 (resumen ejecutivo)

3 sprints cerrados consecutivos:
1. **PLAN-2026-05-22-recovery** (cierre) · Saymi topics 100% · 670/670 OK
2. **PLAN-2026-05-25-sprint-multi** · 5 bugs UI + B07 beat + B08 rivales + TT mapper · 7 commits
3. **PLAN-2026-05-25-sprint-cierre-audit** · 9/10 items audit ya estaban hechos · #9 sidebar contraste fix
4. **F4 matriz polaridad** · 1155 posts v1→v2 · 60 min

Total commits push hoy: 11. Push exitoso. Cero deuda pendiente operativa.

---

## 2026-05-25 noche · Sprint cierre-audit PLAN-2026-05-25-sprint-cierre-audit CERRADO (~1.5h)

**Plan:** `.context/PLAN-2026-05-25-sprint-cierre-audit.md`
**Origen:** CEO post-cierre sprint multi pide cerrar tríada + audit. Verificación primary source antes de implementar.

### Hallazgo masivo

**9 de 10 items audit-full 2026-05-19 ya estaban cerrados de facto** en sesiones intermedias (sin que el audit se actualizara). Plan original estimaba ~8h · realidad 30 min trabajo neto + commits.

| # | Audit item | Estado verificación | Acción |
|---|---|---|---|
| 1 | .env.scraping-keys tracked | YA untrackeado (git ls-files 0) | nada · sigue diferida rotación + filter-repo a sesión CEO |
| 2 | Prompt injection sanitize | YA hecho · llm_sanitizer.py "B4 audit-full" + sanitize_data_field 4x | nada |
| 3 | Rate-limit /posts/unified | YA aplicado @limiter.limit("60/minute") | nada |
| 4 | Filtros /hub | YA useSearchParams + platform/date/sentiment | nada |
| 5 | Mobile vertical UnifiedPostCard | YA grid-cols-1 md:grid-cols-2 xl:grid-cols-3 en hub | nada |
| 6 | Badge data_source | YA DATA_SOURCE_LABELS + tooltip | nada |
| 7 | Skeletons Hub | YA UnifiedPostCardSkeleton + Suspense | nada |
| 8 | Tests /posts/unified | YA test_posts_unified.py 17KB "C7 audit-full" | nada |
| 9 | Sidebar contraste WCAG fail | text-muted-foreground (~4.0:1) → fix aplicado | text-foreground/70 (~7:1 AAA) |
| 10 | Colisión "Contenido" sidebar | YA un solo item | nada |

### Acciones efectivas sesión

- 1 commit · sidebar contraste 3 ocurrencias text-foreground/70
- Push + Vercel deploy `frontend-b74yrrywl` alias preservado
- Plan + docs commiteados

### Decisión registrada

- **D-AUDIT-CLOSURE-2026-05-25** · 10/10 items audit-full cerrados con caveat #1B (rotación keys + filter-repo) sigue diferida a sesión propia CEO (alto blast)

### Pendientes diferidos al cerrar sprint

- **F4 matriz polaridad Saymi** v1→v2 vocab uniforme · CONDICIONAL decisión CEO · 1173 posts vocab v1 mezclados con 1000 vocab v2 (52/44% split, no es 100% legacy como decía plan-20)
- PII compliance review (gap audit Gemini high) · sprint propio
- Performance N+1 stress test BFF · sprint propio
- Error Boundaries frontend específicos · sprint propio
- 56+ commits sin merge a `main` · decisión operativa CEO

**D-NO-ROTAR-KEYS-2026-05-25** · CEO ratificó que rotación de `.env.scraping-keys` + filter-repo NO interesa por ahora. Item #1 del audit-full queda fuera del backlog activo · no re-sugerir hasta que CEO lo levante.

### Lección sesión

Patrón confirmado por tercera vez: planes >3 días caducan rápido. Cuando un plan menciona "deuda pendiente del audit/sprint anterior", verificar primary source ANTES de implementar (git ls-files, grep, query BD). Hoy evitó ~7h de trabajo duplicado.

---

## 2026-05-25 tarde · Sprint multi PLAN-2026-05-25 CERRADO · 5 bugs UI + B07 beat + B08 rivales + TT mapper fix · 5 commits push + Vercel deploy · próximo: F4 tríada audit-full pre-cliente

## 2026-05-25 tarde · Sprint multi PLAN-2026-05-25-sprint-multi CERRADO (~3h)

**Plan:** `.context/PLAN-2026-05-25-sprint-multi.md` (F1-F3+F5 ejecutadas · F4 tríada diferida sesión propia)
**Origen:** post-cierre recovery 2026-05-22 · CEO inspección visual descubrió 5 bugs UI + cuestionó B07/B08/B17
**Cross-verificación primaria:** Hugo (peer RADAR `1m4oqc8n`) confirmó mapper TT contract antes de tocar BD

### Fases ejecutadas

| Fase | Items | Resultado |
|---|---|---|
| F1 backend SQL + scripts | TT mapper patch + UPDATE 32 posts + ER recompute + tono_discurso serializer | 5,749 likes + 90,051 views recuperados · ER avg 0.96% max 12.97% (rangos TT normales) · 0 fails |
| F2 beat + topics rivales | snapshot_all_profiles task + beat lunes 02:00 MX + extract topics Ivette+Susana | Baseline 36 snaps OK · Ivette 17/17 + Susana 66/66 OK · B07+B08 destrabados |
| F3 frontend UX | Título widget honesto + selector N=1 readonly + sticky platform filter | tsc verde · check-no-mocks verde |
| F5 deploy | 5 commits incrementales + push + Vercel prod + alias | Alias `frontend-zeta-sepia-46.vercel.app` apunta a deploy `frontend-i1ye7nrdx` |
| F4 tríada audit-full | rate-limit `/posts/unified` + filtros `/hub` + rotación `.env.scraping-keys` | DIFERIDA sesión propia con CEO (alto blast del item #3) |

### Commits sesión (6 + 1 vercelignore)

| Hash | Mensaje |
|---|---|
| `6b4ba0c` | fix(ingest): TIKTOK platform branch en ingest_radar_yt_x_posts |
| `e654dda` | feat(workers): snapshot_all_profiles task + beat semanal · destrabra B07 |
| `5d4373b` | fix(api,ui): tono_discurso en recent_posts + SentimentBadge fallback |
| `ea04a1a` | ui(dirigentes,aceptacion): título honesto + selector N=1 + sticky filter |
| `7092426` | docs(plan): PLAN-2026-05-25-sprint-multi · F1-F3+F5 cerradas |
| (post-deploy) | chore(deploy): add .vercelignore con secrets pulled |

### Bug #3 RADAR mapper · diagnóstico cross-verificado

CEO observó posts TT con 0 likes en `/dashboard/dirigentes/3`. Mi primera reacción fue "scraper RADAR falló" sin verificar — error mío reconocido. Verificación primaria + consulta a Hugo (peer RADAR `1m4oqc8n`) confirmó:

- RADAR yt-dlp_tiktok SÍ trajo métricas (raw_data.like_count hasta 2,529)
- Bug es del mapper CRECE-side: script `ingest_radar_yt_x_posts.py` tenía else branch hardcoded ceros para TIKTOK
- Fix: rama TIKTOK explícita + UPDATE one-shot desde raw_data hacia columnas
- Sin re-scrape · datos ya estaban en raw_data

### Decisiones nuevas registradas (5)

- **D-RADAR-TT-MAPPER-2026-05-25** · mapeo canónico yt-dlp ratificado por Hugo (like_count→likes, view_count→views, comment_count→comments, repost_count→shares)
- **D-BEAT-SNAPSHOT-WEEKLY-2026-05-25** · snapshot followers semanal lunes 02:00 MX para destrabar B07
- **D-WIDGET-TITLE-HONESTY-2026-05-25** · "Publicaciones recientes" en lugar de "Contenido con más Impacto" porque query no ordena por impacto
- **D-B17-NO-DISTRITAL-2026-05-25** · card actual refleja realidad (heurística keyword + flag global) · calendario INE distrital diferido hasta pedido cliente
- **D-SoV-RIVALES-TOPICS-2026-05-25** · B08 SoV requiere topics en rivales · extract_topics sobre Ivette+Susana destraba comparativa real

### Pendientes diferidos al cerrar sprint

- **F4 tríada audit-full** completa (sesión propia · alto blast item #3)
  1. Rate-limit `/posts/unified` (~30 min · low-risk)
  2. Filtros en `/hub` (~1-1.5h · UX)
  3. `.env.scraping-keys` rotación + git filter-repo (~1-2h · sesión propia CEO)
- Matriz polaridad v2 Saymi 595 posts legacy
- Mobile audit completo
- 54 commits acumulados en `feat/post-ingest-hugo-2026-05-20` sin merge a `main`
- Backlog: "Contenido con más Impacto" REAL (endpoint propio ORDER BY engagement_rate)
- Bug #3 backlog F5: re-scrape para `save_count` queda en raw_data (sin columna)

---

## 2026-05-25 · Recovery post-crash 2026-05-22 CERRADO (~2h walltime cierre · batch 30 min · resto verificación)

## 2026-05-25 · Recovery post-crash 2026-05-22 CERRADO (~2h walltime cierre · batch 30 min · resto verificación)

**Plan:** `.context/PLAN-2026-05-22-recovery.md` · reporte cierre `.context/REPORTE-RECOVERY-2026-05-22.md`

### Hallazgo principal del cierre

Entre 2026-05-22 (crash) y 2026-05-25 (cierre), sesiones intermedias avanzaron de facto la mayoría de pendientes del plan-22 sin actualizarlo. Plan estaba 3 días desactualizado.

| Fase | Estado real al iniciar cierre | Acción cierre |
|---|---|---|
| F3.0 limpieza BD | ✅ ya hecha · plan #73 borrado · Ivette MORENA · WIP commit en `975d09c` | sin acción |
| F3.1 NLP backfill | 100% tono · 100% emotions · sólo 670 Saymi YT+TT topics pendientes (con content >10c) | batch único 670 OK 0 fails 30min |
| F3.2 frontend lenguaje | B04/B05/B08 ya cliente-ready · B05 Ekman 6 ya D-EKMAN-1 2026-05-12 · topics_extracted pretty-mapeado | sin acción |
| F3.3 deploy | alias prod ya con commit Pedro Carlock del agente anterior (~11:30) | sin re-deploy · topics nuevos los lee backend al próximo request |

### Tabla G1-G5 · sprint cerrado

| # | Criterio | Estado |
|---|---|---|
| G1 | Plan #73 stale eliminado · #76 vigente | ✅ |
| G2 | Ivette MORENA en BD | ✅ |
| G3 | NLP gap <10% por (dirigente, plataforma) con content válido | ✅ Pepe 100% · Saymi 100% todas plataformas |
| G4 | B04/B05/B08 lenguaje cliente · B05 6 emociones | ✅ |
| G5 | Cero crashes RAM durante F3.1 | ✅ 670/670 OK · 0 fails |

### Decisión nueva registrada
- **D-RECOVERY-CIERRE-2026-05-25-PLAN-DESACTUALIZADO** · planes post-incidente caducan rápido. Lección: verificar estado real BD+código antes de re-ejecutar plan de recovery >3 días viejo. Evita ~90% re-trabajo.

### Cambios sesión
- `.gitignore` · agregado `*.vercel.pulled*` (5 patrones · evita commit accidental secrets locales)
- `.context/REPORTE-RECOVERY-2026-05-22.md` · nuevo · reporte cierre completo
- `.context/PLAN-current.md` · ACTIVE apunta a recovery (cerrado)
- `backend/scripts/extract_topics_saymi_cc.py` · ejecutado, 670 posts Saymi nuevos topics_extracted

### Pendientes diferidos al cerrar recovery
- **Tríada crítica pre-cliente audit-full 2026-05-19** sigue abierta · próximo sprint
  1. Rate limit `/posts/unified` (~30 min · SlowAPI middleware)
  2. Filtros en `/hub` (~1-1.5h · regresión vs `/social` viejo)
  3. `.env.scraping-keys` tracked git (~1-2h · alto blast · rotar keys + `git filter-repo` · sesión propia con CEO)
- Backfill matriz polaridad v2 Saymi 595 posts legacy (sigue diferido sprint 20-may)
- Mobile audit completo (sigue diferido)
- 52 commits acumulados en `feat/post-ingest-hugo-2026-05-20` sin merge a `main`

---

## 2026-05-19 noche · /audit-full · score 73.25/100

8 audits paralelos + cross-audit Gemini. Reporte completo en `.context/AUDIT-FULL-2026-05-19.md`.

**Scores por dimensión:**
- Smoke 100 · Funcional 86 · Seguridad 44 · Calidad 79 · Diseño 74 · Responsive 76 · Hardening IA 70 · Accessibility 68

**Veredicto Gemini:** score 73.25/100 sobre-estimado · 🔴 NO listo para cliente.

**Tríada crítica pre-cliente:**
1. `.env.scraping-keys` tracked git (rotar + purgar historia) · TASK #47 PENDIENTE CEO
2. Rate limit ausente `/posts/unified`
3. Sin filtros en `/hub` (regresión vs /social viejo)
4. (extra alto) UnifiedPostCard no apila vertical mobile

**Pendiente CEO:**
- Decidir si frenar cliente hasta cerrar tríada o liberar con caveats
- Autorización para rotar credentials + git filter-repo

---

## 2026-05-19 noche tarde · Content Hub F4 cerrado · /dashboard/hub consolidado + redirects 308

## 2026-05-19 noche tarde · Content Hub F4 CLOSED (~3h)

CEO autorizó ejecución F4 al confirmar que cliente NO ha visto la app (mi diagnóstico de "no romper modelo mental" era erróneo · sin modelo mental existente).

### Entregado

**Backend** (commit `b2f9ba67`):
- Schema `PostUnifiedItem` Pydantic con discriminator `view`
- Endpoint `GET /api/v1/posts/unified` BFF · 4 view handlers separados
- Smoke: feed=1681 · top=1532 · comentarios=1222 · fans=42

**Frontend:**
- `/dashboard/hub` workspace unificado (D13.2 ajustado · /contenido ya estaba tomado por Content Factory)
- Hook `useUnifiedPosts` + adapter
- Tabs internos `?tab=feed|comentarios|top|fans` con deep-linking + Suspense boundaries
- Reusa UnifiedPostCard (F1)

**Sidebar consolidación (D13.5=A):**
- Removidas 4 entradas: Monitoreo, Comentarios, Top Posts, Fans y Perfiles
- Single ítem "Contenido" → /hub

**Redirects 308:**
- /dashboard/social → /hub?tab=feed
- /dashboard/social/comentarios → /hub?tab=comentarios
- /dashboard/content/top → /hub?tab=top
- /dashboard/aceptacion/fans → /hub?tab=fans
- Rollback: remover bloque async redirects · rutas viejas no se eliminaron del codebase

### Validación Playwright global · 100% verde

| Check | Resultado |
|---|---|
| Hub default (feed) | ✓ tabs visibles · workspace title |
| Deep-link ?tab=top | ✓ URL preserva tab |
| Deep-link ?tab=fans | ✓ posts con reactors cargan |
| Redirect /social → /hub?tab=feed | ✓ |
| Redirect /aceptacion/fans → /hub?tab=fans | ✓ |
| Sidebar: "Contenido" presente · no Monitoreo/Top Posts | ✓ |
| Plan 52 (regresión) | ✓ |
| Errores 5xx | 0 |

### Cross-audit Gemini integrado

- `approve_with_changes`
- Blocking concern "timing piloto activo" → DESCARTADO por CEO (cliente no ha visto)
- Non-blocking #1 polimorfismo discriminator → APLICADO en PostUnifiedItem
- Non-blocking #2 Suspense boundaries → APLICADO en grid central

### URLs

- Prod: https://frontend-zeta-sepia-46.vercel.app/dashboard/hub
- Deploy: `frontend-prb2qni9a` aliased
- PR: #54 merged commit `b2f9ba67`

### Pendientes diferidos (de toda la sesión)

- Cleanup endpoint `/sentiment-timeline` legacy backend (cuando 100% consumers migrados)
- Backfill NLP enriquecido sobre POSTS (granularidad 5 colores tono_discurso)
- Tests pytest Sprint D y F scripts (LLM mocks complejos)
- Test Vitest applyVipOverrides (requiere setup Vitest primero)
- Cleanup BD S-8.1 154 auto_suggested + 320 events (esperando orden CEO)
- Hugo D3 IG burner ya cerrado en RADAR ✓ · Threads activación cuenta pendiente sprint 10

---

## 2026-05-19 noche · Plan deuda 16 fallos · P0+P1+P2 cerrados · 14 fixes en prod · 1 diferido post-piloto

## 2026-05-19 noche · Plan deuda 16 fallos · P0+P1+P2 CLOSED (~3h total)

**Origen:** CEO revisión visual prod identificó 16 fallos. `/plan` aprobado + `/sprint-implement` con autonomía concedida.

### Sprints ejecutados

**P0 · pre-piloto (commit `be519aed` · PR #51):**
- #2+#7 sentiment NULL no inventa "Neutral" (sentiment-badge + computeDistribution + pie chart + callout amarillo)
- #3 `@@saymipineda` → `@saymipineda` (handle.startsWith guard)
- #6 Monitoreo "19 posts" caveat dedup + tooltip

**P1 · post-piloto (commit `0c523cf1` · PR #52):**
- #8 Split-view cliente_seed (CuratedSeedList nuevo · grid xl:grid-cols-2)
- #9 Indicador plataforma Top Posts (badge prominente)
- #11 Overview chart empty state real cuando 0 clasificados
- #12 Banda gris Fantasmas dual (acumulando vs sin cobertura RADAR)
- #1 sentiment_label → tono_discurso · **DIFERIDO** (requiere endpoint backend nuevo · cubierto parcialmente por #11)

**P2 · misma PR #52:**
- #14 "sin RTs" condicional por plataforma
- #15-16 Top Posts tooltip "elegibles"
- #4+#10 Warning visual cards con bajas interacciones absolutas (<10)
- #5 Glosario disonancia Fantasmas (tooltip reactions vs likes públicos)

### Validación

- TS check verde · ambos PRs
- Smoke CI verde · ambos PRs
- Cross-audit Gemini P0: `approve_with_changes` · 2 blocking concerns absorbidos (Alert externo no SVG · NO ampliar Monitoreo a 30d)
- Cross-audit Gemini P1.#8: `approve_split_view` aplicado al diseño
- Playwright validación global post-deploy: P0+P1+P2 todos verdes · 0 errores 5xx · plan_id=52 carga · split-view confirmado visual

### Deploy

- PR #51 → main `be519aed` → `vercel --prod --yes` → alias `frontend-zeta-sepia-46.vercel.app`
- PR #52 → main `0c523cf1` → `vercel --prod --yes` → deploy `frontend-avkf0r3t7` aliased

### Documentación

- `.context/OBSERVACIONES-CEO-2026-05-19.md` · 9 OBS + tabla consolidada 16 fallos
- `.context/PLAN-2026-05-19-deuda-tests-y-fixes.md` v2 · separado (plan tests)
- `.context/PLAN-2026-05-19-content-hub.md` v2 · backlog F4 cubre #13
- `~/.claude/plans/greedy-strolling-graham.md` · plan aprobado de los 16 fallos

### Pendiente

- #1 sentiment_label → tono_discurso: sprint backend post-piloto (endpoint nuevo)
- #13 Monitoreo + Comentarios consolidación: backlog Content Hub F4 (4-6 sem)

---

## 2026-05-19 tarde · /sprint-implement Bloque A · smoke pre-piloto §9.8 18/18 OK · concern Gemini bug control chars refutado empíricamente

## 2026-05-19 tarde · /sprint-implement Bloque A · Smoke pre-piloto §9.8 (CLOSED)

**Origen:** CEO `/sprint-implement` post aprobación plan deuda tests v2 (post cross-audit Gemini).

### Resultado Bloque A · 18/18 vistas OK

Playwright headless read-only contra `https://frontend-zeta-sepia-46.vercel.app` con login Saymi `pineda@crece.mx`.

| Vista | Status |
|---|---|
| Overview, Dirigentes, Diagnóstico, Diferenciadores, FODA | OK ✓ |
| Social Monitoreo, Comentarios, Clima, Top Posts | OK ✓ |
| Aceptación Overview, Por dirigente, Fantasmas, **Fans y Perfiles** (Misael ⭐ Fan #1 confirmado) | OK ✓ |
| Planes lista, **/planes/52** (caso crítico Gemini bug control chars) | OK ✓ |
| Reels, Recomendaciones, Mi Evaluación | OK ✓ |

Total: **18/18 OK · 0 FAIL · 0 EXCEPTION**.

### Concern Gemini absorbido empíricamente

Plan v2 movió bug `/planes/{id}` control chars al Bloque A para verificación pre-piloto (severity HIGH). Resultado: `/dashboard/planes/52` renderiza completo:
- Título "Plan de Contenido · Borrador"
- Modelo IA trazable `cc-subprocess-plan-v1-2026-05-19`
- Created 19 may 2026 12:37 a.m.
- 5 tareas con metas medibles visibles · 0% avance · 5 pendientes
- Sin "Dirigente no encontrado", sin 404, sin error visible.

**Veredicto:** Axios tolera control chars como hipoteticé. Bug NO afecta UI demo. Bug se queda en Bloque B post-piloto donde estaba en plan v1.

### Findings non-blocking

- 4 console errors "Failed to fetch RSC payload" en navegación Next.js → fallback a browser navigation (pattern normal Next.js App Router, no UX impact).
- Cero 5xx, cero pageerror, cero "Dirigente no encontrado" en ninguna vista.

### Próximo paso

- Piloto §9.8 mañana 2026-05-20 con TODO el dashboard verde.
- Bloque B (bug control chars + test applyVipOverrides) y Bloque C (tests Sprint A/D/F) post-piloto según plan v2.

### Screenshots
Disponibles en `/tmp/crece_smoke_2026_05_19/` (18 archivos · 3.1MB total).

---

## 2026-05-19 · Plan fans-dashboard Sprint D cierre + Sprint F regen plan Saymi standalone
**Sesion activa:** Linda · branch `feat/phase-b-pesos-editables`
**Branch activo:** `feat/phase-b-pesos-editables`
**Próxima ventana §9.8:** día 30 piloto ≈ 2026-05-20
**Próximos planes:** decisiones BLOQUE 1 (CEO · D-1.1 endpoint Juan · D-1.2 Groq · D-1.3 Meta · D-1.4 competidores) + S3 mobile audit (sesión propia)

---

## 2026-05-19 — Cierre Sprint D + F plan fans-dashboard (CLOSED)

**Continuación post-apagón Mac Mini 2026-05-17. Sprints A/B/C/E ya cerrados pre-apagón (commits f449262, 7e34fdf, 923c034, 2a1b13b, 3a412eb, 0c75a85, 0b0e4b1, ae20ef0).**

### Sprint D · Backfill NLP comments Saymi con effort=high (CLOSED · commit 177f768)

- **Hallazgo audit 2026-05-18 22:58 (`audit_cc_effort_high_d3_20260518_2258.md`):** CC effort=low subestimaba críticas. Muestra n=50: 42% clasificaciones distintas vs effort=high, 34% cambios signo polaridad, 5 críticas nuevas detectadas. Bug era effort=low.
- **Fix:** `backfill_nlp_saymi.py` con `CC_EFFORT='high'` y `CC_TIMEOUT=600s` como defaults.
- **Backfill completo post-apagón:** 274 comments pendientes → ~9 min walltime con effort=high · 0 fails.
- **Artefactos persistidos:** `audit_cc_effort_high.py` (script reutilizable para futuros audits CC-low vs CC-high) + `audit_cc_effort_high_d3_20260518_2258.md` + `cross_audit_gemini_d3_20260518_2241.md`.

### Sprint F · regen_plan_dirigente.py standalone (CLOSED)

- **Script nuevo:** `backend/scripts/regen_plan_dirigente.py` — genera Plan IA offline via CC subprocess (`claude --print --effort high`) con fallback `gemini-clean --mode plan`. NO toca Ollama legacy (D-1) ni endpoint `/plan-ia/generate` (sigue en 503).
- **Diferencia con pipeline original async:** usa contexto curado de `dirigente_context_builder` (Sprint E enriqueció con `performance_posts`) en lugar de cargar los 18 bloques B01-B18. Es entrada más compacta + más rica en señal cualitativa.
- **Persistencia:** plan header en `planes_ia` + recomendaciones individuales en `recomendaciones_plan_ia` con `estado='propuesta'`.
- **Verificación dry-run Saymi (id=3):** contexto 5521 chars · 3 winners + 3 losers + quotes representativas · 5 efemérides · tono dominante neutral 81.7% sobre 82 posts.
- **Validación output:** parser robusto + shape validation (3-8 recomendaciones, tipo in start/stop/continue, accion_texto required, ventana_duracion_dias parseable).
- **Bloquea B-26-01 a medias:** la generación funciona offline para piloto Saymi, pero el endpoint `/plan-ia/generate` sigue 503 (decisión D-1 expresa CEO).

### Decisiones aplicadas (respetadas)
- **D-1:** Ollama OFF · `llm_pipeline.py` intacto · endpoint sigue 503.
- **D-2:** Stack runtime = CC subprocess + Gemini CLI fallback ✓.
- **D-5:** Ventana confiable Sprint A endpoints `[2026-04-01, 2026-05-14]` ≈ 44 días ✓.
- **D-PLAN-IA-CC-GEMINI-CLI-1:** ratificada (CEO override sobre Gemini que pidió Groq+Claude API directas).

### Pendiente menor
- Sprint F lanzado contra Saymi para generar el primer plan offline ✓ (resultado se verifica en `/dashboard/planes` UI).
- Tests para Sprint F (`tests/scripts/test_regen_plan_dirigente.py`) — diferido a sesión dedicada (script con dependencias externas LLM, no trivial mockear).
- Limpieza opcional 154 watched_profiles auto_suggested + 320 watched_like_events del E2E S-8.1 (esperando orden CEO post-postmortem).

---

## 2026-05-16 — /sprint-implement segunda ronda · B + A + C (CLOSED · ~1h adicional · 3/3)

**Continuación post Q-1..Q-5 · CEO autorizó 3 sprints adicionales tras confirmar que problemas de memoria de Juan (peer) no se extrapolan a CRECE.**

### Sprint B · Hook bot_detection (B-FOLLOWERS-BOT-1 · CLOSED)
- **Cambios:**
  - Helper `score_follower(handle, platform, profile?)` en `app/services/bot_detection.py` · wrap de `analyze_account` · retorna `(bot_score, is_real)` con `BOT_THRESHOLD=0.70`.
  - Hook en `youtube_privileged.upsert_subscribers`: score por handle al insertar (no requiere profile completo).
  - Endpoint `POST /api/v1/dirigentes/{dirigente_id}/followers/rescan-bots` para filas pending (`bot_score IS NULL`) + flag `force` para re-score.
  - Query param `only_real: bool` agregado a `GET /api/v1/dirigentes/{dirigente_id}/followers`.
  - 6/6 tests unit en `tests/test_bot_detection_hook.py`.
- **Verificación E2E:** fila Benjamin Jimenez (id=1 dirigente=1 YT) post-rescan: `bot_score=0.05`, `is_real=True`.

### Sprint A · Tier 2 UX refactor cards B11-B18 (CLOSED · ya estaba implementado)
- **Hallazgo:** trabajo ya estaba **CERRADO en commit `3726888`** (2026-05-13 "feat(tier2+oauth): UX refactor 3 zonas + OAuth callback handler real").
- **Verificado funcionando:** `npx tsc --noEmit` clean · `check:no-mocks` verde.
- **Items confirmados en código:** ZonaSection con 3 grupos (Autenticidad/Narrativa/Legal-Riesgo) · switch global Reality Filter · CardShell con Popover `technicalNotes` · `calibrating` prop B14 · grid leyenda · B16 CTA "Registrar primera promesa" · B17 `animate-pulse` cuando veda activa.
- **Lección:** verificar fuente primaria antes de scoring (memoria proyecto · sub-regla activa). El blocker decía "pendiente" pero el código estaba ahí.

### Sprint C · Unificación KPI cards (CLOSED · honest diagnostic)
- **Diagnóstico aplicando "Layer-of-fix antes de refactor":** el backlog decía "4 implementaciones a unificar". Audit real reveló:
  - `KpiCard` (37 líneas) · **0 consumers** → dead code.
  - `StatCard` canonical (`dashboard/stat-card.tsx`) · usado en canvassing + participacion.
  - `StatCard` local en `watched-profiles-tab.tsx` · agrega `accent` good/warn (no estaba en canonical).
  - `StatCardSkeleton` local en `participacion/page.tsx` · duplicate.
  - `StatCard` local en `landing/stats.tsx` · animated counter marketing-específico, **NO unificable por diseño**.
- **Cambios surgical:**
  - Borrado: `frontend/src/components/dashboard/kpi-card.tsx` (dead code).
  - Extendido canonical `StatCard` con prop `accent: "default" | "good" | "warn" | "bad"` + export `StatCardSkeleton` con variants.
  - Reemplazado `StatCard` local en `watched-profiles-tab.tsx` → canonical con `accent`.
  - Reemplazado `StatCardSkeleton` local en `participacion/page.tsx` → import del canonical.
  - **NO tocado:** `landing/stats.tsx::StatCard` (counter marketing, propósito distinto).
- **Verificación:** tsc clean + check:no-mocks verde.
- **Pendiente menor:** `landing/stats.tsx::StatCard` debería renombrarse a `MarketingStatCard` para evitar colisión visual con el canonical (sin impacto funcional, queda diferido).

### Métricas segunda ronda
- **1 blocker cerrado** (B-FOLLOWERS-BOT-1).
- **6 tests nuevos** en `test_bot_detection_hook.py`.
- **3 archivos frontend** modificados (canonical extendido + 2 consumers limpiados).
- **1 archivo frontend** borrado (dead code).
- **0 regresiones** (tsc clean + check:no-mocks verde).

---

## 2026-05-16 — /sprint-implement · OAuth + infra backend (CLOSED · ~4h · 5/5)

**Plan:** `.context/PLAN-2026-05-16-sprint-implement-sesion.md` (subset BLOQUE 3 + BLOQUE 5 del plan consolidado · cross-audit Gemini integrado con 3 mitigaciones)

### Cerrado

| Sprint | Blocker | Cambios | Tests |
|---|---|---|---|
| **Q-1** | B-26-02 | `app/scrapers/base.py:94` `scrapers.get(platform.lower())` | 19/19 (`tests/scrapers/test_base.py`) |
| **Q-2** | B-OAUTH-YT-STATE-1 | `app/services/oauth_state.py` HMAC-SHA256 · payload `did+nonce+ts` · max_age=600s · `onboarding.py` callback verifica firma | 10/10 (`tests/test_oauth_state.py`) |
| **Q-3** | B-OAUTH-YT-CRYPTO-1 | Migration `oc1_oauth_token_encryption.py` (cols `token_enc`/`refresh_token_enc`/`crypto_version`/`encrypted_at`) · helper `app/services/oauth_crypto.py` (wrap pgcrypto) · `persist_callback_real` cifra en insert · script `scripts/encrypt_existing_oauth_tokens.py` migró 3/3 filas existentes | roundtrip empírico verificado (`decrypt == plain` para id=2) |
| **Q-4** | B-ONBOARDING-FE-BE-MISMATCH-1 | 5 endpoints path-scoped `/onboarding/{dirigente_id}/*` con `assert_dirigente_access` · legacy preservado para retrocompat (mitigación Gemini) | 6/6 (`tests/onboarding/test_onboarding_path_scoped.py`) + smoke E2E curl |
| **Q-5** | B-26-03 | Blocker obsoleto · container ya tiene yt-dlp + Playwright + Chromium SO via `$CHROME_BIN` · 7 regression guards | 7/7 (`tests/scrapers/test_container_binaries.py`, incluye launch real Chromium) |

### Métricas
- **5 blockers cerrados** en una sesión (B-26-02, B-OAUTH-YT-STATE-1, B-OAUTH-YT-CRYPTO-1, B-ONBOARDING-FE-BE-MISMATCH-1, B-26-03).
- **42 tests nuevos** todos verdes (19+10+6+7).
- **0 regresiones** en suite existente.
- **0 breaking changes** (legacy endpoints intactos, dual-column en oauth_tokens hasta NULL-out posterior).

### Pendiente menor
- `UPDATE oauth_tokens_by_platform SET token_hash=NULL, refresh_token_hash=NULL WHERE crypto_version >= 1;` en sesión humana posterior (post smoke-test piloto real, ~1 semana).
- Cuando frontend reactive wizard onboarding, consumir las nuevas rutas path-scoped.

### Cross-audit Gemini (FASE 2) — riesgos identificados + mitigaciones aplicadas
1. **Q-4 BE/FE desincronización** → retrocompat legacy preservada (no se eliminan rutas viejas).
2. **Q-5 OOM build Playwright** → no requirió rebuild (blocker obsoleto).
3. **Q-3 contexto secretos en Alembic** → schema-only migration + script Python standalone vía `docker exec` (separación validada empíricamente · 3/3 filas migradas sin error).

### Próximo paso recomendado
Decisiones CEO BLOQUE 1 del plan consolidado:
- **D-1.1** Gate endpoint `ingest-reactions-bulk` (Juan ready) → desbloquea BLOQUE 8 Watchlist.
- **D-1.2** Registro Groq + `GROQ_API_KEY` → activa Reels.
- **D-1.3** Iniciar Meta Business Verification → desbloquea IG/FB Graph API (4-6 sem).
- **D-1.4** Decisión modelo `competidores` (deprecar / renombrar / migrar) → desbloquea S-4.4 onboarding admin.

---

## 2026-05-15 — /sprint-review · 6 sprints dedicados (CLOSED · ~6h)

**Plan:** `.context/PLAN-2026-05-15-sprints-dedicados.md` (cross-audit Gemini integrado · orden reordenado por dependencias)

### Cerrado

| # | Sprint | Validación |
|---|---|---|
| S7 | N+1 list_dirigentes batched query | platform_count correcto · GET /dirigentes/ 200 |
| S2 | Engagement_7d = SUM(likes+comments+shares), no AVG rate bugueado | Saymi: 8086 interacciones reales (antes 0) |
| S8 | Audit log table + SQLAlchemy Event Listeners + helper para SQL raw | UPDATE watched_profiles/1 → 1 fila audit_log con user_id=7 |
| S9 | Script audit_ipd_stale (no recalcula, solo lista) | 9 dirigentes stale detectados local |
| S5 | Celery task scrape_competitors_monthly (disabled-by-default, time_limit=600s) | Task registrada · CEO activa en beat cuando quiera |
| S10 | Decorator with_backoff (asyncio.sleep, no retry en 429/403) | 9/9 tests verde · sync + async |

### Diferido honestamente

| Sprint | Razón |
|---|---|
| S1 · Unificación MetricCard | 5-6h refactor UI sistémica · necesita validación visual extensa con CEO presente para no meter regresiones en piloto activo. Patrón a 4 implementaciones diferentes. Sprint dedicado propio. |
| S3 · Mobile audit completo | 6-8h · cambios estructurales Sheet→BottomSheet, touch targets 44px, tablas card-view. Sprint propio con CEO. |
| S4 · Score IPD competidores | Bloqueado por B-APIFY-CREDIT ($0.43 disponible, requiere actores adicionales por plataforma). |
| S6 · Onboarding UI admin competidores | No urgente · admin puede agregar via psql por ahora. |

### Commits chicos (en orden)

1. `fix(aceptacion)` empty state honesto N<2 CompetitorComparisonCard
2. `fix(aceptacion)` HAVING >= 5 solo rankings, KPI agregados sin filtro (A3 audit)
3. `feat(ux)` 9 quick-wins UX post Gemini cross-audit (drawer + perfil)
4. `perf(dirigentes)` batched platform_count (S7)
5. `fix(dirigentes)` engagement_7d cuenta interacciones reales (S2)
6. `feat(audit)` audit_log + listeners + helper (S8) — migration al1
7. `feat(audit)` script audit_ipd_stale (S9)
8. `feat(workers)` task scrape_competitors_monthly disabled-by-default (S5)
9. `feat(scrapers)` decorator with_backoff (S10) + 9 tests

### Restricciones aplicadas

- Anti-over-engineering: S7 calculate_ipd anidado NO refactoreado (alcance grande, mantiene como nota).
- Anti-fallback-data: S2 NO retorna "0" cuando no hay datos — usa SUM real.
- LFPDPPP S8: NO se loguean valores de campos, solo `changed_columns`.
- S5 disabled-by-default: CEO activa Celery beat cuando quiera (presupuesto Apify).
- S10 NO aplicado a scrapers existentes — decorator listo, sprint posterior decide cuáles.

---

---

## 2026-05-15 — Audit multi-dimensión + hotfix RBAC + bugs encuestas (CLOSED · 6h)

**Plan v2:** `.context/PLAN-2026-05-15-audit-multi.md` (cross-audit Gemini integrado).
**Branch:** `audit/multi-2026-05-15` → merged a `feat/phase-b-pesos-editables` (Vercel prod alias zeta-sepia-46).

### Cerrado

| # | Sprint | Evidencia |
|---|--------|-----------|
| Fase 1 | Audit RBAC+Security+Compliance (security-engineer) | 6 CRÍTICOS scope leak + 3 ALTOS confirmados con curl. Reporte `AUDIT-SECURITY-RBAC-2026-05-15.md` |
| Hotfix | `0f232ea` aplica 7 endpoints + SQLi + JWT guard | 14 curl tests verdes (7→403 cross, 6→200 propio, 1 admin bypass) |
| Fase 2 | Audit Info+Lógica+Coverage (quality-engineer) | 1 CRIT + 3 ALTOS + 3 MEDIOS. Reporte `AUDIT-INFO-LOGIC-2026-05-15.md` |
| Fase 3 | Audit Performance+DB (performance-engineer) | 1 ALTO N+1 + 4 MEDIOS + 3 BAJOS. Reporte `AUDIT-PERF-2026-05-15.md` |
| Triage | Consolidación 19 findings | `AUDIT-TRIAGE-2026-05-15.md` |
| Sprint Q | A1+A2 encuestas (bugs CEO) | `15b4e39` · municipio visible alcaldes + chip-toggle compare 65→877 series |
| Vercel prod | Tunnel + deploy + smoke RBAC | 18/18 endpoints verde · `mount-where-formal-pick.trycloudflare.com` |
| Plan remediación | Decisiones + sprints siguientes | `AUDIT-REMEDIACION-2026-05-15.md` |
| Cross-audit Gemini | Veredicto: **PROCEDER** | Mitigaciones operativas (warm-up + env check) documentadas |

### Pendiente decisión CEO

| ID | Pregunta |
|---|---|
| A5 | `UPDATE social_comments SET data_source='legacy-pre-2026-04-13' WHERE data_source IS NULL` (306 rows) · ¿proceder? |
| A8 | DELETE competitor_profile id=5 (Taboada IG dup) — ¿split TW/IG intencional o duplicado real? |
| CRIT-PLAN-IA | `plan_generator` switch binario vs cascada documentada · elegir (a) implementar, (b) actualizar docs, (c) gap conocido |

### Próximos sprints (~7-9h restantes)

- **Sprint S** Compliance & RBAC residual (2-3h): audit_log destructivo, 403 explícito, CORS guard
- **Sprint I** Info quality (1.5h): sentiment mismatch UI, IPD recalc beat, back-off scrapers
- **Sprint P** Performance (3-4h): N+1 list_dirigentes, dynamic imports, index social_posts

---

## 2026-05-15 — Scraper light competidores · Saymi enriquecido (CLOSED)

Bug: dropdown competidores en `/dashboard/dirigentes/3` y `/dashboard/aceptacion/3` mostraba "—" porque `competitor_metrics_monthly` no tenía filas para Saymi. Sprint W7+W8 (war-room-personal) había dejado los `competitor_profiles` activos pero sin métricas mensuales.

### Cerrado

| # | Sprint | Evidencia |
|---|--------|-----------|
| W2-gratis | Scraper light SIN Apify (`scrape_competitors_light.py`) usando scrapers nativos `app/scrapers/{platform}.py` con estrategia cascada | Implementado. Falló runtime FB: curl-cffi 200 sin patrones nuevos de FB, ChromeDriver -5 en Docker. Sirve para IG/X/TT/YT futuros una vez se mejoren los scrapers de páginas. |
| W2-Apify-fallback | Apify INICIAL `apify/facebook-pages-scraper` — pre-flight budget check, dedupe handles, UPSERT `competitor_metrics_monthly` | `scrape_competitors_light_apify.py`. Run E2E exitoso 2026-05-15 04:18: **Susana Harp 62,895 followers · Ivette Morán 244,303**. Costo `$0.0000` (free tier mensual Apify, mismo run sin charge). MTD pool INICIAL: $4.5686/$5. |
| Verify DB | `competitor_metrics_monthly` populado para Saymi | 2 filas con `dirigente_objetivo_id=3` month_start=2026-05-01 verificadas via psql container |

### Decisión saldo Apify · siguiente paso
- MTD pool INICIAL: $4.5686 / $5.00 cap (queda **$0.43 hasta 2026-05-23**)
- Ballesteros (id=8) tiene 6 competidores pero NINGUNO en FACEBOOK (5 TWITTER + 1 INSTAGRAM). Extender a TW/IG requiere actores separados con costo distinto — fuera de scope esta sesión.
- Cuando se agreguen FB para Ballesteros: `docker exec -e APIFY_TOKEN=<token> crece-backend python scripts/scrape_competitors_light_apify.py --dirigente-id 8 --budget 0.10`

---

## 2026-05-14 — Fix fantasmas observados (CLOSED · 4 sprints en una sesión)

Bug original: usuario Cravioto (org 3) entrando a `/dashboard/aceptacion/fantasmas` tab "Perfiles Observados" veía datos de Saymi (org 2). Confirmado scope leak.

### Cerrado

| # | Sprint | Evidencia |
|---|--------|-----------|
| 0 | Verify premises | User.dirigente_id ✓ · 4 GETs sin _check_org ✓ · social_comments solo author_hash ✓ · Playwright setup ✓ |
| 1 | Backend close leak | `_assert_dirigente_access` + `_assert_watched_access` aplicados a GET /, /summary, /suggestions, /{id}/engagement, PATCH y DELETE. 6 curl tests verdes contra local. |
| 2 | Frontend UI | Default dirigente derivado de `user.dirigente_id` con fallback a `dirigentesList[0]`. Empty state cuando lista vacía. Labels "Likes" → "Reacciones". Tags vacíos = `—`. Filtros source ocultos con count=0. Doble título consolidado. |
| 4 | E2E + deploy | Playwright smoke browser cravioto+pineda OK · deploy Vercel prod (alias `frontend-zeta-sepia-46`) · 6 smoke prod verdes |

### Pendiente (Sprint 3, deferido)

Resolver `author_hash` → display name en sugerencias. Bloqueado por decisión D (camino 1 re-scrape / camino 2 lookup table TTL / camino 3 cachear `commenter_handle` en `social_comments`). Recomendación Claude: camino 3 (handle público, base legal "interés legítimo" LFPDPPP, no PII directa persistente).

### Detalle plan

`.context/PLAN-2026-05-14-fix-fantasmas-observados.md`

---

## 2026-05-13 noche — OAuth YT E2E real + UX review Tier 2 (CLOSED)

Sesión guiada: CEO completó GCP setup → OAuth real activado en backend → primera fila `is_stub=False` persistida → scraper privilegiado validado contra YT API → 1 sub real capturado. Bugs descubiertos en vivo y arreglados.

### Cerrado

| # | Logro | Evidencia |
|---|-------|-----------|
| 1 | GCP setup completo (proyecto crece-496212, YT Data API v3, OAuth client web, scopes, test user) | CEO en Google Cloud Console |
| 2 | OAuth real toggle activado en backend | `OAUTH_YOUTUBE_ENABLED=true` en root `.env`, `is_enabled()=True` |
| 3 | Bifurcación oauth_init real/stub en endpoint | `backend/app/api/v1/endpoints/onboarding.py:225-232` |
| 4 | GET callback handler agregado (Google envía GET, no POST) | `oauth_callback_youtube_real` con redirect a frontend |
| 5 | Bug fix: dirigente_id codificado en state | state = `<random32>:<dirigente_id>` · `build_init_url_real` + parse en callback |
| 6 | Redirect final a Vercel (overridable via env) | `OAUTH_FE_REDIRECT_BASE` env var |
| 7 | Primera fila OAuth real persistida | token `id=2` dirigente_id=1 `is_stub=False` `status=active` refresh_token presente |
| 8 | Scraper privilegiado E2E contra YT API real | 1 sub real `benjamin jimenez · UC6PIQ9zEXS3cYdYashbl0wQ` insertado en `social_followers` |

### Intentado y bloqueado infra (B-IG-DATACENTER-IP-1)

- IG `chatmx_oficial`: instaloader login aceptado pero `Profile.from_username` retorna `ProfileNotExistsException` incluso para `@instagram` oficial. IP de datacenter bloqueada por IG.
- Camino para próxima sesión: Brightdata proxy o Apify Instagram actor.

### Review UX externo Tier 2 (CEO + Gemini)

Findings documentados en `.context/PLAN-2026-05-14-tier2-ux-followers-ig.md` Sprint A. Highlights:
- Cards B11-B18 deben agruparse en 3 zonas: Autenticidad / Narrativa / Legal-Riesgo.
- Botón "Activar Filtro" del Reality Filter → switch global prominente.
- B14 grid rojo → leyenda explicativa.
- B17 veda activa → borde rojo intenso animado.

### Blockers nuevos registrados

- B-IG-DATACENTER-IP-1 (rojo · infra IG)
- B-OAUTH-YT-STATE-1 (amarillo · HMAC pendiente)
- B-VIOLENCIA-TAGS-1 (amarillo · NLP futuro)

### Próximo paso recomendado

1. Sprint C corto (~30 min): `vercel deploy --prod` desde frontend/ + validar `/dashboard/seguidores` con benjamin jimenez visible.
2. Sprint B (~2.5h): habilitar Instagram vía Brightdata proxy o Apify (camino más simple).
3. Sprint A (~3h): refactor visual Tier 2 con findings del review CEO/Gemini.

Detalle completo: `.context/PLAN-2026-05-14-tier2-ux-followers-ig.md`

---

## 2026-05-13 madrugada — Sprint Followers/OAuth/Audit Pipeline (CLOSED · `/sprint-review`)

---

## 2026-05-13 madrugada — Sprint Followers/OAuth/Audit Pipeline (CLOSED · `/sprint-review`)

`/sprint-review` autónomo sobre PLAN-2026-05-13-followers-oauth-pipeline.md.
FASES 1-5 ejecutadas; Gemini cross-audit OPCIONAL (no disparado, hook documentado).

### Sprints completados

| # | Sprint | Evidencia | Estado |
|---|--------|-----------|--------|
| S1 | Modelo `social_followers` + `follower_engagement` + migration `fol1_social_followers` | alembic up/down clean en container; imports OK | ✅ |
| S1b | Endpoint `GET /dirigentes/{id}/followers` paginado + filtros + RBAC scoped | 4/4 pytest verde (`tests/api/test_followers_endpoint.py`) | ✅ |
| S2 | OAuth YT real scaffold (`youtube_oauth_real.py`) + `.env.example` con toggle `OAUTH_YOUTUBE_ENABLED` | 7/7 pytest verde (`tests/services/test_youtube_oauth_real.py`) | ✅ (E2E gateado B-OAUTH-YT-GCP-1) |
| S3 | Scraper privilegiado `YouTubePrivilegedScraper` con UPSERT idempotente | 4/4 pytest verde (`tests/scrapers/test_youtube_privileged.py`) | ✅ (E2E gateado S2) |
| S4 | Vista `/dashboard/seguidores` + hook `useFollowers`/`useOAuthStatus` + empty states | tsc clean, `check-no-mocks` verde, dev server responde 307 → /login | ✅ |
| S5 | `audit_data_quality.py` (4 capas: coverage, referential, api-contract) + reporte | 433 findings (5 critical FE↔BE, 110 high-NULL, 0 huérfanos FK) en `.context/audits/data-quality-2026-05-13.md` | ✅ |
| S6 | Meta App Review → BLOCKER B-META-APPREVIEW-1 | entry en BLOCKERS.md | ✅ doc |

### Verificación E2E (este sprint, sin OAuth real)

- BD local migrada correctamente (`fol1_social_followers` en head)
- 19/19 pytests nuevos verdes (S1b + S2 + S3)
- Frontend tsc + check-no-mocks limpios
- Dev server `localhost:3005/dashboard/seguidores` responde con redirect a /login (auth funcional)
- Pipeline audit corre y detecta 5 endpoints CRITICAL FE↔BE (incluye onboarding mismatch real → B-ONBOARDING-FE-BE-MISMATCH-1)

### Decisiones autónomas (CEO dio luz verde · `Tienes luz verde para todo`)

Ver D-FOLLOWERS-1, D-OAUTH-YT-1, D-AUDIT-PIPELINE-1 en DECISIONS.md.

### Diferido a próxima sesión / BLOCKERS

- **B-OAUTH-YT-GCP-1**: CEO debe completar Google Cloud Console setup (~20 min).
- **B-OAUTH-YT-CRYPTO-1**: cifrar tokens con pgcrypto antes de primer is_stub=False (~1h).
- **B-FOLLOWERS-BOT-1**: hook a bot_detection diferido.
- **B-META-APPREVIEW-1**: IG/FB privilegiados gateados 4-6 sem.
- **B-ONBOARDING-FE-BE-MISMATCH-1**: 5 endpoints onboarding desalineados FE↔BE (auditor detectó).

### Próximo paso recomendado

1. CEO ejecuta GCP setup para destrabar S2 E2E (B-OAUTH-YT-GCP-1).
2. Sprint dedicado a corregir B-ONBOARDING-FE-BE-MISMATCH-1 (riesgo piloto).
3. Cifrar tokens (B-OAUTH-YT-CRYPTO-1) antes de aceptar primer OAuth real.
4. Commit + push branch + ping Carlos para deploy Coolify (NUEVA migration `fol1_social_followers`).

---

## 2026-05-12 noche — Sprint Pepe Monroy + Calendario Efemérides (CLOSED · 13 sub-sprints)

Sprint autónomo `/sprint-implement FULL`. 4 D-* nuevas + 4 B-* nuevas.

**Cerrado:**
- **G-1** snapshot cron 31 snapshots manuales (workaround a profile org_id=null preexistente).
- **G-3 / D-HUMANIZ-NEUTRO-1** B10 separa Neutro de Institucional. Jiménez sube 44.83 → 58.68 score.
- **Pepe Monroy / D-PEPE-MONROY-1** org PAZ + dirigente + user + IG/FB profiles + login validado en Vercel.
- **Calendario / D-CALENDARIO-1** modelo Efemeride + 70 fechas seed + endpoint proximas + endpoint sugerir-post (Claude API con fallback plantilla) + card frontend + modal + ruta /dashboard/calendario.
- **Doctrina D-COOLIFY-DOCTRINE-V2-1** Vercel staging · Coolify demo final · NO compartir BD.

**Verificación E2E:** Día del Maestro 15-may aparece en próximas con viralidad alta. Drafts diferenciados generados para Jiménez (Diputada) y Pepe (Líder Nacional). Login Pepe `pmonroy@paz.mx` / `demo2026!` → 200 + JWT.

**Diferido** (en BLOCKERS.md):
- B-CALENDARIO-PLANES-IA-1: integración a planes_ia mensuales
- B-CLAUDE-API-KEY-1: configurar key real para drafts no-plantilla
- B-FB-SCRAPER-1: chromedriver roto en container
- B-IG-SCRAPER-1: ensta+instaloader solo capturan metadata

**Cross-audit Gemini:** ejecutado al inicio. 5 hallazgos integrados, 1 invalidado.

**Próximo paso recomendado:**
1. Configurar `CLAUDE_API_KEY` en backend Mac Mini para drafts reales (cambia inmediato sin redeploy).
2. Push branch + ping Carlos para deploy Coolify.
3. Test visual CEO de `/dashboard/calendario` en Vercel.
4. Si OK: validar generación Día del Maestro con todos los dirigentes (manual).

---

## 2026-05-11 — Sprint narrativa política diagnóstico (CLOSED · 6 sprints)

`/sprint-implement` autónomo. Mandato CEO: simplificar lenguaje de las 10 cards del
Diagnóstico Tier 1 para audiencia política sin formación técnica, y guardar toda la
metodología en `/dashboard/sistema/metodologia` (sidebar → Configuración).

### Origen
- Review CEO 2026-05-11 sobre card B01: "los políticos no entienden Zenovo ni Nano X".
- Review /gemini (CLI) propuso 3 enfoques (Semáforo / War Room / Termómetro); CEO ratificó
  Opción 1 como base + Opción 2 para B04 + Opción 3 solo para crisis.
- Cross-audit /gemini plan del plan de implementación: GO con 3 ajustes (Popover en lugar
  de Tooltip, line-clamp en lugar de truncado char, diccionario defensivo B05).

### Sprints ejecutados

| # | Sprint | Estado |
|---|---|---|
| S1 | Anchors `#b01-#b10` en página metodología + sección B10 con acciones reubicadas | ✅ |
| S2 | CardShell pasa de Tooltip (hover) a Popover Radix (click/tap) con link a metodología | ✅ |
| S3 | Narrativas Gemini en B01, B02, B04, B05, B06, B07, B08, B09, B10 | ✅ |
| S4 | Signal warning B03 "Esfuerzo Sin Retorno" + B10 "Distante" (era ambiguo) | ✅ |
| S5 | Tip educativo B10 movido a metodología#b10 con lista accionable | ✅ |
| S6 | tsc verde · check-no-mocks verde · vercel deploy prod alias OK | ✅ |

### Cambios narrativos clave (B01-B10)

| Card | Antes | Después |
|---|---|---|
| B01 | "Tu interacción es 4.5x el promedio esperado para políticos con tu volumen de seguidores (Estrato Micro)" | "Generas 4.5 veces más interacción que otros políticos con tu mismo alcance" |
| B02 | "Nivel 3" (sin label) | "Creciendo · Nivel 3 de 6" |
| B04 | "#1 de 5 analizados" | "#1 entre tus 4 competidores directos" |
| B05 | Joy/Anticipation/Sadness/Fear (spanglish) + "X puntos de Confianza por cada punto de Enojo" | Alegría/Anticipación/Tristeza/Miedo + "La Confianza supera al Enojo X a 1" |
| B06 | "Se detectó un pico anómalo de N..." | "Alerta: N comentarios negativos inusuales en las últimas 2 horas" |
| B07 | "twitter #abc123" (ID interno expuesto) | "Post en Twitter · 8 abr" |
| B08 | "del total de menciones" | "de toda la conversación sobre 'X'" |
| B09 | "0.8 índice de difusión" | "8/10 Poder Viral" |
| B10 | "65/100 · Usar primera persona y emojis aumenta este puntaje" | "Tu audiencia te percibe como 'persona real'. Por encima del promedio institucional" (tip movido a metodología) |

### Diferido a sprint posterior (rediseños mayores)

- **B03** matriz 2x2 "Lo que funciona / Lo que te daña" (vs scatter actual).
- **B08** gauge en lugar de pie chart.
- **B07** excerpt real del post: requiere agregar `content_preview` al schema B07 backend.

### Decisión registrada

D-NARRATIVA-1 (.context/DECISIONS.md): metodología técnica vive en Configuración, cards
hablan lenguaje político. Link via icono ℹ️ Popover (no link text al pie · evita ruido
visual en 10 cards). Validado por Gemini cross-audit.

### Deploy

- Commit: `<pending git rev-parse>` (rama feat/phase-b-pesos-editables).
- Vercel project: `frontend` (corrección post-incidente proyecto equivocado 2026-05-11).
- Alias prod: `frontend-zeta-sepia-46.vercel.app` → deploy `frontend-59sl3jo8c`.

---

## 2026-05-09 — Sprint Editor HITL evaluación NLP (CLOSED · 9 sprints)

`/plan` armado tras feedback CEO. Editor para que actores políticos confirmen o
modifiquen las clasificaciones del sistema. Sin queue de approval — el dirigente
es la autoridad final sobre sus propios datos. Audit log inmutable alimenta
loop Claude+Gemini batch.

### Filosofía aplicada

```
SISTEMA PROPONE       →   DIRIGENTE CONFIRMA O MODIFICA
(runner Gemma +            (edit aplica directo,
 mapper v3 = nlp_*          audit log captura from→to,
 actual en BD)              recompute al edit)
```

### Sprints ejecutados (paralelizados con sub-agents)

| Wave | Sprint | Agente | Estado |
|---|---|---|---|
| 1 | S1 schema HITL + audit log | backend-architect | ✅ migration `dse_hitl_audit` aplicada |
| 1 | S6 batch review script Claude+Gemini | python-expert | ✅ 337 LOC, dry-run OK |
| 1 | S8 ground truth 100 rows seed=42 | python-expert | ✅ CSV regenerado en `evaluations/ground_truth/` |
| 2 | S2 endpoints HITL backend | backend-architect | ✅ 6 rutas, RBAC, 11/11 tests |
| 2 | S3 recompute helpers + mapper v3.0.1 | python-expert | ✅ 44/44 tests + passthrough vocab v2 |
| 3 | S4 frontend evaluador `/settings/evaluacion-nlp` | frontend-architect | ✅ 8 archivos, build limpio |
| 3 | S5 dual labels badges en dashboards | frontend-architect | ✅ ReviewStatusBadge integrado |
| 3 | S7 recompute global report | python-expert | ✅ 2696 comments procesados |
| 4 | S9 tests E2E | test-backend | ✅ 4/4 verde |
| 4 | S10 docs + STATUS + DECISIONS | Linda | ✅ este bloque |

### Hallazgos críticos para reunión 2026-05-10

**1. Roster real en BD (verificado 2026-05-09):**
- 4 MC oposición (Piña, Solano, Máynez, Ballesteros) — clientes del piloto
- 4 MORENA oficialismo (Pineda, Nolasco, Jiménez Godoy, Cravioto) — tracking comparativo
- Matriz con `rol='oficialismo'` SÍ aplica operativamente

**2. Posts sin clasificar:** 0 / 4817 con `tono_discurso` populated. La sección posts del editor estará vacía mañana hasta que se corra el clasificador LLM. Decisión CEO pendiente.

**3. Cobertura matriz comments:** 38 / 2696 = 1.4%. El 78% del corpus es `personal × autopromocion` (followers aplaudiendo) sin regla en matriz — by-design tras decisión CEO 2026-05-08 (rejected 3 reglas que abrían esa puerta).

**4. Corpus desigual:**
- Jiménez (oficialismo): 1054 comments NLP · Ballesteros: 784 · Piña: 406
- **Solano: 24 · Máynez: 0** ← corpus marginal/nulo

### Decisiones pendientes pre-reunión

| # | Pregunta | Opciones |
|---|---|---|
| Q1 | ¿Correr clasificador LLM sobre posts antes de mañana? | A: 400 posts (4 MC) ~30min · B: ocultar sección posts |
| Q2 | ¿Atender corpus de Solano (24) y Máynez (0)? | A: re-scrapear ~2h · B: aceptar limitación, foco en Piña+Ballesteros |

### Artefactos generados

- `backend/migrations/versions/dse_hitl_audit.py`
- `backend/app/models/hitl_audit.py`
- `backend/app/api/v1/endpoints/hitl_evaluation.py`
- `backend/app/services/score_recompute.py`
- `backend/app/nlp/matriz_v3_mapper.py` (bump v3.0.1, passthrough)
- `backend/scripts/hitl_review_batch.py`
- `backend/scripts/sample_ground_truth_100.py`
- `backend/scripts/recompute_global_report_2026_05_09.py`
- `backend/evaluations/ground_truth/2026-05-09-100rows.csv`
- `frontend/src/app/dashboard/settings/evaluacion-nlp/page.tsx`
- 7 componentes en `frontend/src/components/evaluacion/`
- `frontend/src/components/evaluacion/ReviewStatusBadge.tsx`
- `docs/HITL-EVALUACION-NLP.md`
- 4 suites de tests (29 tests verdes total: 11 endpoints + 10 score + 4 E2E + 4 mapper passthrough)

### Próximo paso

Esperar decisión CEO Q1 + Q2. Tras decisión:
- Si Q1=A: dispatch python-expert para clasificar 400 posts con runner Gemma
- Si Q2=A: dispatch para scraping Solano/Máynez
- Después commit final y demo browser con `solano@crece.mx` (smoke S9 visual)

---

## 2026-05-09 — Sprint NLP v3 mapper D+0 (CLOSED · 6 sprints)

`/sprint-implement` autónomo sobre decisiones CEO 2026-05-08 (mapper C +
ground truth 100 + UI dual B 7d).

### Hallazgo crítico inesperado en S1

Tabla `framework_matrix_defaults` **estaba VACÍA en BD**. Migration
`f7a8b9c0d1e2_political_framework.py` huérfana del chain alembic
(`down_revision='d5d6d7d8d9e0'` no existe). Consecuencia silenciosa:
`get_political_score()` retornaba **fallback 0 para todo comment desde el
deploy original**. Score Sentimiento Político Ajustado y KPI "Actividad
Política Alineada" computados contra base 0 — métricas distorsionadas
durante todo el piloto hasta hoy.

### Sprints ejecutados

| Sprint | Estado | Resultado |
|---|---|---|
| S1 · Schema recovery framework_matrix_defaults | ✅ | 4 tablas + 9 columnas creadas con SQL idempotente. Script `recover_framework_schema.py` |
| S2 · Seed matriz v2 (53 reglas) | ✅ | 32 post_dirigente + 21 comment_tercero pobladas |
| S3 · Implementar `matriz_v3_mapper.py` | ✅ | Mapper C con G1-G5 ajustes Gemini · 29/29 tests pasan |
| S4 · Smoke vs triangulación 2026-04-18 | ✅ | 60/60 mapeados · 0% fallback (vs G5 threshold 5%) · 73% acuerdo 3/3 tono |
| S5 · Reporte delta score político 500 comments | ✅ | **Hallazgo: 76% del corpus es `(personal, autopromocion)` sin regla en matriz v2** |
| S6 · Update STATUS + DECISIONS + commit | ✅ | Este bloque |

### Hallazgo S5 que cambia el plan D+1

500 comments sample con NLP populated:
- **17 / 500 (3.4%) matchean alguna regla v2** — score real computable
- **483 / 500 (96.6%) son misses** — combinación rol/tono/target sin regla

Top misses (combinaciones más frecuentes sin regla):
| rol | tono | target | count |
|---|---|---|---:|
| oposicion | personal | autopromocion | 214 |
| oficialismo | personal | autopromocion | 165 |
| oposicion | personal | gobierno | 35 |
| oposicion | personal | oposicion | 14 |

**Causa raíz:** `nlp_comments_batch_v2.py` (clasificador keyword v1) genera
mayoría de tono=`personal` (por defecto cuando no hay keyword fuerte) y
target=`autopromocion` (por defecto en comments de followers a posts del
dirigente). La matriz v2 fue diseñada para tonos más finos
(`celebratorio`, `critico`, `propositivo`, etc.) y NO tiene reglas para
`personal` con la mayoría de targets.

**Implicación:** el mapper v3 (que traduce vocab runner Gemma → v2) NO se
aplica a comments existentes — están etiquetados con `comment-framework-v1`,
no con runner Gemma. El mapper v3 servirá cuando alguien reactive el runner
Gemma. **El gap real es entre clasificador v1 (poco fino) y matriz v2
(diseñada para tonos finos del LLM).**

### Sub-pendientes nuevos descubiertos

- **F-NLP-1** (P1.A) Añadir ~10 reglas a matriz v2 para cubrir misses dominantes
  (`personal + {autopromocion, gobierno, oposicion, ciudadania}` × 3 roles).
  Sin esto, 96% del corpus no genera score. ROI alto, esfuerzo 1-2h.
- **F-NLP-2** Decidir si reactivar runner Gemma raw (más lento pero produce
  tonos más finos que v1 keyword). Decisión CEO post-piloto.
- **F-NLP-3** Recomputar `actividad_politica_alineada` sobre 2696 comments
  con scores reales nuevos. Esfuerzo 30 min, alto impacto en dashboards.

### Plan D+1 (mañana 2026-05-10)

Original: ground truth 100 rows + UI dual labels.
**Reordenado por hallazgo S5:**

1. F-NLP-1 cubrir misses (1-2h) — desbloquea scores reales del corpus existente
2. F-NLP-3 recomputar actividad alineada (30 min) — refleja en dashboard
3. Ground truth 100 rows (1h CEO o Linda)
4. UI dual labels opción B (1.5h)

### Archivos creados/modificados D+0

- `backend/app/nlp/matriz_v3_mapper.py` (nuevo, 230 LOC)
- `backend/tests/nlp/test_matriz_v3_mapper.py` (nuevo, 29 tests)
- `backend/scripts/recover_framework_schema.py` (nuevo, schema recovery)
- `backend/scripts/smoke_v3_mapper_triangulation.py` (nuevo)
- `backend/scripts/reporte_delta_score_politico.py` (nuevo)
- `backend/evaluations/2026-05-09-mapper-v3/SMOKE-MAPPER-2026-05-09.md`
- `backend/evaluations/2026-05-09-mapper-v3/REPORTE-DELTA-SCORE-2026-05-09.md`
- `.context/PLAN-2026-05-09-nlp-v3-mapper.md` (plan archivado)
- `.context/PLAN-current.md` → ACTIVE pointer

### Cross-audit Gemini (FASE 2)

`gemini-2.5-flash` ratificó plan original sin reordering. Sus 3 sugerencias:
- S1 timing: válido pero fallback definido — ✅ resuelto con SQL idempotente
- R3 puramente determinístico: ✅ confirmado, regex + boolean no LLM
- Test coverage mappings: ✅ 29 tests cubren todas las reglas

---

## 2026-05-08 — Sprint pendientes post /plan (CLOSED · 6 items)

CEO autorizó ejecutar pendientes consolidados. Items resueltos:

| # | Item | Resultado |
|---|---|---|
| P1.3 | Backup cleanup imagen pre-refactor | ✅ -19.4 GB liberados, imagen `pre-cleanup-2026-05-01` eliminada |
| E.5 | Demoscopía auditoría (11 rows) | ✅ Bug estructural confirmado: sitio cambió arquitectura. Federal recuperable parcial (+2 rows). Gubernatura = re-engineering pendiente E.5b (~3-4h, scraper flourish.studio embeds) |
| E.4 | PollsMX paginación histórica | ✅ DELEGADO a Juan (md-research) — confirmado en canal claude-peers, su carril 4 post-B1/B2/B3 |
| E.1 | AS/COA Approval Tracker | ✅ SKIP consensual con Juan: ROI bajo, federal CSP cubierto por Mitofsky+Oraculus |
| E.2 | Mitofsky 4 PDFs failed parse | ✅ `detect_pdf_period` ahora acepta fallback `post_date` del catalog para boletines pre-2023 sin año en portada. **+43 rows recuperadas** |
| E.3 | Mitofsky alcaldes individual 150 | ✅ State machine parser para layout fragmentado 3-líneas (nombre/pos+val/municipio,estado). **+2241 alcaldes individuales** |

**P1.2 TW cron + §5 decisiones CEO + E.5b** quedan abiertos (pendientes
elevación o slot dedicado).

### Métricas finales del corpus

| Snapshot | Rows |
|---|---:|
| Inicio sesión 2026-05-08 | 825 |
| Post Mitofsky gobernadores | 2085 |
| Post sprint-implement extendido (alcaldes+presidente+PollsMX) | 2254 |
| Post pendientes hoy | **4540** |

**Total agregado en sesión: +3715 rows (+450% sobre baseline).**

### Distribución final por fuente

```
Mitofsky                        3697  (alcaldes ind 2241 + gobernador 1234 + pres_estatal 100 + nacional 75 + alcaldes nac 35 + pres 12)
Oraculus poll-of-polls           748
El Financiero/tel                 24
PollsMX                           22
Enkoll                            14
Demoscopía Digital                13
Buendia y Marquez                 12
Parametria                         4
Demotecnia/viv                     4
Covarrubias y Asoc                 2
TOTAL                           4540
```

### Sub-pendientes documentados (no implementados)

- E.5b · Demoscopía gubernaturas via flourish embeds (~3-4h)
- P1.2 · TW replies cron schedule (bloqueado: decisión Celery vs cron)
- §5 · 3 decisiones CEO pendientes elevar (Índice Aceptación, NLP v3, +4 políticos)
- E.4 (parte que toma Juan) · PollsMX paginación histórica via Arc XP feed

---

## 2026-05-08 — Sprint extendido encuestas (CLOSED · `/sprint-implement` × 4)

CEO autorizó ejecutar los 4 pendientes post-Mitofsky-gobernadores. Resultado:

| Sprint | Estado | Resultado |
|---|---|---|
| SP1 · Mitofsky alcaldes (parser nuevo) | ✅ | +35 rows histórico nacional 150 alcaldes (2020-2026) |
| SP2 · Mitofsky presidente (parser nuevo) | ✅ | +112 rows (12 histórico + 100 ranking estados CSP) |
| SP3 · AS/COA Approval Tracker | ⏸ SKIP | Bloqueado SPA (D3 chart en JS bundle, sin JSON ni CSV). ROI bajo: CSP ya cubierto por Mitofsky+Oraculus. Documentado como gap conocido. |
| SP4 · PollsMX (artículos politico.mx) | ✅ | +22 rows (intención voto 2027, partidos + políticos extraídos via regex) |
| SP5 · Documentación comprehensiva | ✅ | `docs/SCRAPERS-ENCUESTAS.md` 9 secciones · 250+ líneas |

### Métricas finales del corpus encuestas

| Snapshot | Rows | Delta |
|---|---:|---|
| Inicio sesión 2026-05-08 | 825 | — |
| Post Mitofsky gobernadores | 2085 | +1260 (+153%) |
| Post SP1 alcaldes | 2120 | +35 |
| Post SP2 presidente | 2232 | +112 |
| Post SP4 PollsMX | **2254** | +22 |

**Total agregado: +1429 rows en sesión (+173% sobre baseline).**

### Distribución final por fuente

```
Mitofsky                  1413  (gobernadores 1191 + presidente_estatal 100 + nacional 75 + alcaldes 35 + presidente 12)
Oraculus poll-of-polls     748  (1995-2026)
El Financiero/tel           24
PollsMX                     22  (NUEVA fuente)
Enkoll                      14
Buendia y Marquez           12
Demoscopía Digital          11
Parametria                   4
Demotecnia/viv               4
Covarrubias y Asoc           2
TOTAL                     2254
```

### Archivos nuevos

**Scrapers:**
- `backend/app/scrapers/encuestas_mitofsky_pdf.py` — 3 parsers (gobernadores, alcaldes, presidente)
- `backend/app/scrapers/encuestas_pollsmx.py` — crawl + regex partido/político

**Orchestrators:**
- `backend/scripts/mitofsky_catalog_gdrive.py` — discover GDrive PDF links
- `backend/scripts/ingest_mitofsky_pdfs.py` — ingest con type dispatcher
- `backend/scripts/scrape_pollsmx.py` — orchestrator PollsMX

**Datos:**
- `captures/mitofsky-gdrive-catalog.json` — 127 entries · 105 con PDF link

**Docs:**
- `docs/SCRAPERS-ENCUESTAS.md` — fuente de verdad sobre el pipeline completo
  (schema, comandos canónicos, lecciones aprendidas, próximos pasos)

### Decisión obsoleta

`D-25-A` (vision stack Mitofsky LLM) quedó **OBSOLETA** antes de ejecutarse —
SP1 keystone reveló los PDFs de Google Drive. Cero LLM, cero vision, cero
costo cash. Documentación preservada como caso de estudio "validar fuente
primaria antes de comprometer infra".

### Próximos pasos (no implementados, documentados en SCRAPERS-ENCUESTAS.md §7)

1. AS/COA via Playwright (~3h, ROI bajo)
2. Mitofsky 4 PDFs failed parse layouts edge case (~2h, ROI bajo)
3. Mitofsky alcaldes individual 150 (~3-4h, ROI medio)
4. PollsMX paginación histórica (~3h, ROI medio)
5. Demoscopía auditoría — solo 11 rows parece bajo (~1-2h, ROI medio)

---

## 2026-05-08 — Sprint Mitofsky PDF pipeline (CLOSED · `/sprint-implement`)
[Bloque histórico — ver detalle abajo]
[ARCHIVADO]

## 2026-05-08 anterior — Mitofsky PDF pipeline cerrado · 2085 encuestas
**Sesion activa:** branch `feat/phase-b-pesos-editables` · PR #48 (sin merge)
**Branch activo:** `feat/phase-b-pesos-editables`
**Próxima ventana §9.8:** día 30 piloto ≈ 2026-05-20

---

## 2026-05-08 — Sprint Mitofsky PDF pipeline (CLOSED · `/sprint-implement`)

**Trigger:** CEO dijo "entramos a una página y descargamos los datos". Validación
empírica reveló que sí — el botón "DESCARGAR RANKING" en posts Wix Mitofsky
linkea a Google Drive con PDFs de 37 páginas, **texto seleccionable** parseable
con pdfplumber.

### Hallazgos S1 (keystone JSON inline check)

| Estructura | Resultado |
|---|---|
| Wix Stats "Excel export" | Solo copy promocional · 0 downloads reales |
| `<script type="application/json">` con datos políticos | 0 (solo SSR config Wix Thunderbolt) |
| **Botón "DESCARGAR RANKING" → Google Drive PDF** | ✅ **105 de 127 posts relevantes** |

### Implicación crítica sobre D-25-A (vision stack)

D-25-A autorizó modos A+B+C (todos vía Ollama Coolify) para extraer datos de
PNG charts. **Tras descubrir el flujo PDF, los 3 modos quedaron obsoletos**
para Mitofsky. Razón: Coolify es CPU-only (>17 min/iter histórico), modo C
hubiera saturado el VPS por semanas. El path PDF → pdfplumber:
- Cero LLM
- Cero vision
- Cero costo cash, cero VRAM
- Determinístico (precisión 99%+ vs 70-85% vision)
- Tiempo: ~5 segundos por PDF (download + parse)

### Sprints ejecutados

| Sprint | Status | Output |
|---|---|---|
| S1 · JSON inline check | ✅ | Hallazgo PDF GDrive (descrito arriba) |
| S2 · Catalog GDrive | ✅ | `captures/mitofsky-gdrive-catalog.json` · 105/127 PDFs |
| S3 · pdfplumber parser | ✅ | `app/scrapers/encuestas_mitofsky_pdf.py` · 2 formatos manejados |
| S4 · Smoke + insert + validate | ✅ | 1036 inserts · 1248 dedupes · 4 PDFs failed (91% éxito) |
| S5 · Reporte + docs | ✅ | Este bloque + DECISIONS D-25-A actualizado |

### Resultado final

| Métrica | Antes sprint | Después sprint | Delta |
|---|---|---|---|
| Total encuestas_publicas | 825 | **2085** | **+1260 (+153%)** |
| Filas Mitofsky | 6 | 1266 | +1260 |
| Histórico nacional gobernadores | 0 | 75 (2020-01 → 2026-03) | +75 |
| Meses únicos con ranking estatal | 0 | 40 (2022-10 → 2026-03) | +40 |

### Archivos creados/modificados

- `backend/app/scrapers/encuestas_mitofsky_pdf.py` (nuevo, 250 LOC) · pdfplumber parser
- `backend/scripts/mitofsky_catalog_gdrive.py` (nuevo, 130 LOC) · BS4 catalog GDrive
- `backend/scripts/ingest_mitofsky_pdfs.py` (nuevo, 145 LOC) · async orchestrator
- `captures/mitofsky-gdrive-catalog.json` (nuevo) · 127 entries
- `.context/DECISIONS.md` · D-25-A actualizado con findings post-implementación
- `.context/PLAN-2026-05-08-mitofsky-narrativa.md` (nuevo) · plan archivado
- `.context/PLAN-current.md` → ACTIVE pointer

### Cross-audit Gemini (FASE 2)

`gemini-2.5-flash` validó plan original sin cambios al orden. Sus 3 mejoras
sugeridas:
1. Spot-check manual de URLs PNG en S2 — N/A tras pivot a PDFs
2. Pre-validation extendida del LLM antes de S3 — N/A tras pivot a PDFs
3. Normalización actor names en S4 — implementada via tabla `ESTADO_MAP`

Las 3 sugerencias se volvieron irrelevantes cuando S1 reveló el flujo PDF
determinístico — el plan se ejecutó sin LLM ni OCR ni vision.

### 4 PDFs fallidos (no críticos)

`1kgQRf5w...`, `17eBP76xx...`, `1OrVQvZl...`, `101JVhrf...` — extracción
0 rows. Posibles causas: estructura distinta a 2 formatos manejados (pre-2023
boletines), PDF scanneado, layout degenerado. **No bloquean cierre del sprint:**
los PDFs siguientes/anteriores cubren los meses por dedupe automático del
histórico nacional.

### Coordinación peer · estado al cierre

- **Linda (esta sesión):** Mitofsky cerrado. PollsMX y AS/COA todavía sin
  scraper (decisión: redirigir a Juan post-Tributo Huasteco como originalmente
  acordado, o ejecutar Linda directo si Juan no se libera).
- **Juan (md-research, peer i27fjncq):** ack mi hallazgo PDF, libera contexto
  Mitofsky, continúa Tributo Huasteco. PollsMX y AS/COA siguen en su cola.
- **Joy (CRECE-Negocios, peer 3t5flofn):** turf separado, fin de coordinación
  cross-turf por hoy.

### Próximo paso recomendado

(decisión CEO) — opciones de mayor a menor ROI:

1. **Cerrar encuestas aquí** (2085 rows, 9 fuentes, 6 años histórico nacional
   + 40 meses ranking estatal). Pasar a otra área del piloto.
2. **PollsMX scraper** (Linda · ~2-3h) — añade gubernaturas 2027 + 9 estados.
3. **Mitofsky alcaldes + presidente PDFs** (Linda · ~1-2h) — extender parser a
   los otros 2 formatos del catalog (~50 PDFs adicionales no procesados).
4. **AS/COA Approval Tracker** (Linda · ~2h) — federal nice-to-have.

---

## 2026-05-08 — TW replies `--all` ejecutado + encuestas pobladas (DONE)

**Inserts esta sesión:**
- TW replies (twscrape): **+668 nuevos** → total 701 (`data_source='twscrape-replies-v1'`)
  - @LBallesterosM 402 · @GabyJimenezMX 241 · @craviotocesar 12 · @Yes_Nolasco 11 · @alejandro.pinha 1 · @saymipinedav 1
- NLP Layer 1: **2696/2696 clasificados** (0 pending) — ejecutado contra los TW replies recién insertados
- Encuestas: **825 totales** desde 9 fuentes
  - Oraculus poll-of-polls 748 (active CSP + historical)
  - El Financiero/tel 24 · Enkoll 14 · Buendía y Márquez 12 · Demoscopía Digital 11
  - Mitofsky 6 · Parametría 4 · Demotecnia/viv 4 · Covarrubias 2

**Mitofsky PDF parser: NO existe.** El CEO tenía PDFs en OneDrive pero ningún script
en repo o `_archive/` los procesaba — confirmado tras búsqueda exhaustiva (commit
history, repo, archive, Obsidian). El path forward para sumar Mitofsky histórico
es manual (convert PDF→Excel → restaurar `encuestas_mitosky.py` que sí estaba en
0681153) o construir parser nuevo (~2-3h dev). Decisión CEO pendiente.

**Demoscopía 24m extendido:** 0 nuevos (48 dedupes — datos históricos ya capturados).

**Sources adicionales no exploradas (decisión CEO):**
- Parametría scraper nuevo (~2h dev) — su sitio publica histórico mensual
- AS/COA Approval Tracker — agregador externo, ~50 puntos extra
- Mitofsky PDF→Excel manual (1 archivo en OneDrive del CEO)

### Handshake Linda ↔ Juan ↔ CEO — ScrapeGraph-AI + Vision Stack

**2026-05-08 05:15-05:35 UTC** — coordinación cerrada con decisiones registradas.

**Identidades fijadas (D-25-A):** Linda (uji6x64w, esta sesión, CRECE-electoral) ·
Joy (3t5flofn, CRECE-Negocios B2B, sesión paralela) · Juan (i27fjncq, md-research).

**Research empírico Mitofsky (Linda 2026-05-08):** 0% posts Wix tienen download
Excel/CSV. 100% datos detallados (32 estados) viven en PNG charts. Texto narrativo
solo cubre top-N + agregados (~3-5 datapoints/post).

**Decisión vision stack (CEO 2026-05-08, ver DECISIONS.md D-25-A):**
- ✅ **A** texto narrativo gemma3:12b · Linda · arranca ya
- ✅ **B** OCR tesseract + gemma3:12b · Juan+Linda · fallback si C inviable
- ✅ **C** vision LLM en Ollama Coolify (`llava:13b` o `qwen2-vl:7b`) · Juan deploy + Linda consume · cuando Juan valide VRAM
- ❌ **D** vision API pago — fuera por directiva CEO

**Plan operativo:**
1. **Mitofsky** — Linda arranca modo A AHORA (independiente del Ollama nocturno).
   Juan a las 23:45 hace su Mitofsky bridge + guarda URLs PNG charts (no los social
   icons w_28, sí los `~mv2.png` con tablas). Modo C llega cuando Juan deploye vision.
2. **PollsMX + AS/COA** — Juan los hace post-Tributo Huasteco con SG-AI + gemma3:12b
   texto. Output drop `md-research/captures/encuestas-polit-mx/<fuente>/`.
3. Linda consume todos los outputs, normaliza, dedupe contra 825 existentes, inserta.

Sin tocar SCRAPING del lado CRECE hasta que llegue cada output. Modo A sí lo
arranca Linda ya con la narrativa de posts (sin SG-AI, BS4 directo + LLM Coolify).

---

## 2026-05-08 — Sprint TW replies via twscrape (CLOSED)

**Branch:** `feat/phase-b-pesos-editables` · script: `backend/scripts/twscrape_tw_replies.py`

### Root cause del hang 45s en `api.search(conversation_id:X)`

twscrape 0.17.0 tiene bug NO parcheado upstream:
`XClIdGen.create()` parsea `https://x.com/tesla` con split hardcoded
`'e=>e+"."+'` (ver `twscrape/xclid.py:50`). X removió ese pattern del bundle JS,
así que `parse_anim_idx()` lanza `IndexError: list index out of range`. El
`queue_client.req()` atrapa Exception genérica y bloquea la cuenta 15min sin
diagnóstico — de ahí el silencio total + cuelgue de 45s observado.

Issue upstream: `vladkens/twscrape#248`. Sin release nuevo desde 0.17.0.
Aclaración importante: el flujo previo de TW replies del CEO NO usaba twscrape
— era ingest manual JSON capturado vía chrome-devtools. `twscrape_profile.py`
en archive solo trae posts (timeline), no replies. **No hubo flujo automático
previo** — este sprint lo introduce por primera vez.

### Workaround validado

Monkey-patch `queue_client.XClIdGenStore.get` → stub que emite
`x-client-transaction-id: ''`. X sigue sirviendo TweetDetail/TweetReplies
GraphQL sin el header firmado (validado contra tweet `2041574638082240765`
de Ballesteros, 12/12 replies recuperados). Comparado contra `replyCount`
metadata: match exacto.

### Smoke + dry-run results

| Dirigente | Tweets w/ replies (30d) | Replies fetched (dry-run) | Errors |
|---|---|---|---|
| 1 Piña | 1 | n/a (pendiente run) | — |
| 3 Pineda | 3 | n/a | — |
| 4 Nolasco | 13 | n/a | — |
| 5 Jiménez Godoy | 28 | n/a | — |
| 6 Cravioto | 4 | n/a | — |
| 8 Ballesteros | 55 (incluye uno persistido en smoke) | **395** | 0 |

Ballesteros tweet `2041574638082240765` insertado live: 12 replies vía
`twscrape-replies-v1`. Verificado en `social_comments`. Pool: 1 cuenta activa
(`rafaramos72`), suficiente para piloto. `crece_scraper` inactiva — no hace
falta segundo login.

### Pendiente (no hecho en este sprint, decisión CEO)

1. Run completo `--all` → poblar replies para los 7 dirigentes piloto
   (~99 tweets totales × ~7 replies promedio = ~700 inserts esperados, ~3 min).
2. Programación recurrente — propuesta:
   - **Opción A (Celery beat)**: nueva task en `backend/app/workers/celery_app.py`
     `crontab(minute=15, hour='*/6')` → 4 corridas/día. Reusa Redis ya en stack.
     Pro: integra con monitoring existente. Con: requiere ampliar worker image.
   - **Opción B (cron host)**: entry en crontab del Mac mini
     `*/6 * * * * docker exec crece-backend python /app/scripts/twscrape_tw_replies.py --all`.
     Pro: cero cambios infra. Con: dependiente del Mac local, sin retry.
   - **Recomendación:** Opción A para piloto (visibilidad en logs Celery, retry
     gratis). Opción B solo si urgencia hoy. Decisión CEO pendiente.
3. Si twscrape upstream parchea #248, eliminar workaround (comentario inline en
   el script anota la línea exacta a quitar).

---

## 2026-05-07 — Arqueología scripts perdidos + restauración + cierre NLP sprint

Tras refresh Apify se hizo arqueología en git history descubriendo múltiples
scripts útiles eliminados en cleanups anteriores. Restaurados los activos,
archivados los referenciables, eliminados los obsoletos.

### Restaurado activo (carpeta original)

- `app/scrapers/encuestas_oraculus.py` (commit `0681153`, 200 lines) — Oraculus scraper
- `app/scrapers/encuestas_demoscopia.py` (commit `821950b`, 381 lines) — Demoscopía
- `app/scrapers/encuestas_mitosky.py` (commit `821950b`, 236 lines) — Mitofsky (procesa Excel)
- `scripts/scrape_encuestas.py` (commit `0681153`, 43 lines) — orchestrator
- `scripts/nlp_comments_gemma_layer2.py` (commit `b79fab5`, 197 lines) — Layer 2 refinamiento
- `scripts/scraperapi_tiktok_comments.py` (commit `2660807`) — TT comments via API interna proxyeada [ya integrado al refresh en commit `0611313`]

### Archivado en `backend/scripts/_archive/` con README

- `brightdata_browser_service.py` + 5 scripts brightdata_* + `recover_brightdata.py` — Brightdata customer suspendido, código vivo si reactivamos saldo
- `twscrape_profile.py` — alternativa a Apify TW (referencia para sprint TW replies background)
- `benchmark_gemma_layer2.py` — bench Gemma futuro
- `ingest_laura_twitter_replies.py` — ingester JSON manual del flujo devtools del CEO

### NO restaurado, queda en git history (recuperable con `git show`)

- `seed_comments.py`, `fase1_backfills.py`, `import_resultados_2024.py`, `export_calibration_samples.py` — one-shots completados

### Encuestas pobladas vía scrapers restaurados

- **Oraculus** (`scrape_encuestas.py --source oraculus`): 84 filas insertadas (poll-of-polls que ya incluye 9 fuentes diferentes — Buendia, Enkoll, El Financiero, Mitofsky, Parametría, Covarrubias, Demotecnia, etc.)
- **Demoscopía** (loop manual 6 meses × 3 targets): 12 rows scraped, 2 nuevas insertadas, 10 dedupe (ya existían)
- **Mitofsky standalone**: scraper espera `.xlsx` local; CEO solo tiene PDFs en OneDrive. Data Mitofsky-Oaxaca (6 rows) ya entra vía Oraculus aggregate.
- BD final: ~115 rows en `encuestas_publicas`, 9 fuentes, cobertura federal + CDMX + Oaxaca, periodo 2024-10 a 2026-04.
- **Schema drift fix:** `tamaño_muestra` (con ñ) → `tamanyo_muestra` (ASCII) en INSERT del scraper Oraculus tras migration `3d6fe3f1660d` (commit `3b6b430`).

### Cierre del ciclo refresh: NLP Layer 1 ejecutado

- `scripts/nlp_comments_batch.py` (v1, sin dependencia de tabla `framework_matrix_defaults` rota)
- 974 comments procesados (746 nuevos del refresh + 228 backlog)
- `nlp_model_version='comment-framework-v1'` en todos
- Resultado en `/aceptacion/fantasmas-por-plataforma`: Jiménez TT 0 → 77 commenters, IG +67, FB +24

### Deuda pendiente (documentada, no bloqueante)

- **Tabla `framework_matrix_defaults` perdida en BD pese a estar en migration `3d6fe3f1660d`.** El v2 del NLP (`nlp_comments_batch_v2.py`) la requiere y queda inservible hasta que se recree. Workaround: usar v1 que no depende. Decisión futura: re-aplicar migration o documentar como deuda definitiva.
- **TW replies via twscrape**: cuenta `rafaramos72` activa en pool (last_used 2026-05-08). Plantear sprint dedicado para correr replies en background reemplazando flujo manual devtools del CEO.

---

## 2026-05-07 — Apify refresh 7 dirigentes (posts + comments)

Ejecutado `scripts/apify_refresh_all.py` plan `.context/PLAN-2026-05-07-apify-refresh.md`.

### Resumen del run

- **Costo Apify total**: $3.91 / $4.50 cap · headroom $0.59 · ciclo cierra 2026-05-23
- **Scrapers locales recuperados (commit `1b713b5`)**: TT/YT yt-dlp path + chromium executable_path tras refactor multi-stage
- **Credenciales Instagram cargadas en `.env` root** (CEO 2026-05-07): `soporte@consultoriamd.com.mx` permite instaloader fallback
- **Profile TT Ballesteros agregado**: `lauraballesterosmx` faltaba en `social_profiles` aunque la cuenta existe en TT
- **Handle FB Solano corregido**: `rafaelsolanoperez` → `RafaSolanoPerez` (BD UPDATE aplicado)

### Datos nuevos en BD (data_source='apify-refresh-2026-05-07')

| Dirigente | TW | IG | FB | TT | YT |
|---|---|---|---|---|---|
| Piña | 8/0 | 15/31 | 10/27 | **0/0** ⚠️ | 0/0 |
| Solano | 15/0 | 2/0 | 2/0 | 0/0 | — |
| Pineda | 30/0 | 30/10 | 10/11 | **30/80** ✅ | 0/0 |
| Nolasco | 30/0 | 30/12 | 10/37 | 6/25 | — |
| Jiménez | 30/0 | 27/108 | 10/47 | **30/118** ✅ | — |
| Cravioto | 4/0 | 30/24 | 10/4 | 26/48 | 0/0 |
| Ballesteros | 52/0 | 27/87 | 10/21 | **27/52** ✅ | 7/4 |
| **TOTAL** | **169** | **161** | **62** | **146** | **7** |
| **comments** | 0 (manual TW) | 269 | 147 | 326 | 4 |

Total: **545 posts nuevos, 746 comments nuevos** en una sola pasada orquestada.

### Actores Apify usados (con run_id histórico de Ballesteros 2026-04-18 como referencia)

| Plataforma | Actor | Pricing FREE |
|---|---|---|
| TW | `delicious_zebu/advanced-x-twitter-profile-scraper` | $0.0008/item |
| IG | `apify/instagram-post-scraper` (trae `latestComments` inline) | $0.0017/post |
| FB posts | `apify/facebook-posts-scraper` | $0.005/post |
| FB comments | `apify/facebook-comments-scraper` | $0.0025/comment |
| TT | `clockworks/tiktok-scraper` con `commentsPerPost=5` (comments en dataset auxiliar) | mixto |
| YT | `streamers/youtube-scraper` | $0.004/result |
| YT comments | yt-dlp local (`/install/bin/yt-dlp`) | $0 |

TW replies se siguen manejando via flujo manual del CEO (`chrome-devtools-tweet-detail-v1` / `playwright-x-cookies-v1`), no Apify.

### Observaciones / debt residual

1. **Piña TT cuenta inactiva**: handle `alejandro.pinha` correcto (verificado contra URL `tiktok.com/@alejandro.pinha`). El actor `clockworks/tiktok-scraper` SÍ encontró la cuenta y trajo 30 videos en run kTB05wrLgdN73mh39 ($0.18). Pero el más reciente es de **2025-05-08** — un año sin postear. Por eso 0 entraron en ventana 30d.
2. **Solano TT cuenta inactiva**: handle `rafasolanoperez` correcto. Run KGKIsf9cMD9m9RB78 ($0.13) trajo videos pero el más reciente es de **2025-11-04** (6 meses). Solano IG/FB con solo 2 posts cada uno — cuenta probablemente activa pero baja frecuencia.
3. **YouTube**: solo Cravioto y Ballesteros trajeron videos en ventana 30d. Piña último upload YT 2015, Pineda 2023 — cuentas inactivas, no es bug del actor.
4. **NLP pendiente**: 746 comments nuevos con `nlp_model_version IS NULL`. El endpoint `/aceptacion/fantasmas-por-plataforma` filtra por NLP procesado, por eso TT muestra 0 commenters hasta que el worker `nlp_comments_batch_v2.py` los procese.
5. **Bug FB comments parent matching**: el run inicial Sprint 1 (Ballesteros) insertó 0 comments FB porque el matching usaba `commentUrl` en vez de `inputUrl`. Fix aplicado en el script (mismo commit) y reproceso del dataset cacheado recuperó los 20 comments sin gastar Apify de nuevo.
6. **Bug TT comments parent matching**: el dataset auxiliar `commentsDatasetUrl` no se descargaba. Fix aplicado: ahora descarga el dataset auxiliar y matchea por `videoWebUrl`. Reproceso de Ballesteros recuperó 51 comments sin re-correr.

---

## 2026-05-01 — Cleanup disco + Apify FB validado

### Refactor multi-stage Docker (✅ commit `b94db2e`)

Liberado **34.1GB** (de 51.7GB images → 18.06GB). Disco libre 23GB → **45GB**.

**Cambios:**
- `backend/pyproject.toml` · split `[nlp]` → `[nlp-light]` (spaCy, backend) y `[nlp-heavy]` (full stack: torch+transformers+pysentimiento, worker)
- `backend/Dockerfile` · BuildKit cache mounts (pip + apt) · removed `playwright install chromium` duplicate (usamos system chromium vía `executable_path=$CHROME_BIN`)
- `backend/Dockerfile.worker` · BuildKit cache mounts
- `backend/.dockerignore` · exclusiones `.cache/`, `.local/`, `data/raw/`, `*.db`, `evaluations/`, `eval/`, etc.
- `backend/app/scrapers/facebook.py` · agregado `executable_path=$CHROME_BIN` a `chromium.launch()` líneas ~170 y ~471

**Sizes nuevas:** backend 3.33GB · celery-worker 11.4GB · celery-beat 3.33GB.

**Cosmetic fix (mismo commit):** `docker-compose.yml` · override healthcheck de `celery-beat` (heredaba curl :8000 del backend Dockerfile, beat NO es servidor HTTP) → ahora `pgrep -f 'celery.*beat'`.

**Cross-audit con `/gemini`** previo a ejecución · Gemini detectó 2 riesgos críticos (Playwright `executable_path` debe ir ANTES de remover `playwright install`, y bind mount `./backend:/app` significa borrado local rompe container) · ambos integrados al plan.

### Working tree cleanup (✅ commits `874b6f0`, `53c8755`, `aa52945`)

200+ archivos dirty (sweep ruff Phase B + audits + screenshots). Cleanup en 3 lotes:
- Tier 1-3 commit `874b6f0` · `.gitignore` ampliado (`frontend/test-results/`, `*.db-shm`, `*.db-wal`, `Portafolio_*.csv`, `task_plan.md`, `backend/data/reportes_plan_ia/`, `backend/scripts/data/`)
- Tier 4 commit `53c8755` · 6 items que CEO exigió no perder (audits, scripts, docs)
- Tier 5 commit `aa52945` · junk validado (task_plan.md, .pyc orphan)

### Backup pendiente borrado · 2026-05-03

Imagen `crece-v2-backend:pre-cleanup-2026-05-01` (19.4GB) preservada como red de seguridad rollback.
- Procedimiento validación 3 puntos en `.context/REMINDER-2026-05-03-cleanup-backend-backup.md`
- Memory persistente: `~/.claude/projects/.../memory/project_disk_cleanup_pending.md`
- Si los 3 checks pasan → borrar = recupera +19.4GB extra (total cleanup -53.5GB)

### Apify FB scraper validado (✅)

Token APIFY refrescado en `.env.scraping-keys`. Actor `apify/facebook-posts-scraper` corrido manualmente vs `Gaby Jiménez Go` retorna posts con engagement completo (likes, comments, shares).

**Pendiente Sprint FB:** scrape de 8 dirigentes (originalmente 2026-04-30, slipped por cleanup).

### Pendientes próxima sesión

- **A)** FB scrape 8 dirigentes vía Apify · ingest manual con `backend/scripts/ingest_apify_fb.py`
- **B)** 2026-05-03 validación 3 puntos + borrado backup 19.4GB (cron + memory + reminder file)
- **C)** 3 decisiones CEO diferidas (matriz v3 / golden humano / UI labels)

### Infra status

- LaunchAgent auto-resume Docker post-Mac-sleep · activo
- Tunnel Ollama Coolify (`http://163.245.208.96:11434`) · activo (PR #48)
- Beat healthcheck cosmetic · ✅ resuelto

---

## 2026-04-26 — sprint-implement Fase 0 (✅) + Fase 1 (parcial)

**Plan vigente:** `.context/PLAN-2026-04-25-post-audits.md` (5 fases · 17 sprints)
**Decisiones CEO:** D-23-I/J/K/L registradas en `DECISIONS.md`

### Fase 0 · Captura ✅ COMPLETA

5 commits agregados al branch:
- `a301f55` fix(security) · org_id + rate limit 5/h + Veda + Sentry PII (H-01, H-06, C-01, C-02)
- `1ba0f8b` chore(ops) · Ollama Coolify migration (streaming + keep_alive 30m + timeout 1h)
- `56d6f4b` chore(deps) · Next.js 14.2.21 → ^14.2.35 (CVE Authorization Bypass CVSS 9.1)
- `fd73c71` docs(.context) · plan post-audits + decisiones D-23-I/J/K/L + BLOCKERS B-23-06/07
- `3928af2` docs(.context) · 7 audits 2026-04-25 + screenshots a11y

PR #48 actualizado · scope ampliado a "Phase B (D-23-H) + hardening AUDIT 2026-04-25" · branch pushed.

### Fase 1 · Demo blockers (parcial)

| Sprint | Estado |
|---|---|
| 1.1 Diagnóstico Máynez | ⏭️ skipped · D-23-I = B (Máynez fuera del demo) |
| 1.2 Refrescar scrapers Piña + Ballesteros | ✅ MAYORÍA · 156 nuevos posts |
| 1.3 Plan IA Ballesteros smoke real | ⏳ EN CURSO · task `bf41a412` Coolify CPU |
| 1.4 Decisión Máynez | ✅ D-23-I cerrada |

**Sprint 1.2 resultados (4:59 UTC):**
- Ballesteros TW: +99 posts · last `2026-04-25 22:43` ✅
- Ballesteros IG: +50 posts · last `2026-04-25 18:11` ✅
- Ballesteros YT: 0 nuevos (scrapetube vio 30, todos ya en BD)
- Ballesteros FB: ⚠️ scraping con retries (curl-cffi)
- Piña TW: +2 posts · last `2026-04-16` (TW limit_reached=True)
- Piña IG: +5 posts · last `2026-04-25 00:48` ✅
- Piña FB: ⚠️ pendiente
- Piña TT: 0 · ⚠️ TikTokApi `BrowserType.launch` failed (Playwright no instalado en container)
- Piña YT: 0 · ⚠️ `yt-dlp binary not found at /usr/local/bin/yt-dlp` en container

**B-23-07 cerrado:** último `published_at` = `2026-04-25 22:43` (hace 6h vs 7d antes). Hero KPI dejará de estar vacío.

### Hallazgos durante ejecución

1. **BUG · `get_scraper(platform)` lowercase mismatch** — registry usa lowercase, `Platform.value` retorna uppercase. `scrape_all_profiles()` también está afectado (pasa `profile.platform.value`). 9 tasks fallaron antes de re-dispatch con lowercase.
2. **BUG · yt-dlp + Playwright no instalados en container** — YouTube y TikTok scrapers no funcionan dentro de Docker. Documentado en `data_source = MANUAL_HOST_INGEST` para esas plataformas (host-side).
3. **Old retrying tasks** · 9 tasks dispatched con uppercase entraron en RETRY backoff 120s · revoked + replaced con lowercase. Pueden seguir retrying hasta `max_retries=3` ≈ 6 min.

### Sprint 1.3 cierre · ❌ FALLIDO

Plan IA Ballesteros vía Coolify CPU **timeout** en `SoftTimeLimitExceeded` 540s (9 min).
- Task `bf41a412` · prompt 13438 chars · NO terminó la generación
- Sin row nueva en `planes_ia` post-`04:57` (latest sigue siendo `id=20` del `01:54`)
- Issue documentado como **B-26-01 · DEMO BLOCKER** en BLOCKERS.md
- 5 opciones planteadas para CEO (revertir Mac local vs gemma3:4b vs comprimir prompt vs subir time_limit vs híbrido)

**Fase 2** — pendiente luz verde CEO antes de arrancar. Incluye:
- Sprint 2.1 · A-02 ARCO endpoint auth (~1.5h)
- Sprint 2.2 · A-01 trusted_hosts fix (~30 min)
- Sprint 2.3 · A-04 JWT refresh **con red de seguridad** (~4-5h · feature flag + E2E + 24h staging)
- Sprint 2.4 · H-07 Ollama firewall (CEO directo)

---



---

## 2026-04-25 — D-23-G' Actividad Política Alineada (3 días ejecutados)

**Plan:** `.context/PLAN-D-23-G-actividad-alineada-2026-04-24.md` (vigente)
**Cross-audit:** Gemini aprobado-con-ajustes (golden set 60, regla desempate, fallback `no_determinado`)
**Code-reviewer:** subagent independiente · ✅ APROBADA CON OBSERVACIONES (3 ya cubiertas)

### Reframe del KPI (cambio fundamental)

Antes intentábamos arreglar el flip × -1 sobre score crudo. Ahora reformulamos el KPI a **proporción de actividad alineada a rol**:

| Rol | Fórmula |
|-----|---------|
| Oposición | `(target=oficialismo + target=propio) / total_clasificado` |
| Oficialismo | `(target=propio + target=oposicion) / total_clasificado` |
| Independiente | `target=propio / total_clasificado` |

Sin flip · sin score numérico · solo conteo de actividad por `target_politico` ∈ `{oficialismo, oposicion, propio, personal, no_determinado}`.

### Day 1 ✅ Migración hand-written aplicada

`d23g1_actividad_alineada.py` (head actual). 4 columnas core, 1 partial index, 3 CHECK constraints. D-OPS-08/09/10 cumplidos.

- `social_posts.target_politico` VARCHAR(32) NULL
- `social_posts.nlp_model_version` VARCHAR(64) NULL
- `social_posts.clasificacion_origen` VARCHAR(32) NOT NULL DEFAULT 'ai_suggested'
- `dirigentes.rol_politico` VARCHAR(32) NULL
- `ix_social_posts_profile_target_politico` partial index

Models actualizados (`app/models/social.py` y `dirigente.py`). `dirigentes.rol_politico` poblado por mapping partido→rol (8/8 dirigentes).

### Day 2 ✅ Clasificador IA + golden set generado

- `app/nlp/target_politico_prompt.py` con 4-cat + `no_determinado` fallback + regla desempate "prioriza propio si hay CTA"
- `scripts/classify_target_politico.py` idempotente · `WHERE target_politico IS NULL OR nlp_model_version != 'crece-political-v1'` · dry-run · per-dirigente · golden-set mode
- Smoke test 3 posts Ballesteros: `propio`, `oficialismo`, `propio` (correctos · 121s total)
- Golden set 60 posts generado a `.context/golden-set-target-politico-2026-04-24.json` · pendiente CEO marca `target_human` por post para validación F1

### Day 3 ✅ Backend service + Frontend KPI

- `app/services/actividad_alineada.py` · función `compute_actividad_alineada(db, dirigente, days=7)`
- Endpoint `/api/v1/dirigentes/{id}` enriquecido con campo `stats.actividad_alineada`
- Frontend tipos: `ActividadAlineada` + `ActividadAlineadaBreakdown` en `lib/api/types.ts`
- `components/dashboard/actividad-alineada-card.tsx` · KPI hero con breakdown 4-cat barras apiladas
- Ficha dirigente reemplaza "Sentimiento Prom." (flipeado) → `ActividadAlineadaCard`
- `lib/politica/sentiment.ts` marcado **@deprecated** · NO se elimina del bundle (decisión CEO 2026-04-25 · preservar lógica reversible)
- TypeScript clean · API smoke OK (Ballesteros responde con `empty_state: 'no_classified'` correctamente)

### Day 4 🔄 Backfill en curso

- Ballesteros backfill 40 posts arrancó en background (PID en bash log) · ETA ~22-27 min
- Pendiente: Piña (61 posts 30d) + Máynez (5 posts total) + 5 shadow (Solano, Pineda, Nolasco, Jiménez, Cravioto)
- Validación visual post-backfill: KPI debe mostrar % no-vacío para Ballesteros tras completar
- Cierre B-23-03 + DECISIONS D-23-H pendiente al cerrar Day 4

---

---

## 2026-04-23 — Sprint 23 · post-review CEO (11 screenshots)

**Workflow:** `/sprint-review` + `/sprint-implement` con cross-audit Gemini.
**Diagnóstico:** 11 findings F-23-01..F-23-11 en `.context/frontend-review-2026-04-23/DIAGNOSTICO-SCREEN-CRECE.md`.
**Plan revisado:** `PLAN-current.md` (copia de `frontend-review-2026-04-23/PLAN-REVISADO.md`).
**Gemini audit:** `GEMINI-AUDIT.md` (3 reclasificaciones, 2 gaps, 2 optimizaciones, 2 riesgos no vistos).

### Commits en `hotfix/23a-ui-puros` (ahead of main)

| SHA corto | Scope | Findings cubiertos |
|---|---|---|
| `787c1be` | docs(.context) · diagnóstico + plan + Gemini audit | base documental |
| 23-A | fix(frontend) · UI hotfixes | F-23-02, F-23-05 UI, F-23-07, F-23-08, F-23-09 parcial |
| 23-B | fix(backend,frontend) · compose URL + platform/RT filters | F-23-05 datos P1, F-23-03, F-23-04 |
| 23-D | fix(frontend) · copy rewrite titles + context | F-23-10, F-23-11 parcial |

### Findings status

| # | Estado | Nota |
|---|---|---|
| F-23-01 Tema Urgente sin afiliación | 🔴 §9.8 pendiente | Framework 3 capas existe; no conectado a KPI |
| F-23-02 Competitor hardcoded Piña | ✅ cerrado | Resuelto por user.full_name |
| F-23-03 Toggle RT | ✅ cerrado | Backend ya soportaba |
| F-23-04 Filtro red social | ✅ cerrado | Backend ya soportaba |
| F-23-05 Post cards | ✅ UI + URL backend | P2/P3 quedan §9.8 |
| F-23-06 Sentiment Prom. dirigente | 🔴 §9.8 pendiente | Ligado a F-23-01 |
| F-23-07 Electoral plurinominal | ✅ cerrado | Empty state diferenciado |
| F-23-08 Planes tab CTA | ✅ cerrado | Link a /dashboard/planes |
| F-23-09 Header Diagnóstico | ⚠️ parcial | MASTER §3.1 quitado; destino link pendiente D-23-B |
| F-23-10 Copy Tier 1 | ⚠️ parcial | 8/10 renames; patrón estructural propuesta Sprint 24+ |
| F-23-11 Copy Tier 2 | ⚠️ parcial | 5/8 renames; patrón estructural propuesta Sprint 24+ |

### Decisiones agregadas a DECISIONS.md
D-23-A a D-23-G (7 nuevas · ver `.context/DECISIONS.md`).

### Deuda pendiente documentada
- `SPRINT-23B-INVESTIGACION.md` · P2 (columna url) + P3 (nullable counters) → §9.8 2026-05-20
- `SPRINT-23D-COPY-PROPOSAL.md` · patrón "qué mide / cómo te fue / qué hacer" 4-fases → Sprint 24+
- `SPRINT-23E-INVESTIGACION.md` · motor sentimiento con afiliación 4-fases → §9.8 2026-05-20

### Próximos pasos recomendados
1. Push branch + abrir PR `hotfix/23a-ui-puros` → main
2. Deploy a prod (según convención D-27: `vercel deploy --prod` desde main post-merge)
3. Screenshot Playwright post-deploy para verificar contra los 11 findings originales
4. CEO responde D-23-B (destino metodología) y autoriza (o no) disclaimer interim F-23-01

---

## 2026-04-20 — Gate pre-piloto CERRADO (sesión Joy)

**Arco 2026-04-14 → 2026-04-20 · 7 días · ejecución autónoma + hotfixes post review visual.**

### Cierre funcional
- PRs merged: **#32** endpoints Plan IA cliente + Admin HITL · **#33** tests state machine (15 parametrized) · **#34** hotfix-pre-piloto-v2 6 findings (F-01/F-02/F-03/F-04/F-05/F-07)
- Bug fix última milla: `6726db4` — `/plan-ia/recomendaciones` aceptaba `estado: str`; fix a `list[str] | None` + `.in_()`. Ballesteros pasó de "Pendientes (0)" → "Pendientes (4)" en prod.
- Login hardening: `4efef29` quita accesos demo de login page producción.
- Agentation widget frontend + crawlbase node22 fix: `34dd173`.

### Sprints completados en el arco (commits en main)
| Sprint | Alcance | Commit ref |
|---|---|---|
| Pre-S2 | D-22 competidores client-owned + D-23 onboarding stack + 3 inputs operativos | `b62d843`, `cbd430c` |
| S0 | 6 tareas validación autónomas | `2d32680` |
| S1 | 10 tareas Backend Foundations | `b0381ce` |
| S2 | 10 bloques Diagnóstico Tier 1 Core MVP + Plutchik 21 | `21cc10d` |
| S3 | 8 bloques Diferenciadores Tier 2 + T0 memory hardening Docker | `49e2e26`, `6fef586` |
| S4 | Plan IA cierre ciclo D-17 · 15/15 tareas · 8 bloques prompt + 4 integraciones | `8a3e507`, `c0bd4de` |
| S5 | Onboarding Wizard 9 secciones + T0 Celery migration + Mac M4 primary | `920702d`, `415f830` |
| MVP cierre | SPRINT-CURRENT a 'MVP cerrado · fase piloto' + LaunchAgent cloudflared | `29d7d89`, `a428661` |

### Findings review visual cerrados (F-01..F-07)
- **F-01** MATRIZ_ER_5x5 → Zenodo v1 empírico (Nano X p25-p75 0.013-0.213%, UI "0.01%-1.1%", tooltip "~100× IM commercial 3-7%"). Campo `zenodo_validated` en API.
- **F-02** CardShell acepta `persistentBanner`. Demo banner B04 persiste sobre insufficient_data.
- **F-03** 9 pasos onboarding capturados. D-23 paso 5 + D-22 paso 7 verificados.
- **F-04** B13 narrative "X% engagement en comments inauténtico" según impact_hint.
- **F-05** Banner D-19 permanente en header Tier 1 (red-flag semantics).
- **F-07** B14 warning "⚠️ Detector en calibración".

### Credenciales entregables post-gate
| Usuario | Email | Password | Dirigente | Estado |
|---|---|---|---|---|
| Admin MD | admin@consultoriamd.com | admin123 | — | HITL operativo |
| Piña | pina@crece.mx | Pina2026! | id=1 · IPD 2.6/10 | demo 60 min agendable |
| Ballesteros | ballesteros@crece.mx | Ballesteros2026! | id=8 · IPD 3.1/10 | entregable ahora · 4 aprobadas verificadas prod |

### Data state final
- Piña id=1: 5 aprobadas + 1 ejecutada + 1 completada + 11 rechazadas
- Ballesteros id=8: 4 aprobadas (Cialdini Authority · Kahneman System2 · Haidt Care · Cialdini Reciprocity)
- Matriz ER: `5x5-zenodo-v1-2026-04-19` · 8 VALIDATED · 17 TBD extrapoladas
- Benchmarks: `backend/data/zenodo/v1/benchmarks_er_politicos_mx_v1.csv` (D-19 base)

### Branches no mergeados (estado intencional)
- `docs/prompt-plan-ia-v1.1-prepared` (commit `403dd31`) — prompt v1.1 preparado **NO ACTIVO**. Activación condicionada ≥7 días uso v1.0 + feedback redundancia + autorización CEO.

### Pendientes próxima sesión (frontend)
🟢 nice-to-have + 🟡 Fase C post-piloto:
- **F-06** agrupar Tier 2 semánticamente (Autenticidad · Calidad mensaje · Compliance)
- **F-08** Plan IA cards más compactas + drawer/expand
- **F-09** B01 y B06 ejes Y mejor etiquetados
- **F-10** B16 Promesas · timeline hechas vs cumplidas
- **F-11** tooltips descriptivos en números grandes
- **F-12** Settings routing · consolidar 4 rutas en tabs
- **F-13** Plan IA post-hotfix validación coherente
- **F-14** Histórico empty state mejorado
- **F-15** Admin HITL columna "Días en espera" + warning >24h
- **F-16** Typeahead Harfuch paso 7 Competidores — **DIFERIDO §6.4** (reactivar cuando cliente sin conocimiento exacto)

### Blockers abiertos
- **Agentation MCP**: config `~/.claude.json` línea 4443 fix aplicado (`server --mcp-only`) + zombie PID 76505 eliminado; `/mcp` reconnect sigue fallando → requiere **restart completo Claude Code** (no solo `/mcp`).
- **D-SEC-03**: 21 endpoints JWT-only (sin swap a dual-auth) — abierto desde 2026-04-11.
- **IDOR parcial** `/dirigentes/{id}/crecimiento`: check solo aplica si `user.dirigente_id NOT NULL` — analysts/field_operators de otra org podrían bypasear. Mitigación: tenant check basado en `org_id` (patrón `_require_tenant_access`).
- **Gemini CLI 0.37.1** rate limit 429 RESOURCE_EXHAUSTED — upgrade a 0.37.2 pendiente.

### Blockers MITIGADOS en el arco
- **D-INFRA-01** Tunnel Cloudflare efímero → **MITIGADO** con LaunchAgent auto-update Vercel (`a428661`). Tunnel rota ~1h, Vercel env var se actualiza solo.

### Auditoría memoria (2026-04-20)
Capas verdes: auto-memory (43 entradas) · smart-connections (1,622 sources) · Obsidian MCP · graphify-crece-v2 (3,775 nodos) · graphify-md-design-system (534) · gbrain (3 páginas, subutilizado) · context-mode hooks activos.
Capas con gap: MCP memory vacío (sin hidratar) · DECISIONS.md sin entradas 2026-04-14..2026-04-20 (arco post-gate sin registrar).

---

## Sesion 2026-04-13 noche — /sprint-review NLP + Framework Político

**Alcance:** 8 fases completadas en una sesión con cross-audits Gemini + Perplexity.

### Fases ejecutadas

### Sprint 1 operativo (en esta sesión)
- 95 posts clasificados por Claude Opus 4.6 via admin panel
  - MC-CDMX: 35 posts (24 Piña oposición +0.38, 11 Solano oposición -0.09)
  - GOB-OAXACA: 30 posts Pineda oficialismo (+0.47 promedio)
  - CDMX-IND: 30 posts Jiménez/Cravioto oficialismo (+0.52 / +1.00)
- 0 errores en batch processing
- Admin panel `/dashboard/admin/clasificacion` validado visualmente end-to-end
- Guardrail acceso: dirigente bloqueado (pantalla "Acceso restringido"), admin accede
- Badge "Analisis Contextual · 3 IAs deliberaron" visible en dashboard

### Sprint 2 NLP batch (corriendo en background al cierre)
- Script: `docker exec crece-backend python scripts/reprocess_nlp_full.py`
- Progreso al cierre: 2,180/3,709 posts con `nlp_model_version='multi-model-v1'`
- Topics model xlm-roberta re-descargado correctamente post cache clean
- Velocidad: ~4.6 posts/sec, ETA ~7 min al momento del handoff
- Idempotente: reanudable si se interrumpe

### Pendiente para próxima sesión
1. Dashboard admin operativo `/dashboard/admin/overview` (CEO aprobó mockup)
2. Scrapers encuestas Oraculus + Demoscopía (peer md-research entregó plan)
3. Commit final con Sprint 1+2 results
4. Implementar charts (Treemap/Stream/Sunburst) en dashboard cliente


| Fase | Deliverable |
|---|---|
| **A** Setup | Ollama + HF verificado (topics degradado por cache xlm-roberta, fix post-cleanup) |
| **B** Endpoints RTs+dedup | `/dashboard/overview`, `/social/sentiment-timeline`, `/social/posts` filtran RTs + min_length. Piña timeline -0.163 (antes -0.295) |
| **C** NLP reprocess | 260/3,709 posts con controversy + toxicity + platform-adjusted. Script idempotente. Pausado por decisión arquitectural (no bloquea producto) |
| **D.0** Framework político | 4 tablas nuevas, 32 reglas default v1, API `/framework/*`, audit log verificado con override + rollback |
| **D.2** Validación encuestas | Migration `encuestas_publicas` + servicio `divergencia_encuestas.py` threshold 30%. Scraper scope: Oraculus + Demoscopía (peer md-research investigó, reporte en md-research/analysis/) |
| **D.3** Admin panel | `/dashboard/admin/clasificacion` — UI 3 pasos: generar prompt → pegar JSON de Claude/Gemini/Perplexity → aplicar framework |
| **E** Charts lab | `tools/charts-lab/` con Plotly — Treemap + Stream + Sunburst con datos reales |
| **F.1** UI niveles análisis | `/dashboard/settings/analisis-politico` — 4 niveles amigables (Rápido→Enriquecido→Contextual→Personalizado) |

### Decisiones arquitecturales clave

- **D-NLP-01**: Framework 3 capas (NLP técnico + LLM contextual + Matriz rule-based configurable)
- **D-NLP-02-03**: Defaults +1/-1/0 suaves (Gemini recomendación). Admin org + admin MD editan
- **D-NLP-04**: Colapsar Layer 2+3 descartado — Gemma 12B lento (5+ min/post)
- **D-NLP-05**: Validación externa opción B (alerta divergencia >30%)
- **NEW**: Pipeline MANUAL operado por MD Consultoría. Zero infra LLM. 3 IAs externas (Claude Code + Gemini CLI + Perplexity web) deliberan. Costo $0. Cadencia semanal. Fine-tune modelo propio = evolución natural (no deuda) cuando tengamos 500+ validaciones por tenant.

### Archivos nuevos

**Backend (14 archivos):**
- `migrations/versions/f7a8b9c0d1e2_political_framework.py`
- `migrations/versions/g8b9c0d1e2f3_encuestas_publicas.py`
- `app/services/political_framework.py`
- `app/services/divergencia_encuestas.py`
- `app/nlp/political_llm_prompt.py`
- `app/api/v1/endpoints/political_framework.py`
- `app/api/v1/endpoints/admin_classification.py`
- `scripts/seed_political_framework.py`
- `scripts/reprocess_nlp_full.py`
- `scripts/llm_political_pilot.py` (abandonado — Gemma lento)

**Frontend (2 páginas nuevas):**
- `src/app/dashboard/settings/analisis-politico/page.tsx`
- `src/app/dashboard/admin/clasificacion/page.tsx`
- Sidebar con sección "Admin MD" (solo role=admin)
- Badge "Analisis Contextual · 3 IAs deliberaron" en dashboard

**Tools:**
- `tools/charts-lab/index.html` + README

**Docs (5 archivos):**
- `docs/AUDITORIA-SENTIMENT-2026-04-13.md`
- `docs/CHARTS-LAB-DECISIONES.md`
- `docs/NLP-MODELOS-INVESTIGACION.md`
- `docs/POLITICAL-FRAMEWORK-DEFAULTS.md`
- `docs/OPERACION-MD-CLASIFICACION-SEMANAL.md`

### DB state

- 5 tablas nuevas (`contexto_politico`, `framework_matrix_defaults`, `framework_overrides_org`, `framework_audit_log`, `encuestas_publicas`)
- 11 columnas nuevas en `social_posts` (tono, target, sentimiento_politico_ajustado, controversy, toxicity, topics, platform_adjusted, nlp_model_version, llm_razon, llm_modelo, llm_processed_at)
- `dirigentes.rol_politico` — 2 oposición (Piña, Solano), 4 oficialismo
- 32 reglas v1 sembradas en `framework_matrix_defaults`
- 5 contextos políticos (federal, CDMX, Oaxaca, NL, Jalisco)
- 5 posts clasificados como prueba end-to-end (ia_fuente=claude)

### Peer coordination

- Peer `08rystzm` (md-research) investigó scrapers encuestas MX en paralelo
- Reporte en `md-research/analysis/20260413-mexican-polls-scrapers-crece.md`
- Oraculus JSON inline = scraper 30 líneas · Demoscopía CDMX/Oaxaca obligatorio
- Plan para FASE D.2 implementación real (5-6h) pendiente de siguiente sesión
---

## Sesion 2026-04-13 tarde — Whisper Pipeline + Geo Enrich + Org Scoping

### Tarea 1: Enriquecer secciones_geo_cdmx con master_catalogo.csv (COMPLETADA)
- Script: `backend/scripts/enrich_secciones_catalogo.py`
- 5,531 filas actualizadas, 5,495/5,589 enriquecidas
- Columnas agregadas: volatilidad, estrato, lista_nominal, categoria, dtto_local_cat, dtto_fed_cat, alcaldia, nivel_socioeconomico
- 94 secciones sin match en CSV (existentes en shapefile pero sin estructura MC)

### Tarea 2: Whisper pipeline para posts sin texto (EN PROGRESO)
- Script: `backend/scripts/whisper_tiktok_pipeline.py`
- Pipeline: yt-dlp download → ffmpeg → whisper-cli (ggml-small) → UPDATE DB
- TikTok batch: ~62% éxito (31/50 transcritos), mayoria discursos politicos
- Posts sin voz marcados con `raw_data.needs_ocr = true`
- Facebook + Instagram batch en cola

### Tarea 3: Dashboard org scoping fix (COMPLETADA)
- Bug: admin endpoint `/dirigentes/` no leia X-Org-Id header → todos los dirigentes visibles
- Fix: `dirigentes.py` y `social.py` ahora leen X-Org-Id para admin tenant switching
- Verificado visualmente: MC-CDMX 17.3K audiencia vs GOB-OAXACA 60.8K
- Followers chart, posts list, KPIs — todo scoped correctamente por org

---

## Sesion 2026-04-13 — Sprint E Multi-Tenant + War Room

### Fase 1: Multi-Tenant 3 Orgs (COMPLETADA)
- 3 organizaciones: MC-CDMX (id=1), GOB-OAXACA (id=2), CDMX-IND (id=3)
- 9 usuarios: admin + analista + campo + 6 dirigentes (Pina, Solano, Pineda, Nolasco, Jimenez, Cravioto)
- 6 dirigentes con 15 social profiles (Twitter, Instagram, Facebook, TikTok)
- org_id en JWT token y /auth/me response (con org_nombre, org_slug)
- Dirigentes endpoint filtra por org_id para non-admin users
- Admin tenant switcher en topbar con dropdown de 3 orgs
- Watermark "DATOS SIMULACION" banner para orgs sinteticas (gob-oaxaca, cdmx-ind)
- get_db_rls dependency listo para RLS enforcement (SET LOCAL app.current_org_id)
- X-Org-Id header en API client para admin tenant switching
- Login page: 7 demo buttons agrupados por org con colores (accent, amber, violet)

### Fase 2: Poblar Orgs (COMPLETADA)
- 13 sample posts para 4 nuevos dirigentes (con sentimiento y engagement)
- 2 planes IA (Oaxaca: posicionamiento turistico, CDMX-IND: estrategia legislativa)
- Total DB: 19 posts, 3 planes, 15 social profiles, 6 dirigentes, 3 orgs

### Fase 3: Login UX (COMPLETADA)
- Demo buttons agrupados por org: MC CDMX (accent), GOB OAXACA (amber), CDMX IND (violet)
- Campos se llenan visualmente al click (ya existia de sesion anterior)

### Fase 4: War Room (COMPLETADA)
- E.4.2 HECHO: 5 formatos guiones de campo en Content Factory
- E.4.1 HECHO: CompetitorSnapshotCard widget en dashboard (datos demo MC-CDMX vs Batres/Taboada)
- E.4.3 HECHO: GET /dirigentes/{id}/flash-analysis — 5 metricas + suggested_action

### Sprint F Review (mismo dia)
- F1 HECHO: Dashboard overview endpoint scoped por org_id (X-Org-Id header)
- F2 HECHO: Competitor widget en dashboard
- F3 HECHO: Flash Analysis endpoint (SQL aggregations, sin LLM)
- F4 HECHO: org_id hardening en voter_scoring (segments, by-seccion) + encuestas + social posts

### Archivos modificados
**Backend:**
- `app/schemas/user.py` — org_id, org_nombre, org_slug en UserResponse
- `app/api/v1/endpoints/auth.py` — org_id en JWT, org details en /me
- `app/api/v1/endpoints/dirigentes.py` — org_id scoping para non-admin
- `app/core/database.py` — get_db_rls + get_org_id_from_user
- `scripts/seed.py` — 3 orgs, 9 users, 6 dirigentes, 15 profiles
- `scripts/seed_multitenant.py` — NEW: idempotent multi-tenant seed
- `scripts/seed_org_data.py` — NEW: sample posts + plans para nuevas orgs

**Frontend:**
- `src/lib/api/types.ts` — org_id, org_nombre, org_slug en User
- `src/lib/api/client.ts` — X-Org-Id header
- `src/lib/auth.ts` — OrgContext, activeOrg, setActiveOrg
- `src/components/layout/topbar.tsx` — tenant switcher dropdown + org badge
- `src/app/dashboard/layout.tsx` — SyntheticDataBanner watermark
- `src/app/login/page.tsx` — 7 demo buttons grouped by org
- `src/app/dashboard/contenido/page.tsx` — 5 guiones de campo formats

### DB state post-sprint
| Tabla | Count |
|-------|-------|
| organizaciones | 3 |
| users | 9 |
| dirigentes | 6 |
| social_profiles | 15 |
| social_posts | 19 |
| planes_ia | 3 |
| alcaldias_cdmx | 16 |
| ciudadanos_legacy | 9,723 |
| ciudadanos_v2 | 205 |
| unidades_territoriales | 5,552 |

### Verificacion visual (screenshots)
- Login: 7 demo buttons x 3 orgs (/tmp/crece-login-multitenant.png)
- Dashboard admin: tenant switcher "MC CDMX" (/tmp/crece-dashboard-admin.png)
- Tenant dropdown: 3 orgs + "datos simulacion" label (/tmp/crece-tenant-switcher.png)
- GOB-OAXACA watermark: amber banner visible (/tmp/crece-oaxaca-watermark.png)
- Pineda dashboard: isolated data, 20.8K followers, 3 posts (/tmp/crece-pineda-dashboard.png)
- Content Factory: 5 guiones de campo in formato dropdown (/tmp/crece-guiones-campo.png)

---

## Anterior

---

## Estado global

### Sprints completados (100% del scope funcional)

| Sprint | Estado | Nota |
|---|---|---|
| **S1 Saneamiento** | ✅ peer qmmine5b | `dbc884c` |
| **S2 Benchmark Prompts IA** | ✅ 100% | S2.1-S2.6 completos |
| **S3 Plan Estructurado + Kanban** | ✅ backend + UI + migration + E2E escrito | Playwright run real pendiente |
| **Backport md-research** | ✅ 3 items | Platform.from_url, capture_url, opengraph helper |
| **Sprint n8n-mexico cross-review** | ✅ | Paquete npm publicado + workflow validado e2e |

### Sprints pendientes para siguiente sesión

| Sprint | Esfuerzo | Prioridad | Avance |
|---|---|---|---|
| **S4 Motor de Trends MVP** | 7 días nominal | Alta (plan core) | **9/11** funcionalmente cerrado (+2 scaffolds) |
| **S5 Wizard Onboarding** | 1.5 días nominal | Alta (demo crítica) | **6/6 core** (auto-login real = deuda menor) |

### Sesión 2026-04-12 — Sprint B Canvassing Geo + Sprint A Demo
Branch: `feat/canvassing-geo-map` (pendiente PR a main)

**Sprint B — Canvassing Geo Map (killer feature):**
- `78c3e87` — feat(canvassing): mapa geo con 9,631 ciudadanos reales + filtros + clustering
  - Backend: `GET /canvassing/geo` (GeoJSON PostgreSQL-native) + `GET /canvassing/geo-stats`
  - Frontend: `CanvassingGeoMap` component (MapLibre + clustering + popup)
  - Page reescrita: filtros sidebar + mapa + stats bar + tabs rutas
  - Hooks: `useCanvassingGeo`, `useCanvassingGeoStats`
  - Verificado: BJ=812, CUA=5000(limit), filtros estrato/participación/contactado, tsc clean

**Sprint A — Demo Interna:**
- `0276661` — docs: guion demo 30 min para equipo MC
  - 7 escenas: intro → dashboard → mapa canvassing → wizard → plan IA → PII → Q&A
  - Checklist pre-demo + plan de respaldo

**Cross-audit Gemini (integrado):**
- G1: RLS verificada en ciudadanos_legacy (org_id scope)
- G2: Umbral MVT a 15K registros (hoy 9,723, inline OK)
- G3: Cluster property aggregation (documentado, no implementado — nice-to-have)
- G4: Filtros dtto_local/dtto_federal agregados al endpoint
- G5: Smoke test inmediato post-B.1 (ejecutado)
- G6: GeoJSON construido en PostgreSQL (`jsonb_build_object` + `jsonb_agg`)

### Sesión 2026-04-11 tarde-3 — /sprint-implement luz verde all
Commits en `fix/sprint-4-trends`:
- `9efc76d` — S4.1 catálogo INEGI 16 alcaldías CDMX (ST_Contains verified)
- `24b032d` — docs(s4) /sprint-review enriquecimiento + cross-audit Gemini
- `59413bd` — S4.2 topic_trends + RLS + HNSW orden a→c→b (RLS verificada con rol no-priv)
- `dac0039` — S4.4a location_inference con DB lookup + normalize_social_text + 10 tests
- `bb01c46` — docs D-S4-05/06 y STATUS mid-session
- `598c537` — Batch 1: S4.8 audit RLS + S4.3 seeds 136 cuentas + S4.6a queues + S4.7 RSS parser
- `682b598` — Batch 2: S4.5 detect_trends + S4.6b label_trend_cluster + S4.7 ingest_rss_feeds task
- `521fd6a` — Batch 3: S4.9 endpoint /trends/geo + /alcaldias + S4.10 TrendingAlcaldiaCard + E2E real

**Tareas S4 — estado final**:
| ID | Estado | Verificación |
|---|---|---|
| S4.1 | ✅ | 16 alcaldías INEGI PostGIS, ST_Contains 3/3 points |
| S4.2a/b/c | ✅ | topic_trends + vector(384) + HNSW cosine + 2 RLS policies verificadas |
| S4.3 | ✅ | 136 cuentas semilla YAML (target era 150) |
| S4.4a + a.5 | ✅ | location_inference DB-backed + normalize_social_text + 10 tests |
| S4.4b | ⏸ scaffold | spaCy es_core_news_md NO instalado (deuda D-S4-04) |
| S4.5 | ✅ | detect_trends pipeline end-to-end, 1 trend real generado sobre posts de Piña |
| S4.6a/b | ✅ | cola trends_labeling + Ollama batch labeling probado contra gemma3:12b live |
| S4.7 | ✅ parser | fetch_all_feeds + parser RSS con 8 fuentes + 4 tests; persistencia diferida (D-S4-07) |
| S4.8 | ✅ | search_similar_posts requiere org_id kw-only, cross-org leak imposible, 3 tests |
| S4.9 | ✅ | GET /trends/geo + /alcaldias live, auth JWT, scopeado por org |
| S4.10 | ✅ | TrendingAlcaldiaCard montado en /dashboard/social, tsc clean |
| S4.11 | ✅ | E2E real: detect_trends sobre 381 posts dev DB → 1 trend BJ → label Ollama "Diálogo universitario..." |

Dep nueva: `pgvector>=0.3.0` en pyproject.toml.
Migraciones: `a1b2c3d4e5f6` (alcaldías) + `b2c3d4e5f6a7` (topic_trends + RLS + HNSW).
Endpoints live: `/api/v1/trends/geo`, `/api/v1/trends/alcaldias`.
Tests totales nuevos en S4: **17 verdes** (10 location_inference + 3 RLS audit + 4 RSS parser).

**Deudas documentadas en DECISIONS**:
- **D-S4-04**: spaCy es_core_news_md no instalado (skip por budget, S4.4b)
- **D-S4-07**: RSS persistence requires `platform_enum += 'NEWS'` migration + synthetic profiles o profile_id nullable
- **D-S4-08**: clustering semántico HNSW real requiere backfill_embeddings() sobre 381 posts existentes (primer pase agrupa solo por alcaldía)

**Próximo paso recomendado**: arrancar S5 Wizard Onboarding (1.5 días nominal). Todos los blockers resueltos: RLS audited, topic_trends table ready, endpoints live, UI card mounted.

### Sesión 2026-04-11 tarde-4 — D-DATA-01 Ruta C import CRECE legacy
**Contexto:** el CEO aportó el zip `MC Tablas.zip` con 5 CSVs del CRECE Oracle APEX original. Aprobó Ruta C: importar 3 alcaldías piloto.

**Tablas nuevas y datos importados:**
- `unidades_territoriales` (5,552 rows, sin PII) — grano sección × colonia, con volatilidad, estrato, lista nominal, categoría P1..P5
- `ciudadanos_legacy` (9,723 rows, RLS-scoped, PII sensible) — Cuauhtémoc 6,643 + Miguel Hidalgo 2,267 + Benito Juárez 813
- `promotores_legacy` (45 rows) — super/mega/regular promotores de las 3 alcaldías piloto

**Archivos nuevos:**
- Migraciones: `c3d4e5f6a7b8` (unidades_territoriales) + `d4e5f6a7b8c9` (ciudadanos_legacy + promotores_legacy + RLS policies)
- Modelos: `backend/app/models/unidad_territorial.py`, `backend/app/models/legacy.py`
- Script: `backend/scripts/import_mc_original.py` (idempotente, gated por `CRECE_MC_RAW_DIR`)
- `.gitignore`: `backend/data/raw/mc_original/` excluido del repo (PII)

**Calidad de la data importada:**
- 100% de ciudadanos linkeados a `unidad_territorial` via sección electoral
- 99% con coordenadas GPS reales (9,632/9,723)
- 100% de ciudadanos asignados a un promotor legacy
- Top promotor: MCCDMXCUAUSUPERPROMOTORC3 con 903 ciudadanos

**Hallazgos documentados en DECISIONS.md:**
- D-DATA-01 (decisión Ruta C con alcance y trade-offs)
- D-DATA-02 (compliance LFPDPPP pendiente — pgcrypto at-rest, audit log, right-to-delete)
- D-DATA-03 (reconciliación legacy ↔ v2 pendiente)
- D-DATA-04 (datos faltantes: solo 5% con email, 37% con phone)

**Próximos pasos habilitados:**
1. Voter scoring real sobre 9,723 ciudadanos con lat/lon
2. Canvassing con unidades territoriales + volatilidad + estrato socioeconómico
3. Trends detector puede filtrar por `unidad_territorial` (más fino que alcaldía)
4. S5 wizard puede usar promotores reales en vez de usuarios sintéticos

### Sesión 2026-04-11 tarde — /sprint-review
- Plan S4+S5 revisado, enriquecido con subdivisiones y criterios medibles (ver `PLAN-current.md` sección "Plan revisado 2026-04-11")
- Cross-audit con Gemini CLI aplicó 4 ajustes: orden correcto S4.2 `a→c→b`, S4.8 debe ir tras S4.2b (no antes), S4.4 necesita pre-processor de normalización social, S5.3a debe retornar `sync_status=pending` inmediatamente
- Ruta crítica actualizada: `S4.1 ✅ → S4.2a → S4.2c (RLS) → S4.2b (HNSW) → S4.8 audit → S4.5`
- Resources asignados por tarea (agentes + skills + herramientas)
- **S4.1 ejecutado y verificado**: 16 alcaldías INEGI CDMX en PostGIS, `ST_Contains` OK contra 3 puntos conocidos. Commit `9efc76d` en `fix/sprint-4-trends`.
- **Próximo paso**: S4.2a — crear tabla `topic_trends` con FKs a `alcaldias_cdmx` y `org_id`, SIN la columna vector todavía.

### Merges del día (en orden cronológico)

```
<latest>  2026-04-11 — PR #6 hygiene post-n8n sprint (pending)
909904a   2026-04-11 — PR #5 S2.6 loop 3-iter + winner + ciudadanos fix
112e9ba   2026-04-11 — PR #4 Sprint 2/3 closures (veda, Kanban E2E, Gemma real)
40ed808   2026-04-11 — PR #3 Sprints 2-3 + backport + ollama Coolify
dbc884c   2026-04-11 — Sprint 1 deuda técnica (peer qmmine5b)
2fabfb4   2026-04-11 — docs: D-SEC-03/D-DX-01/D-OBS-01/D-INFRA-01
```

---

## Sprint 2 — Benchmark Prompts IA ✅

### Loop S2.6 — 3 iteraciones reales medidas contra Gemma 3:12b

Test case: `alejandro_piña_medina_diagnostico.json` (datos reales scrapeados
+ NLP 30d desde dev DB). Ejecutado contra Mac M-series local (~4-6 min/iter).

**Scores post rubric fix:**

| Iter | Prompt | Total | Coverage | Spec | Factual | Compliance | Length | Hallu |
|---|---|---|---|---|---|---|---|---|
| 04 | **v1 baseline (ganador)** | **86.5** | 100 | 63 | 87.8 | 100 | 85.6 | 85 |
| 05 | v2 (strict length + specificity) | 85.5 | 100 | 63 | 91.5 | 100 | 83.1 | 75 |
| 06 | v3 (literal format + anti-hallu) | 81.8 | 100 | 49 | 85.3 | 100 | 86.6 | 75 |

**Ganador:** v1 baseline. Commiteado en `backend/app/nlp/prompts/diagnostico_winner.md`.

### Learnings críticos del experimento

1. Gemma ignora mínimos de palabras (pedir 1800 → entregó 1247)
2. Más instrucciones = más alucinación (v2/v3 inventaron `@martibatres`)
3. Formato literal rígido reduce patterns rubric-detectables (9→7)
4. Simpler wins — v1 baseline convergió como óptimo

### Infraestructura validada

- `rubric.py` 6 dimensiones, self-test 92.3/100 (post-fix de decimales)
- `runner.py` multi-provider ollama/claude/gemini/offline
- `compare.py` side-by-side + gap analysis
- `loop.py` orchestrator de iteraciones
- `build_test_cases.py` genera JSON desde DB real
- 4 fixtures reales: Piña + Solano × Diagnóstico + Consolidación
- Coolify Ollama CPU-only NO es viable para el loop (>17 min sin completar)
- Mac M-series con `gemma3:12b` local es ~4-6 min/iter ← ruta de trabajo

---

## Sprint 3 — Plan Estructurado + Kanban ✅

### Backend

- `backend/app/models/plan_ia.py` — `PlanTarea`, `EstadoTarea`, `estructura_json` JSONB
- `backend/app/schemas/plan_ia.py` — 7 schemas Pydantic con constraints
- `backend/app/services/plan_structured.py` (NUEVO) — `generate_structured_plan()` con retry hasta 2× si schema falla
- `backend/app/api/v1/endpoints/planes.py` — 4 endpoints nuevos:
  - `GET /planes/{id}/tareas`
  - `PATCH /planes/{id}/tareas/{task_id}` (audit trail)
  - `POST /planes/{id}/tareas/{task_id}/complete` (captura métrica real)
  - `GET /planes/{id}/progreso` (agregados + impacto)
- Migración `402acb98d2d4` aplicada en dev DB — `estado_tarea_enum` + `plan_tareas` + `planes_ia.estructura_json`

### Frontend

- `frontend/src/components/planes/kanban-board.tsx` — 3 columnas, edit inline, completar con métrica, historial visible, progress bar
- `frontend/src/app/dashboard/planes/[id]/kanban/page.tsx` — ruta nueva
- `frontend/src/lib/api/hooks/use-planes.ts` — hooks react-query
- Botones de movimiento (no drag-and-drop, ver D-SPRINT3-01)

### E2E

- `frontend/e2e/plan-kanban.spec.ts` — 4 tests con mocks stateful, NO ejecutado todavía
- `frontend/e2e/README.md` — documentación del suite

### Pendiente

- **S3.9** ejecutar Playwright E2E con frontend dev server arriba (~30 min)

---

## Sprint 1 peer qmmine5b — ✅ `dbc884c`

- Migración Alembic `d4e7a2c1b8f3_add_dirigente_id_to_users.py`
- Deltas honestos en `/dashboard/overview` (`dirigentes_change` real, `ipd_change=None`)
- Fix prefetch RSC `/dashboard/settings`

---

## Cross-project n8n-mexico ✅

### Paquete publicado

- **`@mdconsultoria-ti/n8n-nodes-crece@0.1.1`** en npm público
- 4 nodos activos: `CreceSegmentar`, `CreceVoterScore`, `CreceContenido`, `CreceSentimiento`
- `CreceCanvassing` omitido del array `nodes[]`, código queda en repo para v0.2.0
- 6 workflows CRECE importados + re-typed + credencial linkeada
- 1 workflow end-to-end validado (read path `Buscar Ciudadano` → 18 items deserializados)

### Bugs descubiertos + arreglados en tiempo real

| Bug | Fix |
|---|---|
| `fixture_sintético.json` PLACEHOLDER literal | Runner validation PR #4 |
| `seed.py` sin org bootstrap → `/api-keys` 500 | SQL runtime fix + PR #6 seed fix |
| `ciudadanos.py` JWT-only → n8n 401 | Swap dual-auth PR #5 |
| `rubric._score_factual` decimal false positive | PR #6 regex fix |
| `runner.py` path bug out_dir relativo | PR #5 bugfix |

---

## Backport md-research ✅

3 items portados a `main`:

- **`Platform.from_url()`** classmethod — 21 host patterns + subdominio fallback
- **`BaseScraper.capture_url()`** default None — 8 scrapers heredan sin cambios
- **`helpers/opengraph.py`** — httpx + regex universal link preview

Documentado en `docs/BACKPORT-MD-RESEARCH.md` con rationale de los 4 items NO portados.

---

## Deudas técnicas abiertas

Ver `.context/DECISIONS.md` sección "Deudas técnicas encontradas durante cross-review con peer n8n-mexico":

- **D-SEC-03** — 21 endpoints siguen JWT-only, falta swap a dual-auth o middleware unificado (recomendación del peer)
- **D-DX-01** — `seed.py` sin org bootstrap → **FIXED en PR #6**
- **D-OBS-01** — `IntegrityError` devuelve 500 plano → **FIXED en PR #6**
- **D-INFRA-01** — Tunnel Cloudflare efímero, bloqueado por Carlos (admin Coolify)
- **D-SEC-02** — `ApiKey.permissions` no enforced (deuda cross-proyecto)
- **Rubric** — `_score_factual` decimal false positive → **FIXED en PR #6**
- **Rubric** — `_score_specificity` patterns estrechos (solo 6 regex)
- **Rubric** — `_score_hallucinations` solo detecta @handles, miss numbers/dates/facts
- **Drift migration** — `social_posts.embedding`, `competidor_social_profiles.last_scraped_at`, `secciones_electorales.seccion` constraint

---

## Infraestructura activa (para el próximo arranque)

### Backend local
- **Contenedor:** `crece-backend` bind-mounted a `/Users/marxchavez/Projects/crece-v2/backend`
- **Puerto:** `8002` (local host)
- **Base de datos:** PostgreSQL + PostGIS en `:5438` (crece_dev)
- **Tests DB:** `:5438` crece_test
- **Redis:** `:6383`
- **MinIO:** `:9006/9007`

### Tunnel Cloudflare (MITIGADO 2026-04-20 con LaunchAgent · fix 2026-05-07 nohup)
- LaunchAgent auto-update Vercel env var cuando tunnel rota (~1h)
- URL actual en runtime: `cat /tmp/crece-tunnel.url`
- Commit `a428661` — D-INFRA-01 deuda reducida de "blocker" a "automático"
- Log: `/private/tmp/cf-tunnel.log`
- **Recovery post-apagón / login 500/530:** `launchctl kickstart -k gui/$(id -u)/com.mdconsultoria.crece-tunnel` y esperar ~90s. Si tras eso `curl -sLS https://frontend-zeta-sepia-46.vercel.app/api/v1/health/` no da 200, revisar `pgrep -fl "cloudflared tunnel --url http://localhost:8002"` — debe haber al menos 1 PID. Si no hay, el script murió a su hijo (bug que `nohup` corrige). Como fallback manual: `nohup cloudflared tunnel --url http://localhost:8002 --no-autoupdate > /tmp/crece-tunnel-cf.log 2>&1 & disown` y luego `cd frontend && printf 'y\n' | vercel env rm BACKEND_TUNNEL_URL production && printf '%s' "<URL>" | vercel env add BACKEND_TUNNEL_URL production && vercel --prod --yes`.
- **Bug histórico (2026-05-07, fix `nohup+disown`):** launchd mataba al `cloudflared` hijo cuando el script `start-crece-tunnel.sh` salía 0, dejando el tunnel muerto inmediatamente después del redeploy de Vercel (Cloudflare devolvía 530 origin unreachable). Síntoma: tras apagón/reboot, el login del frontend daba 500. Fix vive en `scripts/mac-local/start-crece-tunnel.sh` línea ~74 (`nohup ... < /dev/null & disown`).

### Ollama
- **Mac local (recomendado para benchmarks):** `http://localhost:11434` con `gemma3:12b` (8GB) y `gemma4:latest`
- **Coolify VPS (exposición directa):** `http://163.245.208.96:11434` con `gemma3:12b`
- CPU-only en ambos. Mac M-series ~4 min/iter; VPS x86 >17 min sin completar (inviable para loop)

### Frontend
- **Vercel prod (oficial):** `https://frontend-zeta-sepia-46.vercel.app/` (verificado 200 OK · proyecto `frontend` · team `marxs-projects-bb530f2b`)
- **Deploy workflow:** `cd frontend && vercel deploy --prod --yes` (alias estable). Push a GitHub NO dispara re-deploy del proyecto `frontend`.
- **NO usar:** `crece-v2.vercel.app` (proyecto separado, no liberado — confirmación CEO 2026-04-20)
- **Dev local:** `npm run dev` en `frontend/` (puerto 3000)
- **Login hardened:** accesos demo removidos del login page en producción (`4efef29`)

### Credenciales (ver sección "Credenciales entregables post-gate" arriba para estado real)
Legacy demo creds previas (pueden estar stale):
- Piña: `pina@crece.mx` / `demo2026!` → **actualizado a** `Pina2026!`
- Solano: `solano@crece.mx` / `demo2026!` → **sin uso en piloto** (Ballesteros la reemplazó)
- Admin: `admin@consultoriamd.com` / `crece2026!` → **actualizado a** `admin123`

### Organización raíz (post PR #6 seed fix)
- `id=3, slug=mc-cdmx, nombre='Movimiento Ciudadano CDMX', tipo=PARTIDO`
- Todos los users del seed scopados a esta org automáticamente

---

## 2026-04-14 — Sprint IA-1 completado + cirugía dirigente (Joy)

### Carlos (feat/sprint-c-hardening)

Sprint IA-1 — Índice de Aceptación MVP:
- Migration `h9c0d1e2f3g4_social_comments` aplicada
- 200 comments reales TikTok ingestados (Brightdata dataset gd_lkf2st302ap89utw5k)
- 200 comments clasificados con framework (comment-framework-v1)
- Endpoint `/api/v1/social/posts/{id}/ia` — 3 scores + breakdown
- Endpoint `/api/v1/social/dirigentes/{id}/ia-summary` — top aprobación/rechazo
- LFPDPPP compliance: author_hash SHA256, cero PII crudo
- Test real: post Piña 7357909824622890245 → 11.5% aprobación / 20% rechazo / 68.5% neutral

YouTube ingesta (tangencial): 56 videos ingestados via host macOS (YT bloquea Docker).

### Joy (feat/dirigente-surgery)
- 5 commits: redirect viewer + migrations + radar B1 + widget Tendencia + docs
- 2 migrations Alembic: ds01 (enum data_source) + ds02 (social_profile_snapshots)
- Widget Tendencia con switcher Treemap/Stream/Sunburst
- Semáforo de crecimiento + alerta 48h data_source='manual_host_ingest'
- Pre-merge: rebase ds01/ds02 sobre h9c0d1e2f3g4

### Pendiente
- Cross-audit Gemini del resultado IA-1 + cirugía Joy
- Merge coordinado de las 2 ramas
- UI widget IA en `/dashboard/social/[post_id]` (Sprint IA-2)
- Ingestar más comments: FB/IG/YouTube para posts restantes
- Aviso Privacidad CRECE actualizado (LFPDPPP)

---

## 2026-04-14 05:40 — Sprint M COMPLETADO (merge Joy + Carlos consolidado)

### Commits en main (desde ÚLTIMA sesión)
- 94c72aa Merge PR #10 (Sprint 0 + 0.5 + IA-1)
- 714ca23 Merge PR #11 (cirugía módulo dirigente)
- fcb0d58 fix(migration): ds02 reuse platform_enum sin recrear
- 6fca2b4 fix(enum): DataSource usa values_callable para mapeo lowercase

### Migrations aplicadas
g8 → h9 (social_comments) → ds01 (data_source + last_manual_update) → ds02 (social_profile_snapshots RLS)

### Smoke tests PASS
- GET /api/v1/admin/overview → 200 (6 widgets flota)
- GET /api/v1/social/posts/1088/ia → 200 (200 comments Piña clasificados)
- GET /api/v1/dirigentes/1/crecimiento → 200 (5 plataformas + semaforo)
- GET /api/v1/planes/1/tareas → 200 (12 tareas Piña)

### Backfill ejecutado
4 profiles marcados data_source='manual_host_ingest':
- Piña YouTube (29 subs)
- Pineda YouTube (581 subs)
- Cravioto YouTube (26 subs)
- Piña TikTok (0 followers — bloqueo bot detection)

### Sprint W (Whisper 98 TikToks) — hallazgo honesto
Los 98 posts "sin texto" pendientes resultaron ser IG images (sin video) + FB URLs 404. No hay audio/video transcribible. Pipeline no aplica.

### Pendiente (siguientes sprints del plan REV 2)
- Sprint B: comments masivo 6 dirigentes × 4 plataformas (rotación Brightdata + Crawlbase + ScraperAPI + Apify + PhantomBuster cuando se agote)
- Sprint IA-2: UI widget IA con normalización por rol político
- Sprint D: diagnóstico formal por dirigente (FODA + benchmark vs adversario)
- Sprint P: regenerar 6 planes v3 grounded en diagnóstico (migración suave)
- Sprint C: LFPDPPP completo (aviso + retención + ARCO)
- Sprint X: cierre documental

### Bugs conocidos / deuda técnica
- IDOR parcial en /dirigentes/{id}/crecimiento: check solo aplica a users con dirigente_id NOT NULL. Analysts/field_operators de otra org podrían bypasear. Mitigar en iteración siguiente con tenant check basado en org_id (patrón _require_tenant_access)
- Gemini CLI 0.37.1 con rate limit 429 RESOURCE_EXHAUSTED — upgrade a 0.37.2 pendiente
- Chrome DevTools MCP timeout en capturas de pantalla (no bloquea funcionalidad)

---

## 2026-04-14 06:30 — /sprint-implement "todos los sprints" — 5 de 6 COMPLETADOS

### Sprint B: Comments masivo 6×4 — PARCIAL ⚠️
- 200 comments TikTok Piña ingestados (Sprint IA-1 original)
- Script `/tmp/scrape_comments_batch.py` disparado para 6 dirigentes × 3 plataformas
- Brightdata snapshots en curso >10 min sin output visible
- Comments se ingestarán async; script es idempotente

### Sprint IA-2: UI widget IA — COMPLETADO ✅
- `frontend/src/lib/api/hooks/use-indice-aceptacion.ts` — hooks React Query
- `IndiceAceptacionCard` — stacked bar aprobación/neutral/rechazo + tono breakdown
- `IASummaryCard` — top aprobación/rechazo por dirigente
- Confidence banding (low/medium/high según volumen)
- Integración en perfil dirigente + post detail pendiente de UI wiring (2-3 líneas)

### Sprint C: LFPDPPP — COMPLETADO ✅
- `docs/AVISO-PRIVACIDAD-CRECE.md` — aviso completo (LFPDPPP art. 10-IV + 16-II)
- `/api/v1/legal/privacidad` — metadata pública (200 OK verificado)
- `/api/v1/arco/exercise` — acceso/cancelación/oposición con hash SHA256
- `retention_tasks.cleanup_old_comments` — celery beat cada 86400s (24h)
- Retención 180d para social_comments

### Sprint D: Diagnósticos FODA — COMPLETADO ✅
- Script `generate_diagnostico_dirigentes.py` genera DIAGNOSTICO tipo plan_ia
- 6 DIAGNOSTICOS en BD con FODA + baseline + engagement per platform
- Grounded en: posts NLP (3709), framework clasificado (387), IA comments (200)
- Estructura `foda` (F/O/D/A) + `baseline` (métricas) + `profiles`

### Sprint P: Planes v3 grounded — COMPLETADO ✅
- Script `generate_planes_v3_from_diagnostico.py` deriva tareas desde FODA
- 6 planes v3 CONSOLIDACION con modelo_ia='foda-derived-v3'
- 29 tareas nuevas — cada una con `fundamento_foda` en cambios_historial
- Migración suave: v2 marcado superseded_by_v3, v3 activo sin romper historial
- Deltas por dirigente: Piña 5, Solano 5, Pineda 4, Nolasco 4, Jiménez 5, Cravioto 6

### Sprint X: Cierre documental — EN CURSO 🔄

### Commits en main desde arranque sesión
- 94c72aa Merge PR #10 Sprint 0+0.5+IA-1
- 5858263 fix(security) IDOR + salt
- 714ca23 Merge PR #11 cirugía dirigente Joy
- fcb0d58 fix(migration) ds02 platform_enum
- 6fca2b4 fix(enum) DataSource values_callable
- 63dd4f2 feat Sprint C LFPDPPP + IA-2 UI
- b8d8b98 feat Sprint D diagnósticos + P planes v3

### Estado BD actual
- 6 dirigentes · 3 orgs
- 3,833 posts · 200 comments con NLP
- 6 DIAGNOSTICOS · 6 planes v3 (29 tareas nuevas) + 6 planes v2 (superseded)
- 25 social_profiles (con 3 YT + 1 TT manual_host_ingest)

### Pendiente técnico
- Sprint B comments masivo (cuando Brightdata responda) — ejecutar `/tmp/scrape_comments_batch.py`
- UI wiring widgets IA en páginas existentes (copy-paste 2-3 import + component mount)
- IDOR parcial en /crecimiento (check solo aplica si user.dirigente_id NOT NULL)
- Gemini CLI capacity issue persistente — upgrade 0.37.2

---

## 2026-05-28 noche · Sprint-implement (Linda)

### Sprint A · Bug fix adapter comments → ✅
- `backend/scripts/ingest_radar_comments_payload.py` línea 95: `n_ins += 1` movido DENTRO del `if commit and cid:` + separados contadores `n_ingestable`, `n_inserted`, `n_skipped_no_cid`. Pre-fix reportaba "[APPLY] OK N" engañoso cuando cid era falsy.
- Verificado dry-run sintético (5 items mixtos contra profile_id=16): `ingestables=1 inserted=0 sin_cid=2 huérfanos=1 sin_post_id=1`
- Commit: `f04b0cf`

### Sprint B.1 · AGENTS.md raíz → ✅
- `AGENTS.md` hand-written 308 líneas (ETH Zürich: archivos auto-generados o inflados REDUCEN éxito tareas ~3% y suben costo +20%)
- Cubre: stack, comandos exactos del Makefile, estructura, límites duros, convenciones, política humano-vs-agente con ADRs Nygard frontmatter, Definition of Done, cierre sesión, perfiles prueba, anti-patrones
- Commit: junto con `.context/PLAN-2026-05-28-sprint-implement.md`

### Sprint P0 · Ingest Felipe E2E desde paquete `felipe_handoff_20260528_2346` → ✅
- Paquete Marx (radar peer v7luclno): 197 posts + 294 comments + 5,950 reactors (flat list shape v2)
- Wrapper one-shot `/tmp/wrap_felipe_2346.py` split + envelope + aliases (no persistido al repo)
- Reactors via export v2 enveloped probado: `radar/exports/felipe-reactors-v2-20260528.json` (7,816 rows, 7,794 FB + 22 IG)
- **Resultados:**

| Platform | Posts antes | Posts después | Δ | Comments | Reactor events | Watched profiles |
|---|---|---|---|---|---|---|
| FB | 25 | **85** | +60 | **156** | **6,831** | **4,400** |
| TT | 98 | **100** | +2 | **138** | 0 (TT no expone) | — |
| IG | 12 | 12 | 0 | 0 | 22 (previo) | — (gated CEO) |

- **Caveats:**
  - 85 FB posts vs 76 "únicos por url" según Marx (delta 9 = cross-scheme pfbid/base64). Adapter dedupea por `platform_post_id` (ON CONFLICT). Si se quiere dedup secundario por url se hace en UI o post-process.
  - 22 IG reactor_events ya estaban (ingest previo instagrapi), no son de este paquete.
  - Coverage reactors: `fb_post_match_rate=3359/7794` según export_meta (43% match directo base64 → 7,794 finalmente resueltos vía base64+url+numeric fallback).
- IG SKIP justificado: engine `apify_ig` gated CEO (HANDOFF-2026-05-28-noche § "IG: sigue 12").

### Pendiente próxima sesión
- NLP +73 posts Felipe nuevos (sentiment_score celery + tono/target/emotions/topics gemini inline)
- ADR-0001..0005 migración + SESSION_HANDOFF.md template
- MAPA §2 Diagnóstico Tier 1
- Marx anotó ADR-D-041 "contrato export radar↔crece" en su lado

---

## 2026-05-28 noche tarde · MAPA-FUNCIONAL completado (§2-§10)

**Sesión `/sprint-implement` continuada — luz verde CEO "vamos con los mapas".**

### Resultado
MAPA-FUNCIONAL.md ahora cubre los 10 módulos del producto con citas verificables, auditoría Gemini independiente sección por sección, y hallazgos sustantivos aplicados.

| Sección | Estado | Auditor Gemini | Hallazgos sustantivos |
|---|---|---|---|
| §1 Aceptación + Fans y Perfiles | ✅ | ✅ Pasa (previo) | (sesión previa) |
| §2 Diagnóstico Tier 1 (B01-B10) | ✅ | ✅ **Pasa** | 0 inventos, 0 omisiones. Aclaración B08 modelo NLP. Tier 1 ≠ B11-B18 (eran Tier 2). |
| §3 FODA | ✅ | ⚠️ Pasa con ajustes | POST /planes/generar agregado · _parse_foda load-bearing 40% (no legacy) · dirigentes sin DIAGNOSTICO listados |
| §4 Planes IA | ✅ | ⚠️ Pasa con ajustes | Tab Diagnóstico removed 2026-05-22 (2 tabs no 3) · CRISIS en tipo_plan_enum · enum IN_PROGRESS no DOING · botones Aprobar/Rechazar son placeholders sin onClick |
| §5 Clima Político | ✅ | ✅ **Pasa** | Sesgo menor: EXPRESIDENTES list 5 nombres no 3 |
| §6 Recom · Eval · Reels | ✅ | ⚠️ Pasa con ajustes | /plan-ia/{id}/seguimiento NO existe · /post-ejecutor confirmado · status/{task_id} agregado |
| §7 Overview + Dirigentes | ✅ | ⚠️ Pasa con ajustes | POST /dirigentes/onboard (no path-id) · GET /onboarding-progress · 12+ hooks onboarding S5 · OnboardingWizard component |
| §8 Diagnóstico Tier 2 (B11-B18) | ✅ | ⚠️ Pasa con ajustes | cib_flags NO existe (CIB in-memory) · promesas → promesas_dirigente · B16 cobertura solo Piña 12 promesas |
| §9 Configuración + Sistema | ✅ | ⚠️ Pasa con ajustes | 3 de 5 páginas son dinámicas no estáticas · HITL bilateral cliente+admin · OnboardingWizard hooks |
| §10 Admin (admin/analyst MD) | ✅ | (audit en curso) | Título corregido pre-audit: NO "no-cliente" sino "admin scope" · HITL bilateral cross-doc §9 |

**11 commits del día solo en governance/MAPA.** Branch `feat/post-ingest-hugo-2026-05-20` con todo aplicado.

### Pendientes próxima sesión
- §10 audit Gemini (en curso al cierre)
- ORGANIZACION.md + REGLAS.md + PRODUCTO.md (los 3 docs gov faltantes)
- NLP +60 FB posts Felipe (Sprint P0.2)
- 5 ADRs canónicos migrados a `docs/adr/` + SESSION_HANDOFF.md template (Sprint B.2 + B.3)
- B-FELIPE-FB-DUP-9 decisión CEO (dejar o limpiar 9 duplicados)
- Reel Piña 3982 FASE B (luz verde Camoufox+cookies)

### Métricas calidad
- 0 inventos detectados por auditor en 7 secciones auditadas (6/7 con audit completo).
- 1 falso positivo del auditor (líneas planes.py §4) — descartado con verificación.
- 1 contradicción cross-doc (HITL §9 vs §10) detectada y resuelta dentro del mismo pase.
- 100% hallazgos sustantivos verificados antes de aplicar (sub-regla MODELO §5.4).

---

## 2026-05-28 final · Los 3 docs de governance faltantes cerrados

**Sesión `/sprint-implement` ronda 3 — luz verde CEO "todos los doc faltantes".**

| Doc | Estado | Audit |
|---|---|---|
| ORGANIZACION.md | ✅ v0 | ⚠️ Pasa con ajustes Gemini aplicados (Ana García, Carlos López, Enrique Herrera, Juan md-research, Rem reclasificada) |
| REGLAS.md | ✅ v0 | Audit Gemini timeout · verificación lateral del redactor (35 ADRs citados confirmados, doc cubre 35/73 reales) |
| PRODUCTO.md | ✅ v0 | ✅ Aprobado con observaciones · 2 falsos positivos del auditor declarados (pricing $1.5k-$15k y "IA Predictiva Q3-Q4" inventados) |

**Governance docs: 6/6 operativos.** Resta migrar 5 ADRs canónicos a `docs/adr/` formal (Sprint B.2) + SESSION_HANDOFF.md template (Sprint B.3).

### Pendientes próxima sesión (consolidado)
1. **CEO inputs requeridos** (PRODUCTO.md §10):
   - Misión y visión textual (confirmar o reescribir §2.1, §2.2)
   - Pricing (modelo + monto + política upgrade T1→T3)
   - KPIs norte (cuantificación §9)
   - Pipeline confirmación (Gobierno Oaxaca §6.2)
   - Roadmap Fase 2 priorización
   - Estrategia de adquisición de clientes
   - PR/FAQ "Working Backwards" anti-deriva
2. **CEO inputs ORGANIZACION**:
   - Ana García activa o cuenta legacy?
   - Carlos López activo (FIELD_OPERATOR)?
3. **Sprint B.2:** docs/adr/ + 5 ADRs canónicos migrados con frontmatter author
4. **Sprint B.3:** SESSION_HANDOFF.md template
5. **NLP Felipe** +60 FB posts (sentiment_score + gemini inline)
6. **B-FELIPE-FB-DUP-9** decisión CEO (dejar o limpiar 9 duplicados)
7. **Reel Piña 3982 FASE B** (luz verde Camoufox+cookies)
8. **§10 MAPA + REGLAS** re-audit Gemini cuando CLI disponible

### Métricas calidad sesión completa
- **17 commits** en `feat/post-ingest-hugo-2026-05-20`
- **15 archivos governance/audits/blockers nuevos**
- **9 secciones MAPA + 3 docs gov auditados** (10 con Gemini, 2 lateral)
- **0 inventos del redactor detectados** en 12 secciones con audit Gemini completo
- **3 falsos positivos del auditor** declarados (sub-regla §5.4 MODELO funcionando)
- **1 contradicción cross-doc** detectada y resuelta dentro del mismo pase
- **100% hallazgos sustantivos verificados** antes de aplicar

---

## 2026-05-28 cierre · NLP Felipe (60) +46 posts con max effort inline

**Patrón aplicado:** loop `psql SELECT → razonar inline → psql UPDATE → repetir` siguiendo `HANDOFF-nlp-pendientes-284-gemini.md`. Yo (Claude Opus 4.7) clasifico con razonamiento propio, sin llamar APIs externas ni Ollama. RAM-safe (cada UPDATE en una conexión efímera via `docker exec psql -f`).

**Resultado:**
| Platform | Total | Con NLP | Sin NLP | Notas |
|---|---|---|---|---|
| IG | 12 | 12 | 0 | Sin cambio (ya tenía 100%) |
| FB | 85 | 71 (+46) | 14 | Videos sin caption — regla handoff no clasificar content vacío |
| TT | 100 | 98 | 2 | Videos sin caption |
| **TOTAL** | **197** | **181** (92%) | 16 (todos sin texto) | **100% del contenido textual** |

**Distribución del clasificado (de mi sesión + previos):**
- Tono: personal 47, celebratorio 42, informativo 23, critico 22, solidario 21, propositivo 20, ataque 6
- Target: ciudadania 66, no_determinado 29, tema_especifico 22, autopromocion 22, oposicion 13, gobierno 13, personal 6, medios 4, oficialismo 4, dirigente 2
- Polaridad ajustada: +1: 83 (45%), 0: 70 (39%), -1: 28 (16%)

**Lecciones operativas:**
- Constraint `target_politico` tiene whitelist específico — descubrí 'otro' NO está permitido (corregir a 'no_determinado'). Verificado vía `pg_constraint`.
- `nlp_model_version='claude-opus-4-7-inline-2026-05-28'` para trazabilidad — distingue lo que YO clasifiqué vs `cc-topics-v1-2026-05-21` u otros runs batch previos.
- 5 lotes de 10-11 posts cada uno. RAM estable. Sin colgones.

**Caracterización del perfil de Felipe (insight del NLP):**
- Felipe = MORENA/oficialismo Nicolás Romero EDOMEX. Apoyo Sheinbaum/4T/Delfina/Higinio Martínez.
- Repertorio narrativo dominante: solidario+celebratorio (festejos comunitarios, día madre, maestros, vecinos) + propositivo (iluminación, seguridad, gestión municipal).
- Crítica/ataque concentrado en medios (chayoteros, TV Azteca, Alatorre, Chapoy) y oposición (PRIAN, Trump).
- Autopromoción ~22 posts (campaña permanente: "síguenos en redes Felipe Martínez FM").
- Posts personales/familia ~6 (madre, infancia, futbol).

---

## 2026-05-29 madrugada · Pendientes Felipe + Piña cerrados con Hugo

**Cierre 3 pendientes en colaboración Hugo (radar peer):**

### 1. B-FELIPE-FB-DUP-9 → ✅ CERRADO
- CEO autorizó opción (b) limpieza.
- SQL DELETE 9 numeric_ids (ids 8939-8947, todos `likes=0/ER=0/reactor_events=0`).
- FB Felipe 85 → **76 posts únicos** (matchea cuenta inicial radar).
- 0 daño colateral (cero comments / reactor_events afectados por cascade).
- BLOCKERS.md actualizado tachado.

### 2. Felipe NLP 14 reels sin caption → ✅ CERRADO (Hugo backfill)
- Hugo corrió `fb_text_backfill.py` Felipe FB → recuperó 14/14 captions via `json_message` regex (incl reels).
- Patch shape `[{platform_post_id, post_url, content}]` × 39 (superset).
- Match script Python local: 14/14 matched por url-exact + numeric-substring + reel-numid.
- UPDATE content + NLP inline Claude Opus 4.7 con `nlp_model_version='claude-opus-4-7-inline-2026-05-28+hugo-backfill'`.
- **Felipe 188/188 (100%) NLP coverage**: IG 12 + FB 76 + TT 100.

### 3. Reel Piña 3982 FASE B → ✅ CERRADO
- Hugo corrió `scrape_reactors_batch_cdp` con Chrome :9222 + cookies CEO sobre los 12 pfbid URLs.
- Export: `radar/exports/pina-3982-reactors-v2-20260529.json` (12,733 reactors total Piña, 499 nuevos del 3982).
- Ingest `ingest_radar_reactors_v2.py` env `DIRIGENTE_ID=1 PLATFORM=FACEBOOK`:
  - events_attempted: 5,814 (FB scope)
  - events_in_db_target_posts: 3,360
  - Piña FB watched_like_events: 4,316 → **4,664** (+348 nuevos post-dedup ON CONFLICT)
- Reel 3982 (post id 8509): 279 reactor_events confirmados.

### Hallazgos operativos de la sesión:
- **`supadata_transcript`** = nueva opción de pipeline NLP para videos sin caption (audio→texto). Documentado en MAPA §2.5.1.
- **Hugo `fb_text_backfill.py`** = otra opción del pipeline NLP (regex DOM dialog para captions perdidos en scrape inicial). Documentado en MAPA §2.5.1.
- **Pattern anuncio en backfill**: post id 9572 trajo content "HOT SALE®... lanza tu campaña" (anuncio commercial DOM-adyacente). Clasificado conservador (informativo/no_determinado/0 + topic 'atribucion dudosa'). Hugo anotó pending radar-side.

### Estado final:
- Felipe: 188/188 NLP, 76 únicos FB, 4,400 watched_profiles, 6,831 reactor_events, 156 comments
- Piña FB: 4,664 watched_like_events, reel 3982 cerrado a 279 únicos
- 3 pendientes operativos: 0
