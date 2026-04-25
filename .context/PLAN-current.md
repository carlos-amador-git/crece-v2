ACTIVE: PLAN-D-23-G-actividad-alineada-2026-04-24.md

---

# Plan revisado — Hotfixes piloto 2026-04-23 (post-review CEO 11 screenshots)

> ⚠️ SUPERSEDED 2026-04-23: el plan vigente al día de hoy es
> `PLAN-recuperacion-post-incidente-2026-04-21.md` (v3, aprobado CEO + Joy + Gemini cross-audit).
> Sprint 23-A..E se ejecutó en paralelo SIN invadir el incidente 3d6fe3f. Los hotfixes
> de este documento están cerrados · lo que queda pendiente es Frente 0 (observabilidad)
> y Frente 1 (schema restauración) del plan de recuperación.
> Todo diagnóstico sobre migrations, schema, framework político o seguridad debe leer
> PRIMERO `PLAN-recuperacion-post-incidente-2026-04-21.md`.

---

**Origen:** `/sprint-review` sobre diagnóstico `DIAGNOSTICO-SCREEN-CRECE.md` (F-23-01..F-23-11).
**Contexto de disciplina:** MVP cerrado · piloto comercial activo · próximo §9.8 ≈ 2026-05-20.
**Regla vigente (SPRINT-CURRENT.md L65-77):** bugs críticos = hotfix PR directo; cambios estructurales D-01..D-24 = esperar §9.8.

---

## FASE 1 — Revisión crítica del plan previo

