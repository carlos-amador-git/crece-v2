# PLAN Recuperación post-incidente · 2026-04-21

**Creado:** 2026-04-21 (noche)
**Estado:** APROBADO (CEO + Joy + Gemini cross-audit)
**Versión:** v3 consolidada · sucesor de `PLAN-post-review-2026-04-21.md` (v1 overplanning) y v2 (pre-integración review visual)
**Scope:** recuperación de 2 incidentes concurrentes descubiertos en sesión 2026-04-21 (Lenis scroll + migración destructiva `3d6fe3f1660d`) + consolidación deudas abiertas.

---

## Contexto

**Incidentes origen:**
1. **Lenis scroll roto** en `/dashboard/*` (descubierto + fixeado vía PRs #36-#39 chain · **cerrado**)
2. **Migración Alembic destructiva `3d6fe3f1660d`** (autoría CEO+Claude Opus 4.7 · 2026-04-18 · autogenerate contaminado) · dropeó 14 tablas + 23 columnas · 5 endpoints backend 500 silenciosos por 6 días · 4 rutas frontend rotas · **abierto, pendiente remediación**

**Hallazgos paralelos descubiertos en sesión:**
- Review frontend manual CEO · 52 hallazgos F-17..F-68 (3 🔴 · 16 🟠 · 23 🟡 · 10 🟢) · `.context/frontend-review-2026-04-21/_HALLAZGOS-CEO.md`
- `/dashboard/aceptacion` muestra error al cliente Piña — caso de libro de por qué review visual importa

**Políticas vigentes durante ejecución:**
- D-OPS-07 post-mortem incidente 3d6fe3f documentado
- D-OPS-08 prohibición Alembic autogenerate sin revisión manual + firma commit
- D-OPS-09 atomicidad migraciones (migration: aparte de feat:)
- D-OPS-10 revisor §9.8 lee diff completo antes de schema changes

**Cross-audit aplicado:** Gemini CLI review rechazó plan v1 (overplanning + orden seguridad/UX invertido + cherry-pick D.2 riesgo + observabilidad ausente). Plan v3 incorpora las 7 correcciones.

---

## Estructura en 3 Frentes

| Frente | Ventana | Tipo ejecución | Contenido macro |
|---|---|---|---|
| **Frente 0** · Observabilidad | 24-48h | Sprints atómicos (Joy sola) | Alertas 5xx · Tests E2E smoke rutas críticas |
| **Frente 1** · Recuperación crítica | 5-8 días | Sprints ordenados con dependencias | Schema restauración · sprint seguridad · triage review visual · fixes UX críticos piloto |
| **Frente 2** · Kanban continuo | 4-6 semanas | WIP limit 2 · flujo continuo | Merge eval-v1 interactive rebase · backlog UX F-17..F-68 · Prompt v1.1 · Fase 3 GIS · Fase 4 NLP |

---

## Frente 0 · Observabilidad (24-48h)

**Objetivo:** cerrar el gap sistémico que permitió 6 días de HTTP 500 silenciosos. **Prerequisito duro antes de Frente 1.**

### F0.1 · Sentry/webhook alertas 5xx backend (1 día · Joy sola)

**Entregable:**
- Integración Sentry SDK en FastAPI backend (o equivalente · webhook Slack/Discord si no hay plan Sentry activo)
- Alertas dispara sobre: HTTP 5xx · exception no capturada · rate limit 429 sostenido · tunnel cloudflared caído
- Dashboard/canal de notificación configurado
- Test manual: forzar 500 → llega notificación <60s

**No requiere revisor §9.8:** cambio infra · middleware add · 0 schema.

**PR:** `feat(observability): Sentry integration + 5xx alerting`

### F0.2 · Tests E2E smoke rutas críticas (1 día · Joy sola)

**Entregable:**
- Playwright suite mínima sesión Piña + admin · cubre:
  - `/login` renderiza + auth funcional
  - `/dashboard` renderiza con KPIs + alertas
  - `/dashboard/aceptacion` renderiza (actualmente roto · después de F1.1 debe pasar)
  - `/dashboard/admin/overview` renderiza (idem)
  - `/dashboard/diagnostico/1` + `/dashboard/diagnostico-tier2/1` KPIs con data
- Setup CI: corre en cada PR que toque `backend/app/api/` o `frontend/src/app/dashboard/`
- Test baseline (antes de F1.1): documenta cuáles fallan como "known failures" que F1.1 debe resolver

**No requiere revisor §9.8:** tests only · 0 schema.

**PR:** `test(e2e): Playwright smoke rutas críticas sesión Piña + admin`

### F0.3 · (eliminado)

Originalmente "hotfix /aceptacion condicional". CEO declaró sin urgencia business-blocker → se espera revisor §9.8 jueves para ejecutar F1.1 con rigor D-OPS-10.

---

## Frente 1 · Recuperación crítica (5-8 días)

**Objetivo:** remediar daño incidente `3d6fe3f1660d` + cerrar deuda seguridad preexistente + triage hallazgos review visual.

### F1.1 · Schema restauración Fase 1+2 (2 días · Joy + revisor §9.8 · post-F0.1+F0.2)

**Depende de:** Frente 0 completo (alertas activas + tests E2E baseline).

**Entregables:**

**Migración política framework** (escrita a mano, NO autogenerate per D-OPS-08):
- Restaurar `dirigentes.rol_politico` column (VARCHAR(20) nullable)
- Recrear tablas: `contexto_politico`, `framework_matrix_defaults`, `framework_overrides_org`, `framework_audit_log`
- Re-ejecutar `seed_political_framework.py`
- Models SQLAlchemy: `Dirigente.rol_politico` + 4 models framework

**Migración LFPDPPP**:
- Recrear tabla `data_access_log`
- Restaurar 6 columnas `ciudadanos_legacy.*_enc`
- Model `DataAccessLog` + retornar columnas a `CiudadanoLegacy`

**Tests integration:**
- Endpoints que volverán 200: `/social/aceptacion/overview`, `/admin/overview`, `/admin/classification/stats`, `/framework/matrix`, `/framework/audit`
- Cross-tenant: analyst-A no ve data org-B · admin ve multi-org

**Estructura commits (D-OPS-09):**
- Commit 1: `migration: restore political framework schema (post-3d6fe3f)` — firma D-OPS-08
- Commit 2: `feat(models): Dirigente.rol_politico + political framework models`
- Commit 3: `migration: restore LFPDPPP data_access_log + encrypted columns` — firma D-OPS-08
- Commit 4: `feat(models): DataAccessLog + ciudadanos_legacy PII columns`
- Commit 5: `test(integration): aceptacion + framework + admin endpoints 200`

**Criterio éxito:**
- Playwright F0.2 rutas críticas verdes
- Sentry F0.1 alertas 0 sobre endpoints restaurados
- `/dashboard/aceptacion` sesión Piña renderiza data real

**PR:** `fix(db): restore political framework + LFPDPPP audit — post-3d6fe3f remediation`

**Checkpoint D-OPS-10:** revisor §9.8 lee diff completo de AMBAS migraciones antes de autorizar merge.

### F1.2 · Sprint seguridad (5-7 días · Joy + revisor §9.8)

**Depende de:** F1.1 completo (`data_access_log` restaurado para que PII audit funcione).

**Orden dentro del sprint:**

**F1.2.a · Prep read-only (1 día):**
- Inventario 25+ endpoints con `_current_user: Annotated[User, ...]`
- Clasificación por endpoint: tenant-sensitive vs global
- Patrón helper `_require_tenant_access(user, org_id, dirigente_id=None)` diseñado en `core/security.py`
- Matrix tests esperados: analyst-A→data-B=403, field_operator→dirigente-ajeno=403, admin→any=200
- Plan por endpoint documentado en `.context/PLAN-frente-1-2-seguridad.md`

**F1.2.b · Fix D-SEC-04 IDOR + D-SEC-03 dual-auth (3 días):**
- `_require_tenant_access` helper en `core/security.py`
- `/dirigentes/{id}/crecimiento` check incondicional (sin early-exit si `user.dirigente_id NULL`)
- 21 endpoints JWT-only → aceptar `X-API-Key` (dual-auth via existente `get_current_user_or_api_key`)
- Tests integration por endpoint cambiado
- Aplicación D-OPS-09 estricta: 1 commit por endpoint o grupo ≤5 archivos

**F1.2.c · Auditoría 25+ endpoints `_current_user` (2-3 días):**
- Por endpoint: activar `current_user` con scope si tenant-sensitive · mantener `_current_user` si global
- Tests integration cross-tenant por endpoint promovido
- Update `.context/AUDIT-AUTH-IGNORED-2026-04-14.md` con resultados
- PR con estructura D-OPS-09

**Criterio éxito:**
- 0 endpoints con bypass tenant por `user.dirigente_id NULL`
- Tests cross-tenant verdes en 25+ endpoints
- D-SEC-03 cerrada (dual-auth operativa) · D-SEC-04 cerrada (IDOR fixed)

**Checkpoint D-OPS-10:** revisor §9.8 lee diff por cada endpoint antes de autorizar merge.

**PRs:** múltiples (1 por endpoint o grupo) · estructura D-OPS-09

### F1.3 · Triage hallazgos review visual (0.5 día · Joy sola)

**Depende de:** ninguna (ejecutable en paralelo con F1.1 o F1.2 prep).

**Entregable:**
- Revisar 52 hallazgos F-17..F-68 del archivo `_HALLAZGOS-CEO.md`
- Clasificar por:
  - **Crítico-piloto:** rompe demo al cliente actual (ej. F-28 FODA[D], F-46/47 ortografía, F-38 i18n error, F-41 landing vacío)
  - **Arquitectural:** requiere rediseño de componente (ej. F-29/40 componente error unificado, F-55 paridad Overview vs detalle)
  - **Nice-to-have:** diferibles Frente 2 Kanban
- Documentar en `.context/TRIAGE-F-17-F-68-2026-04-21.md` con orden de ataque

**No requiere revisor §9.8:** doc-only.

**Output:** backlog priorizado para F1.4 + Frente 2.

### F1.4 · Fixes UX críticos del triage (1-2 días · Joy sola)

**Depende de:** F1.3 (triage completado).

**Entregable:**
- Solo atacar los marcados "crítico-piloto" por F1.3
- Fixes ortografía (F-46, F-47) · FODA[D] literal (F-28) · i18n error "Failed to fetch" (F-38) · otros críticos según triage
- PR por grupo temático (D-OPS-09 no aplica estricto si no hay migrations)

**No requiere revisor §9.8:** frontend-only sin schema.

**PR:** `fix(ux): críticos review visual pre-piloto — triage F1.3`

---

## Frente 2 · Kanban continuo (4-6 semanas)

**Formato operativo:**
- Sin sprints rígidos · flujo continuo con **WIP limit = 2 tareas activas simultáneas**
- Backlog ordenado por severidad en board Kanban (Notion/archivo local)
- Revisor §9.8 asíncrono por PR individual · no bloqueante para tareas paralelas
- Revisión semanal (viernes 30 min) para reordenar backlog según feedback piloto

**Contenido:**

### Categoría 2.A · Merge `feat/eval-benchmark-v1` progresivo (interactive rebase)

**Método obligatorio (mitigación Gemini crítica #4):** 
- NO cherry-pick directo
- `git rebase -i` en rama temporal · separar commits Alembic de commits código/seed/scripts
- Migraciones extraídas → revisión aislada D-OPS-10 → aplicación primero
- Código aplicado después · commit atómico per D-OPS-09

**11 commits a procesar (preservados en `origin/backup/pre-opcion-d-eval-v1`):**

| SHA | Contenido | Prioridad Frente 2 |
|---|---|---|
| `821950b` parcial | Scrapers X + OrgContext.config + multitenant + semáforo crecimiento | Alta (OrgContext.config desbloquea F-39 banner logic) |
| `a919c5f` | 5 redes IG+TT+FB+YT cierre integral | Alta (data ingesta) |
| `0681153` | Oraculus + Demoscopía scrapers encuestas | Media |
| `b79fab5` | Aceptación drill-down + Gemma3 Layer 2 + **11 cols NLP social_posts** (cubre Fase 4) | **Alta** (restaura NLP pipeline) |
| `959e040` | Seed Fase 1 backfills | Baja (data-only) |
| `4d6286a` | Layer 2 benchmark | Baja (eval-only) |
| `73337b9` | body/html max-width iOS | Alta (mobile fixes) |
| `81fe01e` | iOS viewport + topbar mobile | Alta (mobile fixes) |
| `3921f10` | Calibración XLS | Baja (reporting-only) |
| `c6eddfe` | Favicon amarillo | Low |
| `3765881` | Ocultar acceso demo (ya cubierto D-PILOTO-02) | Skip (duplicado) |
| `22c62e2` | `dirigente_nombre` SocialPostResponse | Media |

### Categoría 2.B · Backlog UX F-17..F-68

**Ordenado por severidad post-triage F1.3:**
- 🟠 funcionales primero (jerga técnica, empty states, landing social proof, paridad dirigente detalle)
- 🟡 consistencia después (padding, formato, paridad contadores)
- 🟢 nice-to-have último (sparklines, mejoras estéticas menores)

### Categoría 2.C · Prompt Plan IA v1.1 (condicional D-GATE-03)

**Criterios activación (vigentes):**
1. ≥7 días de uso real de v1.0 en piloto
2. Feedback explícito de redundancia o falla en output v1.0
3. Autorización CEO

**Flexibilidad vs plan v1:** activar cuando 3 criterios se cumplan · NO fijo en día 30 · puede ser día 10, 14, 20, etc.

### Categoría 2.D · Fase 3 GIS (restauración post-3d6fe3f)

**Depende de:** Frente 2.A commit relevante (si viene GIS en algún commit de eval-v1) · si no, ejecutar independiente.

**Entregable:**
- Migración `restore_gis_tables.py` (escrita a mano, D-OPS-08)
- Models `DistritoFederal`, `DistritoLocal`, `SeccionGeo` × CDMX/Oaxaca
- Re-import SHPs desde `backend/data/raw/ine_cartografia/cdmx/09/*.shp` y `oaxaca/20/*.shp`
- Scripts cartografía (ya en repo) verificados funcionales

**Target:** §9.8 intermedia 2026-05-20 si no urgente antes.

### Categoría 2.E · Fase 4 NLP social_posts

**Cubierto por:** Frente 2.A commit `b79fab5` (11 cols NLP). Al mergearse con rebase interactivo, la Fase 4 de D-OPS-07 queda resuelta automáticamente.

---

## Dependencias entre Frentes

```
Frente 0 (observabilidad 2d) ──> gate obligatorio
                                  │
                                  ├──> F1.1 (schema restauración 2d) · requiere revisor jueves
                                  │    │
                                  │    ├──> F1.2 (sprint seguridad 5-7d) · requiere revisor
                                  │    │
                                  │    └──> Frente 2 (Kanban continuo)
                                  │
                                  └──> F1.3 (triage 0.5d) · paralelo a F1.1/F1.2
                                       │
                                       └──> F1.4 (fixes UX críticos 1-2d)

Frente 2 opera continuo desde aprox día 10 (post-F1.4)
§9.8 intermedia 2026-05-20 · checkpoint formal
§9.8 terminal 2026-07-19 · métricas §7.4
```

**Critical path:** F0 → F1.1 → F1.2 → F2 ≈ 12-15 días hábiles

**Trabajo paralelizable Joy:**
- F0.1 + F0.2 simultáneos (2 PRs distintos)
- F1.3 triage durante F1.2 prep read-only
- F1.4 fixes UX durante F1.2.b backend seguridad (tocan áreas distintas)

---

## Decisiones CEO pendientes

| Sprint | Decisión |
|---|---|
| F1.3 triage | Confirmar clasificación 🔴 crítico-piloto vs 🟠 funcional (cuáles F-XX atacar en F1.4) |
| F1.4 | F-30 "Fantasmas" rename semántico (qué label · "Cuentas dormidas" · "Sin datos") |
| F1.4 | F-39 "Operacion de flota" label correcto |
| F1.4 | F-33 qué tipo son las "0 secciones" (electorales/territoriales) |
| F2.A | Cuáles 11 commits eval-v1 traer completos · cuáles parciales · cuáles skip |
| F2.B | F-44 aprobación legal testimoniales prueba social landing |
| F2.C | Prompt v1.1 activación cuando 3 criterios cumplan (decisión en vivo, no agendable) |

---

## Riesgos + mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Revisor §9.8 no vuelve jueves | Baja | Alto (bloquea F1.1) | Joy espera · no squeeze · Frente 0 + F1.3 + F1.4 ejecutables sola |
| Cherry-pick eval-v1 (F2.A) recrea `3d6fe3f` | **Alta** | Alto | **Obligatorio:** interactive rebase separando migrations · Gemini cross-audit del plan de merge · aplicación secuencial (migration first) |
| Fase F1.2 regresión endpoints | Media | Alto | Tests integration obligatorios antes de cada merge · D-OPS-10 revisor lee diff |
| Feedback piloto requiere re-priorizar | Alta | Medio | Revisión semanal viernes + flexibilidad Kanban WIP |
| Prompt v1.1 activación prematura | Media | Alto | D-GATE-03 vigente · 3 criterios son AND no OR |
| Observabilidad F0.1 se convierte en proyecto en sí (Sentry compleja) | Media | Medio | MVP: webhook Slack primero · Sentry full si webhook escala |

---

## Métricas de éxito por Frente

| Frente | Métrica | Verificación |
|---|---|---|
| 0 | Alertas 5xx llegan <60s · Tests E2E baseline documentan "known failures" F1.1 debe resolver | Manual trigger 500 · CI run |
| 1 | 5 endpoints pre-500 devuelven 200 · D-SEC-03 + D-SEC-04 cerradas · 25 endpoints auditados · fixes UX críticos aplicados | Smoke prod sesión Piña · tests integration · review visual iteración 2 |
| 2 | 11 commits eval-v1 procesados (mergeados o explícitamente diferidos) · backlog F-17..F-68 resuelto por severidad · Prompt v1.1 activado o diferido con justificación · GIS operativo | Commits en main · DECISIONS.md actualizada con decisiones §9.8 intermedia |

---

## Políticas vigentes durante todo el plan

- **D-OPS-07** post-mortem incidente 3d6fe3f (contexto histórico)
- **D-OPS-08** Alembic autogenerate prohibido sin review manual + firma commit
- **D-OPS-09** atomicidad migrations (migration: aparte de feat:)
- **D-OPS-10** revisor §9.8 lee diff completo antes de schema changes
- **D-PILOTO-01/02/03** piloto comercial · 3 activos + 5 shadow · Ballesteros activa
- **D-GATE-01..07** gate pre-piloto cerrado
- **D-SI-01..04** LFPDPPP + IA estructurada

---

## Archivos de trabajo (no committed hasta aprobación final)

- `.context/PLAN-recuperacion-post-incidente-2026-04-21.md` · este documento (v3)
- `.context/frontend-review-2026-04-21/_HALLAZGOS-CEO.md` · 52 hallazgos review visual
- `.context/PLAN-post-review-2026-04-21.md` · borrador v1 (superseded · mantener como histórico)

**Borradores subsecuentes (por crear durante ejecución):**
- `.context/PLAN-frente-1-2-seguridad.md` (F1.2.a output)
- `.context/TRIAGE-F-17-F-68-2026-04-21.md` (F1.3 output)
- Migraciones en `backend/migrations/versions/xxxx_restore_*.py` (F1.1)

---

## Nota sobre ejecución

Joy espera luz verde explícita para iniciar F0.1. El plan v3 no se ejecuta automáticamente · requiere:

1. CEO aprobación final del plan
2. Decisión sobre commitear este archivo como doc de plan activo
3. Decisión sobre mover `PLAN-current.md` link al v3 o mantener separado

Tiempo restante CEO + Joy hoy: estimado pausa inminente (fatiga sesión larga · Frente 0 puede arrancar mañana fresh).
