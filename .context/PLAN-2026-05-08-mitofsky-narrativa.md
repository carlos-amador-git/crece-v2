# PLAN — Sprint Mitofsky encuestas (Linda · 2026-05-08)

**Origen:** `/sprint-implement` post-decisión D-25-A + flags Juan post-confirmación CEO.

## Constraint actualizado (post-flag Juan)

**Coolify VPS es CPU-only x86** (evidencia: STATUS.md mide >17 min/iter, smoke
plan-IA Ballesteros timeout 540s, doc memory `reference_coolify_services.md`).

Implicación sobre D-25-A:

| Modo | Estado real |
|---|---|
| A · texto narrativo gemma3:12b | ✅ viable en CPU (post async, batch nocturno) |
| B · OCR tesseract + gemma3:12b | ⚠️ viable pero precisión OCR cuestionable; deprio |
| C · vision LLM en Coolify | ❌ INVIABLE en CPU (45-90 min/imagen × 127 posts × ~3 imgs) |
| D · vision API pago | ❌ vetado por CEO |

**Vía nueva (Juan flag 3):** si charts Wix tienen JSON inline → ningún LLM necesario.

## Sprints

### S1 · JSON inline check (10-30 min) — KEYSTONE

**Objetivo:** descubrir si charts en Wix Mitofsky son render JS desde dataset
JSON inline en `<script>` (similar a Oraculus/AS-COA).

**Archivos:** ninguno (research only).

**Criterio de aceptación:**
- ✅ 3 posts inspeccionados (gobernadores reciente, aprobación presidencial, alcaldes)
- ✅ Si JSON encontrado: documentar selector + ejemplo
- ✅ Si no encontrado: salto a S2 con confianza

### S2 · PNG URLs catalog (10 min) — Linda turf determinístico

**Objetivo:** producir `crece-v2/captures/mitofsky-png-urls.json` con shape
`{post_url, post_date, chart_urls[], post_title}` × 127 posts.

**Archivos:** `backend/scripts/mitofsky_catalog_pngs.py` (nuevo).

**Criterio de aceptación:**
- ✅ Sitemap parseado (349 posts → 127 relevantes)
- ✅ JSON output >100 entries con chart_urls
- ✅ Filtro descarta social icons (w_28) — chart imgs son `~mv2.png`

### S3 · Modo A scraper narrativa (1-2h)

**Objetivo:** scraper Python que por cada post:
1. Descarga HTML
2. Extrae body article (BS4)
3. Identifica sentences con datos %
4. Llama Coolify Ollama gemma3:12b vía httpx con prompt estructurado:
   ```
   Extrae: fecha (YYYY-MM-DD), ámbito (federal/estatal/municipal),
   metrica (aprueba/desaprueba), actores mencionados con valor_pct,
   promedio_nacional (si existe). Output JSON.
   ```
5. Mapea response a `EncuestaRow` (shape `encuestas_publicas`)
6. UPSERT idempotente con dedupe `(fuente, fecha, actor, metrica)`

**Archivos:**
- `backend/app/scrapers/encuestas_mitofsky_narrativa.py` (nuevo)
- `backend/scripts/scrape_mitofsky_narrativa.py` (orchestrator)

**Criterio de aceptación:**
- ✅ Coolify Ollama responde 200 con JSON estructurado en al menos 4/5 smoke
- ✅ Tiempo por post < 2 min (gemma3:12b texto en CPU es ~30-90s típico)
- ✅ Schema válido contra `EncuestaRow`

### S4 · Smoke + insert + validate (30 min)

**Objetivo:** ejecutar scraper contra 5 posts, validar inserts.

**Criterio de aceptación:**
- ✅ Inserted > 0
- ✅ Total `encuestas_publicas` aumenta
- ✅ Sin duplicados (dedupe respeta UNIQUE-like)
- ✅ Posts mensuales históricos contribuyen (no solo el más reciente)

### S5 · Reporte (15 min)

Update STATUS.md, DECISIONS.md, mensaje al CEO con métricas finales.

## Branches

- **Si S1 finds JSON inline:** S2/S3 reemplazados por scraper directo JSON. S4 sigue.
- **Si S1 vacío + Coolify Ollama timeout en smoke (S3):** abort modo A, escalar
  CEO con opción HF Inference API free tier (Juan sugerencia) o aceptar 825 rows
  como cierre.

## Dependencies

S1 → S2/S3 (paralelos pueden correr) → S4 → S5.
