# PLAN D-23-H · Panel Editable de Evaluación · Fase B (actualizado)

**Fecha:** 2026-04-24
**Última corrección:** Claude IA review (2026-04-25)
**Status:** ✅ Luz verde CEO 2026-04-25 post-merge Phase A
**Branch:** `feat/phase-b-pesos-editables`
**Estimado:** 2 días (Palanca 1 solo · Palanca 2 diferida a Phase C)

---

## Decisiones consolidadas (3 revisiones · Gemini → Claude IA → CEO)

| Decisión | Justificación |
|----------|---------------|
| **Solo Palanca 1** (pesos por categoría) · Palanca 2 (override per-post) → Phase C | Empirismo: si nadie toca pesos, nadie hará override. Medir antes de invertir. |
| **3 presets políticos + Personalizado** (no sliders Baja/Normal/Alta) | UX semántica: lenguaje del usuario, no abstracción matemática. 80% elegirá preset. |
| **Doble métrica visible siempre** · KPI defaults vs KPI ajustado + brecha | Self-serving bias se vuelve auditable. Cap 0.5-1.5 sin transparencia es teatro. |
| **Comparativa entre dirigentes usa SIEMPRE default** (no ajustado) | Nadie gana ranking por toquetear pesos. Vista personal vs vista comparativa. |
| **last_modified stamp en columna · sin tabla history MVP** | History si vemos manipulación · simple ahora. |
| Cap 0.5-1.5 en CHECK + UI | Limita extremos. Brecha es el verdadero audit. |

## Schema (1 migration)

```sql
ALTER TABLE dirigentes ADD COLUMN pesos_target_politico JSONB DEFAULT
  '{"oficialismo":1.0,"oposicion":1.0,"propio":1.0,"personal":1.0}'::jsonb;
ALTER TABLE dirigentes ADD COLUMN pesos_last_modified_by BIGINT REFERENCES users(id);
ALTER TABLE dirigentes ADD COLUMN pesos_last_modified_at TIMESTAMPTZ;
```

CHECK constraint:
- `pesos_target_politico` debe contener exactamente las 4 keys
- Cada valor en `[0.5, 1.5]`

## Presets (en frontend, no en BD)

```typescript
const PRESETS = {
  conservador: { oficialismo: 1.0, oposicion: 1.0, propio: 1.0, personal: 1.0 },
  balanceado:  { oficialismo: 1.0, oposicion: 1.3, propio: 1.0, personal: 1.0 },
  combativo:   { oficialismo: 1.0, oposicion: 1.5, propio: 1.2, personal: 0.8 },
  // personalizado: lo que el dirigente edite manualmente
};
```

Calibración inicial · iterar con Piña/Ballesteros antes de ship.

## Backend

`actividad_alineada.py` extendido con `modo`:
```python
def compute_actividad_alineada(db, dirigente, *, days=7, modo="ajustado"):
    if modo == "default":
        pesos = {"oficialismo":1.0, "oposicion":1.0, "propio":1.0, "personal":1.0}
    else:
        pesos = dirigente.pesos_target_politico or DEFAULT_PESOS
    # ... fórmula ponderada
```

Endpoint existente `GET /dirigentes/{id}` retorna ambos:
```json
"actividad_alineada_default": { ... }, // pesos=1
"actividad_alineada_ajustada": { ... }  // con pesos del dirigente
```

Endpoint nuevo:
```
PATCH /dirigentes/{id}/pesos
Body: {oficialismo, oposicion, propio, personal}
- Valida cap 0.5-1.5
- Actualiza pesos_last_modified_by, pesos_last_modified_at
- Retorna ambos KPIs recalculados
```

## Frontend

**Nueva página:** `/dashboard/evaluacion/[id]`

Layout:
```
┌─────────────────────────────────────┐
│ [Análisis IA]      [Tu Lectura]    │  ← Doble KPI hero
│  KPI: 52%          KPI: 67%        │
│                    Brecha: +15pp   │  ← banner si > 15pp
├─────────────────────────────────────┤
│ Tu enfoque                          │
│ ◉ Conservador  ○ Balanceado        │  ← 3 presets + Personalizado
│ ○ Combativo   ○ Personalizado      │
│                                     │
│ [Personalizado] (si seleccionado): │
│  Oficialismo: ◯◯●◯◯ Normal         │  ← selector 5 puntos · 0.5/0.75/1.0/1.25/1.5
│  Oposición:   ◯◯◯●◯ Alta-          │
│  ...                                │
└─────────────────────────────────────┘
```

Botón "Guardar enfoque" → PATCH endpoint · debounced 800ms.

## Día por día

**Día 1 (HOY) · backend:**
- [x] Branch `feat/phase-b-pesos-editables`
- [ ] Migration hand-written `phase_b_pesos.py` (D-OPS-08)
- [ ] Code-reviewer subagent audit
- [ ] Apply migration
- [ ] Model `dirigente.py` con 3 columnas nuevas
- [ ] Service `actividad_alineada.py` con `modo` param
- [ ] Endpoint `PATCH /dirigentes/{id}/pesos`
- [ ] Endpoint existente retorna ambos KPIs
- [ ] Tests backend
- [ ] Commit + push

**Día 2 (próxima sesión) · frontend:**
- [ ] Página `/dashboard/evaluacion/[id]`
- [ ] Componente `<DobleKpiHero />` con brecha
- [ ] Componente `<PresetSelector />` con 3 + custom
- [ ] Selector 5-puntos por target en custom
- [ ] Tests Playwright local + Vercel
- [ ] PR + merge

## Forward-compat

- `clasificacion_origen` ya soporta `human_dirigente|human_admin|human_consultor` (Phase A)
- Si Phase C activa Palanca 2 (override per-post), columna `target_politico_humano` se añade vía nueva migration
- Si vemos manipulación grosera, agregar tabla `pesos_history` en Phase B.1

## Riesgos honestos

| Riesgo | Mitigación |
|--------|------------|
| Self-serving bias (peso 1.5 a "propio") | Doble métrica + brecha visible · auditable |
| Adopción dispar | Default pesos=1.0 · KPI default siempre disponible · Comparativas inter-dirigentes usan default |
| Calibración presets arbitraria | Iterar con Piña/Ballesteros pre-ship · números actuales son v0 |
| Performance debounce | 800ms + cache 60s server side |

## Métricas de éxito (post-deploy 7d)

- ≥1 dirigente toca pesos
- Brecha sostenida promedio < 30pp
- 0 errores 500 en endpoint PATCH
- pesos_last_modified_at acumula stamps
