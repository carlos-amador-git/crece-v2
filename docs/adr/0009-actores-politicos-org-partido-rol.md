---
adr: 0009
title: Actores políticos — org ≠ partido ≠ rol_politico (tres ejes, función única)
status: Proposed
date: 2026-07-16
author: AGENT linda (claude-fable-5)
deciders: [ceo]
supersedes: null
superseded_by: null
---

# ADR-0009 — Actores políticos: org ≠ partido ≠ rol_politico

## Context

El alta de Hannah de Lamadrid (2026-07-16, deploy) creó una org nueva "Morena" cuando ya
existían dirigentes MORENA-CDMX en la org `cdmx-independiente` (Gaby Jiménez, Cravioto), y
nació sin `rol_politico` porque ningún flujo de alta lo capturaba. Medido ese día: 4
dirigentes con rol NULL siendo calificados con fallback silencioso a "independiente"
(`actividad_alineada.py`), fórmula equivocada para los MORENA (D-23-H define fórmula POR
rol). Diseño deliberado por tríada Claude+Gemini+GPT (consenso 3/3 en 2 rondas —
`.context/DISENO-actores-politicos-2026-07-16.md`) y ratificado por el CEO (GO + decisiones
1-3 del doc).

## Decision

1. **Tres ejes con función única e independiente:**
   - `org_id` = tenant comercial: quién paga y quién VE. JAMÁS afinidad política. Naming
     por cliente/contrato (nunca un partido a secas). Referencia en código/scripts/seeds
     SIEMPRE por `slug` (los ids numéricos divergen entre ambientes).
   - `partido` = identidad política declarativa (hecho del mundo).
   - `rol_politico` = parámetro del motor de scoring (KPI D-23-H, prompts NLP, framework),
     ∈ {oficialismo, oposicion, independiente}, calibrado a la plaza principal del dirigente.
2. **Asignación humana explícita del rol en el alta** — obligatoria en `DirigenteCreate` y
   `OnboardingRequest` (422 sin él). Nunca derivación silenciosa desde partido.
3. **NOT NULL en BD** (migración `5a6505d74dc7`) con backfill: MORENA→oficialismo,
   MC→oposicion, PAZ→independiente (decisión CEO: partido nuevo, vinculado a Morena),
   SISTEMA/bots→independiente.
4. **Fallo visible, nunca número falso:** rol ausente (ambientes pre-migración) → el KPI
   retorna `empty_state="rol_sin_clasificar"` con score None y la UI muestra badge, no
   número (extensión de D-ANTI-MOCK-1 / ADR-0003). Aplica también a agregados.
5. **Cero defaults mágicos de org:** el alta resuelve org = payload explícito o la org del
   creador; sin org resoluble → 422. Se elimina el `or 3` histórico (su comentario "org 3 =
   MC CDMX root per D16" contradecía la BD; el CEO declaró no tener intención de ese default).
6. **Diferido explícito:** multi-rol por ámbito (federal/estatal/municipal) y catálogo
   `partido×ámbito→rol` como sugerencia pre-llenada en el wizard. El modelo `competidores`
   sigue diferido (B-COMPETIDORES-MODELO-1).

## Consequences

- Ningún dirigente nuevo puede entrar al pipeline con rol indefinido; los 4 existentes
  quedaron backfilleados con decisión humana registrada aquí.
- El wizard exige una decisión política explícita del operador — el runbook
  `.context/governance/RUNBOOK-alta-actores.md` guía esa decisión.
- Ambientes desplegados (Coolify) requieren `alembic upgrade head` para el NOT NULL; hasta
  entonces el guard de fallo visible cubre el hueco.
- Los fixtures de tests legacy (test DB vía `create_all`) mantienen el campo Optional en
  Python; el contrato real vive en API + constraint de BD real + guard visible.
- Alta de Hannah (deploy): org PROPIA con nombre comercial (cliente aparte — decisión CEO),
  `partido=MORENA`, `rol_politico=oficialismo`, display "Hannah" (doble-n).
