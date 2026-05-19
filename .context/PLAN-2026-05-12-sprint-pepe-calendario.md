# PLAN · Sprint 2026-05-12 noche · Pepe Monroy + Calendario Efemérides

**Generado:** 2026-05-12 noche
**Mandato CEO:** `/sprint-implement FULL` · luz verde para ejecución autónoma
**Branch:** `feat/phase-b-pesos-editables` · HEAD `7139218`
**Base estable de deploy:** `88486ba` (Vercel cherry-pick desde aquí, evitar WIP `a366d78` que rompe build)

---

## Resumen ejecutivo

Sprint mixto que combina:
1. **Cierre de pendientes** del bloque anterior (G-1 snapshot cron + G-3 B10-2 neutro/institucional)
2. **Onboarding cliente independiente** Pepe Monroy + proyecto PAZ (org nueva, dual-env Vercel + Coolify)
3. **Feature completa** calendario de efemérides mexicanas con generación de post IA, aplicado a TODOS los dirigentes

Total estimado: 6-7 horas continuas. Tier 1 (mínimo viable) ~3h · Tier 2 (full UX + integración planes) ~3h.

---

## Doctrina nueva confirmada por CEO 2026-05-12

**Vercel = staging-prueba** (validación de features antes de promover)
**Coolify = demo final** (lo que se muestra a stakeholders post-validación)
**Mac Mini :8002** = backend único, expuesto vía cloudflared a Vercel y vía VPS a Coolify.

Antes (2026-05-11) era "Vercel=piloto, Coolify=demo". Ahora se ratifica: Vercel queda como **staging del piloto**; Coolify queda como **demo final** (lo que el cliente y stakeholders ven).

---

## Fases

### FASE 1 · Quick wins (~40 min)

| # | Tarea | Criterio aceptación | Tiempo |
|---|---|---|---|
| S1.1 | G-1 ejecutar `scrape_all_profiles` 1× manual | `social_profile_snapshots` ≥1 fila por dirigente activo | 10 min |
| S1.2 | G-3 backend: separar Neutro de Institucional en `humanizacion_service.py` | posts sin señal devuelven categoría `Neutro`, no penalizan score | 15 min |
| S1.3 | G-3 frontend: card B10 muestra "X analizados / Y sin marcador" | UI honesta del denominador efectivo | 10 min |
| S1.4 | `DECISIONS.md` · D-HUMANIZ-NEUTRO-1 | Texto + diff archivos | 5 min |

### FASE 2 · Pepe Monroy onboarding (~90 min)

| # | Tarea | Criterio aceptación | Tiempo |
|---|---|---|---|
| S2.1 | Org PAZ + Dirigente Pepe + User pmonroy@paz.mx | login 200 + JWT con dirigente_id correcto | 20 min |
| S2.2 | `social_profiles` IG + FB con followers iniciales del OG (16K IG / 10.9K FB) | 2 filas en social_profiles | 5 min |
| S2.3 | Sync inicial IG vía instaloader (paralelo S2.4) | ≥5 posts + 1 snapshot | 25 min |
| S2.4 | Sync inicial FB vía scraper o fallback OG (paralelo S2.3) | followers + posts, o blocker documentado | 20 min |
| S2.5 | Validación en Vercel | login pmonroy@paz.mx → /diagnostico/{id}/tier1 → 200 + cards renderan | 10 min |
| S2.6 | Mensaje Carlos Coordinación Coolify | Texto preparado, NO ejecutado | 5 min |

### FASE 3 · Calendario efemérides (FULL, ~3-4h)

