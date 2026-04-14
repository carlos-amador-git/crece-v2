# Plan Sprint Cierre — 2026-04-13 noche (REV 2: Dashboard Admin)

**Origen:** `/sprint-review` post-compactación — incorporar Dashboard Admin como prioridad 1
**Branch:** `feat/sprint-c-hardening`
**Estado:** **REVISIÓN — esperando aprobación CEO antes de ejecutar**

---

## Contexto actualizado

Sprints S1 (clasificación 95 posts) y S2 (NLP batch) YA se ejecutaron en sesión anterior — commit `385aad5`. NLP batch terminó en background (exit 0).

Pendiente real post-compactación, en orden de prioridad CEO:

1. **Dashboard Admin `/dashboard/admin/overview`** — mockup aprobado por CEO antes del reinicio. Admin MD NO debe ver dashboard cliente; necesita vista operativa de flota.
2. **Scrapers encuestas públicas** (Oraculus + Demoscopía) — plan md-research listo
3. **Charts Treemap/Stream/Sunburst** en dashboard cliente (post charts-lab)
4. **Cierre documental + PR**

---

## Sprints propuestos

### Sprint 0 — Dashboard Admin Operativo (2.5-3 h) ⭐ NUEVO PRIORIDAD 1

**Objetivo:** Admin MD tiene vista operativa de flota de clientes. NO muestra dashboard político (eso es del cliente); muestra estado del sistema, cola de trabajo semanal, salud del pipeline NLP y alertas.

**Contexto de diseño (aprobado por CEO pre-compactación):**
Widgets propuestos → "Esta semana toca" (cola clasificación) · "Flota clientes" (3 orgs, posts pendientes, % clasificados) · "System health" (DB, Redis, scrapers, workers) · "Pipeline NLP" (coverage multi-model-v1) · "Divergencia encuestas" (placeholder hasta Sprint 3) · "Peers activos" (claude-peers) · "Quick actions" (generar prompts, reprocess).

| Subtarea | Archivos | Duración | Criterio |
|---|---|---|---|
| S0.1 Endpoint `/admin/overview` backend | `backend/app/api/v1/endpoints/admin_overview.py` (nuevo) | 45 min | GET devuelve flota, coverage NLP, cola semanal, health checks |
| S0.2 Queries agregadas multi-tenant | mismo archivo + `services/` | 30 min | Counts por org sin cross-leak, RLS respetado para admin |
| S0.3 Health checks (DB/Redis/workers) | `admin_overview.py` | 20 min | Status OK/WARN/ERROR por servicio |
| S0.4 Página `/dashboard/admin/overview` | `frontend/src/app/dashboard/admin/overview/page.tsx` (nuevo) | 45 min | Grid responsive con 6-7 cards widgets |
| S0.5 Redirect admin login → admin overview | `frontend/src/app/dashboard/page.tsx` o middleware | 15 min | role=admin cae en `/admin/overview`, no en `/dashboard` |
| S0.6 Sidebar: admin ve solo secciones MD | `components/layout/sidebar.tsx` | 15 min | Admin NO ve nav cliente (monitoreo, dirigentes, etc.) |
| S0.7 Link "Ver como cliente" con org selector | sidebar admin | 20 min | Admin puede ponerse X-Org-Id y ver dashboard cliente para QA |
| S0.8 Smoke test visual Chrome DevTools | — | 10 min | Screenshot overview + navegación a clasificación |

**Dependencias:** Ninguna (admin panel clasificación ya existe, solo agregamos overview).
**Paralelizable:** S0.1+S0.2+S0.3 en backend pueden concurrir; S0.4 espera endpoint.
**Recursos:** fastapi skill, frontend-architect, shadcn/ui cards, Chrome DevTools.

**Riesgos:**
- Admin también es dirigente de una org (doble rol) → probar caso borde
- RLS puede bloquear queries agregadas → usar service role o bypass explícito con `is_admin`
- Sidebar actual tiene filter `adminOnly`; extender con `clientOnly` para separación limpia

**Decisión CEO:** Redirect duro admin → `/dashboard/admin/overview` (opción A). Admin nunca ve dashboard cliente a menos que use selector "Ver como cliente".

**Charts corrección CEO:** Los 3 charts (Treemap/Stream/Sunburst) NO van uno por menú. Van con **switcher en el mismo widget** para alternar visualización de la MISMA data.

**Ajustes post cross-audit Gemini (aceptados):**
- **A1:** Dashboard reactivo — polling 30s en cards críticos (cola semanal, health). No SSE en esta fase.
- **A2:** Schema `plan_tareas` congelado (ya aplicado en migración previa) — no tocar durante paralelo S0/S0.5.

---

