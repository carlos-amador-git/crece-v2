# PLAN · Sprint multi-bug + B07/B08 + tríada · 2026-05-25

**Origen:** sesión post-cierre PLAN-2026-05-22-recovery · CEO inspeccionó UI prod y descubrió bugs nuevos + cuestionó B07/B08/B17. Diagnóstico cross-verificado con Hugo (peer RADAR).

**Branch:** `feat/post-ingest-hugo-2026-05-20` (53 commits ahead de main · 5ta sesión consecutiva deployando vía `vercel --prod` directo sin merge).

**Operador:** Linda (Claude Opus 4.7).

**Premisas CEO (vigentes desde 2026-05-22):**
- Calidad > Tiempo
- Eficiencia y operación de la app > Tiempo
- Autonomía total, sin pedir confirmación por fase salvo gate fallido
- Política RAM dura: un subprocess Claude `--print` a la vez, abort si swap >4.5GB sostenido o `memory_pressure >70%`

---

## Estado verificado (read-only · primary source)

### Bugs descubiertos UI prod hoy

| # | Bug | Archivo culpable | Evidencia | Scope |
|---|---|---|---|---|
| 1 | "Contenido con más Impacto" muestra los 3 más recientes (no de impacto) | `frontend/src/app/dashboard/dirigentes/[id]/page.tsx:235-251` | `recent_posts.slice(0,3)` viene ORDER BY published_at DESC desde backend | Todos los dirigentes |
| 2 | "Sin clasificar" aunque `tono_discurso` poblado en BD | `backend/app/api/v1/endpoints/dirigentes.py:268-291` | Serializa sentiment_score+sentiment_label, NO incluye tono_discurso | recent_posts API |
| 3 | Mapper ingest TT no copia raw_data → columnas | `backend/scripts/ingest_radar_yt_x_posts.py:105-109` | else branch hardcoded `likes=comments_n=shares=views=0` para TIKTOK | 32 posts Saymi TT del 22-may |
| 4 | Selector dirigente N=1 inútil | componente compartido (por localizar) | Saymi sólo ve a Saymi por scope JWT · dropdown ruido | /aceptacion/fans-y-perfiles y otras |
| 5 | Platform filter no sticky al scroll | `/dashboard/aceptacion/fans-y-perfiles` | Usuario debe regresar arriba para cambiar plataforma | misma vista (replicable a otras) |

### Hugo confirmó (peer RADAR `1m4oqc8n` · 2026-05-25 19:27)

- RADAR no normaliza, entrega keys yt-dlp crudos en `payload`
- CRECE guarda `payload` verbatim como `raw_data` (+ key `caption_source` agregada por ingest)
- Mapper yt-dlp → columnas:
  - `like_count → likes`
  - `view_count → views`
  - `comment_count → comments`
  - `repost_count → shares` (TT repost = share)
  - `save_count → (sin columna)` · queda en raw_data
- Veredicto: NO re-scrape · `raw_data` ya tiene los datos

### B07/B08/B17 inquietudes CEO

**B07 · Growth Attribution:**
- Snapshots Saymi: 5 filas, 1 día distinto (`2026-05-12`)
- Snapshots Pepe: 2 filas, 1 día distinto (`2026-05-12`)
- B07 requiere ≥2 días distintos para `delta_followers` → hoy regresa `insufficient`
- CEO recuerda: scraper inicial corrió, periódico nunca se activó · correcto
- Acción: activar Celery beat task `scrape_all_profiles` ya existe (`schedule: 86400.0` = diario) pero el snapshot dedicado **NO está enganchado al beat actual**. Decisión CEO: schedule **semanal**

**B08 · Share of Voice:**
- NO es scraper de menciones externas (eso nunca se implementó)
- Servicio (`sov_service.py`) compara posts propios con topics vs posts rivales con topics
- Estado: Saymi 100% topics todas plataformas · Ivette (58) y Susana (59) ambas con 0% topics
- Resultado actual: Saymi `self_pct=100%` artificial · sin base comparativa real
- Acción: correr `extract_topics_saymi_cc.py` (mal nombrado · sirve para cualquier dirigente_id) sobre rivales 58 y 59

