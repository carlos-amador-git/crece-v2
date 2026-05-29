---
adr: 0002
title: VIP overrides como mockup frontend-only · BD jamás se toca
status: Accepted
date: 2026-05-19
author: HUMAN ceo
deciders: [ceo]
informed: [linda, joy]
supersedes: null
superseded_by: null
legacy_id: D-3
legacy_path: vip-overrides.ts:38-43
related_adr: [0005]
---

## Title

ADR-0002 · VIP overrides como mockup frontend-only · BD jamás se toca

## Status

Accepted (2026-05-19)

## Context

Durante el desarrollo del piloto comercial con MC CDMX (D-PILOTO-01), el CEO identificó la necesidad de mostrar **Top Fans con casos VIP específicos** para demostraciones a cliente, sin esperar a que el pipeline de captura (RADAR → CRECE) tuviera la cobertura suficiente para reflejar el resultado deseado.

Ejemplo: Saymi (dirigente_id=3) tiene un seguidor identificado por el CEO como su "Fan #1 cliente_seed" llamado **Misael Gómez** (`misael.gomez.981351`). Las métricas reales en BD pueden no reflejar esa posición porque:
- RADAR no captura el 100% de reactions (cobertura ~85-95% según postmortem S-8.1).
- Otros fans auto_suggested (sin que el CEO los conozca) pueden tener más activity capturada y aparecer encima de Misael en el ranking.

El CEO necesita controlar el orden mostrado en demos sin alterar la BD (que sería inconsistente con otros consumidores como el módulo Diagnóstico).

## Decision

Implementar **overrides frontend-only** en `frontend/src/lib/api/utils/vip-overrides.ts` que reemplazan métricas de display sin tocar la BD:

```typescript
// vip-overrides.ts
export const VIP_OVERRIDES = {
  3: { // Saymi
    "misael.gomez.981351": { reactions: 250, comments: 12 }
  }
};
```

**Reglas operativas:**

1. **BD jamás se toca.** Cualquier intervención en la BD (UPDATE/INSERT directo, scripts seed) está prohibida para "fixear" rankings. Si el dato real no muestra al VIP arriba, se ajusta el override frontend, NO la BD.
2. **El override aplica solo en `top-fans-ranking.tsx`** (UI cliente). Endpoints `/aceptacion/watched-profiles/top-fans` retornan datos reales sin modificar.
3. **El número del override debe ser matemáticamente defendible** (verificar contra BD que sea creíble · ver ADR-0005 para el caso Misael 250).
4. **Comentario inline obligatorio** en `vip-overrides.ts` redirigiendo al ADR específico del valor.

## Consequences

### Positivas
- **Demos al cliente sin disonancia.** Misael aparece consistente como "Fan #1" sin importar el ciclo de captura RADAR.
- **Otros consumidores BD inalterados.** Diagnóstico, Plan IA, métricas de engagement leen el dato real (Misael donde realmente está, ~#16).
- **Reversibilidad inmediata.** Borrar el override revierte a comportamiento real. Cero rollback BD requerido.
- **Auditoría clara.** Toda intervención queda en un solo archivo (`vip-overrides.ts`) versionado en git.

### Negativas
- **Inconsistencia interna conocida.** UI cliente ve Misael #1 con métrica ajustada; reportes internos / admin / BD muestran orden real. Documentada y aceptada.
- **Dependencia de coordinación CEO.** Si el VIP real captura suficiente engagement para superar el override, se necesita ajustar manualmente. Sin alarma automática que avise.
- **Riesgo de oblvido.** Futuros agentes que toquen `vip-overrides.ts` sin leer este ADR pueden cambiar valores sin entender el contexto. Mitigación: comentario inline obligatorio.

### Riesgos aceptados
- **Si CEO se ausenta y el cliente pregunta por discrepancia entre UI y reporte interno**, la respuesta corta es "Es un ajuste de presentación; el pipeline real está acumulando data". Riesgo mínimo porque el cliente no compara reportes internos con la UI.

## Confirmation

Verificable:
- `vip-overrides.ts` existe en `frontend/src/lib/api/utils/` con la estructura definida.
- BD tabla `watched_profiles` NO tiene records con métricas alteradas para Misael (verificable con SELECT).
- Endpoint `/aceptacion/watched-profiles/top-fans` retorna datos reales (verificable con `curl`).
- Top Fans ranking FE renderiza con overrides aplicados (verificable visualmente o con Playwright).

## More Information

- Texto original: `.context/DECISIONS.md` línea 91-115 (D-MISAEL-VIP-40 inicial) y línea 2292-2330 (D-MISAEL-VIP-250 vigente).
- Memoria: `memory/MEMORY.md` ítem "Misael VIP mockup".
- Cross-reference MAPA: §1.4 Deuda · `VIP overrides documentado en código` · §6B Mi Evaluación (no relacionado pero comparte concepto de adjustments frontend-only).
- ADR concreto del valor actual: ADR-0005 Misael 250/12.
- AGENTS.md raíz §5 lista `vip-overrides.ts` como archivo límite duro: cambios requieren PR humano explícito.
