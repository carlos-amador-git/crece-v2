## ⚠️ DEPRECATED — Ver `PLAN-recuperacion-post-incidente-2026-04-21.md`

**Este documento es el borrador v1 (Joy pre-Gemini cross-audit).**

Preservado por trazabilidad histórica. Fue rechazado por Gemini review (2026-04-21) por overplanning (14 sprints para equipo de 3) + orden seguridad/UX invertido + cherry-pick D.2 riesgo repetir `3d6fe3f1660d` + observabilidad ausente.

**Plan canónico vigente:** `.context/PLAN-recuperacion-post-incidente-2026-04-21.md` (v3 · 3 Frentes · CEO + Claude.ai + Gemini aprobado).

---

# PLAN post-review frontend 2026-04-21 · Fases + Sprints cortos

**Creado:** 2026-04-21 (noche, post PR #42 D-OPS-07..10)
**Autor:** Joy (borrador) · pendiente cross-audit Gemini + aprobación CEO
**Contexto crítico:** Revisor §9.8 (Claude.ai) al límite de uso **hasta jueves 2026-04-23**. D-OPS-10 vigente = cualquier cambio a `backend/migrations/`, `backend/app/models/`, o endpoints con SQL debe esperar a que vuelva el revisor.

---

## Resumen ejecutivo

**Scope total:** 5 fases · ~14 sprints cortos de 1-3 días cada uno · ventana total ~4-6 semanas efectivas (piloto + §9.8 intermedia).

**Distribución:**

| Fase | Ventana | Sprints | Entregable macro |
|---|---|---|---|
| **A** · Fix críticos + restauración schema | 2026-04-22 → 2026-04-24 | 3 | 🔴 CRÍTICOS resueltos + schema restaurado |
| **B** · UX/UI consolidación frontend | 2026-04-24 → 2026-05-02 | 5 | 🟠 funcionales + design system coherence |
| **C** · Seguridad endpoints (Frente 3) | 2026-05-05 → 2026-05-12 | 3 | D-SEC-03/04 cerradas + 25 endpoints auditados |
| **D** · §9.8 intermedia + merge eval-v1 | 2026-05-13 → 2026-05-20 | 2 | Fase 3 GIS + Fase 4 NLP + D-OPS-03 formalizada |
| **E** · Backlog post-piloto | 2026-05-21 → 2026-07-19 (§9.8 terminal 90d) | 1 | 🟢 nice-to-have + Prompt v1.1 + §7.4 métricas |

**Políticas vigentes durante todo el plan:** D-OPS-07..10 + D-PILOTO-01..03 + D-GATE-01..07 + D-SI-01..04 + todas las D-?? previas en main.

---

## Fase A · Fix críticos + restauración schema (3 sprints, ~3 días)

**Objetivo:** cerrar los 🔴 críticos del review frontend + desbloquear las 4 rutas rotas por migración destructiva `3d6fe3f1660d` (D-OPS-07).

### Sprint A.1 · Fixes ortográficos + branding (0.5 día · Joy sola, **puede hoy mismo o mañana**)

**Entregables:**
- F-46 `"Iniciar sesion"` → `"Iniciar sesión"`
- F-47 `"Contrasena"` (label + placeholder) → `"Contraseña"`
- F-48 `"ConsultoriaMD"` → `"MD Consultoría"` (login lado izquierdo)

**Alcance:** 1 archivo `frontend/src/app/login/page.tsx` + posibles strings en locale file si existe.

**Requiere revisor §9.8:** NO. Solo frontend, sin schema.

**Criterio de éxito:** Login prod muestra acentuación correcta verificado visualmente.

**PR:** `fix(login): acentuación española + branding MD Consultoría`

### Sprint A.2 · `FODA[D]:` literal expuesto (1 día · Joy sola)

**Entregables:**
- F-28 `FODA[D]:` en Kanban de Plan IA → reemplazar por etiqueta humana o ícono
- Analizar si el patrón se repite en otros bloques (F-57 `B11 T2`..`B18 T2`) — si sí, incluir en este sprint o separar a Sprint B.1.

**Alcance:** `frontend/src/components/planes/kanban-board.tsx` + `frontend/src/components/planes/plan-tareas-list.tsx` + posibles traducciones tag→label humano.

**Criterio:** ningún código interno `FODA[X]`, `B##`, `§3.6` visible al cliente.

**PR:** `fix(ux): reemplazar nomenclatura técnica por labels humanos (F-28 + F-57)`

### Sprint A.3 · Restauración schema Fase 1+2 conjunta (2 días · REQUIERE revisor §9.8 · **jueves mínimo**)

**Entregables:**
- Migración compensatoria `xxxx_restore_political_framework.py` (escrita a mano, NO autogenerate per D-OPS-08)
  - Restaurar `dirigentes.rol_politico` column
  - Recrear tablas `contexto_politico`, `framework_matrix_defaults`, `framework_overrides_org`, `framework_audit_log`
  - Re-correr `seed_political_framework.py`
- Migración compensatoria `yyyy_restore_lfpdppp_audit.py`
  - Recrear tabla `data_access_log`
  - Restaurar 6 columnas `ciudadanos_legacy.*_enc`
- Models SQLAlchemy nuevos para las 5 tablas destruidas + add `rol_politico` a `Dirigente` model
- Tests integration: endpoints `/social/aceptacion/overview`, `/admin/overview`, `/admin/classification/stats`, `/framework/matrix`, `/framework/audit` devuelven 200 con data real

**Requiere revisor §9.8:** SÍ. D-OPS-10 vigente. Joy prepara plan completo antes · revisor lee diff completo de ambas migraciones.

**Estructura commits (D-OPS-09):**
- Commit 1: `migration: restore political framework schema (post-3d6fe3f)`
- Commit 2: `feat(models): Dirigente.rol_politico + political framework models`
- Commit 3: `migration: restore LFPDPPP data_access_log + encrypted columns`
- Commit 4: `feat(models): data access log + ciudadanos_legacy PII models`
- Commit 5: `test(integration): endpoints political framework + LFPDPPP audit`

**Criterio éxito:**
- `/dashboard/aceptacion` carga correctamente sesión Piña
- `/dashboard/admin/overview` renderiza
- `/dashboard/admin/clasificacion` operativo
- `/dashboard/settings/analisis-politico` accesible
- Console 0 errores · HTTP 200 en 5 endpoints previamente 500

**PR:** `fix(db): restore political framework + LFPDPPP audit — Fase 1+2 post-3d6fe3f`

**Checkpoint de aprobación:** revisor §9.8 lee diff de ambas migraciones antes de autorizar merge.

---

## Fase B · UX/UI consolidación frontend (5 sprints, ~8 días)

**Objetivo:** atacar los 🟠 funcionales del review frontend + deudas F-06..F-15 post-gate que quedaron en backlog.

### Sprint B.1 · Jerga técnica expuesta al cliente (2 días · Joy sola · post-A.2 si A.2 fue incompleto)

**Entregables:**
- F-29 `/aceptacion` error discreto → componente de error unificado con icono + CTA retry
- F-30 "Fantasmas" → rename semántico en sidebar ("Cuentas dormidas" o pendiente decisión CEO)
- F-35 `HITL §3.6` → tooltip expansivo
- F-38 `Failed to fetch` → i18n al español
- F-51 `3 IAs deliberaron` → tooltip con expansión
- F-57 códigos `B11 T2`..`B18 T2` → labels humanos + código en tooltip
- F-58 `CIB (ITESO/DFRLab)` → tooltip con glosario
- F-61 `Jaccard sobre captions` → reformular con lenguaje común + tooltip
- F-40 (admin/overview error) agrupar con F-29 en componente unificado

**Alcance:** ~8-10 archivos frontend · crear componente `ErrorFallback` reutilizable.

**PR:** `fix(ux): reemplazar jerga técnica por labels humanos + componente Error unificado (F-29..61)`

### Sprint B.2 · Landing público fixes + prueba social (1-2 días · Joy sola · parte requiere decisión CEO)

**Entregables:**
- F-41 diagnosticar espacio vacío vertical grid↔footer (render error vs scroll animation vs intencional) + fix
- F-42 `48hrs` → `48 hrs`
- F-43 mockup dashboard pequeño → agrandar o habilitar modal zoom
- F-44 prueba social — PENDIENTE DECISIÓN CEO · aprobar testimoniales o placeholder
- F-45 nav `Métricas` → rename según sección destino

**Requiere CEO:** F-44 aprobación legal testimoniales (MC CDMX, ConsultoriaMD proyectos previos).

**PR:** `fix(landing): espacio vacío + prueba social + rename nav (F-41..45)`

### Sprint B.3 · Paridad Overview vs detalle dirigente (3 días · Joy sola)

**Entregables:**
- F-31 `/dashboard/dirigentes/1` gráfico Sentimiento ilegible → revisar densidad + formato fechas `dd/MM/yy` + separadores
- F-32 Radar IPD vacío/casi vacío → empty state explícito cuando valores < threshold
- F-33 `"0 secciones"` → tooltip/label explícito tipo
- F-34 handles `@` sin nombre real → mostrar handle o tooltip
- F-55 paridad calidad Overview vs detalle (aplicar mismas prácticas KPI + empty states)

**Alcance:** páginas `/dashboard/dirigentes/[id]` + componentes radar/sentiment-line-chart + data enrichment.

**PR:** `feat(dirigente): paridad calidad con Overview + fixes gráficos + empty states (F-31..34, F-55)`

### Sprint B.4 · Tema temporal + contexto data (1-2 días · Joy sola)

**Entregables:**
- F-52 `↗ 100%` sin periodo → `+100% este mes` o explícito
- F-53 `IPD` con `—` ambiguo → label explícito
- F-54 `320 posts ↗ 100%` relación no obvia → separar métrica del delta
- F-18 formato fechas `a.m./p.m.` → normalizar formato 24h o AM/PM sin punto
- F-62 `0/12 promesas` sin contexto temporal → agregar ventana + distinguir vencidas vs en curso

**Alcance:** componentes KPI card, formatNumber utility, date formatter.

**PR:** `fix(ux): contexto temporal explícito en KPIs + formato fechas normalizado (F-18, F-52..54, F-62)`

### Sprint B.5 · Design system coherence + misc 🟡 (2 días · Joy sola)

**Entregables:**
- F-17, F-19, F-20 tags/chips/sidebar en /dashboard/planes
- F-21..24 padding + alineación /dashboard/planes/13
- F-25..27 Kanban empty states + chevrons tooltips
- F-37 "Refrescar" → "Actualizar cola"
- F-49 contraste bajo login bullets (WCAG audit)
- F-50 "CRECE v2.0" a footer
- F-56 filtros periodo subheader
- F-63 sidebar "Indice Aceptacion" expandido consistente entre modos
- F-64 alertas org vs dirigente — clarificar visualmente scope
- F-65 FB=0 Ballesteros verificar data
- F-66 total 88.8K paridad Piña
- F-67 clarificar Plan vs Recomendación taxonomía
- F-68 empty state iconografía unificada

**PR:** `fix(ux): design system coherence + paridad tenant/sidebar + WCAG login (F-17..68 misc)`

---

## Fase C · Seguridad endpoints (Frente 3) (3 sprints, ~7-8 días)

**Objetivo:** cerrar D-SEC-03 (21 endpoints JWT-only) + D-SEC-04 (IDOR parcial `/dirigentes/{id}/crecimiento`) + auditoría de 25+ endpoints `_current_user` (`AUDIT-AUTH-IGNORED-2026-04-14.md`).

**Requiere revisor §9.8:** SÍ para todos los sprints. D-OPS-10 vigente.

### Sprint C.1 · Prep + inventario (1 día · Joy sola)

**Entregables (read-only):**
- Lista completa endpoints con `_current_user: Annotated[User, ...]` (25+ según auditoría 04-14)
- Clasificación por endpoint: ¿tenant-sensitive o global?
- Propuesta de patrón unificado `_require_tenant_access` basado en `org_id` + `dirigente_id`
- Tests integration esperados (matriz cross-tenant: analyst-A pide data-B → 403)
- Doc `.context/PLAN-frente-3-seguridad.md`

**No modificar código · solo planeación.**

### Sprint C.2 · Fix IDOR específicos + dual-auth (3-4 días · Joy + revisor §9.8)

**Entregables:**
- D-SEC-04: `/dirigentes/{id}/crecimiento` aplicar `_require_tenant_access` incondicional (sin early-exit si `user.dirigente_id NULL`)
- D-SEC-03: 21 endpoints JWT-only → aceptar `X-API-Key` (dual-auth)
- Patrón `_require_tenant_access` helper en `core/security.py`
- Tests integration por cada endpoint cambiado

**Estructura commits (D-OPS-09):**
- Por endpoint o grupo pequeño de endpoints relacionados
- Ningún commit > 10 archivos

**PR:** `fix(security): D-SEC-03 dual-auth + D-SEC-04 IDOR crecimiento (Frente 3 Sprint C.2)`

### Sprint C.3 · Auditoría 25+ endpoints `_current_user` (2-3 días · Joy + revisor §9.8)

**Entregables:**
- Por cada endpoint con `_current_user`, decidir:
  - Mantiene `_current_user` si es data global legítima (geo, electoral público)
  - Activa a `current_user` si necesita scope (aplicar `_require_tenant_access`)
- Tests integration cross-tenant para los que pasaron a scoped
- Update `AUDIT-AUTH-IGNORED-2026-04-14.md` con resultados finales

**PR:** `fix(security): auditoría _current_user endpoints — scoped vs global decision (Frente 3 Sprint C.3)`

---

## Fase D · §9.8 intermedia (2 sprints, ~7 días) · 2026-05-13 → 2026-05-20

**Objetivo:** mergear trabajo diferido de `feat/eval-benchmark-v1` + formalizar D-OPS-03 + restaurar GIS + Fase 3 + 4 de D-OPS-07.

### Sprint D.1 · Preparación §9.8 intermedia (2 días · Joy + CEO + revisor §9.8)

**Entregables (planeación):**
- Revisar feedback acumulado del piloto (30 días de uso)
- Evaluar D-OPS-03 (política release branch) para formalización dos puertas
- Plan de merge de 11 commits restantes de `feat/eval-benchmark-v1`:
  - `821950b` parcial → solo compact ya aplicado · decidir qué más traer (X scrapers, OrgContext.config, semáforo crecimiento, multitenant hardening)
  - `a919c5f` 5 redes IG+TT+FB+YT
  - `0681153` Oraculus + Demoscopía encuestas
  - `b79fab5` aceptación drill-down + Gemma3 Layer 2 (incluye 11 columnas NLP `social_posts` que cubre Fase 4 D-OPS-07)
  - `959e040` Seed Fase 1 backfills
  - `4d6286a` Layer 2 benchmark
  - `73337b9` body/html max-width iOS (mobile fix)
  - `81fe01e` iOS viewport + topbar mobile
  - `3921f10` calibración XLS
  - `c6eddfe` favicon amarillo (tal vez ya cubierto)
  - `3765881` ocultar acceso demo (ya cubierto por D-PILOTO-02)
  - `22c62e2` dirigente_nombre en SocialPostResponse
- Plan restauración GIS (Fase 3 D-OPS-07): re-import INE desde `backend/data/raw/ine_cartografia/`

### Sprint D.2 · Ejecución merge + restauración GIS (5 días · Joy + revisor §9.8 · cross-audit Gemini obligatorio)

**Entregables:**
- Merge selectivo de commits de `feat/eval-benchmark-v1` a main (cherry-pick o merge según decisión D.1)
- Migración restauración GIS `zzzz_restore_gis_tables.py` + re-import shapefiles
- Models GIS: `DistritoFederal`, `DistritoLocal`, `SeccionGeo` × CDMX/Oaxaca
- Scripts cartografía actualizados si aplica
- Tests cobertura GIS (consultas por sección, alcaldía)

**Cross-audit Gemini:** obligatorio para el plan completo de merge (commit coverage + conflict resolution + data integrity).

**PR:** múltiples · 1 por grupo lógico según D-OPS-09

### Sprint D.3 (opcional) · Formalización D-OPS-03 (0.5 día · CEO + revisor §9.8)

**Entregables:**
- D-OPS-03 pasa de PROPUESTA a APROBADA si dos puertas dan luz verde
- Actualizar DECISIONS.md
- PR doc-only

---

## Fase E · Backlog post-§9.8 intermedia (1 sprint consolidado · 2026-05-21 → 2026-07-19)

**Objetivo:** nice-to-have + Prompt v1.1 activation + §7.4 métricas terminales 90d.

### Sprint E.1 · Polish + activación Prompt v1.1 + §7.4

**Entregables:**
- 10 hallazgos 🟢 nice-to-have (F-37, F-42, F-50, F-66 entre otros)
- D-GATE-03: activar Prompt Plan IA v1.1 si criterios cumplen (≥7 días uso v1.0 + feedback + autorización CEO)
- §7.4 métricas terminales 90d:
  - Métrica 1: 3 pilotos firmados (expansión Cravioto/Pineda tras Fase 2 piloto)
  - Métrica 2: ≥1 recomendación ejecutada con resultado
  - Métrica 3: ≥1 conversión T3 → T1 OAuth
- Revisión §9.8 terminal del arco MVP comercial (§9.8 90d ≈ 2026-07-19)

---

## Dependencias + gate-checks

### Bloqueantes operacionales

| Condición | Impacto |
|---|---|
| Revisor §9.8 al límite de uso hasta jueves | Sprints que requieren schema/migrations (A.3, C.2, C.3, D.2) bloqueados hasta 2026-04-23 |
| D-OPS-10 vigente | Todo schema change requiere revisor §9.8 lea diff completo |
| D-OPS-09 vigente | Migraciones en commits atómicos separados de features |
| D-OPS-08 vigente | Autogenerate Alembic prohibido sin review manual + firma commit |

### Decisiones CEO pendientes (desbloqueos)

| Sprint | Decisión pendiente |
|---|---|
| B.1 | F-30 rename semántico "Fantasmas" (qué label adoptar) |
| B.2 | F-39 label sidebar "Operacion de flota" (fresh eyes check) |
| B.2 | F-44 aprobación legal testimoniales prueba social |
| B.3 | F-33 qué tipo de secciones es `0 secciones` (electorales/territoriales) |
| D.1 | Qué commits de `feat/eval-benchmark-v1` traer completos vs parciales |
| E.1 | Activación Prompt v1.1 post-condiciones D-GATE-03 |

### Dependencias entre sprints

```
A.1 (fixes ortografía) ──┐
                         ├── independientes · Joy sola · hoy/mañana
A.2 (FODA[D] literal) ──┘
                         │
A.3 (schema restauración) ──> requiere jueves (revisor §9.8 regresa)
                              │
                              ├──> B.1 (jerga) · post-A.3 para componente error unificado
                              │
                              ├──> B.3 (paridad) · depende de que aceptacion funcione
                              │
                              └──> C.1 (prep seguridad) · independiente, Joy sola
                                   │
                                   └──> C.2 (fix IDOR + dual-auth) · requiere revisor
                                        │
                                        └──> C.3 (auditoría 25 endpoints) · requiere revisor
                                             │
                                             └──> D.1 (prep §9.8 intermedia) · Joy + CEO + revisor
                                                  │
                                                  └──> D.2 (merge eval-v1 + GIS) · revisor + Gemini
                                                       │
                                                       └──> E.1 (polish + activación + §7.4)
```

**Critical path largo:** A.3 → C.2 → C.3 → D.1 → D.2 → E.1 (~25-30 días efectivos)
**Critical path corto:** A.1 → A.2 → B.1 → B.2 → B.4 → B.5 (~10 días efectivos, sin bloqueo revisor)

---

## Riesgos + mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Revisor §9.8 no vuelve jueves | Media | Alto (bloquea schema) | Joy difiere Fase A.3 + toda Fase C hasta confirmación |
| Cherry-pick selectivo eval-v1 (D.2) genera conflictos | Alta | Medio | Gemini cross-audit obligatorio del plan de merge antes de ejecutar |
| Prompt v1.1 activación prematura polluye baseline | Media | Alto | D-GATE-03 vigente · no activar sin 3 criterios |
| Fase C genera regresión en endpoints existentes | Media | Alto | Tests integration obligatorios antes de merge (D-OPS-10 lectura diff + tests) |
| Feedback piloto requiere re-prioritizar backlog | Alta | Medio | Sprint D.1 incluye revisión de feedback antes de ejecución |

---

## Métricas de éxito por fase

| Fase | Métrica éxito | Verificación |
|---|---|---|
| A | 5 endpoints previamente 500 devuelven 200 · /aceptacion renderiza limpio · ortografía login correcta | Smoke prod sesión Piña · curl endpoints |
| B | 0 🟠 funcionales pendientes · design system coherence en empty states · paridad Overview↔detalle dirigente | Review visual captura por captura (segunda iteración de review frontend) |
| C | D-SEC-03 cerrada · D-SEC-04 cerrada · 25 endpoints auditados con scope decidido · tests cross-tenant passing | Tests integration · AUDIT-AUTH-IGNORED-2026-04-14 actualizado |
| D | 11 commits eval-v1 mergeados (o decisión explícita de diferir subset) · GIS operativo · D-OPS-03 formalizada | Commits en main · curl endpoints GIS · DECISIONS.md actualizada |
| E | Prompt v1.1 activado o justificadamente diferido · §7.4 3 métricas cumplidas o plan de recalibración | Revisión §9.8 terminal 90d |

---

## Pendientes Joy (no escribir)

- Cross-audit del plan con Gemini CLI (`/gemini review`) antes de aprobación CEO
- Incorporar síntesis + priorización CEO cuando esté disponible
- Actualizar SPRINT-CURRENT.md con Fase A post-aprobación
- Documentar D-PLAN-01 en DECISIONS.md si se aprueba como decisión estructural

---

## Cambios potenciales post-review

Este plan asume ejecución secuencial. Si CEO prioriza:
- **Velocidad pura:** agrupar A.1 + A.2 + B.1 en un solo sprint de 2 días · saltarse sprint C.1 prep y hacer inventario durante C.2
- **Rigor máximo:** extender cada sprint 50% · Gemini cross-audit en CADA PR no solo en D.2
- **Piloto primero:** atacar SOLO lo crítico para cliente (A.1, A.2, A.3, B.1, B.3) · diferir Fase C y D.1 a post-§9.8 intermedia

Espera decisión CEO sobre priorización.
