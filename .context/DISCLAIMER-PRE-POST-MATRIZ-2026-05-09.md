# Disclaimer · Números pre/post matriz política · 2026-05-09

**Para uso de:** cualquier persona que reuse números del piloto CRECE en reportes ejecutivos, presentaciones a cliente, o comparativos cross-temporal.
**Severidad:** ALTA — los números pre-2026-05-09 NO son comparables con los post.
**Última actualización:** 2026-05-09 (Linda · sesión CRECE electoral)

---

## El hecho duro

Hasta hoy 2026-05-09, la tabla `framework_matrix_defaults` estaba **VACÍA en BD**. Causa: migration `f7a8b9c0d1e2_political_framework.py` quedó huérfana del chain alembic (`down_revision='d5d6d7d8d9e0'` referencia una revision que no existe), por lo que **nunca se aplicó**.

Consecuencia silenciosa: la función `political_framework.get_political_score()` retornaba **fallback 0 para todo comment** sin error, sin warning, sin alert. Durante todo el piloto hasta hoy, **el KPI "Actividad Política Alineada" se calculó contra base 0** y mostraba números artificialmente estables.

Hoy 2026-05-09 se reparó:
- Schema recovery aplicado vía SQL idempotente
- 60 reglas pobladas (32 post_dirigente + 28 comment_tercero) — 53 originales + 7 añadidas tras revisión CEO
- Mapper v3.0.1 con passthrough vocab v2

---

## Qué cambió: tabla pre/post

### KPI Σscore por dirigente · 2696 comments populated

| Dirigente | Rol | Comments NLP | KPI Σ pre (matriz vacía) | KPI Σ post (matriz reparada) | Δ |
|---|---|---:|---:|---:|---:|
| Gabriela Jiménez Godoy | oficialismo | 1054 | 0 | +1 | +1 |
| Laura Ballesteros Mancilla | oposicion | 784 | 0 | +1 | +1 |
| Alejandro Piña Medina | oposicion | 406 | 0 | +1 | +1 |
| Saymi Adriana Pineda Velasco | oficialismo | 179 | 0 | 0 | 0 |
| César Cravioto Romero | oficialismo | 129 | 0 | -3 | -3 |
| Yesenia Nolasco Ramírez | oficialismo | 120 | 0 | 0 | 0 |
| Rafael Solano Pérez | oposicion | 24 | 0 | 0 | 0 |

### Tasa de cobertura de matriz

| Métrica | Pre (2026-04-13 a 2026-05-08) | Post (2026-05-09) |
|---|---|---|
| Comments con score ≠ 0 | 0 / 2696 (0%) | 38 / 2696 (1.4%) |
| Comments con score 0 | 2696 / 2696 (100%) | 2658 / 2696 (98.6%) |
| Posts con score ≠ 0 | 0 / 4817 (0%) | 0 / 4817 (0%, sin `tono_discurso` populated) |
| Razón score 0 dominante | matriz vacía (bug) | combinación rol/tono/target sin regla en matriz (gap conocido) |

### Distribución corpus comments — Top 5 combinaciones (% del corpus 2696)

| tono | target | count | % corpus | Tiene regla en matriz |
|---|---|---:|---:|---|
| personal | autopromocion | 2105 | 78.1% | NO (rejected CEO 2026-05-08) |
| personal | gobierno | 187 | 6.9% | NO |
| celebratorio | autopromocion | 152 | 5.6% | NO (rejected CEO 2026-05-08) |
| personal | ciudadania | 70 | 2.6% | NO |
| personal | oposicion | 56 | 2.1% | NO |

---

## Qué interpretación es correcta

### ✅ INTERPRETACIÓN VÁLIDA

> "El KPI Σscore mostró 0 para todos los dirigentes durante el piloto pre-2026-05-09 porque la matriz política nunca se aplicó. La métrica era estructuralmente inválida — no es que los dirigentes tuvieran actividad política neutral, sino que el motor no la calculaba. Tras la reparación del 2026-05-09, los nuevos números reflejan la fracción del corpus que SÍ matchea reglas (1.4%)."

### ❌ INTERPRETACIONES INVÁLIDAS (no usar)

> "El KPI Σscore cayó de 0 a -3 para Cravioto entre abril y mayo, indica deterioro." → INCORRECTO. El score -3 siempre fue lo correcto; el 0 anterior era un bug del motor.

> "Los nuevos números muestran que la matriz casi no clasifica nada (1.4%)." → INCOMPLETO. La cobertura 1.4% es by-design tras decisión CEO 2026-05-08 que rechazó 3 reglas que abrirían la categoría dominante (`personal+autopromocion`) por considerarla bolsa de basura sin valor político (incluye desde "👏" hasta "puto presidente"). El 98.6% en score=0 NO es ruido del motor — es el motor declarando "esto no es contenido político clasificable".

> "Comparemos el dashboard del 2026-04-25 vs hoy para ver tendencia." → INCORRECTO. Los dashboards pre-2026-05-09 reflejan motor roto; los post reflejan motor reparado. Cualquier comparación cross-fecha sobre Σscore o "Actividad Política Alineada" debe excluir el período pre-reparación.

---

## Reglas para reportes ejecutivos

1. **Cualquier reporte que cite Σscore o Actividad Política Alineada cross-temporal DEBE incluir este disclaimer** o uno equivalente que explique el reset 2026-05-09.

2. **Para comparativos del piloto**, usar como nuevo baseline el día 2026-05-09. Comparativos vs días anteriores son inválidos para esta KPI específica.

3. **Otras KPIs sin afectación:** alcance, engagement rate, sentiment_score (de pysentimiento, no afectado por matriz política), volumen de posts/comments — estas SÍ son comparables cross-temporal pre/post 2026-05-09.

4. **Si el cliente pregunta por la caída:** la explicación correcta es "calibración del motor" — no "deterioro de actividad política". El motor pre-reparación no aplicaba la matriz; ahora sí. Los números son más honestos, no peores.

---

## Pendientes que cambiarán esta tabla en D+1 a D+7

| Acción | Impacto esperado |
|---|---|
| Ground truth humano 100 rows (en marcha) | Identifica reglas faltantes, podría aumentar cobertura del 1.4% |
| Ampliación matriz post ground truth | Cobertura sube si ground truth revela combos sistemáticos no cubiertos |
| Recompute global tras matriz ampliada | Tabla pre/post se actualiza con nuevos Σscore |
| UI dual labels opción B | Frontend mostrará en cada comment si la clasificación es "del sistema" vs "validada por humano" |

**Cuando estos cierren, este disclaimer se actualiza con tabla nueva.** Hasta entonces, los números del 2026-05-09 son el baseline operativo.

---

## Referencias

- Hallazgo + reparación: `.context/DECISIONS.md` § D-NLP-X (Matriz política vacía descubierta + reparada)
- Reporte global recompute fuente: `backend/evaluations/2026-05-09-mapper-v3/RECOMPUTE-GLOBAL-2026-05-09.md`
- Decisiones CEO sobre reglas rechazadas: `.context/DECISIONS.md` § D-NLP-X tabla "7 reglas aprobadas + 3 rechazadas"
- Mapper actual: `backend/app/nlp/matriz_v3_mapper.py` v3.0.1
