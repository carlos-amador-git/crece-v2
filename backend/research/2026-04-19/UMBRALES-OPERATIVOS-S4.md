# Umbrales Operativos · Sprint S4 Plan IA · 2026-04-19

**Autor:** Joy · **Estado:** approved (integrado al prompt v1.0 bloque 3) · **Sujeto a recalibración:** post-30 días de uso piloto.

Este documento formaliza los 3 umbrales binarios/categóricos que el Plan IA del Sprint S4 consume como entradas de recomendación. Cada umbral tiene: **justificación empírica · fórmula exacta · path de calibración · criterio de ajuste**.

Contexto: los 3 umbrales derivan del documento aprobado `SPRINT-S4-PRE-REQUISITOS.md` §T-1.2. Se anclan aquí porque el pipeline LLM (`llm_pipeline.py`) y el validador anti-vanidad (`anti_vanity_validator.py`) los consumen programáticamente.

---

## Umbral 1 · Topic Drift (B14) — normal vs anómalo

### Justificación
B14 `drift_score` mide la distancia entre el vocabulario de captions del dirigente y el vocabulario de los comments recibidos. Actualmente saturado (~0.997 por Jaccard bigram sobre captions cortos) — un valor absoluto no discrimina. La solución operativa es medir delta vs baseline propio del dirigente.

### Fórmula
```
baseline_dirigente = promedio(drift_score) sobre últimos 30 días de posts del dirigente
delta_pct = (drift_score_post_actual - baseline_dirigente) / baseline_dirigente * 100

status = "normal"  si |delta_pct| ≤ 15%
status = "anomalo" si delta_pct > +15% sostenido en ventana 7d consecutivos
```

### Path de calibración
1. A los 30 días de operación piloto con 8 dirigentes (target): calcular `flag_rate` = `# posts marcados anomalo / # posts totales` sobre 100+ posts reales.
2. **Criterio de ajuste:**
   - `flag_rate < 15%` → umbral demasiado permisivo (no captura drift real). Bajar delta a ±10%.
   - `15% ≤ flag_rate ≤ 40%` → umbral en rango. Mantener ±15%.
   - `flag_rate > 40%` → umbral demasiado sensible (ruido). Subir delta a ±20%.
3. Calibración se documenta incrementando versión del prompt: `PROMPT-PLAN-IA-v1.1.md` si cambio menor, `v2.0` si cambio estructural.

### Consumo en Plan IA
Plan IA solo recomienda revisión de topic drift si `status="anomalo"` EN ventana 7d consecutivos. Un drift puntual de 1 día no es señal accionable.

---

## Umbral 2 · CIB Confidence mínimo para recomendación

### Justificación
B12 CIB Detector devuelve `confidence_score` entre 0 y 1 por author flagged. Un falso positivo en CIB tiene costo reputacional alto (marcar a crítico legítimo como troll). Umbral conservador protege contra falsos positivos en recomendaciones accionables; el dashboard muestra todas las señales pero solo las de alta confianza entran en Plan IA.

### Fórmula
```
confidence_mínima_plan_ia = 0.70

Para cada author flagged por B12:
  si author.confidence_score >= 0.70 → elegible para mención en recomendación Plan IA
  si author.confidence_score < 0.70 → aparece solo en dashboard B12, no en Plan IA
```

### Path de calibración
1. Tras 200 casos de CIB flagged con etiqueta humana MD review (S4 operativo → S5):
   - Precisión a 0.70 debería ser ≥ 85% (pocos falsos positivos accionables).
   - Recall a 0.70 puede ser bajo (<50%) — preferimos perder casos dudosos que causar daño reputacional.
2. **Criterio de ajuste:**
   - Si precisión <85%: subir a 0.75 o 0.80.
   - Si recall <30% Y precisión >95%: bajar a 0.65 (abrir ventana).
   - Nunca bajar por debajo de 0.60 sin review CEO.

### Restricción dura integrada al prompt
**Plan IA NUNCA recomienda bloqueo automático, reporte a plataforma, o acción unilateral sobre cuentas CIB.** La máxima recomendación accionable sobre CIB es:

> "Revisar con equipo MD las N cuentas flagged con confidence ≥0.70 antes de decidir acción humana."

Esto está integrado en el bloque 1 "Restricciones duras" del prompt `PROMPT-PLAN-IA-v1.md`.

---

## Umbral 3 · Humanización target por perfil §1.5

### Justificación
B10 Humanización Score mide (0-100) el balance entre contenido institucional y contenido personal/humano. Cada perfil §1.5 del MVP tiene un rango óptimo distinto derivado de investigación académica (Bail 2018, Latinobarómetro, LAPOP).

### Tabla de targets

| Perfil §1.5 | Score target | Umbral "needs action" | Justificación |
|---|---|---|---|
| `politico_activo` | 45-65 | `< 35` (sobre-institucional) | Balance institucional/humano. Políticos activos que solo publican comunicados pierden conexión afectiva. |
| `funcionario_gobierno` | 25-45 | `< 15` o `> 55` | Preferencia institucional (autoridad). Demasiada humanización lee como frivolidad. Muy poca lee como distante. |
| `figura_precampaña` | 50-70 | `< 40` | Humanización alta para activar identificación afectiva (Tajfel) previo a campaña formal. |
| `empresario_transicion` | 35-55 | `< 25` o `> 65` | Autoridad + calidez. Desbalance en cualquier dirección daña credibilidad. |

### Fórmula
```
target_low, target_high = TARGETS[dirigente.perfil_1_5]
action_threshold_low, action_threshold_high = ACTION_THRESHOLDS[dirigente.perfil_1_5]

needs_action = score < action_threshold_low OR score > action_threshold_high
direction = "aumentar_humanizacion" si score < target_low
          | "disminuir_humanizacion" si score > target_high
          | "mantener" si target_low ≤ score ≤ target_high
```

### Path de calibración
1. Validar con 100+ posts anotados manualmente por MD review: ¿el score correlaciona con percepción de humanización humana?
2. Si Kappa < 0.60 contra anotadores humanos: recalibrar el léxico de B10 y/o ajustar rangos de target.
3. Por perfil, tras 4 semanas de piloto: si un perfil tiene `needs_action=true` en >60% de dirigentes del perfil, el target del perfil está mal calibrado → revisión CEO.

### Aplicación ejemplo
Piña actual: humanización = 15.14 · perfil = `politico_activo` → `15.14 < 35` → `needs_action=true, direction=aumentar_humanizacion`. Plan IA debe sugerir acciones concretas post-drill-down B10/examples.

---

## Resumen ejecutivo

| Umbral | Valor S4 inicial | Flag rate aceptable | Recalibración | Consumidor |
|---|---|---|---|---|
| Topic Drift delta | ±15% vs baseline 30d | 15-40% | post-30d piloto | Plan IA bloque 3 del prompt |
| CIB confidence mínimo | 0.70 | precisión ≥85% | post-200 casos MD review | Plan IA bloque 1 restricciones |
| Humanización target | tabla por perfil §1.5 | <60% `needs_action` por perfil | post-4 semanas piloto | Plan IA bloque 5 behavioral library |

**Todos los cambios de umbral se registran en el changelog de `PROMPT-PLAN-IA-v{N}.md`** — cambio menor incrementa v1.x, cambio estructural incrementa v2.0.
