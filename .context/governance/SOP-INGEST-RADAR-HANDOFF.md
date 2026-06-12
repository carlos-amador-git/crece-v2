# SOP — Ingest de handoff RADAR → CRECE (cadena completa por dirigente)

**Estado:** 🟡 **NO certificado** · redactado desde ejecución real del piloto **Saymi
(dirigente_id=3)**, pendiente de auditoría independiente (Gemini, MODELO-TRABAJO-AUDIT §5).
**Autor:** AGENTE claude-opus-4-8 (sesión piloto) — el mismo que ejecutó, por lo que NO
puede auto-certificar. **Defecto detectado 2026-06-04:** el header anterior decía
"Certificado" contradiciendo el footer 🟡 — error del autor, corregido.
**Propósito:** procedimiento reproducible para ingestar un handoff de RADAR y llevarlo
end-to-end hasta planes IA. NO reconstruir el camino cada vez — seguir este SOP.

> **Regla de oro de la sesión piloto:** medir, no inferir. Cada paso se verifica con SQL
> o dry-run ANTES de afirmar. Cada claim lleva su evidencia (comando + número).

---

## 0. Precondiciones
- Backend `crece-backend` arriba (:8002) **y `crece-redis` arriba** (el login lo necesita;
  sin Redis → 500 en `/auth/login`). Levantar: `docker compose up -d redis` (sin `-v`).
- `crece-db` arriba (:5438). Backup pre-ingest **OBLIGATORIO** (postmortem S-8.1):
  `docker exec crece-db pg_dump -U crece -d crece -Fc > backups/crece-pre-radar-ingest-<TS>.dump`
- Export de Hugo en formato **POR-PLATAFORMA** (no combinado). Contrato canónico decidido
  2026-06-03: `crece_perplatform_<TS>/<slug>/` con `x_posts.json`, `yt_posts.json`,
  `tt_posts.json`, `fb_posts.json` (envelope `{platform_post_id, payload}`), `ig_posts.json`
  (aplanado), `fb_comments.json`, `ig_comments.json`, `reactors.json` (`{export_meta, reactors}`),
  `followers.json` (`{PLATFORM: count}`).
- **Archivo del dirigente = SOLO self.** Competidoras salen a `competitors_*.json` aparte
  (Hugo filtra por `target_type='self'` en la fuente). Verificar con guard (paso 1).

## 1. Guard de competidoras (antes de tocar BD)
```bash
# Confirmar que fb_posts.json NO trae handles de competidoras (author_username en payload)
python3 -c "import json; from collections import Counter; d=json.load(open('<slug>/fb_posts.json')); \
print(Counter((it.get('payload') or {}).get('author_username') for it in (d if isinstance(d,list) else d.get('posts',[]))))"
```
Si aparecen competidoras → NO ingestar, pedir a Hugo re-export self-only.

## 2. Orden de ingest (CRÍTICO)
**Followers ANTES que posts** (lección piloto: si posts van primero, su ER se computa con
followers viejos · ~1.3% desviación). Comandos host (venv), `dirigente-id` y `profile-id`
reales (`SELECT id,platform,followers_count FROM social_profiles WHERE dirigente_id=N`):

```bash
cd backend; DB=postgresql://crece:crece_dev@localhost:5438/crece

# 2.1 Followers + snapshot (cierra gap B07 · adapter creado 2026-06-03)
PYTHONPATH=. .venv/bin/python3 scripts/ingest_radar_followers.py --dirigente-id N --followers <slug>/followers.json --commit

# 2.2 Posts por plataforma (yt_x para X/YT/TT/FB · cada uno mapea a su profile)
for plat in TWITTER:x YOUTUBE:yt TIKTOK:tt FACEBOOK:fb; do
  P=${plat#*:}; PL=${plat%:*}
  DATABASE_URL_RAW=$DB PYTHONPATH=. .venv/bin/python3 scripts/ingest_radar_yt_x_posts.py \
    --json <slug>/${P}_posts.json --platform $PL --dirigente-id N --commit
done
# IG (posts + comments en un solo adapter)
PYTHONPATH=. .venv/bin/python3 scripts/ingest_radar_ig.py --dirigente-id N --profile-id <IG_PID> \
  --posts <slug>/ig_posts.json --comments <slug>/ig_comments.json --commit

# 2.3 Comments FB
PYTHONPATH=. .venv/bin/python3 scripts/ingest_radar_comments_payload.py --dirigente-id N --profile-id <FB_PID> \
  --comments <slug>/fb_comments.json --commit

# 2.4 Reactors (FB + IG · por plataforma)
DIRIGENTE_ID=N PLATFORM=FACEBOOK  DATABASE_URL_RAW=$DB PYTHONPATH=. .venv/bin/python3 scripts/ingest_radar_reactors_v2.py --json <slug>/reactors.json --commit
DIRIGENTE_ID=N PLATFORM=INSTAGRAM DATABASE_URL_RAW=$DB PYTHONPATH=. .venv/bin/python3 scripts/ingest_radar_reactors_v2.py --json <slug>/reactors.json --commit
```
**Verificar cada uno con `COUNT(*)` antes/después.** Idempotentes (UPSERT/DO NOTHING).

## 2.5 Gate de COBERTURA de reactors por fecha (OBLIGATORIO — añadido 2026-06-04)
**Por qué existe:** un `COUNT(*)` que sube NO garantiza que los reactors cubran las fechas
de los posts. Incidente 2026-06-04: Saymi tenía posts FB/IG todos los días 20/05–02/06 pero
0 reactor-events en ese rango → la gráfica "Interacción diaria" (que arma las barras con
`watched_like_events`, no con `social_posts.likes`) salía vacía. El count global había
subido (7,691 nuevos de 03/06) y se dio por bueno. El gate de count NO lo cazó.

