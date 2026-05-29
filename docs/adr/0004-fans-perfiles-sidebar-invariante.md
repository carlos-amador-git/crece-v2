---
adr: 0004
title: Fans y Perfiles · sidebar invariante · NO eliminar
status: Accepted
date: 2026-05-19
author: HUMAN ceo
deciders: [ceo]
informed: [linda, joy]
supersedes: null
superseded_by: null
legacy_id: D-FANS-PERFILES-SIDEBAR-INVARIANTE
legacy_path: .context/DECISIONS.md:2269
---

## Title

ADR-0004 · Fans y Perfiles · sidebar invariante · NO eliminar

## Status

Accepted (2026-05-19)

## Context

Histórico del rework detectado por el CEO al revisar el sidebar de producción:

- **PR #50 (2026-05-18, follow-up D-MISAEL-VIP-40):** CEO pidió entrada `"Fans y Perfiles"` como standalone en sidebar, apuntando a `/dashboard/aceptacion/fantasmas?tab=observados`.
- **PR #54 (2026-05-19, maratón F4 Content Hub):** la entrada fue **eliminada** como parte de consolidación visual ("Contenido" único). Sin objeción explícita del CEO porque dijo *"cliente no ha visto la app"* — la sesión entendió como autorización tácita para reorganizar todo el sidebar.
- **PR #55 (cierre 2026-05-19):** CEO detectó la pérdida al revisar `/dashboard/aceptacion/fantasmas` y notar que la entrada YA NO está en sidebar.

Texto verbatim CEO: *"y no se supone que los perfiles observados eran parte del sidemenu, de hecho así los revise antes, y ahora los volviste a cambiar... esto ya lo habíamos hecho y es volverlo a hacer."*

**Aprendizaje cristalizado:** "Cliente no ha visto la app" NO es autorización para eliminar features que el CEO ya pidió antes. Consolidación de sidebar requiere preservar lo que el CEO ya definió como necesario, incluso si reduce de 4 → 1 ítems "Contenido".

## Decision

La entrada de sidebar **`"Fans y Perfiles" → /dashboard/aceptacion/fantasmas?tab=observados` es INVARIANTE**.

**Reglas operativas:**

1. **No se elimina** en futuros refactors de sidebar sin autorización CEO explícita en sesión.
2. Cualquier PR que toque `sidebar.tsx` y proponga eliminar/reorganizar `Fans y Perfiles` requiere **comment explícito del CEO en el PR**.
3. Si un refactor de sidebar elimina una entry definida en este ADR como INVARIANTE, el PR queda **bloqueado** hasta autorización formal.

**Implementación 2026-05-19 (PR #55):**

- `sidebar.tsx`: leaf agregado en grupo "Indice Aceptacion" después de "Fantasmas". Icono `Eye`. Apunta a `/dashboard/aceptacion/fantasmas?tab=observados`.
- `fantasmas/page.tsx`: deep-link via `useSearchParams` lee `?tab=` y setea `defaultValue` del Tabs component. Suspense wrapper agregado.
- Tab values existentes preservados (`resumen`, `por-plataforma`, `observados`). NO se renombran.

## Consequences

### Positivas
- **Feature consistente entre sesiones** del cliente — bookmarks y memoria muscular del cliente preservados.
- **Pattern establecido para futuros invariantes.** El catálogo de entries INVARIANTES crece según el CEO pide en sucesivos sprints.
- **PR de refactor bloqueado** preventivamente — agente IA recibe señal clara antes de proponer eliminación.

### Negativas
- **Riesgo de duplicación visual.** Si "Contenido" reaparece como consolidado en futuro, "Fans y Perfiles" sigue como standalone — puede sentirse redundante. Acceptable: preferir ruido visual a perder feature.
- **Backlog organizacional:** cada invariante agregado complica refactors de sidebar futuros. ROI positivo si previene re-trabajo.

### Riesgos aceptados
- Si el CEO en sesión futura decide formalmente eliminar "Fans y Perfiles" del sidebar, escribir ADR nuevo que `Supersede` este. NO editarlo.

## Confirmation

Verificable:
- `grep -n "Fans y Perfiles\|fantasmas?tab=observados" frontend/src/components/layout/sidebar.tsx` retorna ≥1 match.
- Navegar a `/dashboard/aceptacion/fantasmas?tab=observados` carga directamente el tab "Observados" (deep-link funcional).
- Tab values en `fantasmas/page.tsx`: `resumen`, `por-plataforma`, `observados` (sin renombre).

## More Information

- Texto original: `.context/DECISIONS.md` línea 2269-2290.
- Memoria: `memory/feedback_persist_peer_decisions.md` (la decisión de PR #50 NO se persistió originalmente, parte del aprendizaje).
- Cross-reference MAPA: §1.1 Vistas FE del sidebar · Aceptación · Fans y Perfiles.
- AGENTS.md raíz §5 menciona el patrón de archivos INVARIANTES requiriendo PR humano explícito.
- Histórico de PRs:
  - PR #50 (2026-05-18) — agregó la entrada
  - PR #54 (2026-05-19) — la eliminó (error)
  - PR #55 (2026-05-19) — la restauró y declaró invariante
