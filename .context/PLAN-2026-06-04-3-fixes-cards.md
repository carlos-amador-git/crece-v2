# PLAN 2026-06-04 — 3 fixes cards Saymi (autónomo)

**Mandato CEO:** atender los 3 hallazgos en autónomo. Backup de hoy existe
(`backups/crece-pre-reactors-radar-20260604-185112.dump`).
**Regla rectora:** `feedback_layer_of_fix_before_refactor` — data duplicada/confusa se
arregla PRIMERO en capa API/UI, NO con DELETE en BD. Cambios reversibles. ADR donde cambie
semántica de card cliente-facing.

## Item 3 — Dedup posts misma-red (PRIMERO · CEO ya dijo "hay que corregir")
**Evidencia:** ids 7533/9694 ambos INSTAGRAM, mismo media_pk `3895666228052496021` bajo dos
esquemas (`_userid` vs pelón). Mismo post IG 2×. Patrón dual-scheme (FB num/base64, IG mediapk/mediapk_userid).
- **3a. Mostrar plataforma en las cards** (top-posts winners/losers + recepción). Permite
  distinguir dup-real (misma red) de repetición cross-red legítima (IG+FB del mismo reel).
- **3b. Dedup en capa query/API** (NO DELETE): colapsar filas mismo (platform, media_pk
  normalizado) → quedarse con 1 (id menor / más completa). IG: quitar sufijo `_userid`; FB: numeric embebido.
- Verificar: la card 12-may deja de salir 2×; conteos no se inflan.
- **Salvaguarda:** cross-plataforma (mismo contenido IG+FB) NO se colapsa — posts distintos.

## Item 1 — B01 peso por red
**Evidencia:** `PLATFORM_WEIGHTS` (legacy.py:14): TW .30 FB .25 IG .20 TT .10 YT .10. Definidos
para IPD. Trazar endpoint que arma las barras per-plataforma de la card B01.
- Si barras crudas → aplicar ponderación/normalización en capa card. ADR (reversible).
- Si ya ponderadas → reportar, no tocar.

## Item 2 — B04 competidoras asimétricas
**Evidencia:** SoV por topic 28d: Saymi 469 vs Ivette 1 vs Susana 9. No "vacío" — share ~0%.
Causa: competidoras casi sin ingest (44/80 posts) ni NLP topics.
- **Autónomo-safe:** etiquetar honestamente cobertura parcial. NO inventar data.
- **Dependencia de datos** (flag, no ejecuto solo): scraping+NLP de Ivette/Susana con Hugo.

## Orden: 3 → 1 → 2. Cada item: leer código → editar → verificar (tsc/SQL/HTTP) → reportar.
## Cierre: commit por item verificado (NO push sin OK CEO). STATUS append.