### Sprint 0.5 — Planes deliberados (partido tras audit Gemini) ⭐

**Ajustes post-Gemini:**
- **A3 Métricas híbridas:** IA propone `metrica_valor_objetivo` inicial, dirigente edita. `metrica_valor_real` se calcula automático desde social_posts (job en Sprint A). "La brecha es el KPI real."
- **A4 RAG local:** Generador lee `AUDITORIA-SENTIMENT-2026-04-13.md` + `POLITICAL-FRAMEWORK-DEFAULTS.md` + 95 posts framework + social_posts del dirigente antes de proponer tareas.
- **A5 Feature creep mitigado:** S0.5 se parte en **S0.5a (piloto)** y **S0.5b (replicación)**. NO se generan 6 planes sin validar UX de aprobación con UNO.

### Sprint 0.5a — Plan piloto + flujo aprobación (1.5 h)

**Objetivo:** Los 6 dirigentes reales tienen planes con tareas ESTRUCTURADAS (metas numéricas, plataforma, frecuencia, deadline) generadas con deliberación Claude + Gemini. Hoy: 3 planes con markdown libre, 0 tareas estructuradas. Meta: 6 planes × ~12 tareas = **~72 tareas medibles**.

**Estado actual BD:**
- Con plan (solo markdown): Piña, Pineda, Jiménez
- Sin plan: Solano, Nolasco, Cravioto
- Tareas estructuradas: 0 en los 6

**Flujo por dirigente (3 IAs deliberan):**
1. **Claude (yo)** — draft: lee social_posts reales del dirigente + rol_politico + estado/municipio + engagement histórico, propone 10-15 tareas con `metrica_objetivo` + `metrica_valor_objetivo` + plataforma + frecuencia + deadline
2. **Gemini CLI** — audita: cuestiona metas irrealistas, detecta plataformas ignoradas, propone tareas faltantes
3. **Claude** consolida: integra feedback, produce JSON final para `plan_tareas`

| Subtarea | Archivos | Duración | Criterio |
|---|---|---|---|
**S0.5a — Piloto con Piña (1 plan + UI aprobación):**

| Subtarea | Archivos | Duración | Criterio |
|---|---|---|---|
| S0.5a.1 RAG local: indexar contexto (docs + posts) | `backend/scripts/plan_context_loader.py` | 20 min | Devuelve bundle con audit + framework + 50 posts recientes de Piña |
| S0.5a.2 Generador deliberado 1 dirigente | `backend/scripts/generate_plan_deliberado.py` | 30 min | Produce JSON 10-15 tareas con metricas para Piña |
| S0.5a.3 Cross-audit Gemini al plan Piña | gemini CLI | 15 min | Claude integra ≤20% ajustes |
| S0.5a.4 Seed tareas Piña en `plan_tareas` | SQL | 5 min | Plan 1 tiene 10-15 tareas |
| S0.5a.5 UI tareas + aprobar/rechazar por tarea | `frontend/src/app/dashboard/planes/[id]/page.tsx` | 30 min | Lista de tareas con checkbox estado, botón editar meta |
| S0.5a.6 Endpoint PATCH `/planes/{id}/tareas/{tid}` | `backend/app/api/v1/endpoints/planes.py` | 15 min | Cambia estado + metrica_valor_objetivo + audit en cambios_historial |

**PAUSA CEO aquí.** Solo si CEO aprueba flujo UX → arrancar S0.5b.

### Sprint 0.5b — Replicación a los 5 restantes (1.5 h, POST-APROBACIÓN CEO)

| Subtarea | Duración | Criterio |
|---|---|---|
| S0.5b.1 Parser markdown → tareas (Pineda, Jiménez) | 20 min | 2 planes existentes con tareas estructuradas |
| S0.5b.2 Generar 3 planes nuevos (Solano, Nolasco, Cravioto) | 45 min | 3 planes con 10-15 tareas cada uno |
| S0.5b.3 Cross-audit Gemini batch | 15 min | Reporte por plan, integración |
| S0.5b.4 Seed en BD + verificación | 10 min | `COUNT(plan_tareas) ≥ 60` total |

**Dependencias:** Ninguna (modelo `plan_tareas` ya existe). Puede correr en paralelo con Sprint 0 si hay dos sesiones (tú ejecutas Sprint 0 frontend, peer genera planes).
**Recursos:** Claude Opus 4.6, Gemini CLI, modelo `PlanTarea` existente, posts reales ya clasificados (95 framework + 3,709 NLP).

**Salida:** Base de datos con tareas medibles. Precondición para Sprint A (Avances y Metas widget).

---

### Sprint 1 — Clasificación inicial operativa (1-1.5 h) ✅ COMPLETADO
**Objetivo:** Validar end-to-end el admin panel construido. Las 3 orgs pasan de 0% cobertura a ~60-80 posts clasificados cada una.

