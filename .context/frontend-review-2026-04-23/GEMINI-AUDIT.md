# Gemini cross-audit · Plan revisado 2026-04-23

**Ejecutado:** `~/.claude/bin/gemini-clean --mode review --context PLAN-REVISADO.md`.
**Output crudo:** ver abajo.

## Resumen integrado al plan

**Aprobadas (8 findings):** F-23-01, 02, 03, 04, 06, 07, 08, 09 — clasificación correcta.

**Cuestionadas (3):**
- **F-23-05 datos (reclasificación condicional):** Si requiere alembic migration en piloto activo → es 🔴 §9.8, no "no bloqueado". Mitigación propuesta por Gemini: **graceful degradation** en frontend (ocultar botón link si `source_url` null) para desacoplar S23-A.2 de S23-B.
- **F-23-10 → CALIB** (no §9.8). Confirma duda de FASE 3: rewrite de copy sin tocar fórmulas no es estructural.
- **F-23-11 → CALIB** (no §9.8). Mismo caso.

**Gaps:**
1. Falta estrategia de graceful degradation post-card → **aplicar en S23-A.2**.
2. Falta plan de rollback para alembic migration → **incluir en S23-B si se procede**.

**Optimizaciones:**
1. S23-A y S23-C paralelizables (archivos disjuntos).
2. F-23-07 + F-23-08 agrupables (ambos empty states).

**Riesgos no vistos:**
1. **Downtime BD:** alembic en prod bloquea tabla → ventana de mantenimiento programada.
2. **Fragilidad scraper:** revalidar rate limits al extraer comment/share counts → puede romper recolección actual del piloto.

## Cambios al plan post-audit

| Ajuste | Sección afectada | Razón |
|---|---|---|
| F-23-10 y F-23-11 → 🟡 CALIB | FASE 2 clasificación | Gemini confirma: solo copy, no fórmulas |
| Sprint 23-A.2 añade graceful degradation | Sprint 23-A | Rompe dependencia con S23-B; deploy seguro sin tocar BD |
| Sprint 23-B pasa a "INVESTIGACIÓN PRIMERO" | Sprint 23-B | Verificar existencia campos antes de proponer migration; si falta → escalar §9.8 |
| Sprint 23-D pasa a CALIB ejecutable | Sprint 23-D | Reclasificación F-23-10/11 habilita ejecución en ventana del piloto |
| S23-A + S23-C marcados paralelizables | FASE 4 recursos | Archivos disjuntos permiten ejecución concurrente |
| F-23-07 + F-23-08 agrupados en PR único | Sprint 23-C | Empty states en un solo commit |

---

## Output crudo Gemini

```json
{
  "aprobadas": [
    "F-23-01", "F-23-02", "F-23-03", "F-23-04", "F-23-06",
    "F-23-07", "F-23-08", "F-23-09"
  ],
  "cuestionadas": [
    {
      "finding": "F-23-05",
      "motivo": "Clasificar la modificación de modelos de base de datos (Alembic) y scrapers como 'no bloqueado' (Sprint 23-B) durante un piloto comercial activo es de alto riesgo. Si requiere migración de DB, su impacto es 🔴 ESTRUCTURAL §9.8 y no un simple hotfix."
    },
    {
      "finding": "F-23-10",
      "motivo": "Se confirma el hallazgo de la FASE 3 del plan. Al tratarse exclusivamente de un rediseño de textos (copy) y presentación sin alterar métricas, umbrales o lógica de negocio, se clasifica erróneamente como §9.8. Debe reclasificarse a 🟡 CALIB."
    },
    {
      "finding": "F-23-11",
      "motivo": "Mismo caso que F-23-10. Al ser una actualización puramente visual/semántica del componente React sin tocar NLP o el motor, aplica como 🟡 CALIB."
    }
  ],
  "gaps": [
    "El plan asume que la validación de F-23-05 (datos) bloqueará la UI. Falta definir una estrategia de 'graceful degradation' en el frontend (ej. si `source_url` es null, ocultar el botón enlace temporalmente) para poder desplegar S23-A.2 sin depender de S23-B.",
    "Ausencia de plan de rollback para la migración de Alembic propuesta en el Sprint 23-B."
  ],
  "optimizaciones": [
    "Paralelización de Sprints: S23-A (Hotfixes UI) y S23-C (Empty States) modifican archivos/componentes disjuntos. Pueden ser ejecutados en paralelo por el `frontend-architect`.",
    "Agrupación Lógica: F-23-07 y F-23-08 se enfocan en estados vacíos (empty states) en tabs diferentes. Pueden agruparse bajo un solo PR/ticket de 'Mejora de UX en Tabs Vacíos'."
  ],
  "riesgos_no_vistos": [
    "Downtime de Base de Datos: Ejecutar migraciones de Alembic (Sprint 23-B) en un entorno de producción (piloto) puede generar bloqueos de tabla. Esto requiere una ventana de mantenimiento programada.",
    "Fragilidad de Scrapers: Intervenir los scrapers para extraer `comment_count` y `share_count` requiere revalidación de límites de rate y estructuras de la plataforma origen (ej. Facebook/Twitter). Es un proceso inherentemente frágil que excede el tiempo estimado de 45 min y podría romper la recolección actual de datos del piloto."
  ]
}
```
