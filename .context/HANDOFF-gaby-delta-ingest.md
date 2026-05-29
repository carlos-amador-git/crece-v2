# HANDOFF — Ingest + Enrich delta NUEVO de Gaby (dir 5) · 2026-05-27

Para ejecutar APARTE (con Gemini, sin gastar tokens CC). Datos ya extraídos de radar_db :5453.

## Datos (archivos listos)
Carpeta: `~/Projects/crece-v2/backend/data/gaby_delta/`
| archivo | n |
|---|---|
| fb_posts.json | 84 |
| tt_posts.json | 100 |
| x_posts.json | 130 |
| ig_posts.json | 100 |
| fb_comments.json | 122 |
| ig_comments.json | 223 |
(TT comments = 0, gap del burner; no hay nada que ingestar ahí.)

Gaby = **dirigente_id 5**. Sus profiles: `TWITTER=10, INSTAGRAM=11, FACEBOOK=12, TIKTOK=13`.

## Paso 1 — INGEST (adapters · NO usan CC ni Gemini, puro Python/SQL)
Desde `cd ~/Projects/crece-v2/backend`. Idempotentes (ON CONFLICT → solo persiste lo nuevo).
```bash
DB="postgresql://crece:crece_dev@localhost:5438/crece"
# posts FB / X / TT  (adapter yt_x · requiere DATABASE_URL_RAW)
DATABASE_URL_RAW=$DB PYTHONPATH=. .venv/bin/python scripts/ingest_radar_yt_x_posts.py --json data/gaby_delta/fb_posts.json --platform FACEBOOK --dirigente-id 5 --commit
DATABASE_URL_RAW=$DB PYTHONPATH=. .venv/bin/python scripts/ingest_radar_yt_x_posts.py --json data/gaby_delta/x_posts.json  --platform TWITTER  --dirigente-id 5 --commit
DATABASE_URL_RAW=$DB PYTHONPATH=. .venv/bin/python scripts/ingest_radar_yt_x_posts.py --json data/gaby_delta/tt_posts.json --platform TIKTOK   --dirigente-id 5 --commit
# posts + comments IG  (adapter ig · profile 11)
PYTHONPATH=. .venv/bin/python scripts/ingest_radar_ig.py --dirigente-id 5 --profile-id 11 --posts data/gaby_delta/ig_posts.json --comments data/gaby_delta/ig_comments.json --commit
# comments FB  (adapter comments_payload · profile 12)
PYTHONPATH=. .venv/bin/python scripts/ingest_radar_comments_payload.py --dirigente-id 5 --profile-id 12 --comments data/gaby_delta/fb_comments.json --commit
```
Verificar en el output de cada uno: `inserted`/`ingestables` > 0 y `huérfanos` razonable. (Nota: el contador "inserted" cuenta INTENTOS; los dups por re-scrape caen en ON CONFLICT y NO persisten — el número real es el de filas únicas, ver Paso 3.)

## Paso 2 — ENRICH NLP con GEMINI (sin CC)
Los sub-scripts intentan CC primero y caen a Gemini si `CLAUDE_BIN` no existe. Forzar Gemini:
```bash
CLAUDE_BIN=/nonexistent CC_EFFORT=medium PYTHONPATH=. .venv/bin/python scripts/post_ingest_enrich.py --dirigente-id 5
```
- Idempotente (`WHERE col IS NULL` → solo el delta nuevo; no re-procesa lo ya enriquecido de Gaby).
- Fallback Gemini = `/opt/homebrew/bin/gemini --sandbox --approval-mode plan -p`.
- ✅ Confirmado: los 4 sub-scripts (backfill_nlp_posts, backfill_nlp_saymi, backfill_emotions_cc, extract_topics_saymi_cc) tienen fallback Gemini → `CLAUDE_BIN=/nonexistent` fuerza Gemini en TODOS. Cero CC.

## Paso 3 — VERIFICAR (filas NETAS reales, no el contador del adapter)
```bash
PGPASSWORD=crece_dev psql -h localhost -p 5438 -U crece -d crece -tA -c "SELECT 'posts='||COUNT(sp.id)||' tono='||COUNT(sp.tono_discurso)||' emo='||COUNT(sp.emotions)||' top='||COUNT(sp.topics_extracted) FROM social_profiles spr JOIN social_posts sp ON sp.profile_id=spr.id WHERE spr.dirigente_id=5;"
# comments: JOIN social_comments sc ON sc.parent_post_id=sp.id ; COUNT(sc.nlp_tono)
```
Pipeline completo documentado en `.context/RUNBOOK-ingest-enrich-pipeline.md`.