| Subtarea | Archivos | Duración | Criterio |
|---|---|---|---|
| S1.1 Generar prompt MC-CDMX 30 posts | Panel admin | 2 min | 30 posts top engagement |
| S1.2 Clasificar con Claude (yo) | chat mismo | 5 min | JSON array 30 items válidos |
| S1.3 Aplicar vía /batch | Panel admin | 1 min | processed=30 failed=0 |
| S1.4 Verificar dashboard cliente MC-CDMX | Chrome visual | 3 min | Scores políticos visibles |
| S1.5 Repetir para GOB-OAXACA | — | 15 min | Igual para org 2 |
| S1.6 Repetir para CDMX-IND | — | 15 min | Igual para org 3 |
| S1.7 Cross-audit Gemini muestra 10 posts | gemini CLI | 10 min | Gemini valida/corrige ≤ 20% |
| S1.8 Screenshot dashboards actualizados | Chrome | 5 min | 3 screenshots en `/tmp/` |
| S1.9 Pruebas robustez admin panel (Gemini) | Panel admin | 10 min | Upload JSON mal formado, post_ids inexistentes, volumen > 60 posts |

**Dependencias:** Ninguna (panel ya construido, APIs funcionan).
**Paralelizable:** No (pipeline secuencial).
**Recursos:** Claude Code (yo) + admin panel + Chrome DevTools.

### Sprint 2 — NLP reprocess reanudar + Topics cache (30-45 min) ✅ COMPLETADO (background exit 0)
**Objetivo:** Completar los 3,449 posts restantes con campos nuevos de `analyze_full()`.

| Subtarea | Archivos | Duración | Criterio |
|---|---|---|---|
| S2.1 Limpiar cache xlm-roberta | `~/.cache/huggingface/hub/` | 5 min | Directorio borrado |
| S2.2 Re-descargar modelo (~2GB) | pip + primera llamada | 10-15 min | `predict_topics()` devuelve lista |
| S2.3 Smoke test con 5 posts | reprocess_nlp_full.py | 3 min | Topics JSONB poblado |
| S2.4 Batch full (background) | reprocess_nlp_full.py | 30-60 min bg | 3,709 con nlp_model_version=v1 |
| S2.5 Query verificación coverage | SQL | 2 min | 100% procesados |

**Dependencias:** S2.1 → S2.2 → S2.3 → S2.4
**Paralelizable:** S2.4 (background) con Sprint 3
**Recursos:** Bash, Python backend container.

### Sprint 3 — Scrapers encuestas públicas (3-5 h)
**Objetivo:** Implementar scrapers Oraculus + Demoscopía según plan del peer md-research.

**S3.0 PRE-REQUISITO (nuevo, por Gemini)** — 30 min validación manual
- Abrir Oraculus `/aprobacion-presidencial/` en browser, validar que el JSON inline sigue en línea ~138
- Abrir Demoscopía `/aprobacionEstado/ciudad-de-mexico/` y `/aprobacionEstado/oaxaca/`, validar que Flourish IDs están expuestos en HTML
- Documentar los regex exactos que funcionan HOY (puede cambiar mañana)
- Si algo cambió vs reporte peer: ajustar antes de codear

| Subtarea | Archivos | Duración | Criterio |
|---|---|---|---|
| S3.1 Scraper Oraculus federal | `backend/scrapers/oraculus.py` (nuevo) | 45 min | JSON inline parseado, 7+ presidentes extraídos |
| S3.2 Persistir en `encuestas_publicas` | script seed | 15 min | ≥ 50 encuestas Sheinbaum últimos 6 meses |
| S3.3 Scraper Demoscopía CDMX | `backend/scrapers/demoscopia.py` | 60 min | Brugada aprobación mensual ≥ 3 puntos |
| S3.4 Scraper Demoscopía Oaxaca | mismo archivo | 30 min | Jara aprobación mensual ≥ 3 puntos |
| S3.5 Celery task scheduler | `backend/app/workers/tasks.py` | 20 min | Cron diario a las 14:00 MX |
| S3.6 Servicio divergencia + endpoint | `divergencia_encuestas.py` + endpoint `/dashboard/divergencia` | 30 min | Query mensual devuelve dict con flag alert |
| S3.7 Badge "Atención divergencia >30%" en UI | dashboard page | 20 min | Visible cuando alert=true |
| S3.8 Test end-to-end | — | 15 min | Datos reales visibles en dashboard |

**Dependencias:** S3.1-S3.4 independientes entre sí, S3.6 depende de S3.2
**Paralelizable:** S3.1+S3.3 foreground si hago uno y el peer hace otro
**Recursos:** python-expert, fastapi skill, httpx + regex, Alembic.

