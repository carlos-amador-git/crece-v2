# Sprint D — Design Review Implementation (Enrique)

**Fecha:** 2026-04-12
**Objetivo:** Implementar los 2 pendientes del design review de Enrique:
md: breakpoints tablet en 17 paginas + Framer Motion selectiva.
**Branch:** `feat/design-enrique-review`
**Worktree:** `../crece-v2-design` (Jess ocupa CWD principal)
**Aprobado por CEO:** Pendiente
**Fuente:** D-DESIGN-01 en DECISIONS.md (10 respuestas Enrique persistidas)

---

## Inventario actual (18 paginas dashboard)

| Pagina | Lines | md: breakpoints | Framer Motion | StatCard |
|--------|-------|-----------------|---------------|----------|
| dashboard/page.tsx | 483 | SI | NO | NO |
| benchmark/page.tsx | 267 | SI | NO | NO |
| settings/page.tsx | 192 | NO | NO | NO |
| planes/page.tsx | 310 | SI | NO | NO |
| planes/[id]/page.tsx | 226 | NO | NO | NO |
| planes/[id]/kanban/page.tsx | 38 | NO | NO | NO |
| dirigentes/page.tsx | 313 | SI | NO | NO |
| dirigentes/[id]/page.tsx | 330 | SI | NO | NO |
| canvassing/page.tsx | 720 | SI | YES (StatCard) | SI |
| bot-detection/page.tsx | 407 | SI | NO | NO |
| campanas/page.tsx | 201 | SI (lg: only) | NO | NO |
| compliance/page.tsx | 358 | SI (lg: only) | NO | NO |
| sistema/onboarding/page.tsx | 48 | NO | NO | NO |
| social/page.tsx | 288 | SI | NO | NO |
| participacion/page.tsx | 433 | SI (lg: only) | NO | SI |
| ciudadanos/page.tsx | 335 | SI | NO | NO |
| scoring/page.tsx | 310 | SI (lg: only) | NO | NO |
| electoral/page.tsx | 30 | NO | NO | NO |
| contenido/page.tsx | 127 | NO | NO | NO |

**Hallazgos:**
- 0/18 paginas usan Framer Motion (solo landing page lo usa)
- Paquete `motion` v12.38.0 ya instalado (no `framer-motion`)
- 4 paginas tienen lg: pero NO md: (campanas, compliance, participacion, scoring)
- 6 paginas sin breakpoints responsive (settings, planes/[id], kanban, onboarding, electoral, contenido)
- SmoothScrollProvider existe en `src/components/providers/smooth-scroll-provider.tsx`
- StatCard existe en `src/components/dashboard/stat-card.tsx`

---

## Bloque 1: md: Breakpoints Tablet (10 paginas)

**Problema:** Tablets (768-1023px) reciben layout de phone. Las paginas solo tienen
`sm:` y `lg:/xl:` breakpoints. Enrique aprobo agregar `md:` y sus componentes DS
(ResponsiveTable, MobileFilterSheet, useBreakpoint) estan listos.

### Estrategia

No reescribir paginas completas. Agregar clases `md:` donde el salto sm->lg es
demasiado brusco. Patrones tipicos:
- `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` (KPI cards)
- `hidden md:block` (sidebars que se ocultan en mobile)
- `md:flex-row` (stacks que pasan a horizontal en tablet)
- `md:w-1/2` (columnas 50/50 en tablet)

### Paginas a tocar (ordenadas por impacto visual)

| ID | Pagina | Tipo de fix | Esfuerzo |
|----|--------|-------------|----------|
| D.1 | dashboard/page.tsx | KPI grid 1->2->4 cols, chart layout | 30min |
| D.2 | canvassing/page.tsx | Sidebar filtros + mapa side-by-side en tablet | 30min |
| D.3 | social/page.tsx | Feed + stats 2-col en tablet | 20min |
| D.4 | dirigentes/page.tsx | Cards grid 1->2->3 cols | 15min |
| D.5 | dirigentes/[id]/page.tsx | Tabs + content layout | 15min |
| D.6 | bot-detection/page.tsx | Gauge + cards 2-col | 15min |
| D.7 | campanas/page.tsx | Ya tiene lg:, agregar md: intermedio | 10min |
| D.8 | compliance/page.tsx | Ya tiene lg:, agregar md: intermedio | 10min |
| D.9 | participacion/page.tsx | Ya tiene lg:, agregar md: intermedio | 10min |
| D.10 | scoring/page.tsx | Ya tiene lg:, agregar md: intermedio | 10min |

