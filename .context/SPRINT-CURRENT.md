# SPRINT-CURRENT — Sprint S1 Backend Foundations (calibrado post-S0) ✅ CERRADO 2026-04-19

**Función:** documento vivo del sprint actualmente en ejecución. Cualquier sesión Claude Code lee PRIMERO este documento después de NORTH-STAR.

**Sprint actual:** S1 · **Status:** ✅ COMPLETADO 2026-04-19 14:06 CDT · **Arranque S2 disponible** pendiente autorización CEO
**Reporte ejecutivo:** `backend/research/2026-04-19/SPRINT-S1-REPORTE-EJECUTIVO.md`
**Sprint previo cerrado:** S0 · 2026-04-19 · archivo `.context/archive/sprint-s0-2026-04-19.md` · reporte `backend/research/2026-04-19/SPRINT-S0-REPORTE-EJECUTIVO.md`
**Decisiones vinculantes pre-arranque:** D-19 reescrita post-dictámenes (**reemplazo estructural** de Gemini DR · tabla IM commercial descartada · matriz 5×5 + temporalidad electoral + dataset Zenodo MX) · D-20 (cierre S0) · D-21 (Coolify dual-mode) en MASTER §6. Dictámenes convergentes en `.context/external-review/dictamen-01-*.md` y `dictamen-02-*.md`

---

## Contexto pre-arranque

Sprint S0 cerró 2026-04-19 con 5 PASS + 1 AMBIGUO + 0 FAIL. Sprint S1 arranca con alcance expandido de MASTER §5 S1 incorporando **3 recomendaciones no bloqueantes derivadas de S0** (ajustes operativos, no redefinición de scope):

1. **Consumo directo de `settings_strata.json`** (T0.2 output) por la tarea T2 — evita ingreso manual de estratos
2. **Migration `likes_count` + `views_count` + cron `scrape_followers_daily`** — cierra gap de ingeniería de datos que hizo incomputable el criterio binario T0.2 y habilita recalibración D-19
3. **Pre-warm SLA Ollama Coolify** como requisito operativo en el health-check failover (T0.6 output + D-21)

Estas adiciones NO renumeran las tareas 1-9 del MASTER §5 S1. Se integran como requisitos explícitos dentro de las tareas existentes (T1 consume seed, T3 añade columnas y cron, T8 implementa SLA dual-mode).

---

## Requisito transversal de reproducibilidad (heredado de S0)

Cada artefacto generado en S1 debe incluir:
- `system_prompt` exacto cuando haya LLM involucrado
- `temperature=0.0` y seed donde aplique
- Modelo + versión específicos (ej. `gemma3:12b-q4_K_M`)
- Paths absolutos de inputs/outputs
- Timestamp + autor

---

## Tareas (10)

### T1 — Migration `dirigentes` + `social_profile_snapshots` extendida
- [ ] Alembic migration: añadir a `dirigentes` los campos `data_fidelity_tier` (JSON por plataforma), `estrato_politico` (enum Nano/Micro/Mid/Macro/Mega), `competidor_directo_ids` (array FK), `data_origin` (enum T1/T2/T3)
- [ ] Alembic migration: añadir a `social_profile_snapshots` el campo `data_origin_checkpoint` (timestamp nullable) para marcar la transición T3→T1 post-OAuth (§4.5 MASTER)
- [ ] **Consumo directo:** T1 debe leer `backend/research/2026-04-19/settings_fidelity.json` como seed del campo `data_fidelity_tier` (40 celdas iniciales)

