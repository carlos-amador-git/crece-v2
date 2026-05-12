# F0.2 E2E Baseline · Tests Playwright smoke rutas críticas 2026-04-23

**Plan origen:** `.context/PLAN-recuperacion-post-incidente-2026-04-21.md` F0.2
**Workflow CI:** `.github/workflows/e2e-smoke.yml`
**Target:** Vercel Preview deployment (CEO guard: opción b)
**Scope MVP:** 4 rutas piloto críticas

---

## Rutas cubiertas en CI MVP

| Ruta | Spec(s) que la ejercitan | Estado esperado |
|---|---|---|
| `/login` | `pages.spec.ts:12,41,48,62` + todas las specs (auth shared) | ✅ verde |
| `/dashboard` | `pages.spec.ts:79,98,112,121,176` | ✅ verde |
| `/dashboard/diagnostico/{id}` (Tier 1) | `diagnostico.spec.ts` (6 navegaciones) | ✅ verde |
| `/dashboard/diagnostico-tier2/{id}` (Tier 2) | `diagnostico-tier2.spec.ts` (9 navegaciones) | ✅ verde |

---

## Known failures esperadas post-F1.1 (NO intentar fixear ahora)

Estas rutas están rotas desde la migración destructiva `3d6fe3f1660d_add_resultados_electorales_seccion_2024` (2026-04-18) que dropeó 14 tablas + 23 columnas. Solo se restauran cuando F1.1 (Schema restauración post-3d6fe3f) se ejecute con revisor §9.8 per D-OPS-10.

| Ruta | Razón del fallo | Resuelve con |
|---|---|---|
| `/dashboard/aceptacion` | Endpoint backend 500 por tablas framework dropeadas | F1.1 migración manual restaura `contexto_politico`, `framework_matrix_defaults`, `framework_overrides_org`, `framework_audit_log` |
| `/dashboard/admin/overview` | Endpoint backend 500 por `dirigentes.rol_politico` column dropeada | F1.1 restaura `dirigentes.rol_politico` + LFPDPPP `data_access_log` |
| `/dashboard/admin/classification/*` | Depende de framework tables | F1.1 |
| `/dashboard/admin/plan-ia-review` | Solo parcial — plan-ia-flow.spec.ts cubre este · no incluido en MVP por scope CEO guard "4 rutas piloto" | — |

**Convención:** cuando F1.1 se aplique y estos endpoints retornen 200, agregar specs dedicadas en `.github/workflows/e2e-smoke.yml` (línea "Run piloto smoke specs"). No antes.

---

## Specs NO incluidos en MVP (cobertura existente pero out-of-scope)

Estos specs existen en `frontend/e2e/` pero no corren en el CI MVP por no cubrir las 4 rutas piloto según CEO guard. Pueden activarse después.

| Spec | Cubre | Activación futura |
|---|---|---|
| `onboarding-wizard.spec.ts` | `/dashboard/onboarding/{id}` 9 pasos | Agregar a CI cuando Máynez complete onboarding |
| `plan-ia-flow.spec.ts` | `/dashboard/admin/plan-ia-review` + `/dashboard/recomendaciones` | Activar post-F1.1 + revisor §9.8 |
| `plan-kanban.spec.ts` | `/dashboard/planes` kanban | Activar cuando se estabilice Sprint 24 rewrite copy |
| `visual.spec.ts` | Regresión visual | Activar post-F1.1 con baseline Playwright actualizada |

---

## Flujo del workflow

1. CEO/dev push a branch → Vercel detecta commit → deploya preview → publica deployment_status event al repo
2. GitHub Actions escucha `deployment_status` con `environment=Preview` y `state=success`
3. Workflow resuelve `BASE_URL = github.event.deployment_status.target_url`
4. Corre las 3 specs MVP contra esa URL
5. Si falla: sube `playwright-report/` + `test-results/` como artifact (7 días retención)
6. Summary muestra BASE_URL + specs corridas + recordatorio de known failures

---

## Dependencia crítica: Vercel-GitHub App

Para que `deployment_status` llegue al repo, **Vercel-GitHub App debe estar instalada y autorizada sobre `MarxCha/crece-v2`**. Si no lo está:
- El workflow nunca dispara por `deployment_status`
- Fallback: usar `workflow_dispatch` manualmente con BASE_URL override

### Verificación CEO

Antes de dar por cerrado F0.2, verificar en [GitHub Settings → Installed GitHub Apps](https://github.com/settings/installations):
- Vercel está listada
- Tiene acceso al repo `MarxCha/crece-v2`
- El proyecto Vercel `frontend` (ID `prj_vZRkADGGGaq5V23gS8jm8hgJcNXI`) está enlazado a este repo

Si falta instalación: el CEO autoriza desde Vercel dashboard → Settings → Git → Connect repo.

---

## Test manual de verificación (criterio éxito F0.2)

Tras hacer merge del PR con el workflow:
1. Abrir PR nuevo trivial (fix de 1 línea en `README.md` o similar)
2. Vercel deploya preview → publica deployment_status
3. Workflow dispara y corre las 3 specs
4. Todas 4 rutas piloto pasan verde
5. Log del workflow muestra BASE_URL = URL preview Vercel
6. Cerrar PR (o mergearlo si el fix es trivial)

Criterio éxito: **las 4 rutas piloto verdes en CI automático tras `git push` de commit nuevo**.

---

## Known failures registradas tras primer run real

_(se actualizará tras primera corrida con resultado real)_

| Ruta | Spec | Error | Fecha | Siguiente paso |
|---|---|---|---|---|
| | | | | |

---

## Registrado por

Claude Code · sesión 2026-04-23 · post-meta-fix + F0.1 diagnóstico binario (Bugsink roto, en `.context/OBSERVABILITY-STATE-2026-04-23.md`).