**Paginas excluidas (no necesitan md:):**
- settings: layout simple, funciona en cualquier ancho
- planes/[id]: contenido markdown lineal
- kanban: 38 lineas, wrapper simple
- onboarding: wizard step-by-step, inherentemente responsive
- electoral: 30 lineas stub (eliminado del sidebar por Enrique)
- contenido: layout simple
- benchmark: ya tiene md: funcional
- planes/page.tsx: ya tiene md: funcional

**Esfuerzo total Bloque 1:** ~2.5h

### Criterio de aceptacion
- Abrir cada pagina en viewport 768px (iPad portrait)
- Layout debe ser 2 columnas donde aplique, no stack vertical
- Verificar con Chrome DevTools o Playwright screenshot a 768x1024

---

## Bloque 2: Framer Motion Selectiva (4 componentes)

**Problema:** Todas las animaciones son CSS @keyframes. Enrique aprobo migracion
selectiva: solo donde aporte valor de interaccion, no decorativos.

**Paquete:** `motion` v12.38.0 ya instalado. Import: `from "motion/react"`

### Componentes a animar

| ID | Componente | Animacion | Esfuerzo |
|----|-----------|-----------|----------|
| D.11 | StatCard (stat-card.tsx) | Fade-up stagger al entrar en viewport | 30min |
| D.12 | KPI cards (dashboard/page.tsx) | Fade-up stagger (reusar patron StatCard) | 20min |
| D.13 | BentoGrid items (si existe) o card grids | Bento-fade-up con delay incremental | 20min |
| D.14 | Page transitions (layout-level) | Fade suave entre paginas dashboard | 30min |

### Patron de animacion (reutilizable)

```tsx
import { motion } from "motion/react"

// Fade-up stagger para cards/stats
const fadeUpVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.4, ease: "easeOut" }
  })
}

// Uso
<motion.div
  variants={fadeUpVariants}
  initial="hidden"
  whileInView="visible"
  viewport={{ once: true }}
  custom={index}
>
  <StatCard ... />
</motion.div>
```

### Lo que NO se migra (por decision de Enrique)
- `pulse-dot` (CSS loop simple, no interactivo)
- Keyframes puramente decorativos sin interaccion de usuario
- Animaciones de loading/spinner (CSS nativo es mas eficiente)

**Esfuerzo total Bloque 2:** ~1.5h

---

## Bloque 3: Verificacion Visual

| ID | Tarea | Esfuerzo |
|----|-------|----------|
| D.15 | Screenshots 768x1024 de las 10 paginas con md: | 20min |
| D.16 | Verificar animaciones en Chrome DevTools | 10min |
| D.17 | tsc clean (0 errores TypeScript) | 10min |
| D.18 | Reducir motion: `prefers-reduced-motion` media query | 10min |

**Esfuerzo total Bloque 3:** ~50min

---

## Orden de ejecucion

```
Bloque 1 (breakpoints)     Bloque 2 (motion)
D.1-D.6 alta prioridad     D.11 StatCard animation
D.7-D.10 rapidos            D.12 KPI cards
         |                  D.13 BentoGrid
         v                  D.14 Page transitions
    Bloque 3 (verificacion)
    D.15 Screenshots
    D.16 Motion check
    D.17 tsc clean
    D.18 reduced-motion
```

No paralelizable (soy una sesion sola). Secuencial, commit por bloque.

---

## Estimado total

| Bloque | Esfuerzo |
|--------|----------|
| 1. Breakpoints md: | 2.5h |
| 2. Framer Motion | 1.5h |
| 3. Verificacion | 50min |
| **Total** | **~5h** |

---

## Criterios de aceptacion globales

- [ ] 10 paginas con md: breakpoints funcionales a 768px
- [ ] 4 componentes con Framer Motion fade-up stagger
- [ ] `prefers-reduced-motion` respetado
- [ ] tsc clean (0 errores)
- [ ] Screenshots de verificacion en .context/screenshots/
- [ ] Commit(s) en branch feat/design-enrique-review
- [ ] Worktree limpio, mergeable a main

## Dependencias

- Enrique (DS): componentes listos, no necesito nada mas de el
- Jess: worktree separado, sin conflicto
- CEO: aprobacion de este plan