`PLAN-current.md` es el **plan Sprint B del 2026-04-14 (PR #12)**, ya ejecutado y mergeado. Está obsoleto. No debe usarse como referencia actual.

**Acción sugerida:** mover a `.context/archive/` tras confirmación CEO; este documento toma su lugar durante la ventana del 2026-04-23.

---

## FASE 2 — Enriquecimiento: clasificación por disciplina §9.8

Cada finding se clasifica en:

- 🟢 **HOTFIX** — bug visible en prod, puede cerrarse con PR directo a main sin tocar D-01..D-24.
- 🟡 **CALIBRACIÓN** — ajuste de umbrales/copy/flags dentro del scope aprobado. Permitido por SPRINT-CURRENT L76.
- 🔴 **ESTRUCTURAL §9.8** — toca matriz NLP, motor de afiliación, o rediseño de bloques. Requiere puerta dos §9.8 o luz verde explícita CEO para adelantarse.

| # | Finding | Banda | Clasif. | Archivo(s) principales |
|---|---|---|---|---|
| F-23-01 | Sentimiento sin afiliación en Tema Urgente + Alertas | 1 | 🔴 §9.8 | `backend/app/services/sentiment_afiliacion.py` (nuevo o revisar existente) · `frontend/app/dashboard/page.tsx` |
| F-23-02 | `vs Competidor Principal` hardcodea a Piña | 1 | 🟢 HOTFIX | `frontend/src/components/dashboard/competitor-snapshot-card.tsx` |
| F-23-03 | Falta toggle RT en Tono Discursivo | 3 | 🟡 CALIB | `frontend/app/dashboard/page.tsx` chart section |
| F-23-04 | Falta filtro por red social en Tono Discursivo | 3 | 🟡 CALIB | mismo |
| F-23-05 | Post cards: 0 comments, sin ícono red, sin link | 1 | 🟢 HOTFIX (UI) + 🔴 datos | `frontend/src/components/social/post-card.tsx` + backend scraper fields |
| F-23-06 | Ficha dirigente Sentimiento Prom. `-59%` sin afiliación | 3 | 🔴 §9.8 | Ligado a F-23-01 |
| F-23-07 | Tab Electoral vacío sin mensaje diferenciado | 3 | 🟡 CALIB | dirigente page Electoral section |
| F-23-08 | Tab Planes sin CTA generar | 3 | 🟡 CALIB | dirigente page Planes section |
| F-23-09 | Diagnóstico Tier 1 header con "MASTER §3.1", link metodología roto | 2 | 🟡 CALIB (quitar ref interna) + 🔴 (metodología) | `frontend/src/components/diagnostico/cards.tsx` |
| F-23-10 | Tier 1 copy académico, 10 bloques ininteligibles | 2 | 🔴 §9.8 (rewrite estructural) | `frontend/src/components/diagnostico/cards.tsx` (39.5KB) |
| F-23-11 | Tier 2 copy académico, 8 bloques ininteligibles | 2 | 🔴 §9.8 (rewrite estructural) | `frontend/src/components/diagnostico_tier2/cards.tsx` (32.3KB) |

**Conteo:** 3 🟢 HOTFIX · 4 🟡 CALIB · 5 🔴 §9.8 (F-23-06 cuenta dentro de F-23-01).

---

## FASE 3 — Cross-audit (sustituto `/gemini review`)

Auto-crítica al plan propio (sin llamar al wrapper Gemini para no gastar cuota en algo resoluble por lectura):

1. **Gap identificado:** la clasificación §9.8 de F-23-10/11 puede estar **sobreprotegiendo**. El copy de los bloques **NO** toca decisiones D-01..D-24 (definiciones métricas) — solo reformula la presentación UX. Se puede reclasificar a 🟡 CALIB si el CEO confirma que el rewrite mantiene intactas: fórmulas, nombres de campos en BD, umbrales, y solo ajusta *labels, descripciones, tooltips, orden visual*.
2. **Optimización:** F-23-03 y F-23-04 comparten archivo y componente → mergear en una sola tarea.
3. **Dependencia oculta:** F-23-06 cierra sola si F-23-01 cierra (mismo motor). Dejar como verificación.
4. **Riesgo de regresión:** F-23-05 (post-card link) requiere verificar que `post.source_url` exista en el modelo. Si no existe → bloqueante scraper, NO cerrar UI hasta poblar campo.

---

## FASE 4 — Asignación de recursos

| Banda | Agentes | Skills | Herramientas |
|---|---|---|---|
| Banda 1 bloqueantes | `frontend-architect` · `backend-architect` | `nextjs15`, `shadcn-ui`, `playwright-testing`, `react-ui-patterns` | Playwright MCP (validación visual) · chrome-devtools (console) |
| Banda 2 UX copy | `frontend-architect` · `technical-writer` | `tailwindcss-v4`, `web-design-guidelines`, `baseline-ui` | shadcn MCP · Playwright screenshots post/pre |
| Banda 3 filtros/empty | `frontend-architect` | `shadcn-ui`, `react-ui-patterns` | — |

---

## FASE 5 — Ejecución con verificación (bloqueada por decisiones CEO)

**No inicio ejecución** porque faltan 3 decisiones del CEO + 1 decisión de disciplina:

### Decisiones pendientes (copiar respuesta en chat)

1. **D-23-A (disciplina §9.8):** ¿Se puede cerrar F-23-10 y F-23-11 (rewrite de copy Tier 1/2) como **🟡 CALIB** dentro del scope del piloto — dado que NO se tocan fórmulas ni campos, solo textos visibles? O se queda para §9.8 del 2026-05-20?
2. **D-23-B (F-23-09):** "Metodología completa →" actualmente apunta a página vacía. ¿Opciones? (a) página pública breve con 1 párrafo por métrica; (b) doc interno con link restringido; (c) eliminar el link.
3. **D-23-C (F-23-10/11):** ¿Se mantienen referencias académicas (Brookings, Zenodo, ITESO, DFRLab) como sello de credibilidad, o se eliminan completamente para simplificar?
4. **D-23-D (F-23-07):** Para dirigentes plurinominales (sin secciones electorales), ¿se oculta el tab Electoral o se muestra con mensaje "Sin territorio asignado · CTA asignar"?

### Sprints propuestos (orden de ejecución tras luz verde)

**Sprint 23-A — Hotfixes UI puros (≈ 60 min) · 🟢 no bloqueado por decisiones**
- S23-A.1 · F-23-02 · Competitor hardcoded → bind a `activeLeaderId` + empty state si sin rival
- S23-A.2 · F-23-05 (UI) · Post cards: añadir ícono red social + link a `source_url` · validar campo en BD
- S23-A.3 · F-23-03 + F-23-04 · Toggle RT + filtro red social en Tono Discursivo
- S23-A.4 · F-23-08 · CTA "Generar plan" en tab Planes vacío
- S23-A.5 · F-23-09 (parcial) · Quitar "(MASTER §3.1)" del header · tooltip "ER"
- **Verificación:** `npm run build` · Playwright screenshot comparativo post/pre · reporte diff

**Sprint 23-B — Datos scraper (≈ 45 min) · 🟢 no bloqueado**
- S23-B.1 · F-23-05 (datos) · Validar `comment_count`, `share_count`, `source_url` en modelo `SocialPost` y scrapers. Si faltan → alembic migration + backfill.
- **Verificación:** SELECT de 10 posts aleatorios · los 3 campos no null

**Sprint 23-C — Empty states (≈ 30 min) · 🟡 bloqueado por D-23-D**
- S23-C.1 · F-23-07 · Empty state Electoral según D-23-D
- S23-C.2 · F-23-09 (resto) · Página metodología según D-23-B

**Sprint 23-D — Copy rewrite Tier 1 + Tier 2 (≈ 3-4h) · 🔴 bloqueado por D-23-A + D-23-C**
- S23-D.1 · F-23-10 · Rewrite 10 bloques Tier 1 con patrón "qué mide / cómo te fue / qué hacer"
- S23-D.2 · F-23-11 · Rewrite 8 bloques Tier 2 mismo patrón
- S23-D.3 · F-23-09 (parte copy) · Subtítulo header en lenguaje llano
- **Verificación:** Playwright screenshot + revisión CEO antes de merge

**Sprint 23-E — Sentimiento con afiliación (≈ 4-6h) · 🔴 bloqueado por §9.8**
- S23-E.1 · Evaluar si motor `polariza_por_bando` existe o hay que construirlo
- S23-E.2 · Aplicar en Tema Urgente + Alertas + Sentiment Prom.
- **Nota CEO:** esto parece §9.8 duro — afecta la matriz y el cómputo central. Proponer formalmente para revisión día 30, O luz verde explícita para adelantarse.

---

## Criterios de aceptación globales

- ✅ Un screenshot post-fix por cada finding cerrado (archivar en esta carpeta)
- ✅ Cada sprint en branch separada con PR individual (convención: `hotfix/f-23-XX`)
- ✅ Merge solo tras screenshot aprobado y `npm run build` verde
- ✅ `.context/DECISIONS.md` actualizado con D-23-A..D al cierre
- ✅ `.context/STATUS.md` anotado con referencia a este plan

## Riesgos

| Riesgo | Mitigación |
|---|---|
| `post.source_url` no existe en modelo | Sprint 23-B como gate antes de Sprint 23-A.2 |
| Rewrite copy rompe i18n | No hay i18n activa en CRECE — riesgo bajo |
| CEO rechaza D-23-A → §9.8 | Sprint 23-D y 23-E se difieren a mayo; 23-A/B/C se cierran solos |
| Scope creep si se tocan otros findings vecinos | Karpathy rule 3: surgical changes, 1 commit = 1 finding |

---

**Estado:** ⏸ PAUSADO esperando respuesta a D-23-A..D.
**Siguiente acción al recibir respuesta:** iniciar Sprint 23-A en branch `hotfix/23a-ui-puros`.
