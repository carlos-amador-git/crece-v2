# PLAN · Recuperación y consolidación de branches CRECE

**Fecha:** 2026-05-09
**Sprint:** Branches recovery + consolidación a main
**Owner:** Linda + sub-agents · revisión CEO entre fases
**Origen:** Hallazgo 2026-05-09 — commit `0681153` (benchmark 4H×4M humano + Oraculus + Demoscopía) en `origin/feat/eval-benchmark-v1` nunca llegó a main ni a HEAD actual. Se identifica deuda de merge: **13 ramas no-mergeadas a main**, riesgo recurrente de "trabajo perdido".
**Estado:** PROPUESTO — Fase 1 lista para arrancar autónoma. Fases 2-4 requieren decisión CEO entre cada paso.

---

## Diagnóstico estructural verificado

| Hecho | Evidencia |
|---|---|
| Commit `0681153` (14-abr) creó benchmark 4H×4M completo | `feat(encuestas+eval): Oraculus + Demoscopía scrapers + benchmark 4H×4M` |
| Ramas que contienen el commit | `origin/feat/eval-benchmark-v1` · `origin/backup/pre-opcion-d-eval-v1` |
| Branch `main` | NO contiene el commit |
| Branch actual `feat/phase-b-pesos-editables` | NO contiene el commit |
| Archivos del commit ausentes en HEAD | 33 / 33 |
| Branches not-merged a main | 13 (incluye eval-benchmark-v1 + 12 más) |

**Causa raíz:** PR #38 (`fix(frontend): technical preconditions post eval-v1 cherry-pick`) hizo cherry-pick parcial. PR #37 (`revert: remove Lenis (will be reapplied after eval-v1 merge)`) implicó merge planeado que nunca ocurrió. Branch quedó huérfano.

---

## Filosofía del plan

- **Tiempo no es limitante; calidad es.** Sin atajos.
- **Solo lectura en Fase 1.** Inventario antes de cualquier acción.
- **CEO decide rama por rama** (Fase 2). Nada se mergea sin confirmación.
- **PRs pequeños y verificables** (Fase 3). CI verde obligatorio.
- **Política nueva** (Fase 4) para que la situación no se repita.

---

## Fases

### FASE 1 · Inventario forense (~2-3 h, lectura solo)

**Estado:** propuesto · puede arrancar autónoma porque no toca código

**Objetivo:** Producir matriz auditable de las 13 ramas not-merged con datos suficientes para que CEO tome decisión informada por cada una.

**Entregable:** `.context/BRANCHES-INVENTORY-2026-05-09.md` con tabla:

| Columna | Significado |
|---|---|
| rama | nombre branch |
| última actividad | fecha último commit |
| commits únicos vs main | `git log main..<branch>` count |
| LOC neto | `git diff main...<branch> --stat` |
| archivos únicos | lista paths que NO existen en main |
| migrations alembic | sí/no, hash de revision |
| schema BD | columnas/tablas nuevas |
| tests | nuevos tests + estado pasa/falla en branch |
| trabajo activo en otro lado | sí/no — si lo de esta rama ya quedó superado |
| dependencias entre ramas | si una rama depende de otra |
| recomendación | merge / cherry-pick / archive / re-trabajar |
| razón | por qué la recomendación |

**Sprints:**

| Sprint | Acción | Aceptación | Tiempo |
|---|---|---|---|
| F1.1 | Setup `BRANCHES-INVENTORY-2026-05-09.md` con header + 13 sub-secciones (1 por rama) | MD existe con estructura | 15 min |
| F1.2 | Por cada rama: ejecutar `git log main..<branch> --oneline` + `git diff main...<branch> --stat` + listar archivos únicos | 13 secciones llenas con datos crudos | 60 min |
| F1.3 | Por cada rama: identificar migrations alembic, schema BD, tests | Cada sección con flags ✅/❌/⚠️ | 30 min |
| F1.4 | Cross-reference entre ramas: ¿hay dependencias? ¿una superó a otra? | Sección "Dependencias y conflictos" en MD | 30 min |
| F1.5 | Recomendación + razón por cada rama | Cada sección con `Acción: <merge\|cherry-pick\|archive\|re-trabajar>` y razón | 30 min |
| F1.6 | Resumen ejecutivo + plan de orden de acción | 5-10 bullets al inicio del MD para CEO | 20 min |

**Asignación:** general-purpose agent en mode read-only. Una sola pasada autónoma. Output completo en MD.

**Gate Fase 1:** CEO revisa MD y aprueba/ajusta recomendaciones antes de Fase 2.

---

### FASE 2 · Decisión CEO + plan de acción (CEO-driven, sin código)

**Estado:** bloqueado por Fase 1

**Objetivo:** Para cada rama, decisión cerrada y orden de operaciones.

**Sprints:**

| Sprint | Acción | Owner |
|---|---|---|
| F2.1 | CEO revisa `BRANCHES-INVENTORY-2026-05-09.md` y marca cada rama con su decisión final | CEO |
| F2.2 | Linda documenta plan de orden secuencial (qué se mergea primero, dependencias) en `BRANCHES-RECOVERY-PLAN-2026-05-09.md` | Linda |
| F2.3 | CEO aprueba plan secuencial | CEO |