**B17 · Veda Compliance:**
- CEO validó screenshot Saymi: "Puede publicar / sin veda activa — modo informativo / 4 posts con keywords de riesgo en ventana" · "Así me gusta porque es real"
- Verificación primaria código (`veda_compliance_service.py`):
  - Calendario electoral distrital **no implementado** (Sprint S4 documentado pendiente)
  - `dirigentes.seccion_electoral` vacío para Saymi/Pepe/Ballesteros
  - Flag `en_veda` es global (query param), no por dirigente
  - Diferencias Saymi vs Jiménez sólo vendrían por keywords en últimos 14d (heurística static)
- Acción: NINGUNA · card actual refleja realidad

---

## FASES

### F1 · Backend SQL one-shot + script patch (~45 min · sin LLM · cero RAM risk)

**Objetivo:** corregir 32 posts TT con métricas en 0 + arreglar mapper para futuros runs.

#### F1.1 · Patch script ingest TT
Archivo: `backend/scripts/ingest_radar_yt_x_posts.py`

Agregar rama TIKTOK antes del `else` (línea ~105):
```python
elif platform == "TIKTOK":
    content = payload.get("description") or payload.get("title") or ""
    likes = int(payload.get("like_count") or 0)
    comments_n = int(payload.get("comment_count") or 0)
    shares = int(payload.get("repost_count") or 0)   # TT: repost = share
    views = int(payload.get("view_count") or 0)
    published_at = to_datetime(payload.get("timestamp"))
    post_type = "VIDEO"   # TT siempre es video
```

#### F1.2 · UPDATE one-shot 32 posts
```sql
UPDATE social_posts SET
  likes = COALESCE((raw_data->>'like_count')::int, 0),
  views = COALESCE((raw_data->>'view_count')::int, 0),
  comments = COALESCE((raw_data->>'comment_count')::int, 0),
  shares = COALESCE((raw_data->>'repost_count')::int, 0)
WHERE (raw_data->>'_source') = 'ytdlp_tiktok' AND likes = 0;
```

#### F1.3 · Recompute engagement_rate
Script existente: `backend/scripts/recompute_engagement_rate.py` (verificar nombre real) sobre los 32 IDs afectados.

#### F1.4 · Backend serializer fix B17→tono_discurso
Archivo: `backend/app/api/v1/endpoints/dirigentes.py:268-291`

Agregar al diccionario:
```python
"tono_discurso": post.tono_discurso,
```

Frontend `SentimentBadge` ya no muestra "Sin clasificar" si recibe `tono_discurso` válido (fallback secundario · ajuste si requiere).

### Gate F1
- 32 posts TT con `likes>0, views>0` en BD post-UPDATE
- `engagement_rate` recomputado coherente con nuevos valores
- `git diff backend/scripts/ingest_radar_yt_x_posts.py` muestra rama TIKTOK agregada
- `pytest backend/tests/` no rompe nada (suite existente)
- `grep tono_discurso backend/app/api/v1/endpoints/dirigentes.py` confirma serializer

---

### F2 · Backend beat snapshot semanal + topics rivales (~30 min · LLM secuencial)

#### F2.1 · Celery beat snapshot semanal
Archivo: `backend/app/workers/celery_app.py`

Agregar al `beat_schedule`:
```python
"snapshot-all-profiles-weekly": {
    "task": "app.workers.tasks.snapshot_all_profiles",   # crear si no existe
    "schedule": crontab(hour=2, minute=0, day_of_week=1),  # lunes 02:00 MX
},
```

Verificar `app.workers.tasks.snapshot_all_profiles` existe. Si no, crear (lee `social_profiles`, INSERT en `social_profile_snapshots` con `followers_count`, `posts_count`, `taken_at=NOW`).

#### F2.2 · Extract topics rivales Saymi (Ivette 58 + Susana 59)
```bash
backend/.venv/bin/python backend/scripts/extract_topics_saymi_cc.py --dirigente-id 58 --limit 50
backend/.venv/bin/python backend/scripts/extract_topics_saymi_cc.py --dirigente-id 59 --limit 100
```

Política RAM dura: lanzar uno tras otro, no paralelo. Verificar `memory_pressure` antes de cada uno.

### Gate F2
- `celery_app.py` con beat semanal registrado
- BD: rivales 58+59 con topics_extracted poblado (>50% sobre posts con content válido)
- B08 endpoint `/diagnostico/3/sov` ya no devuelve `self_pct=100%` artificial · refleja comparativa real

---

