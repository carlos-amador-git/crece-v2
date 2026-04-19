# Propuesta Matriz v3 — Skeleton

**Creado:** 2026-04-18
**Base:** matriz v2 (53 reglas) + triangulación NLP Layer 2 2026-04-18
**Status:** skeleton — final se llena tras cerrar triangulación completa

> Esta propuesta NO se aplica automáticamente. CEO decide aplicar/iterar/descartar en Fase 4.

---

## Input de esta propuesta

- `output/REPORTE-TRIANGULACION.md` — kappas y divergencias (pendiente Gemma)
- `output/rule_gaps.md` — gaps por row (pendiente)
- `research/memory/2026-04-14-matriz-polaridad-v2-comments.md` — matriz v2 actual
- `docs/POLITICAL-FRAMEWORK-DEFAULTS.md` — matriz v1 pública

## Hallazgo central (Fase 2 inicial)

**Gap de vocabulario entre runner Gemma en producción y schema matriz v2.**

| Dimensión | Prompt runner | Matriz v2 schema |
|---|---|---|
| tono | elogio · critica · pregunta · ataque · informativo · personal · autopromocion | critico · propositivo · celebratorio · informativo · solidario · ataque · personal |
| target | dirigente_post · gobierno · oposicion · ciudadania · institucion · otros | gobierno · oposicion · ciudadania · medios · autopromocion · dirigente · tema_especifico · otro |

Implicación: el output de Gemma NO mapea directo a `framework_matrix_defaults.get_polarity()`. Actualmente requiere un mapping post-hoc no documentado, o el score político no se está computando bien contra comments procesados en Layer 2.

---

## 3 opciones de arquitectura para matriz v3

### Opción A — Adoptar vocab del runner en matriz v3

- Pros: mínimo cambio en producción (Gemma ya corre); migración incremental
- Contras: perdemos `celebratorio`, `propositivo`, `solidario` (matices positivos); `pregunta` y `autopromocion` en tono chocan con matriz v2 (autopromocion es target en v2)
- Impacto en BD: migración ds05 redefine enums + reetiqueta 53 reglas al nuevo vocab
- Costo: medio (~4-6h)

### Opción B — Alinear el runner al vocab matriz v2 (re-prompt)

- Pros: el schema BD es la fuente de verdad, el runner se adapta
- Contras: invalidar benchmark Gemma aceptado CEO 2026-04-14; re-correr batch ~1,100 comments; re-validar rate 31.4 min / 400 comments
- Impacto en BD: ninguno (schema actual mantiene)
- Costo: medio-alto (~6-8h) + recorrida de benchmark

### Opción C — Mapper intermedio runner↔matriz (sin tocar ninguno)

- Pros: no rompe producción ni schema; reversible
- Contras: dos vocabularios conviven; onboarding más pesado para quien lea el pipeline
- Impacto: mapper en `services/political_framework.py` + tests de mapping
- Costo: bajo-medio (~2-4h)

**Recomendación preliminar:** **Opción C** como MVP → **Opción B** a 3 meses (una vez estable). Opción A invalida el avance de matriz v2.

---

## Ajustes específicos de reglas (pendiente rule_gaps.md final)

_Se llena tras Fase 3.1 con resultados de triangulación completa._

Candidatos a ajuste según hallazgo preliminar (Fase 2 con 20 rows X-biased):

1. **`target` es el punto más débil** — Fleiss 0.314, Claude↔Gemma 0.175. La matriz v2 tiene 8 targets vs 6 del runner. Revisar si la ambigüedad está en el prompt o en la granularidad de la matriz.
2. **Falsos 0 en elogios cortos con emojis** — documentado en Sprint B. Si los 3 modelos no detectan el elogio por emoji solo, ninguna regla v2 alcanza — requiere preprocessing emoji→sentiment antes de Layer 2.
3. **Sátira / ironía** — si 3-way divergence se concentra aquí, la matriz v2 no ayuda (reglas asumen tono literal).

---

## Cambios propuestos al schema (preliminar)

```sql
-- Solo si Opción A o C
ALTER TABLE framework_matrix_defaults
  ADD COLUMN vocab_version VARCHAR(20) DEFAULT 'v2' CHECK (vocab_version IN ('v2', 'runner'));
```

---

## Riesgos identificados

1. **Cambio retroactivo de scores políticos** — cualquier edit de reglas v2 existentes re-score histórico. Documentar en `framework_audit_log` + opt-in por org.
2. **Drift del runner vs matriz** — el runner puede evolucionar (Gemma3:27b en v3?) y desalinearse otra vez. Mitigación: tests que validen vocab-compat en CI.

---

## Criterios de aprobación CEO (Fase 4)

- ¿Adoptar Opción A, B, C o combinación?
- ¿Alguna regla específica de matriz v2 ajustar con base en triangulación?
- ¿Re-correr benchmark Gemma post-ajuste, o mantener el actual como baseline?

## Cross-audit Gemini

_(pendiente Fase 3.3)_