### Sprint 4 — Cierre documental + commit (15 min)
**Objetivo:** Cerrar la sesión con docs actualizados.

| Subtarea | Archivos | Duración | Criterio |
|---|---|---|---|
| S4.1 Actualizar STATUS.md con resultados S1+S2+S3 | `.context/STATUS.md` | 5 min | Sección nueva |
| S4.2 Registrar decisiones | `.context/DECISIONS.md` | 3 min | D-SCRAPER-01 para Oraculus |
| S4.3 Commit + push | git | 2 min | Commit pusheable a origin |
| S4.4 Reporte final al CEO | text | 5 min | Tabla con deliverables |

**Dependencias:** Después de S1-S3
**Recursos:** Edit + git.

---

## Dependencias visuales (REV 2)

```
✅ Sprint 1 (clasificación) ──── DONE commit 385aad5
✅ Sprint 2 (NLP batch)    ──── DONE background exit 0

⭐ Sprint 0 (Dashboard Admin) ────┐
⭐ Sprint 0.5 (6 planes IA) ──────┤  (paraleliza con S0)
                                  │
   [PAUSA · CEO revisa] ──────────┤
                                  │
   Sprint A (Avances/Metas UI) ───┤  (depende de S0.5)
   Sprint 3 (Scrapers) ───────────┤
                                  │
        Sprint 4 (cierre) <───────┘
```

Orden aprobado por CEO:
1. **Sprint 0 + Sprint 0.5** en paralelo (dashboard admin + generación 6 planes)
2. **PAUSA** — CEO revisa antes de continuar
3. Post-revisión: **Sprint A** (widget Avances/Metas) + **Sprint 3** (scrapers)
4. **Sprint 4** cierre

---

## Recursos asignados por sprint

| Sprint | Agent/Skill | Herramientas |
|---|---|---|
| **0** ⭐ | frontend-architect + fastapi skill + shadcn/ui + kpi-dashboard-design | Chrome DevTools, Docker exec, Edit |
| 1 ✅ | Claude Opus 4.6 clasificador | (completado) |
| 2 ✅ | python-expert | (completado) |
| 3 | fastapi skill, python-expert | httpx, regex, Alembic, Celery |
| 4 | technical-writer | Edit, git |

---

## Riesgos y mitigaciones

| Riesgo | Prob | Mitigación |
|---|---|---|
| Clasificación Claude sesgada | Media | Cross-audit Gemini sobre 10 muestra |
| Oraculus cambia HTML structure | Baja | Regex con fallback, log si no matchea |
| Demoscopía Flourish IDs cambian | Media | Scraper con fallback a scraping directo HTML |
| Topics cache re-descarga falla red | Baja | Fallback: seguir sin topics |
| Admin panel UX quiebra en uso real | Media | Iterar después de S1.1, no esperar S1.6 |

---

## Criterios de aceptación finales

- ✅ Admin panel probado end-to-end con datos reales de 3 orgs
- ✅ Dashboards clientes reflejan scores políticos
- ✅ 3,709 posts con controversy/toxicity/topics completos
- ✅ Scrapers encuestas corriendo diario
- ✅ Badge de divergencia funcional
- ✅ Commit pushable a `main` vía PR

---

## Cross-audit Gemini (aplicado 2026-04-13)

Gemini validó el plan. Integrados 3 cambios:
1. **S3.0 NUEVO** — validación manual de endpoints Oraculus/Demoscopía ANTES de codear (riesgo #1 identificado)
2. **S1.9 NUEVO** — pruebas robustez admin panel con datos inesperados
3. **Tiempo recalibrado: 8-10h (antes 5-6h)** — Gemini dijo optimista

### Estimación realista REV 2 (pendiente)

| Sprint | Duración |
|---|---|
| **Sprint 0 Dashboard Admin** ⭐ | 2.5-3h |
| Sprint 3 Scrapers | 4-5h |
| Sprint 4 Cierre | 30min |
| **TOTAL pendiente** | **7-8.5h** |

Si solo Sprint 0 + Sprint 4 parcial: **3-3.5h**. Si todo: sesión completa.

---

## Pendiente FASE 4 (ejecución)

**NO EJECUTAR HASTA APROBACIÓN CEO.**

REV 2 — CEO debe responder:
1. ¿Apruebas Sprint 0 (Dashboard Admin) con los 6-7 widgets propuestos?
2. ¿Admin al login cae en `/admin/overview` o sigue viendo `/dashboard` con banner?
3. ¿Después de Sprint 0 seguimos con Sprint 3 (scrapers) en esta sesión o paramos?
4. ¿Cross-audit con Gemini antes de codear Sprint 0?