### F3 · Frontend UX (~1.5h · sin LLM · cero RAM risk)

#### F3.1 · Título widget honesto
Archivo: `frontend/src/app/dashboard/dirigentes/[id]/page.tsx:235`

Cambiar:
```diff
- Contenido con más Impacto
+ Publicaciones recientes
```
(Honestidad >> marketing wording. Si CEO quiere "más impacto" real, F5 backlog: nuevo endpoint que ordena por engagement_rate DESC con cap >= 5 likes.)

#### F3.2 · Selector dirigente N=1 ocultar
Localizar componente (probablemente `DirigenteSelector` o equivalente). Si la lista de dirigentes accesibles `dirigentes.length === 1`:
- Render header readonly con nombre del dirigente
- NO render `<Select>` dropdown

Aplicar a `/dashboard/aceptacion/fans-y-perfiles` y replicar a `/dashboard/aceptacion/[id]`, `/dashboard/diagnostico` y otras vistas que usen el selector.

#### F3.3 · Platform filter sticky
Archivo: `frontend/src/components/aceptacion/watched-profiles-tab.tsx` (probable · localizar)

Wrapper de las pills:
```tsx
<div className="sticky top-0 z-10 -mx-4 px-4 py-2 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-b">
  {/* pills Plataforma: Todas / FB / IG / TW / TT / YT */}
</div>
```

### Gate F3
- `npx tsc --noEmit` verde
- `bash scripts/check-no-mocks.sh` verde
- Smoke visual local: 
  - `/dashboard/dirigentes/3` muestra "Publicaciones recientes" en lugar de "Contenido con más Impacto"
  - `/dashboard/aceptacion/fans-y-perfiles` con login Saymi: NO dropdown dirigente, solo header
  - Scroll en `/dashboard/aceptacion/fans-y-perfiles` mantiene pills visibles al top

---

### F4 · Tríada audit-full pre-cliente (~3-4h · diferida a sesión propia)

**Nota:** F4 NO se ejecuta en este sprint salvo decisión explícita CEO. Doy plan detallado para referencia.

#### F4.1 · Rate-limit `/posts/unified` (~30 min · low-risk)
Endpoint `backend/app/api/v1/endpoints/posts_unified.py` (asumido nombre · verificar).
Replicar patrón `slowapi` de otros endpoints (buscar `@limiter.limit` en codebase).

#### F4.2 · Filtros en `/hub` (~1-1.5h · UX)
Recuperar paridad con `/social` viejo. Filtros: plataforma, fecha, sentiment, dirigente.

#### F4.3 · Rotación `.env.scraping-keys` + git filter-repo (~1-2h · ALTO BLAST)
**NO autopiloto.** Sesión propia contigo. Pasos:
1. Inventariar todas las keys en `backend/.env.scraping-keys`
2. Rotar cada una en su proveedor (Apify dashboard, RADAR config, etc.)
3. Actualizar `.env` local + Coolify env vars + Vercel env vars
4. `git filter-repo --path backend/.env.scraping-keys --invert-paths`
5. `git push --force-with-lease origin feat/post-ingest-hugo-2026-05-20`
6. Coordinar con peer Hugo (puede afectar RADAR si keys compartidas)

---

### F5 · Deploy + commit + push + validación (~30 min)

#### F5.1 · Commit incremental
Un commit por fase:
- `fix(ingest): TIKTOK platform branch + UPDATE 32 posts métricas`
- `feat(workers): beat snapshot semanal · destrablock B07`
- `chore(nlp): topics rivales Saymi (Ivette+Susana)`
- `fix(api): tono_discurso en recent_posts serializer`
- `ui(dirigentes): título widget honesto + selector N=1 + sticky filter`

#### F5.2 · Push + Vercel deploy
```bash
git push origin feat/post-ingest-hugo-2026-05-20
cd frontend && vercel --prod --yes
vercel alias <deploy-url> frontend-zeta-sepia-46.vercel.app
```

#### F5.3 · Smoke prod
- `/dashboard/dirigentes/3` muestra topic-fixed métricas TT (likes>0)
- `/dashboard/aceptacion/fans-y-perfiles`: sin dropdown, sticky filter funciona
- B08 muestra comparativa real con rivales

### Gate F5
- Push exitoso
- Vercel alias respondió 200
- CEO valida visualmente (al menos uno de los 3 puntos del smoke)

