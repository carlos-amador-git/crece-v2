# SPRINT-CURRENT — 🟢 MVP CERRADO · Fase piloto comercial activa

**Estado actual:** ✅ **MVP CRECE v2 completo y vendible** · autorización CEO 2026-04-20 post-merge PR #30 · arco MVP cerrado
**Fase activa:** PILOTO COMERCIAL (no es sprint de desarrollo)
**Ventana:** 2-3 semanas calibración con 2 dirigentes activos + 6 shadow → expansión §7.4 si calibración exitosa

**Sprint previo cerrado:** S5 · `.context/archive/sprint-s5-2026-04-20.md` · reporte `backend/research/2026-04-19/SPRINT-S5-REPORTE-EJECUTIVO.md`

**Documento operativo del piloto:** `PILOTO-COMERCIAL-TRACKING.md` (este mismo directorio)

---

## Arco MVP cerrado · resumen

| Sprint | Entregable | PR |
|---|---|---|
| S0 Validación | 6 tareas binarias + D-19 reemplazo estructural | #19 · #21 |
| Estabilización | 3 fixes pre-S1 | #22 |
| S1 Backend Foundations | 10 tareas · engagement metrics · Plan IA schema · health-check | #23 |
| Pre-S2 | Máynez + Zenodo + test Harfuch + D-23 | #24 · #25 |
| S2 Diagnóstico Tier 1 | 10 bloques B01-B10 | #26 |
| S3 Diferenciadores Tier 2 | 8 bloques B11-B18 | #27 |
| S4 Plan IA D-17 | Ciclo 5 fases + D-24 prompt 8-bloques | #28 · #29 |
| S5 Onboarding Wizard | T0 Celery + 9 pasos + HITL D-23 | #30 |

**11 PRs mergeados · 26 decisiones formales · 6 revisiones §9.8 aprobadas.**

---

## Fixes post-MVP

### 2026-04-21 · Opción D · recuperación UX/UI + scroll wheel

**Incidente:** deploy prod de `main @ f29d7db` (PR #36 · remoción de Lenis) regresionó 15 commits UX/UI no mergeados que vivían en `feat/eval-benchmark-v1` (alertas crisis sintéticas reemplazadas por reales, card tema urgente reacomodado en columna compact, tono discursivo con gráficos de líneas + toggles %/N, fixes iOS, favicon amarillo, aceptación drill-down).

**Chain de recuperación ejecutada (2026-04-21):**

1. **PR #37** · revert `f29d7db` sobre main → `6126421`
2. **Cherry-picks selectivos** de `feat/eval-benchmark-v1` sobre main:
   - `74b7b15` (alertas_crisis real) → `ffda7ec`
   - `7f44130` (mobile overflow + dashboard layout) → `9a00294` con conflict-resolved (omite `data-lenis-prevent`)
3. **PR #38 (c22f61e)** · precondiciones técnicas post cherry-pick:
   - Revert hunk `SyntheticDataBanner` a slug-based (dep de `OrgContext.config` no disponible)
   - Hunk mínimo `compact` prop en `CrisisAlertList` (extraído de `821950b`)
4. **PR #39 (5a88860)** · remove Lenis v2 (re-aplicación del fix original sobre main actualizado)
5. **Deploy prod** `2026-04-21` · URL específica `frontend-osw9z35tw-marxs-projects-bb530f2b.vercel.app` · alias `frontend-zeta-sepia-46.vercel.app` · SHA `5a88860`

**Backups remotos preservados:**
- `origin/backup/pre-opcion-d-main` @ `f29d7db`
- `origin/backup/pre-opcion-d-eval-v1` @ `3921f10`

**Deuda pendiente:** merge completo de `feat/eval-benchmark-v1` (11 commits restantes: X scrapers Apify+Scrapling+Brightdata, Oraculus + Demoscopía scrapers encuestas, aceptación drill-down por dirigente, Gemma3 Layer 2 batch, seed backfills, eval Layer 2 benchmark, 5 redes cierre integral IG+TT+FB+YT, calibración XLS). Target revisión **§9.8 intermedia 2026-05-20**.

**Nueva convención propuesta (D-27 — pendiente protocolo dos puertas):**
- `main` como único SSOT para `vercel deploy --prod`
- Prohibido deploy desde ramas sueltas con CLI local
- Toda feature branch debe mergearse a main antes de deploy

---

## Fase actual: piloto comercial

No hay sprint de desarrollo activo. Durante el piloto:

### Prioridades

1. **Observación empírica** del producto con clientes reales (2 activos + 6 shadow)
2. **Captura de feedback** como GitHub issues con label `piloto-feedback`
3. **NO reabrir decisiones estructurales** D-01 a D-24 sin protocolo §9.8
4. **Calibraciones operativas** (umbrales Topic Drift, prompt v1→v1.1, etc.) por PRs incrementales dentro del scope aprobado

### Protocolos vivos

- **Feedback cliente** → issue GitHub con label `piloto-feedback` + dirigente_id + plataforma
- **Bug crítico** producción → hotfix PR directo a main con notificación CEO
- **Decisión estructural que emerja** del piloto → protocolo §9.8 regular (Claude.ai Puerta 1 + Gemini Puerta 2)
- **Iteración prompt Plan IA** → nuevo `PROMPT-PLAN-IA-v1.X.md` con changelog obligatorio D-24

### Próxima revisión §9.8

**Día 30 del piloto** (≈ 2026-05-20): review de feedback acumulado para decidir:
- Mantener scope MVP → continuar hacia 90d métrica §7.4 métrica 1
- Ajustar scope → Sprint S6 iteración producción (estructurada)

---

## Criterios de éxito §7.4 (30/60/90 días)

Heredados del MASTER §7.4 · métricas duras de validación de mercado:

1. **3 pilotos reales** con perfiles distintos ejecutados 90d completos con contratos con fecha cierre — perfiles objetivo: 1 político activo · 1 funcionario en ejercicio · 1 empresario en transición O 1 político en precampaña
2. **≥1 recomendación Plan IA efectivamente ejecutada** por cliente con resultado medible (movimiento SoV · breakout post · reducción rage click)
3. **≥1 conversión T3 → T1 OAuth firmado** como validación de upgrade comercial en práctica

El piloto actual (Piña + Máynez · 2 políticos activos/precampaña) cumple parcialmente métrica 1. Expansión a 3 perfiles distintos requerida en Fase 2 del piloto.

---

## Protocolo de cierre del piloto (día 90)

Al día 90 se evalúa:

- ✅ Si se mueve aguja real en ≥1 caso → producto vendible · caso de estudio autovendible
- ❌ Si no → recalibración estructural antes de más inversión (posible Sprint S6)

El resultado se documenta en reporte ejecutivo final + revisión §9.8 terminal del arco MVP comercial.

---

## Enlaces operativos

- **Dashboard principal:** `/dashboard/diagnostico/{id}` (Tier 1 · 10 bloques)
- **Diferenciadores:** `/dashboard/diagnostico-tier2/{id}` (Tier 2 · 8 bloques)
- **Recomendaciones cliente:** `/dashboard/recomendaciones`
- **Admin Plan IA review (HITL):** `/dashboard/admin/plan-ia-review`
- **Onboarding wizard:** `/dashboard/onboarding/{id}`
- **Health-check LLM:** `GET /api/v1/ops/llm/health`
- **Reporte semanal PDF cron:** lunes 09:00 UTC
