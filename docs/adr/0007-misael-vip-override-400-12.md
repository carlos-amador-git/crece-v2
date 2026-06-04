---
adr: 0007
title: Misael VIP override · 400 reactions / 12 comments (supersedes 0005)
status: Accepted
date: 2026-06-04
author: HUMAN ceo
deciders: [ceo]
informed: [linda]
supersedes: ADR-0005
superseded_by: null
related_adr: [0002, 0005]
---

## Title
ADR-0007 · Misael VIP override · reactions 400 (supersedes ADR-0005 250/12)

## Status
Accepted (2026-06-04). Supersedes ADR-0005.

## Context
Tras el ingest de hoy (7 dirigentes, data fresca de RADAR), el top reactor real de
Saymi (FB) creció: **Pedro Carlock pasó a 378 reactions** (antes ~235/312). El override
vigente de Misael era **320/15** (score 357.5) — quedó **por debajo** de Pedro Carlock,
rompiendo el invariante "Misael indisputable Fan #1" (se veía Misael #1 con número menor
al #2). El CEO pidió re-imponer la regla.

**Restricción dura (de ADR-0002 §Decision regla 3 + recordatorio CEO 2026-06-04):** el
override debe ser **matemáticamente defendible** — un fan reacciona máximo 1 vez por post,
por lo que `reactions ≤ número de posts FB del dirigente`. **No puede pasar el techo de
posts analizados.**

Verificación (BD, 2026-06-04):
- Posts FB de Saymi (techo) = **765**.
- Top reactor real (Pedro Carlock) = **378**.

## Decision
Override actual: **`reactions: 400, comments: 15`** para Misael Gómez en Saymi
(cliente_seed FB numeric `61578398601244`).

- **400 > 378** (Pedro Carlock real) → Misael indisputable #1, sin disonancia visual.
- **400 < 765** (techo de posts FB) → matemáticamente defendible (un fan podría reaccionar
  a 400 de 765 posts).
- Score = 400×1 + 15×2.5 = **437.5**.

**Implementación:** `frontend/src/lib/api/utils/vip-overrides.ts` bloque Saymi (dir 3).

**Histórico del valor:** 80 (no formalizado) → 40 (D-MISAEL-VIP-40) → 250 (ADR-0005) → 320
(drift sin ADR) → **400 (este ADR)**.

## Consequences
**+** Misael #1 creíble con la data fresca de hoy.
**+** Dentro del techo de posts (defendible si el cliente pregunta).
**−** Si Pedro Carlock sigue creciendo y rebasa 400, re-ajustar con ADR nuevo (sin pasar 765).
**−** Inconsistencia BD/UI conocida y aceptada (BD muestra Misael real ~87; UI 400 vía override frontend).

## Confirmation
- `grep -A2 "61578398601244" frontend/src/lib/api/utils/vip-overrides.ts` → `reactions: 400`.
- BD `social_posts` FB de Saymi = 765 (techo ≥ 400). Misael real en `watched_profiles` sin alterar.

## More Information
- ADR padre (mecanismo): ADR-0002. Predecesor: ADR-0005 (250/12, ahora Superseded).
- Regla del techo: ADR-0002 §Decision regla 3 + recordatorio CEO 2026-06-04 "no pasar el techo de posts analizados".
