---
adr: 0003
title: Anti-fallback data en UI · guardrail automatizado
status: Accepted
date: 2026-05-11
author: HUMAN ceo
deciders: [ceo]
informed: [linda, joy]
supersedes: null
superseded_by: null
legacy_id: D-ANTI-MOCK-1
legacy_path: .context/DECISIONS.md:581
related_adr: [0002]
---

## Title

ADR-0003 · Anti-fallback data en UI · guardrail automatizado

## Status

Accepted (2026-05-11)

## Context

CEO revisó dashboard en producción 2026-05-11 logueado como Ballesteros (rol VIEWER). Detectó factor 10x de inconsistencia visible al cliente:

- Card **"Tu Audiencia"** mostraba 89.8K (suma real de followers por plataforma).
- Card **"vs Competidor Principal → Laura Ballesteros"** mostraba 8.8K (mock hardcoded `DIRIGENTE_METRICS_FALLBACK` en `CompetitorSnapshotCard`).

Causa raíz: el componente tenía un comentario `// Will be replaced by /benchmark/comparison API call in a future sprint.` que nunca se ejecutó. La regla informal de `CLAUDE.md` "NUNCA mocks o datos inventados" NO estaba validada programáticamente — dependía solo de revisión humana.

Patrón identificado en múltiples archivos: `_FALLBACK = { ... followers: N ... }`, `DEMO_<resource>[]`, `MOCK_<resource>[]`, `FAKE_<resource>[]`, comentarios `TODO replace with API`.

## Decision

**Cero hardcoded fallback con números visibles al usuario.** Cuatro acciones:

1. **Borrar** todo hardcoded fallback existente con números mostrados en UI. `CompetitorSnapshotCard` reescrita para usar `useKpiOverview()` (followers reales) + `useBenchmarkRanking()` (competidores reales filtrando `followers=0`).

2. **Skeleton o estado vacío explícito** si el endpoint aún no está listo. Componentes muestran `<Skeleton />` durante loading o `<EmptyState message="..." />` si el endpoint retorna sin data. **Cero números falsos en cualquier momento.**

3. **Guardrail automatizado:** `frontend/scripts/check-no-mocks.sh` detecta 3 patrones:
   - `_FALLBACK = { ... followers: N ... }` (objeto con números hardcoded)
   - `DEMO_/MOCK_/FAKE_*[]` (arrays con nombre clave)
   - Comentarios `TODO replace with API` (intención de mocking sin completar)

   Comando: `npm run check:no-mocks`. Exit 1 = violaciones, exit 0 = limpio. Validado en ambos sentidos (sintético + real).

4. **Regla operativa** añadida a `CLAUDE.md` §"Reglas de Calidad" ítem 5 y a `AGENTS.md` §11 anti-patterns.

## Consequences

### Positivas
- **Imposible introducir mock numérico al usuario por accidente.** El script CI bloquea el commit/merge.
- **Cliente no ve discrepancias 10x** entre cards adyacentes (problema original detectado por CEO).
- **Patrón explícito** para futuros componentes: si el endpoint no está, mostrar skeleton/empty, no inventar.
- **Reusa endpoint existente `/benchmark/ranking`** en lugar de crear `/benchmark/comparison` nuevo — economía de alcance.

### Negativas
- **Lint usa grep regex, no AST.** Puede dar false positives en código legítimo (test fixtures, ejemplos de docs).
  - **Mitigación:** convención de marcar excepciones con `/* allow-mock: <razón> */` en la misma línea. Validado en producción.
- **Más esfuerzo upfront** para componentes con backend incompleto: necesitan estado vacío diseñado, no número placeholder.
- **No detecta mocks no-numéricos** (strings, booleans) — solo el patrón de fallback común con números. Acceptable porque el problema original era numérico.

### Trade-offs explícitos
- **No AST-based check** porque exigiría agregar `ts-morph` u otra dep. Grep es lo suficientemente preciso para los 3 patrones identificados y se ejecuta en <1s.
- **Endpoint `/benchmark/ranking` reusa el existente** en lugar de crear `/benchmark/comparison` nuevo. Si en el futuro se necesita comparativa head-to-head con engagement/sentiment, ampliar entonces.

## Confirmation

Verificable:
- `frontend/scripts/check-no-mocks.sh` existe y `npm run check:no-mocks` retorna exit 0 sobre código actual.
- `CompetitorSnapshotCard` usa `useKpiOverview()` y `useBenchmarkRanking()` (verificable con grep).
- `package.json` tiene `"check:no-mocks": "bash scripts/check-no-mocks.sh"` (verificado en MAPA-FUNCIONAL §1).
- `CLAUDE.md` proyecto §"Reglas de Calidad" ítem 5 cita esta regla.
- `AGENTS.md` raíz §11 lista "Fallback data hardcoded en UI con números" como anti-patrón.

## Pendientes a futuro

- Scraper de profile metrics FB+TT no corre para 5 perfiles (Solano FB · Máynez FB+TT · Ballesteros FB+TT). UI mitigada en este sprint: muestra "Sin datos · sync pendiente" en lugar de "0" engañoso. Para datos reales, scraper Playwright debe correr con cookies válidas.
- Coverage clasificación sentiment muy bajo en algunos dirigentes (Ballesteros 13.6%, Solano 20%, Piña 52.7% al momento de la decisión). UI mitigada con disclaimer "X de Y posts clasificados" en card Tono Discursivo.

## More Information

- Texto original: `.context/DECISIONS.md` línea 581-615.
- Cross-reference MAPA: §1.4 Deuda · `Reacciones tipo placeholder` (no aplica, pero comparte concepto de transparencia con disclaimers explícitos).
- AGENTS.md raíz §11 — anti-patrón documentado.
- Componentes auditados en sprint cierre: `CompetitorSnapshotCard`, `check-no-mocks.sh`, `package.json`.