### T2 — Seed manual estratos + competidores
- [ ] **Consumo directo de `backend/research/2026-04-19/settings_strata.json`** como seed inicial del campo `estrato_politico` para los 8 dirigentes (seed mínimo — el estrato en sí sobrevive; la **tabla de rangos** por estrato queda descartada por D-19 reescrita y se sustituye por matriz 5×5 del MASTER §3.1 #01 pendiente de calibración vía dataset Zenodo en T10)
- [ ] Seed manual de `competidor_directo_ids` por dirigente (pares políticos mismo rango + geografía): pendiente definir lista — **requiere 30 min de input CEO o research previo**
- [ ] Commit `scripts/seed_strata_competidores.py` reproducible
- [ ] **Importar matriz 5×5 provisional** del MASTER §3.1 #01 a `settings_strata_matrix.json` con celdas 🟡 TBD explícitas (todas las 25 por default hasta validación en T10)

### T3 — **[AJUSTE S0 #2]** Engagement metrics + cron followers diario
- [ ] Alembic migration: añadir a `social_posts` los campos `likes_count`, `views_count`, `shares_count`, `comments_count` (todos integer nullable)
- [ ] Adaptar runners de scraping (Apify IG/FB/TikTok/YT + Scrapling X) para poblar estos campos cuando estén disponibles en la respuesta
- [ ] Cron daily `scrape_followers_snapshot_daily` que actualiza `social_profile_snapshots` con `followers_count` por plataforma para los 8 dirigentes
- [ ] Smoke test: 1 corrida manual + verificación de que al menos 5 dirigentes tienen snapshot de hoy
- [ ] **Recalibración D-19:** al terminar T3 con snapshots acumulados ≥30d, recomputar ER real y validar delta vs tabla Gemini DR provisional. Si delta >30% en ≥3 dirigentes → reabrir D-19 y recalibrar `settings_strata.json`

### T4 — Persistencia `views` desde output Apify
- [ ] Integrado en T3 — si la migration ya añade `views_count` y los runners lo pueblan, T4 es verificación: una prueba de scraping produce `views_count` poblado en 1 post IG + 1 X + 1 TT
- [ ] Dashboard backend endpoint `GET /api/v1/posts/{id}/engagement` que devuelve los 4 campos poblados

### T5 — Topic extraction Gemma 3:12b
- [ ] Servicio `backend/app/nlp/topic_extractor.py` que consume Gemma 3:12b local (D-15/D-16) con seed fijo de 12 topics validado en S0 T0.4 (kappa 0.810, precisión 75%)
- [ ] Migration: añadir `topics_extracted JSONB` a `social_posts`
- [ ] Reutilizar prompt exacto documentado en `backend/research/2026-04-19/t04_prompt.txt` (temperature=0.0, seed=42)
- [ ] Procesar muestra de 50 posts del corpus 2026-04-19 y persistir topics
- [ ] Endpoint `GET /api/v1/posts/{id}/topics` funcional

### T6 — Migration `recomendaciones_plan_ia` (por D-17)
- [ ] Alembic migration con schema completo de §6.3.2 MASTER (18 columnas + 3 índices compuestos)
- [ ] Sin data seed — la tabla se puebla en Sprint S4 al generarse la primera recomendación
- [ ] Test: crear, transicionar estados, query por dirigente+estado

### T7 — Endpoint ARCO LFPDPPP (por D-18)
- [ ] `POST /api/v1/admin/compliance/purge-hash` que elimina recursivamente comments + embeddings + vectores asociados a un `author_hash_sha256`
- [ ] Audit log obligatorio en tabla `compliance_purge_audit` (timestamp + admin_id + hash + count_purged)
- [ ] Test: crear 5 comments con hash X, ejecutar purga, verificar cascada en vector store
- [ ] Doc: actualizar `docs/AVISO-PRIVACIDAD-CRECE.md` con procedimiento operativo

### T8 — **[AJUSTE S0 #3]** Health-check Ollama con pre-warm SLA (D-21)
- [ ] Servicio `backend/app/ops/llm_health.py` con 3-layer check:
  - Layer 1: ping `/api/tags` timeout 2s
  - Layer 2: smoke inference timeout 60s warm / 180s cold
  - Layer 3: pre-warm cada 4h via cron (00:00 y 04:00 y 08:00 y 12:00 UTC)
- [ ] Endpoint `GET /api/v1/ops/llm/health` devuelve `{primary: ok, failover: ok, last_inference_ms, circuit_state}`
- [ ] Circuit breaker: si Mac M4 falla >3 min → switch automático a Coolify VPS
- [ ] Alerta (log o webhook) si primario **Y** failover simultáneamente DEGRADED
- [ ] Tabla `llm_health_log` con al menos 4h de datos de prueba
- [ ] Consumir SLOs documentados en `backend/research/2026-04-19/coolify_failover_smoke.md`

### T9 — CONDICIONAL T1.9 refinamiento Plutchik
- [ ] **Estado:** ❌ NO ACTIVAR — S0 T0.4 cerró con Kappa 0.810 (supera 0.65 holgadamente, D-20)
- Si en producción la kappa observada cae <0.65 sobre >200 comments nuevos, reabrir T1.9 con criterio de cierre binario del MASTER §5 S1

### T10 — **[NUEVA por D-19 reescrita]** Dataset Zenodo benchmarks ER políticos mexicanos
- [ ] Pipeline de agregación: consumir snapshots de T3 (≥30d cuando disponibles) + likes/views/shares por post para los 8 dirigentes piloto
- [ ] Calibración matriz 5×5 estrato × plataforma de MASTER §3.1 #01 con percentiles p25/p50/p75 por celda en ventana 90d fuera de pre-comicio (modificador temporal=1.0)
- [ ] Marcar celdas 🟢 VALIDATED (n≥30 + IC95%) vs 🟡 TBD en `settings_strata_matrix.json`
- [ ] Generar bundle reproducible en `backend/data/zenodo/v1/`: `benchmarks_er_politicos_mx_v1.csv` + `methodology.md` + `code.zip` + `LICENSE` (CC BY 4.0)
- [ ] Publicar en Zenodo con DOI asignable (cuenta MD Consultoría) · etiquetas: `political-communication`, `mexico`, `engagement-rate`, `benchmark`, `CRECE-v2`
- [ ] Actualizar MASTER §3.1 #01 + §8.7 reemplazando citas IM commercial (Hootsuite/Rival IQ/Emplifi/Sprout Social) por el propio DOI como fuente de referencia
- [ ] **Tolerancia de scope:** si al cerrar S1 solo hay 10 de 25 celdas 🟢 VALIDATED, publicar como "v1 preliminar" con TBD explícitos; v2 en S2 al acumular más data

---

## Paralelización operativa recomendada

Agrupación sugerida para ejecución concurrente:

- **Bloque A (infra data):** T1 + T2 + T3 + T4 — son migrations y seed, secuenciales entre sí pero independientes de T5-T8
- **Bloque B (LLM + compliance):** T5 + T6 + T7 — cada uno aislado, paralelizables
- **Bloque C (ops):** T8 — aislado
- **Bloque D (post-data):** T10 — depende de T3 acumulando snapshots; se arranca el pipeline en paralelo, la calibración final ocurre cuando haya ≥30d de data
- Clock estimado secuencial: 9-12h · paralelo con 3 agents: ~5-7h (Zenodo v1 preliminar)

---

## Criterio acceptance del Sprint S1

Sprint S1 se declara completo cuando:

1. 8 dirigentes tienen `data_fidelity_tier` poblado con las 40 celdas de `settings_fidelity.json`
2. 8 dirigentes tienen `estrato_politico` poblado con `settings_strata.json`
3. Cron daily corre 1 vez manual y escribe snapshots de followers
4. Muestra de ≥50 posts con `topics_extracted` poblado
5. Tabla `recomendaciones_plan_ia` creada con test de transición de estados
6. Endpoint purge-hash operativo con 1 test de purga completa
7. Health-check Ollama dual-mode operativo con circuit breaker activo + pre-warm cron instalado
8. D-19 calibración: matriz 5×5 `settings_strata_matrix.json` existe con al menos ceildas TBD marcadas; si hay ≥30d de snapshots, al menos 10/25 celdas 🟢 VALIDATED
9. Dataset Zenodo v1 preliminar preparado (bundle listo) — publicación con DOI opcional si hay data suficiente, diferible a S2 en caso contrario

Con 8/9 dura (puntos 8+9 pueden quedar en watch con v1 preliminar) → arranque Sprint S2 autorizado.

---

## Protocolo de actualización

1. **Al inicio de cada tarea:** marcar `- [ ]` → `- [x]` + notas debajo
2. **Al completar tarea:** `- [x]` + link al output generado
3. **Al cerrar sprint:** rellenar `HANDOFF.md` con 5 preguntas + archivar este `SPRINT-CURRENT.md` a `.context/archive/sprint-s1-YYYY-MM-DD.md` + resetear para Sprint S2

**Nunca hay 2 sprints activos en este documento.**
