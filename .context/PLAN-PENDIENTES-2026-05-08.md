# PLAN integrado de pendientes CRECE v2 — 2026-05-08

**Owner consolidación:** Linda (CRECE-electoral)
**Próximo gate forzoso:** §9.8 día 30 piloto ≈ **2026-05-20** (faltan 12 días)
**Ventana antes del gate:** ~12 días con cargas asignables

Este plan unifica los pendientes vivos en CRECE v2. No incluye trabajo de Joy
(CRECE-Negocios, turf separado) ni de Juan/Pau (md-research, md-design-system).

## 0. Categorización de pendientes

| Categoría | Items | Bloqueante para piloto §9.8 |
|---|---:|---|
| Frontend findings F-06..F-15 | 9 | No (nice-to-have) |
| Encuestas (post-Mitofsky-4-sprints) | 5 | No (corpus 2254 ya supera baseline piloto) |
| Infra: deploy Ollama 4B/7B en Coolify | 1 | **Sí** — desbloquea SG-AI Juan + clones Pau |
| UX/visual cinematic CRECE | 1 | No (Fase C post-piloto) |
| Decisiones CEO pendientes | 3 | Variable (depende de cuál) |
| Operación recurrente | 2 | Sí (TW replies cron) |
| Cleanup post-refactor | 1 | No |

---

## 1. PRIORIDAD ALTA — bloqueantes o cercanos al gate

### P1.1 · Deploy Ollama smaller model en Coolify
**Origen:** Plan A aprobado por CEO 2026-05-08 (canal Pau md-design-system).
Juan midió `gemma3:12b` ~2 tok/s en CPU = subdimensionado. Bloquea SG-AI
Tributo Huasteco (Juan), pipeline cloning tools (Pau), y modo A vision Mitofsky
si en algún momento se reabre.

**Acciones:**
1. Coordinar slot con CEO (preferible >22h CDMX, baja carga CRECE)
2. Linda admin Coolify → `ollama pull qwen2.5:7b-instruct` (preferido sobre `gemma3:4b` por mejor manejo español + structured output)
3. Smoke contra `/api/generate` con prompt corto (tok/s objetivo: ≥10)
4. Pau valida con `caso-c-structured-data/c1_crawl4ai_ollama.py` (5 min)
5. Juan re-corre SG-AI smoke contra modelo nuevo
6. Documentar en `reference_coolify_services.md`

**Esfuerzo:** 30-60 min activos · **ROI:** ALTO (desbloquea 2 pipelines)
**Owner:** Linda
**Ventana:** Coordinable hoy o mañana

### P1.2 · TW replies recurring schedule
**Origen:** smoke con monkey-patch xclid validado en sprint TW replies 2026-05-08.
701 inserts una sola corrida. Sin schedule recurrente, los TW replies se
estancan tras cada deploy.

**Acciones:**
1. Decisión CEO: Celery beat (preferida) vs cron host
2. Si Celery beat: añadir task en `backend/app/workers/celery_app.py`
   con `crontab(minute=15, hour='*/6')` (4×día)
3. Verificar `crece-celery-beat` y `crece-celery-worker` se levanten en stack
4. Logs a `data_source='twscrape-replies-v1'` para idempotencia
5. Smoke en sandbox antes de prod

**Esfuerzo:** 1.5h · **ROI:** ALTO (operativo, no manual)
**Owner:** Linda
**Bloqueante:** Decisión CEO Celery vs cron

### P1.3 · Backup cleanup post-refactor multi-stage
**Origen:** memoria `project_disk_cleanup_pending.md` —
`crece-v2-backend:pre-cleanup-2026-05-01` ocupa 19.4 GB. Eligible para borrado
tras validar 48h post-refactor multi-stage (ya pasaron, hoy es 2026-05-08).

**Acciones:**
1. Verificar refactor multi-stage estable (smoke build + tests)
2. `docker rmi crece-v2-backend:pre-cleanup-2026-05-01`
3. Liberar 19.4 GB disco
4. Update memoria

**Esfuerzo:** 5 min · **ROI:** medio (disco)
**Owner:** Linda
**Riesgo:** ninguno si la imagen actual está estable (ha estado 7 días en uso)

