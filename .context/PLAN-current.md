# Plan Sprint Cierre — 2026-04-13 noche

**Origen:** `/sprint-review` de pendientes post-commit `118ce13` (framework político)
**Branch:** `feat/sprint-c-hardening`
**Estado:** **REVISIÓN — esperando aprobación CEO antes de ejecutar**

---

## Contexto

El sprint previo cerró el framework político (3 capas, admin panel, UI niveles, charts lab, docs). Quedan 4 pendientes claros para "terminar la sesión":

1. **Clasificación inicial real** de top 60 posts por org (usar el admin panel construido)
2. **Scrapers encuestas públicas** (Oraculus + Demoscopía) — plan del peer md-research listo
3. **NLP reprocess reanudar** (3,449 posts restantes con controversy/toxicity/topics)
4. **Topics model cache fix** (xlm-roberta corrupto)

---

## Sprints propuestos

### Sprint 1 — Clasificación inicial operativa (1-1.5 h)
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

### Sprint 2 — NLP reprocess reanudar + Topics cache (30-45 min)
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

## Dependencias visuales

```
Sprint 1 (clasificación operativa) ───────────┐
                                              │
Sprint 2.1-2.3 (topics cache fix) ──> S2.4 bg │
                                          │   │
            Sprint 3 (scrapers) ──────────┘   │
                                              │
                         Sprint 4 (cierre) <──┘
```

Sprint 1 + Sprint 2 + Sprint 3 **pueden hacerse en cualquier orden** una vez sus dependencias internas resuelvan. Sugiero:
- **Sprint 1 primero** (más corto, valida todo lo ya hecho)
- **Sprint 2.4 batch NLP en background** mientras se hace Sprint 3
- **Sprint 3 foreground**
- **Sprint 4 al final**

---

## Recursos asignados por sprint

| Sprint | Agent/Skill | Herramientas |
|---|---|---|
| 1 | Claude Opus 4.6 (clasificador) + systematic-debugging | Chrome DevTools, admin panel, Gemini CLI |
| 2 | python-expert, pgvector skill | Bash, Docker exec, Alembic |
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

### Estimación realista post-Gemini

| Sprint | Antes | Realista |
|---|---|---|
| Sprint 1 | 1-1.5h | 1.5-2h (+robustez) |
| Sprint 2 | 45min | 1h (re-download + verificación) |
| Sprint 3 | 3-4h | 4-5h (+validación manual + debugging inesperado) |
| Sprint 4 | 15min | 30min (doc + commit + PR) |
| **TOTAL** | **5-6h** | **7-8.5h** |

Gemini dijo 8-10h; mi estimación intermedia 7-8.5h porque tengo ventaja de contexto acumulado.

---

## Pendiente FASE 4 (ejecución)

**NO EJECUTAR HASTA APROBACIÓN CEO.**

El CEO debe responder:
1. ¿Apruebas el orden S1 → S2+S3 paralelo → S4?
2. ¿Hacemos los 3 sprints en esta sesión o dejamos Sprint 3 (scrapers) para mañana?
3. ¿Quieres cross-audit también con Perplexity antes de ejecutar?
