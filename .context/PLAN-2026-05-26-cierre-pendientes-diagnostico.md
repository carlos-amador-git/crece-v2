# PLAN · Cierre de pendientes diagnóstico + deuda relacionada · 2026-05-26

**Origen:** CEO "no me gusta dejar pendientes pendientes" tras review visual de 8 cards. Consolidación de TODO lo real pendiente, ordenado por valor/riesgo.

**Estado base (ya hecho hoy, pusheado a origin, HEAD `bd4a54e`):**
- 8/8 cards revisadas cerradas: B18, B07, B14, B15, B03, B12, B13, B11.
- Fix de raíz `engagement_rate` en todas las rutas de ingest.
- Fix PII `author_hash` (257 filas pseudonimizadas) + guard en ingest.
- Recuperación post-apagón (túnel rotado).

**EXCLUIDO por decisión CEO:** migración a túnel nombrado estable (seguimos con quick-tunnel + rotación).

---

## F0 — Cierre inmediato (rápido, ~30 min)
- **F0.1** Actualizar STATUS.md + DECISIONS.md + memoria con los 3 commits ya hechos (PII `aab8edf`, B11 `aba8087`, B12 `bd4a54e`). → verificar: docs reflejan HEAD actual.
- **F0.2** Registrar `audit_listeners` en el Celery worker (`worker_process_init`, mismo patrón que el fix de engagement de hoy). Cierra el gap LFPDPPP: ops destructivas en tasks Celery sin auditar. → verificar: `event.contains` True en worker para los modelos auditados.

## F1 — Triage de las 10 cards sin revisar (~1-1.5h)
Inspección real (servicio + datos de Saymi/otro) de: **B01** ER · **B02** Breakout · **B04** Benchmark · **B05** Sentiment Plutchik · **B06** Crisis Spike · **B08** Share of Voice · **B09** Share/Like · **B10** Humanización · **B16** Promesas · **B17** Veda.
- Por cada una clasificar: OK / labels-inglés / calibración / datos / docstring-vs-código.
- Nota: B01 y B09 usan `engagement_rate` (hoy backfilleado) — verificar que ahora dan números correctos.
- B08 usa `topics_extracted` (ver F5).
- → entregable: tabla de hallazgos VERIFICADOS (sin especular) → alimenta F2.

## F2 — Fixes de hallazgos del triage (depende de F1)
- Aplicar el mismo trío donde aplique: labels español + calibración + datos reales.
- Un commit por card. → verificar: tsc + check-no-mocks + dato real por card.

## F3 — Calibración B12/B15 + dup vs coordinación
- **F3.1** Subir umbrales B12 (coro/maestro) y B15 para reducir falsos positivos sobre elogio genérico.
- **F3.2** Investigar si los "texto idéntico" de B12 son **duplicación de ingesta** (comparar platform_comment_id / data_source) o coordinación real. Si es dup → dedup; si es real → mantener.
- → verificar: recompute Saymi con flags solo en señales fuertes.

## F4 — Sprint palabras de moderación configurables
- Ejecutar `.context/PLAN-2026-05-26-palabras-moderacion-config.md` (tabla `palabras_moderacion` categoría+severidad+scope, seed, B18/B15 leen de BD, CRUD admin + "Probar"). Default scope=exacta.

## F5 — Backfill `topics_extracted` para dirigentes != Saymi
- Saymi 93%, global 42%. Correr extracción de topics para el resto → destrabar B14 composición + B08 SoV para todos los clientes. → verificar: fill >85% por dirigente activo.

## F6 — Deuda pre-existente (CEO prioriza cuáles)
- Mobile audit completo · N+1 stress test BFF · Error Boundaries frontend · matriz polaridad v2 legacy · **merge de ~58 commits `feat/post-ingest-hugo-2026-05-20` → `main`** (decisión operativa).

## Dependencia externa (no bloquea, tracked)
- **B07 datos reales** ← RADAR (Hugo): persiste timeseries follower_count, CRECE ingiere a `social_profile_snapshots`. Hugo lo retoma tras cerrar 3 MC + Felipe.

---

## Orden propuesto de ejecución
`F0` (rápido, cierra LFPDPPP) → `F1` (triage, define el resto) → `F2` (fixes) → `F3` → `F5` → `F4` → `F6`.

**Criterio de éxito global:** 18/18 cards validadas contra datos reales · 0 PII cruda · 0 gaps LFPDPPP conocidos · docs al día.

---

## Cross-audit Gemini (FASE 2 · integrado 2026-05-26)
- **Veredicto:** viabilidad alta, orden lógico, prioriza LFPDPPP.
- **Riesgo #1 (adoptado):** F5/F1 antes de confirmar dup → procesar basura. **→ F3.2 (dup vs coordinación) sube a F0.3, ANTES de triage/backfill.**
- **Riesgo #2 (notado, no reordena):** merge 58 commits al final. Es outbound (esta rama→main), autor único, sin otra rama tocando ingesta → riesgo bajo. F6 se queda al final.
- **Mejora #3 (adoptado):** F5 backfill topics en chunks de 100 + sleeps para no saturar Celery.

**Orden ejecución revisado:** F0.1 docs → F0.2 audit_listeners worker → **F0.3 dup investigation** → F1 triage → F2 fixes → F3 calibración → F5 (chunked) → F4 → F6.
