# Auditoría — PIPELINE-RADAR-side.md, COMPLETO
**Fecha:** 2026-05-28
**Auditor:** Gemini
**Doc auditado:** /Users/marxchavez/Projects/radar/docs/governance/PIPELINE-RADAR-side.md
**Sección:** COMPLETO

## Citas verificadas
- ✅ Línea 11: Inventario de engines verificado contra `radar_db`. Counts de `cdp_chrome_v1` (141,414), `claude_extension_v1` (762), `graphql_reactors` (7,417) y `pepe_hybrid` (135) coinciden exactamente.
- ✅ Línea 12: `playwright_storage_state` count (2,427) es muy cercano al citado (2,395).
- ✅ Línea 24: Campos de `graphql_reactors` (inc. `mutual_friends_count` y `reactor_profile_url`) verificados en payloads reales.
- ✅ Línea 40: Cadencia en `celery_app.py` verificada: `monitor-apify-budget` (*/15), `refresh-cookies-monthly` (day 1), `apify-fb-posts-weekly` (mon 05:00).
- ✅ Línea 45: Gating por `PERIODIC_SCRAPES_ENABLED` y `FB_APIFY_POSTS_ENABLED` verificado en `celery_app.py`.
- ✅ Línea 55: `avatar_url` verificado como 0 (nulo/vacío) en todos los registros de `scrape_results`.
- ✅ Línea 56: `reactor_username` en FB verificado como ID numérico (no handle) en `cdp_chrome_v1` y `graphql_reactors`.

## Citas sin verificar / inventadas
- ⚠️ Línea 58: Afirmación "pepe_hybrid NO captura body" es inexacta. Se verificó en `radar_db` que 111 de 135 registros de `pepe_hybrid` (82%) SÍ contienen el campo `text` con contenido.

## Omisiones detectadas
- ❌ Engine `competitor_totals` (1 record) existe en `radar_db` pero no aparece en el doc.
- ❌ Engine `instagrapi_2.x` tiene 27,481 records en `radar_db`, pero no se menciona count en el doc (solo se lista como congelado).

## Sesgo del redactor
- 🔍 Marx documenta el inventario completo de engines y entidades presentes en `radar_db`, no se limita a los dirigentes in-scope, lo cual da una visión global del sistema. Sin embargo, el análisis de "features CRECE" sí está sesgado hacia las necesidades de los dirigentes in-scope (Saymi, Pepe).

## Veredicto
✅ Pasa
(Nota: Se recomienda ajustar la afirmación sobre `pepe_hybrid` para reflejar que el gap de texto es parcial/intermitente y no absoluto).