**Gate Fase 2:** plan secuencial firmado por CEO antes de Fase 3.

---

### FASE 3 · Ejecución consolidación (PRs ordenados, CI verde)

**Estado:** bloqueado por Fase 2

**Objetivo:** Ejecutar el plan secuencial. PRs pequeños, CI verde, tags de rollback.

**Patrón por cada rama a recuperar:**

1. Crear PR fresco contra main: `recover/<descripcion>` desde el branch original
2. Resolver conflictos manualmente (preservar trabajo posterior)
3. CI verde obligatorio: pytest backend + npm typecheck + npm build + alembic upgrade head smoke
4. Review (auto-review documentando trade-offs)
5. Merge a main
6. Tag `recovery-2026-05-09-NN` con descripción
7. Archive del branch origen: `git tag archive/<branch> <branch>` + push tag + delete branch
8. Update `.context/STATUS.md` post-merge

**Variantes según decisión Fase 2:**

- **MERGE rama completa** → patrón anterior
- **CHERRY-PICK selectivo** → PR con commits específicos
- **ARCHIVE** → solo `git tag archive/<branch> <branch>`, no PR
- **RE-TRABAJAR** → tickets nuevos en `.context/BACKLOG.md`, branch original archivado

**Después de las 13 ramas:** mergear `feat/phase-b-pesos-editables` (current branch) a main como cierre.

**Sprints:** estructurados según plan F2 (lista variable de PRs, ~30-90 min cada uno).

**Gate Fase 3:** main contiene todo el trabajo válido + tags de archivo en su lugar + CI verde en main HEAD.

---

### FASE 4 · Política operativa (~2 h docs)

**Estado:** bloqueado por Fase 3

**Objetivo:** Reglas para que esto no se repita.

**Sprints:**

| Sprint | Acción | Entregable |
|---|---|---|
| F4.1 | Documentar política de branches en `CONTRIBUTING.md` | Política con regla "máximo 7 días de vida por feature branch antes de merge o archive" + checklist |
| F4.2 | PR template `.github/PULL_REQUEST_TEMPLATE.md` | Checklist: migration aplicable a main · tests pasando · docs actualizadas · ¿afecta piloto? |
| F4.3 | Branch protection main (revisar permisos GitHub) | Config: CI obligatorio · review requerido · no force-push |
| F4.4 | CI gate "branch divergence": fail si rama diverge >30 commits de main | `.github/workflows/branch-divergence-check.yml` |
| F4.5 | Skill `/branch-audit` semanal: ejecuta inventario de Fase 1 automatizado | Script `backend/scripts/branch_audit.py` + cron weekly |
| F4.6 | Update `.context/DECISIONS.md` con D-OPS-NN documentando la política | Decision record permanente |

**Gate Fase 4:** política documentada + automatización mínima + CEO informa al equipo.

---

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Conflictos masivos al mergear branches viejas a main | Procesar de menos divergente a más divergente; preservar trabajo posterior siempre |
| Migrations alembic incompatibles entre branches | Fase 1 detecta migrations conflictivas; Fase 2 decide consolidación |
| Romper piloto activo durante Fase 3 | Tag de rollback antes de cada merge; smoke test post-merge en staging |
| BD diverge entre branches (schema diferente) | Fase 1 audita schema por rama; Fase 2 decide migration de consolidación |
| Tests rotos en branches viejas | Fase 1 reporta estado; si el código vale, se actualiza tests durante Fase 3 |
| 13 ramas demasiadas para 1 sesión humana | Plan procesa de a 3-4 por sesión, multi-día está OK |
| CEO no disponible para Fase 2 (gate humano) | Plan se pausa esperando, no bloquea trabajo paralelo en otras tareas |

---

## Criterio de éxito final

1. ✅ `main` contiene todo el trabajo válido (incluido benchmark 4H×4M humano)
2. ✅ 13 ramas not-merged resueltas (mergeadas, archivadas, o re-tickadas)
3. ✅ Tags de archivo `archive/<branch>` para preservar historia sin contaminar tree
4. ✅ Inventario `BRANCHES-INVENTORY-2026-05-09.md` con razón documentada por cada decisión
5. ✅ Política `CONTRIBUTING.md` + branch protection main + CI gate divergencia
6. ✅ `/branch-audit` semanal automatizado
7. ✅ CEO firma cierre del proceso

---

## Decisiones cerradas (no preguntar)

1. ✅ Fase 1 puede arrancar autónoma — solo lectura, sin riesgo
2. ✅ Fases 2-4 requieren gate CEO explícito entre cada una
3. ✅ NO mergear todo a main de un jalón — PRs pequeños y verificables
4. ✅ NO descartar branches sin auditoría — todo se evalúa con datos
5. ✅ Tags `archive/<branch>` para preservar historia en lugar de delete crudo
6. ✅ `feat/phase-b-pesos-editables` (current) se mergea al final como cierre del proceso