| # | Tarea | Criterio aceptación | Tiempo |
|---|---|---|---|
| S3.1 | Modelo `Efemeride` + migration | tabla creada, migration aplicada | 30 min |
| S3.2 | Seed 80+ fechas (calendario CEO) | `COUNT(*) FROM efemerides ≥ 80` | 30 min |
| S3.3 | Endpoint `GET /calendario/proximas` | scope multi-tenant, ordenado proximidad | 25 min |
| S3.4 | Card frontend `EfemeridesProximas` | lista 5 próximas + tooltip ideas | 40 min |
| S3.5 | Endpoint `POST /calendario/sugerir-post` + Claude API | draft persiste en contenidos_generados + ia_content_registry | 60 min |
| S3.6 | Modal `SugerirPostModal` frontend | editor + counter chars + copy | 45 min |
| S3.7 | Integración a `planes_ia` mensuales | tareas tipo efemeride en plan_tareas | 45 min |
| S3.8 | Test E2E Día del Maestro 15-may | 2 drafts distintos (Jiménez vs Pepe) | 30 min |

### FASE 4 · Deploy + cierre (~45 min)

| # | Tarea | Criterio aceptación | Tiempo |
|---|---|---|---|
| S4.1 | Commits por fase (4 commits limpios) | git log mostrarables | 15 min |
| S4.2 | Cherry-pick + `vercel deploy --prod` | alias `frontend-zeta-sepia-46` reasignado, 200 OK end-to-end | 10 min |
| S4.3 | Push branch + msg Carlos para Coolify | mensaje preparado | 5 min |
| S4.4 | `DECISIONS.md` + `BLOCKERS.md` + `STATUS.md` | 4 D-* nuevas + STATUS actualizado | 15 min |

---

## Recursos asignados

- **Backend (sentiment, calendario, scrapers):** python-expert (yo, single session)
- **Frontend (cards, modal):** frontend-architect (yo, single session)
- **BD + migrations:** backend-architect inline
- **LLM integration:** claude-api skill + servicio existente plan_ia
- **Deploy:** Vercel CLI + cherry-pick

NO Agent Team (over-engineering; mayoría dependencias secuenciales).

---

## Cross-audit Gemini · ejecutado 2026-05-12 noche

**Veredicto Gemini:** ROJO con 5 hallazgos.

**Hallazgos integrados al plan:**
- 🔴 (invalidado) Vercel/Coolify comparten BD: Coolify tiene SU propia BD en VPS, no comparte con Mac Mini.
- 🔴 (aceptado) Modelo `Efemeride` usa `mes INT + dia INT` para recurrencia anual.
- 🟡 (aceptado) Scrapers S2.3 + S2.4 ejecutan secuencialmente, no paralelo. Máx 3 posts iniciales.
- 🟡 (aceptado) S1.1 (`scrape_all_profiles`) se mueve a FASE 4 post-Pepe para no quemar IP antes del onboarding.
- 🟡 (aceptado) Prompt LLM S3.5 inyecta: nombre + org + partido + tono humanización + plataforma.
- 🟢 (aceptado) Reorden FASE 3: S3.1 → S3.2 → S3.3 → S3.5 (endpoint) → S3.4 (card) → S3.6 (modal) → S3.7 → S3.8.

Plan ajustado y se procede a ejecución.

---

## Riesgos identificados (amarillos)

| Riesgo | Mitigación |
|---|---|
| Scraper IG/FB falla para Pepe Monroy | Fallback OG-only para poblar followers; dejar posts vacíos con disclaimer |
| Claude API rate-limit en S3.5 al testear 9 dirigentes × Día del Maestro | Test 2 dirigentes (Jiménez + Pepe) en S3.8; resto se diferirá si necesario |
| WIP `a366d78` impide deploy desde HEAD | Cherry-pick desde `88486ba` (ya validado en sesión anterior) |
| Tunnel quick cloudflared caduca | Documentar como blocker B-TUNNEL-1; reiniciar si cae mid-sprint |

---

## Acuerdo de autonomía

- Modo autónomo activado por `/sprint-implement FULL`
- Si un riesgo amarillo se realiza y bloquea: paro y reporto, no bandaid
- Updates al CEO solo en hitos clave (final de fase) o blocker real
- Reporte final actualiza STATUS.md + DECISIONS.md + BLOCKERS.md

---

## Tareas trackeadas

Tasks #1-#18 creadas en sistema interno. Updates via TaskUpdate al completar cada sub-sprint.