---

## 2. PRIORIDAD MEDIA — frontend findings F-06..F-15

Findings nice-to-have del review visual 2026-04-21 (post-screenshots CEO).
Cerrados parcialmente (F-01..F-07) en hotfix `#34`. F-06..F-15 siguen abiertos
como Fase C post-piloto.

| Finding | Descripción | Estimado | ROI |
|---|---|---:|---|
| F-06 | Agrupar Tier 2 semánticamente (Autenticidad · Calidad · Compliance) | 1h | medio |
| F-08 | Plan IA cards más compactas + drawer/expand | 2h | medio |
| F-09 | B01 y B06 ejes Y mejor etiquetados | 30 min | bajo |
| F-10 | B16 Promesas · timeline hechas vs cumplidas | 2h | medio |
| F-11 | Tooltips descriptivos en números grandes | 1.5h | medio |
| F-12 | Settings routing · consolidar 4 rutas en tabs | 1h | bajo |
| F-13 | Plan IA post-hotfix validación coherente | 30 min | medio |
| F-14 | Histórico empty state mejorado | 30 min | bajo |
| F-15 | Admin HITL columna "Días en espera" + warning >24h | 1h | medio |
| F-16 | Typeahead Harfuch paso 7 — **DIFERIDO §6.4** | — | — |

**Total esfuerzo F-06..F-15:** ~10h
**ROI agregado:** medio
**Owner:** Linda + frontend-architect agent
**Cuándo:** post-§9.8 día 30 (Fase C). Ventana actual demasiado corta para
abordar 9 findings antes del gate sin riesgo a piloto.

---

## 3. PRIORIDAD MEDIA — encuestas (post-corpus 2254)

Documentados en `docs/SCRAPERS-ENCUESTAS.md §7`. Recap:

| # | Item | Esfuerzo | ROI | Bloqueante |
|---|---|---:|---|---|
| E.1 | AS/COA via Playwright | 3h | bajo (CSP ya cubierto Mitofsky+Oraculus) | No |
| E.2 | Mitofsky 4 PDFs failed parse layouts edge case | 2h | bajo (4/105 = 4% pérdida) | No |
| E.3 | Mitofsky alcaldes individual 150 | 3-4h | medio (políticos seguidos en piloto) | No |
| E.4 | PollsMX paginación histórica (sitemap real o crawler) | 3h | medio (intención voto 2027) | No |
| E.5 | Demoscopía auditoría (solo 11 rows parece bajo) | 1-2h | medio (puede haber bug) | No |

**Total esfuerzo E.1-E.5:** ~12-14h
**Recomendación:** ejecutar E.5 (auditoría 1-2h, alta probabilidad de bug
silencioso) y E.4 (PollsMX histórico, +N filas intención voto 2027 = relevante
para gate §9.8) **antes** del 2026-05-20. E.1, E.2, E.3 difieren a Fase C.

---

## 4. PRIORIDAD MEDIA — UX/visual cinematic

### V.1 · PLAN-OUTSTANDING-CRECE.md
**Origen:** propuesta UX/UI 2026-05-07 (sin tracking, sin commit, sin ejecutar).
4 fases: De-cluttering Glassmorphism · Factoría assets IA visual · Hero Login
scroll-tied · Pulido micro-interacciones.

**Análisis crítico:**
- Pro: visualmente impactante, diferenciador comercial CRECE
- Con: requiere assets IA visual (Luma/Runway) — costo cash no presupuestado
- Con: scroll-tied playback con GSAP — performance budget en mobile a verificar
- Con: piloto MC CDMX prefiere serenidad institucional sobre cinematografía

**Recomendación:** ejecutar como **proyecto Fase C post-piloto** (post 2026-05-20).
No usar ciclos pre-gate. Coordinable con frontend-architect agent + diseño Pau.

**Esfuerzo:** Fase 1 (de-cluttering) ~3h · Fase 2 ~2h producción + 1-2 días render IA · Fase 3 ~6h · Fase 4 ~3h. Total ~14-16h dev + assets.
**ROI:** alto comercialmente, bajo para piloto MC actual.

---

## 5. PRIORIDAD VARIABLE — decisiones CEO pendientes