Tras ingestar reactors, correr este check y reportar los huecos ANTES de cerrar:
```sql
WITH posts AS (
  SELECT sp.platform plat, p.id pid, p.published_at::date dia
  FROM social_posts p JOIN social_profiles sp ON sp.id=p.profile_id
  WHERE sp.dirigente_id=N AND sp.platform IN ('FACEBOOK','INSTAGRAM')
    AND p.published_at::date >= (NOW()::date - interval '45 days')
)
SELECT plat, count(*) dias_sin_react, sum(posts) posts_sin_react,
       string_agg(to_char(dia,'MM-DD'),',' ORDER BY dia) dias
FROM (
  SELECT po.plat, po.dia, count(DISTINCT po.pid) posts,
         count(DISTINCT po.pid) FILTER (WHERE wle.id IS NOT NULL) con_react
  FROM posts po LEFT JOIN watched_like_events wle ON wle.post_id=po.pid
  GROUP BY 1,2
) c WHERE con_react=0 GROUP BY plat ORDER BY plat;
```
- Si hay días con posts y 0 reactors → **NO marcar la cadena "completa"**. Reportar el hueco
  y pedir a RADAR el re-export de reactors FB/IG para esas fechas exactas (no "mándame todo").
- Solo FB/IG (X/TT/YT no exponen reactors). Posts muy recientes (<3d) pueden seguir
  acumulando → tolerar conteo bajo, NO hueco total.

## 3. NLP enrich (gateado, attended, UN solo job)
```bash
~/.claude/bin/ram-gate.sh   # exit 0 = SAFE. Si HOLD/ABORT → esperar, NO lanzar.
PYTHONPATH=. .venv/bin/python3 scripts/post_ingest_enrich.py --dirigente-id N --limit 2000 [--allow-unattended]
```
- **NUNCA lanzar más de un enrich a la vez** (lección piloto: 3 jobs concurrentes = mess).
  Verificar con `pgrep -fl post_ingest_enrich` que haya 1.
- `--dry-run` cuesta lo MISMO que el real (es LLM por item) → NO usar como preview barato.
- **Tiempos medidos Saymi** (459 posts + 162 comments delta): paso 1 Posts 927s · paso 2
  Comments 1408s · paso 3 Emotions 341s · paso 4 Topics 400s · **total ~51 min**.
- `sentiment_score` NO lo cubre este enrich (va por Celery `analyze_sentiment`) → queda ~54%.
  No bloquea emisión de D's (B05 usa emotions; B03 tolera).

## 4. Verificar emisión de los D's (base del FODA — NO saltarse)
```bash
TOK=$(curl -s -X POST :8002/api/v1/auth/login -d "username=admin@consultoriamd.com&password=crece2026!" | jq -r .access_token)
# OJO: admin necesita header X-Org-Id con la org del dirigente (si no, todo sale insufficient_data)
curl -s ":8002/api/v1/diagnostico/N" -H "Authorization: Bearer $TOK" -H "X-Org-Id: <ORG>"        # B01-B10
curl -s ":8002/api/v1/diagnostico_tier2/N" -H "Authorization: Bearer $TOK" -H "X-Org-Id: <ORG>"  # B11-B18
```
Esperar ~17/18 `ok`. `B16 promesas` sale `insufficient` salvo que el dirigente tenga
promesas curadas (`promesas_dirigente`) — gap conocido, no falla de pipeline.

## 5. Generar FODA → CONSOLIDACIÓN → CONTENIDO (LLM, gateado, 1 job)
```bash
EM=<email_dirigente>   # ej. pineda@crece.mx (VIEWER del dirigente)
PYTHONPATH=. .venv/bin/python3 scripts/regen_diagnostico_enriched_host.py --dirigente-id N --dirigente-email $EM  # FODA
PYTHONPATH=. .venv/bin/python3 scripts/regen_consolidacion_v2.py --dirigente-id N --dirigente-email $EM           # estrategia
PYTHONPATH=. .venv/bin/python3 scripts/regen_contenido_v2.py --dirigente-id N --dirigente-email $EM               # contenido
```
- Cada uno = 1 llamada CC subprocess (effort=high) → ~1-3 min. `modelo_ia` se puebla
  (INE etiquetado IA). Verificar `length(contenido)` y que el `[1/4]` traiga **followers
  reales, no 0**.

## 6. Bugs cazados en el piloto (ya corregidos · evidencia)
| Bug | Causa | Fix |
|---|---|---|
| `followers.json` sin consumidor | ningún adapter lo leía | **creado** `ingest_radar_followers.py` (patrón `tasks.py:386`) |
| D's todos `insufficient_data` | admin sin `X-Org-Id` scopea a su org | pasar `X-Org-Id: <org>` |
| Login 500 | Redis caído | `docker compose up -d redis` |
| Consolidación con `followers=0` | `regen_consolidacion_v2.py:111` pegaba a `/api/v1/aceptacion/overview` (404) | **fix** → `/api/v1/social/aceptacion/overview` |

## 7. Cierre por dirigente
- Reporte: counts antes/después por etapa · tiempos · bugs · plan_ids generados.
- `STATUS.md` append. Commit local (NO push sin OK CEO).

---
**Pendiente de auditoría Gemini independiente** (MODELO-TRABAJO-AUDIT §5) antes de marcar
`✅ cerrado`. Estado: 🟡 redactado desde ejecución real, sin auditar.