---

## Criterios G1-G7 sprint

| # | Criterio | Cómo se mide |
|---|---|---|
| G1 | 32 posts TT con likes/views correctos | SQL `SELECT MIN(likes) FROM social_posts WHERE _source='ytdlp_tiktok'` > 0 |
| G2 | Mapper TT futuros runs OK | Diff `ingest_radar_yt_x_posts.py` muestra rama TIKTOK |
| G3 | recent_posts incluye tono_discurso | curl al endpoint, JSON contiene clave |
| G4 | Beat semanal snapshot activo | `celery_app.py` con entrada · `celery -A app.workers.celery_app inspect scheduled` lo lista |
| G5 | B08 SoV refleja rivales reales | `topics_cubiertos` incluye self_pct distinto a 100% |
| G6 | Frontend UX 3 fixes en prod | Visual o cURL HEAD |
| G7 | Cero RAM crash en F2 LLM batches | logs sin "ABORT" |

---

## Política RAM (heredada y vigente)

- 1 subprocess Claude `--print` a la vez
- Antes de cada batch: verificar `memory_pressure` ≤ 70% y swap activo (no reservado) ≤ 4.5GB
- F2.2 lanza secuencial: primero Ivette (44 posts), después Susana (80 posts)
- Si abort → reportar + parar fase

---

## Rollback por fase

| Fase | Rollback |
|---|---|
| F1 | `git revert` commit + `UPDATE social_posts SET likes=0,views=0,comments=0,shares=0 WHERE id IN (32 IDs)` desde log del batch |
| F2 | Beat: borrar entrada del `beat_schedule` y restart worker · Topics rivales: `UPDATE social_posts SET topics_extracted=NULL WHERE id IN (...)` por log batch |
| F3 | `git revert` commits frontend |
| F5 | `vercel rollback` al deploy anterior (alias preservado) |

---

## Diferidos explícitos (NO en este sprint)

- F4 tríada audit-full · sesión propia con CEO (BLAST alto del item #3)
- Matriz polaridad v2 Saymi 595 posts legacy (sigue diferido desde 20-may)
- Mobile audit completo
- 53 commits sin merge a `main` (decisión operativa CEO)
- F5 backlog: "Contenido con más Impacto" REAL (nuevo endpoint ORDER BY engagement_rate DESC con cap mín)
- Sprint S4 calendario INE distrital B17 real (cuando sea pedido por cliente)
- B-IG-DATACENTER-IP-1 descartado: RADAR cubre · sin acción

---

## ETA total estimada

| Fase | ETA |
|---|---|
| F1 backend SQL + script patch | 45 min |
| F2 beat semanal + topics rivales | 30 min |
| F3 frontend UX | 1.5h |
| F5 deploy + smoke | 30 min |
| **TOTAL** | **~3.5h** |

F4 tríada queda fuera de este sprint.

---

## Decisiones registradas

- **D-RADAR-TT-MAPPER-2026-05-25** · Mapper ingest TT yt-dlp confirmado por Hugo (peer RADAR). Mapeo canónico: like_count→likes, view_count→views, comment_count→comments, repost_count→shares. save_count queda en raw_data.
- **D-BEAT-SNAPSHOT-WEEKLY-2026-05-25** · Snapshot followers semanal lunes 02:00 MX. Decisión CEO sobre diario (less noise, suficiente para delta_followers B07).
- **D-WIDGET-TITLE-HONESTY-2026-05-25** · "Contenido con más Impacto" renombrado a "Publicaciones recientes" porque la query backend no ordena por impacto. Honestidad >> marketing. "Más Impacto" real backlog F5 con endpoint propio.
- **D-B17-NO-DISTRITAL-2026-05-25** · B17 actual (heurística keyword + flag global) refleja realidad y CEO lo aprueba. Calendario INE distrital diferido hasta pedido cliente.
- **D-SoV-RIVALES-TOPICS-2026-05-25** · B08 SoV requiere topics también en rivales. Correr extract_topics sobre Ivette+Susana destraba la comparativa real sin scraper de menciones externas.

---

## Cómo lanzar

```
/sprint-implement
```

Linda ejecuta autónoma con loops verificación por fase. Política RAM dura activa. Cross-audit Gemini OBLIGATORIO antes de arrancar Fase 1 si plan se considera grande.
