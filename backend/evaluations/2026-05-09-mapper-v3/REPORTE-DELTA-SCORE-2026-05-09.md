# Delta Score Político · Impacto matriz v2 poblada

**Fecha:** 2026-05-09  
**Sprint:** S5 post-/sprint-implement v3 mapper  

## Hallazgo crítico

La tabla `framework_matrix_defaults` estaba **VACÍA** en BD hasta hoy 2026-05-09. La migración `f7a8b9c0d1e2_political_framework.py` estaba huérfana del chain alembic — nunca se aplicó. Como resultado, `get_political_score()` retornaba **fallback 0 para todo comment**, invalidando silenciosamente el KPI "Sentimiento Político Ajustado".

Después de S1+S2: 53 reglas pobladas (32 post + 21 comment).

## Resumen ejecutivo

- **Comments sample:** 500 (los 500 más recientes con NLP + dirigente)
- **Comments con score que CAMBIA (pre 0 → post ≠0):** 0 (0.0%)
- **Score positivo:** 0 (0.0%)
- **Score negativo:** 0 (0.0%)
- **Score 0 / sin match en matriz:** 500 (100.0%)
- **Misses (combinación rol/tono/target sin regla):** 483 (96.6%)

## KPI agregado por dirigente

| Dirigente | rol | comments | Σscore pre | Σscore post | Δ |
|---|---|---:|---:|---:|---:|
| Laura Ballesteros Mancilla | oposicion | 285 | 0 | 0 | +0 |
| Gabriela Jiménez Godoy | oficialismo | 190 | 0 | 0 | +0 |
| César Cravioto Romero | oficialismo | 12 | 0 | 0 | +0 |
| Yesenia Nolasco Ramírez | oficialismo | 11 | 0 | 0 | +0 |
| Alejandro Piña Medina | oposicion | 1 | 0 | 0 | +0 |
| Saymi Adriana Pineda Velasco | oficialismo | 1 | 0 | 0 | +0 |

## Combinaciones (rol, tono, target) sin regla en matriz

Top 15 combinaciones más frecuentes que retornan 0 por falta de regla:

| rol | tono | target | count |
|---|---|---|---:|
| oposicion | personal | autopromocion | 214 |
| oficialismo | personal | autopromocion | 165 |
| oposicion | personal | gobierno | 35 |
| oposicion | personal | oposicion | 14 |
| oficialismo | personal | gobierno | 9 |
| oposicion | personal | ciudadania | 6 |
| oficialismo | personal | ciudadania | 5 |
| oficialismo | personal | tema_especifico | 4 |
| oficialismo | critico | autopromocion | 4 |
| oposicion | propositivo | autopromocion | 3 |
| oposicion | personal | tema_especifico | 3 |
| oposicion | critico | gobierno | 3 |
| oficialismo | ataque | autopromocion | 2 |
| oficialismo | personal | medios | 2 |
| oficialismo | propositivo | autopromocion | 2 |

## Implicación para piloto §9.8

- **Pre-S2 (hasta hoy):** dashboards mostraban score=0 para todos los comments. KPI 'Actividad Política Alineada' computado contra base 0 — métricas distorsionadas.
- **Post-S2:** scores reales aplicados. Los dirigentes con engagement positivo (propositivo + dirigente target) reciben +1, los con ataque + gobierno reciben -1, etc.
- **Recomendación:** pasar batch `recompute_actividad_alineada.py` sobre los 2696 comments populated para que el dashboard refleje scores reales antes del gate.

## Pendiente D+1

- Ground truth humano 100 rows (validar concordancia v3 mapper vs anotación)
- UI dual labels opción B (frontend, 1.5h)
- Recomputar `actividad_politica_alineada` con scores nuevos sobre 2696 comments