| Decisión | Impacto | Bloqueante |
|---|---|---|
| Índice de Aceptación propuesta 2026-04-13 (memoria `project_indice_aceptacion_propuesta.md`) | Alto si se implementa: nueva métrica activación/expansión/aceptación/fantasmas por post | No (sistema actual funciona) |
| Triangulación NLP Layer 2 v3 — opciones C/B/A 2026-04-18 | Medio: refinamiento clasificación comments | No (Layer 1 sigue corriendo) |
| Real Users Roster — 4 nuevos políticos (memoria `project_real_users_roster.md`) | Alto: piloto se extiende de 2 → 6 dirigentes | Sí si se quiere antes del gate §9.8 |

**Acción Linda:** elevar las 3 al CEO para decisión expresa antes de gate
§9.8. Si decide "no" en cualquiera, marcar resuelta y archivar.

---

## 6. PRIORIDAD VARIABLE — operación recurrente

| Item | Esfuerzo | Bloqueante |
|---|---:|---|
| TW replies cron schedule (P1.2 arriba) | 1.5h | Decisión CEO |
| Refresh Apify 7 dirigentes — schedule recurrente | 1h dev + costo Apify | Decisión CEO sobre frecuencia (semanal? mensual?) |
| Audit data_quality post cargas | 30 min | No |

---

## 7. Propuesta de orden de ejecución (12 días pre-gate)

**Esta semana (8-12 mayo):**
1. P1.1 deploy Ollama 7B Coolify (30-60 min, slot CEO)
2. P1.3 backup cleanup (5 min)
3. P1.2 TW replies cron (1.5h, post decisión Celery vs cron)
4. E.5 Demoscopía auditoría (1-2h)
5. Decisiones CEO §5 (15 min reunión + decisión documentada)

**Subtotal:** ~5h activas Linda + ~30 min CEO

**Próxima semana (15-20 mayo, pre-gate):**
6. E.4 PollsMX paginación histórica (3h)
7. F-13 Plan IA post-hotfix validación coherente (30 min — quick win)
8. F-15 Admin HITL columna Días en espera (1h — útil para gate review)
9. Reset condicional según decisiones §5

**Subtotal:** ~5h activas Linda

**Post-gate §9.8 (2026-05-20+):**
10. Encuestas E.1, E.2, E.3 (8-9h)
11. Frontend F-06, F-08, F-10..F-12, F-14 (~6h)
12. V.1 Outstanding cinematic Fase 1-4 (~14-16h)

---

## 8. Riesgos identificados

| # | Riesgo | Mitigación |
|---|---|---|
| R1 | Deploy Coolify Ollama 7B falla por RAM/CPU del VPS | Sanity test antes (`free -h`, `top` desde Coolify shell). Rollback `ollama rm` |
| R2 | TW replies cron interfiere con login users en horarios pico | Schedule a 03h/09h/15h/21h CDMX (no horarios coincidentes con uso pico) |
| R3 | Decisiones CEO §5 se posponen y bloquean gate §9.8 | Pre-elevar a CEO con propuesta concreta + recomendación, no preguntas abiertas |
| R4 | Backup cleanup borra imagen aún necesaria | Verificar último deploy contra refactor multi-stage. `docker images` antes y después |
| R5 | E.4 PollsMX paginación da datos noisy (regex frágil) | Smoke contra 5-10 artículos antes de full run. Aceptar si captura ≥60% comparado contra ground truth manual |

---

## 9. Pendientes que NO entran en este plan

Por turf separado (no es Linda CRECE-electoral):
- CRECE-Negocios B2B → Joy (PRD v0.1, GBP OAuth, Tributo Huasteco)
- ScrapeGraph-AI eval, PollsMX/AS-COA from md-research → Juan
- Cloning tools comparison → Pau (md-design-system)
- B3 Maps reviews → Juan

Por estar resueltos / archivados:
- D-25-A vision stack Mitofsky (obsoleta tras hallazgo PDF)
- Sprint NLP framework manual (commit `118ce13`)
- Sprint B aceptación dashboard (PR #12)
- Hotfix pre-piloto F-01..F-05 + F-07 (PR #34)
