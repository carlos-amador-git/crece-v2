# Scripts archivados

Archivos restaurados desde git history que conservamos como **referencia**, no
están en el flujo activo. Se rescataron 2026-05-07 durante arqueología tras
descubrir que múltiples scrapers desaparecieron en cleanups previos.

## Inventario

### Brightdata (cuenta del CEO actualmente "Customer is not active")

Si Brightdata se reactiva (saldo, billing), estos scripts retoman trabajo
inmediatamente. NO eliminar antes de confirmar que la cuenta queda muerta.

- `brightdata_browser_service.py` — wrapper Service del Brightdata Scraping Browser
- `brightdata_facebook_comments.py` — FB comments dataset `gd_lkay758p1eanlolqw8`
- `brightdata_fb_comments_from_posts.py` — variante FB comments (input por URL de post)
- `brightdata_fb_posts.py` — FB posts dataset `gd_lkaxegm826bjpoo9m5`
- `brightdata_twitter_replies_test.py` — TW replies (sandbox)
- `brightdata_youtube_comments.py` — YT comments dataset `gd_lk9q0ew71spt1mxywf`
- `recover_brightdata.py` — utility para recuperar snapshots Brightdata caídos

### TW alternativas

- `twscrape_profile.py` — TW profile scraper via twscrape (alternativa a Apify
  delicious_zebu). Útil si se reactiva TW replies background con cuentas auth.

### NLP benchmarks históricos

- `benchmark_gemma_layer2.py` — bench Gemma3:12b vs alternativas. Útil cuando
  se evalúe migración de modelo NLP.

### Ingester manual (depende del flujo CEO devtools)

- `ingest_laura_twitter_replies.py` — ingester de archivos JSON producidos por
  flujo manual chrome-devtools del CEO. Solo útil cuando el CEO produzca otro
  batch JSON con devtools.

## Cuándo restaurar a flujo activo

Mover de `_archive/` a `backend/scripts/` (su path original) cuando:
- Brightdata se reactive y se quiera retomar el stack BD
- Se planifique sprint dedicado a TW replies background con twscrape
- Se haga benchmark NLP comparativo (Gemma vs Claude vs otros)

## NO archivado, eliminado completamente (en git history)

- `seed_comments.py` — seed inicial obsoleto, ya hay datos
- `fase1_backfills.py` — backfills Fase 1 ya aplicados
- `import_resultados_2024.py` — datos electorales antiguos cargados via otro flujo
- `export_calibration_samples.py` — calibración legacy

Cualquiera puede recuperarse con:
```
git log --all --oneline -- 'backend/scripts/<nombre>.py'
git show <commit>:backend/scripts/<nombre>.py > <path destino>
```
