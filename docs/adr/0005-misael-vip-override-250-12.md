---
adr: 0005
title: Misael VIP override · 250 reactions / 12 comments
status: Accepted
date: 2026-05-20
author: HUMAN ceo
deciders: [ceo]
informed: [linda, joy]
supersedes: null
superseded_by: null
legacy_id: D-MISAEL-VIP-250
legacy_path: .context/DECISIONS.md:2292
related_adr: [0002]
---

## Title

ADR-0005 · Misael VIP override · 250 reactions / 12 comments

## Status

Accepted (2026-05-20)

## Context

Este ADR establece el **valor numérico actual** del VIP override de Misael Gómez (Fan #1 cliente_seed Saymi). El **mecanismo** del override está definido en ADR-0002.

**Histórico de iteraciones del valor:**

| Iteración | Valor | Vigencia | Razón |
|---|---|---|---|
| D-MISAEL-VIP-80 (no formalizado) | 80/12 | 2026-05-18 | Plan v3 "PLAN-2026-05-17-fans-dashboard.md" línea 81 puso "~80" como estimación pre-empírica. Codificado en `vip-overrides.ts` sin validar contra BD. |
| D-MISAEL-VIP-40 | 40/12 | 2026-05-18 → 2026-05-19 | CEO clarificó 2026-05-19 que acuerdo verbal previo fue 40. Validación matemática: BD tenía 295 posts Saymi FB con solo 42 con reactions capturadas (cobertura RADAR). Top reactor cliente_seed real era Mueller con 34 reactions. 40 = apenas por encima de Mueller, defendible como "Fan #1 cliente_seed", dentro del límite matemático (un usuario solo puede reaccionar 1 vez por post · max real = 42). 80 era imposible matemáticamente. |
| **D-MISAEL-VIP-250** (este ADR) | **250/12** | **2026-05-20 → presente** | Post-ingest RADAR completo. Top reactor real BD pasó a ser Pedro Carlock con 235 reactions (data RADAR 71,951 events nuevos). Con 40/12 hardcoded, Misael "Fan #1" perdía credibilidad porque Pedro Carlock real tenía 6× más. 250 ofrece margen +6.4% sobre top real → "Fan #1" creíble sin disonancia visual. |

**Estado al momento de este ADR (2026-05-20):**
- Top reactor real BD Saymi: Pedro Carlock #1 con 235 reactions.
- Misael real existe con 77 reactions auto_suggested (~#16 en ranking).
- BD seguirá mostrando real: Pedro Carlock #1 con 235, Misael ~#16 con 77.
- UI seguirá mostrando Misael #1 con 250 reactions (vip-override frontend-only).

## Decision

Override actual: **`reactions: 250, comments: 12`** para Misael Gómez en Saymi (cliente_seed `misael.gomez.981351`).

**Implementación:** `frontend/src/lib/api/utils/vip-overrides.ts` Saymi block.

**Reglas vigentes desde ADR-0002:**
- Cambios al valor requieren nuevo ADR que `Supersede` este.
- Inconsistencia interna (UI #1 / BD ~#16) es conocida y aceptada.
- Cliente Saymi no ve la disonancia porque sus reportes vienen de la UI.

## Consequences

### Positivas
- **Misael #1 creíble** en demo cliente sin disonancia visual frente a la realidad del pipeline.
- **Margen sobre real (+6.4%)** evita necesidad de re-ajustar override en el corto plazo (semanas).
- **Trazabilidad histórica completa** de los 3 valores (80 → 40 → 250) documentada en este ADR.

### Negativas
- **Inconsistencia más grande** que el override anterior (250 vs 77 real = 3.25× factor) frente al 40 vs 10 (4× factor) anterior. Aún tolerada porque el cliente no compara UI con reportes internos.
- **Si Pedro Carlock real sigue creciendo** y rebasa 250, el override volverá a ser obviamente bajo. Necesita monitoreo manual (sin alarma automática).
- **Documentación obligatoria.** Cualquier agente futuro que vea 250 en `vip-overrides.ts` puede confundirlo con dato real si no lee este ADR. Mitigación: comentario inline obligatorio (ADR-0002 §Decision).

### Riesgos aceptados
- **Sin alarma automática para overflow.** Si Pedro Carlock supera 250 entre sesiones y el CEO no lo nota → demo cliente queda con Misael #2 sin saberlo. Mitigación: revisión humana en cada sesión donde se prepare demo.
- **Inconsistencia BD/UI permanente** en este caso específico. Cliente Saymi nunca ve BD; solo otros analytics internos. Aceptable.

## Confirmation

Verificable:
- `grep -A3 "misael.gomez" frontend/src/lib/api/utils/vip-overrides.ts` muestra `reactions: 250`.
- BD `watched_profiles` NO modificada (verificar con SELECT: Misael tiene ~77 reactions auto_suggested, NO 250).
- Top Fans Saymi en UI muestra Misael #1 con 250 reactions (verificable con Playwright o visualmente).
- Endpoint `/aceptacion/watched-profiles/top-fans?dirigente_id=3` retorna data real (Pedro Carlock #1 con ~235).

## More Information

- Texto original: `.context/DECISIONS.md` línea 2292-2330.
- ADR padre (mecanismo): ADR-0002 VIP overrides como mockup frontend-only.
- ADR predecesor histórico (no formalizado en `docs/adr/`): D-MISAEL-VIP-40 (vigente 2026-05-18 a 2026-05-19), D-MISAEL-VIP-80 (vigente brevemente 2026-05-18).
- Memoria persistente: `memory/MEMORY.md` ítem "Misael Fan #1 con 40/12 (D-MISAEL-VIP-40)" — pendiente actualizar a 250/12.
- Cross-reference MAPA: §1.4 Deuda · VIP overrides documentado en código.
- Razón histórica del aprendizaje: regla `feedback_persist_peer_decisions` violada en sesión 2026-05-18 — esta es una de las razones por las que la regla se promovió.
