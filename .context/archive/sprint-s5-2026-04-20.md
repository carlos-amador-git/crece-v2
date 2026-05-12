# SPRINT-CURRENT — Sprint S5 Onboarding Wizard Meta OAuth (cierre MVP)

**Sprint actual:** S5 · **Status:** 🟢 EN EJECUCIÓN · autorizado CEO 2026-04-20 post-smoke S4
**Sprint previo:** S4 · `.context/archive/sprint-s4-2026-04-19.md` · PR #29 merged (`e924fb2`)
**Decisiones vinculantes:** D-22 · D-23 · D-24 · scoping `backend/research/2026-04-19/SPRINT-S5-SCOPING.md`

**Al cierre S5 → MVP completo vendible** (Tier 1 + Tier 2 + Plan IA D-17 + Onboarding comercial)

---

## T0 · BLOQUEANTE · Migrar /plan-ia/generate a Celery worker (DIFERIDO-06)

CEO 2026-04-20: hang silencioso en endpoint FastAPI con httpx.AsyncClient + host.docker.internal. Pipeline funciona vía docker exec (Agent A: 4 recs reales). Resolver antes de Onboarding por consistencia con cierre_service.py (Celery pattern).

### T0.1 Refactor
- [ ] Nueva Celery task `plan_ia_generate_async` invocando `PlanIAPipeline.generate()`
- [ ] Endpoint `POST /plan-ia/generate/{dirigente_id}` encola task + poll interno 180s · devuelve 200 con recs o 504 timeout
- [ ] Logs: task_id, queued_at, started_at, completed_at, n_recomendaciones

### T0.2 Smoke binario
- [ ] `curl -X POST /plan-ia/generate/1?force=true` → HTTP 200 OK
- [ ] Response con ≥1 recomendación
- [ ] Roundtrip <180s warm
- [ ] DB tiene N nuevas filas estado='propuesta'

Falla → debug antes Onboarding. 2-3h estimado.

---

## S5 Core · 9 secciones Onboarding

1. **Detección perfil §1.5** — 4 opciones (político_activo · funcionario · precampaña · empresario)
2. **Input manual URLs** (flujo primario D-23) — por plataforma IG/FB/X/TikTok/YouTube
3. **SERP asistido opcional** (client-driven) — Brightdata primary + Apify fallback
4. **Validación profiles Apify** — score confianza (full_name +0.4 · verified +0.3 · fw>50K +0.2 · posts>20 +0.1 · umbral ≥0.7)
5. **Confirmación humana OBLIGATORIA** (D-23 regla dura) — checkbox explícito por candidato
6. **Meta OAuth activable** — IG/FB (Meta Graph) + TikTok Business + YouTube Data · X queda T3 permanente (D-19)
7. **Seed competidores** (D-22) — cliente declara 3-5 · libera bloque #04
8. **Seed promesas** (D-17) — libera B16
9. **Activación + resumen** — data_fidelity_tier preview + trigger scrape_all_profiles

---

## Criterio acceptance S5

1. T0 verde: curl endpoint 200 OK con recs persistidas <180s
2. 9 secciones wizard navegables
3. Confirmación humana obligatoria pre-scraping (checkbox)
4. 1 dirigente end-to-end en wizard (demo)
5. OAuth Meta activo ≥1 plataforma
6. Competidores + promesas populadas vía wizard
7. E2E Playwright cubre flujo completo

Con 6/7 → **MVP vendible** · piloto comercial autorizable.

---

## Paralelización

- **Agent A** (backend): T0 Celery migration + smoke
- **Post-T0 Agent B** (backend): secciones 2-8 backend (SERP + profile validation + OAuth + seed endpoints)
- **Post-T0 Agent C** (frontend): wizard UI 9 pasos + E2E

Clock estimado 3-5 días D-23 ajustado.

## Protocolo cierre

Archivar S5 · `SPRINT-S5-REPORTE-EJECUTIVO.md` · revisión §9.8 final MVP.
