# CRECE v2.0 — Brief UX/UI para Revisión de Diseño

**Para:** Enrique (Design System Lead)
**De:** Carlos (Desarrollo)
**Fecha:** 2026-04-12
**Referencia:** md-design-system
**Audit score UX/UI:** 88/100

---

## Fundamentos de diseño actuales

| Elemento | Implementación | Alineado con DS? |
|---|---|---|
| **Fonts** | Instrument Sans (headings 400-700) + DM Sans (body 300-700) | ~70% — DS usa Satoshi + General Sans |
| **Colores** | HSL CSS variables. Deep Navy primary, Warm Amber accent, MC Orange CTA | Sí — 60-30-10 respetada |
| **Dark mode** | Completo (class-based, todos los tokens redefinidos) | Sí |
| **Spacing** | Tailwind 4px scale (gap-2/3/4/6, p-4/5/6) | Sí |
| **Radius** | 0.5rem base con sm/md/lg/xl | Sí |
| **Shadows** | 3-layer card-elevated + glass-card con blur | Parcial — DS tiene más variantes |
| **Animaciones** | bento-fade-up, pulse-dot, stat-card-transition (CSS) | Parcial — DS usa GSAP + Framer Motion |
| **Responsive** | sm/lg/xl breakpoints. Falta md: (tablets) | Gap |
| **Touch targets** | h-10 (40px) default, h-11 (44px) lg | OK post-fix |

---

## Módulos por página (17 total)

### 1. Overview (Dashboard principal)

**Layout:** BentoGrid — 2 hero KPIs (span-2) + 2 regulares + gráficas 3:2 + posts + mapa placeholder
**Gráficos:** SentimentLineChart (Recharts line), barras de followers por plataforma
**Interacción:** Filtro temporal (Hoy/7d/30d/90d) con aria-pressed, alertas de crisis expandibles
**Animaciones:** bento-fade-up con stagger delays (d1/d2/d3), pulse-dot rojo en alertas
**Estados:** Skeleton loading, empty con icono, datos con trending arrows (emerald/red)
**Responsive:** 2-col mobile → 4-col xl en KPIs. Charts 5-col grid (3:2 split en lg)
**Para revisar:** Hero cards podrían tener más diferenciación visual. Mapa placeholder en overview (solo muestra en canvassing).

### 2. Social Monitor

**Layout:** 3-col stats + filtros + feed 2:1 (feed izq, sidebar sentiment der)
**Gráficos:** SentimentPieChart (Recharts pie con Cell colors), TrendingAlcaldiaCard
**Interacción:** Filtros plataforma/sentimiento (Select), toggle RTs (aria-pressed), búsqueda
**Estados:** Skeleton, empty contextual ("sin originales" vs "sin publicaciones"), crisis banner
**Colores:** Plataformas con brand colors (Twitter #1DA1F2, IG #E4405F, etc.)
**Responsive:** Feed 2-col + sidebar 1-col en lg. Stacks en mobile.
**Para revisar:** Stats bar sin skeleton loading. Crisis banner podría ser más prominente.

### 3. Canvassing (Mapa de campo) — Killer feature

**Layout:** Stats bar 4-col + sidebar filtros (glass-card) 1:5 ratio con mapa MapLibre
**Gráficos:** MapLibre GL JS con GeoJSON clustering (9,631 puntos), leyenda por estrato
**Interacción:** 5 filtros (alcaldía, estrato, participación, contactado, volatilidad), color mode toggle, click popup con datos ciudadano, cluster expand al zoom
**Animaciones:** stat-card-transition en cards de filtro
**Estados:** Loader2 spinner en mapa, skeleton stats, empty rutas, puntos de visita con status icons
**Colores estrato:** Azul (alto) → Verde (medio) → Amarillo (medio bajo) → Naranja (bajo) → Rojo (muy bajo)
**Responsive:** Filtros stack arriba del mapa en mobile (gap — podría ser Sheet collapsible). Mapa h-500px fijo en mobile (podría ser h-350px).
**Para revisar:** Filtros en mobile empujan mapa abajo del fold. Popup maxWidth 260px podría ser tight en desktop.

### 4. Dirigentes (Roster)

**Layout:** Header + filtros + tabla/cards responsive
**Interacción:** Búsqueda real-time, filtros partido/estado, click → detalle
**Estados:** Skeleton rows, empty, error
**Responsive:** Cards (md:hidden) ↔ Table (hidden md:table) — dual view pattern
**Para revisar:** IpdScoreBadge con colores dinámicos (verde/amarillo/rojo). Podría tener más contexto visual.

### 5. Benchmarking (Comparación competitiva)

**Layout:** Selector 3-col (A vs B) + comparación 2-col + radar + engagement + sentiment
**Gráficos:** IpdRadarChart (Recharts radar, azul vs rojo), EngagementBarChart, SentimentLineChart
**Interacción:** Selectors A y B, comparación condicional
**Responsive:** 2-col en sm para comparación, lg para charts
**Para revisar:** Radar chart azul/rojo puede ser difícil para daltonismo. Considerar patterns además de colores.

### 6. Planes IA + Kanban

**Layout:** Lista de planes (stacked cards) + dialog generación + kanban 3-col
**Gráficos:** Ninguno (texto + badges)
**Interacción:** Generar plan (dialog con selects), filtro por estado, cards clickeables → detalle → kanban
**Colores:** Tipo de plan: azul (diagnóstico), esmeralda (consolidación), rojo (crisis), ámbar (contenido)
**Para revisar:** Kanban usa botones "→" en vez de drag-and-drop. UX podría mejorar con @dnd-kit.

### 7. Bot Detection (Salud Digital)

**Layout:** Overall health card (color-coded bg) + grid de perfiles por plataforma
**Gráficos:** Barras de métricas (engagement, ff_ratio, comment_like) custom CSS
**Interacción:** Selector dirigente, botón "Analizar", anomalías expandibles (click count)
**Colores:** Semáforo (verde/amarillo/rojo) en cards, top bar 1.5px, signals dots
**Responsive:** Perfiles 2-col md, 3-col lg
**Para revisar:** Health score grande (number) podría tener gauge/donut visual.

### 8. Ciudadanos CRM

**Layout:** 4 KPI cards + filtros + tabla/cards responsive + paginación
**Interacción:** Búsqueda, filtros intención/escolaridad, dialog agregar, paginación
**Responsive:** Card/Table dual view pattern (md breakpoint)
**Para revisar:** Dialog de agregar ciudadano podría tener validación visual inline.

### 9. Voter Scoring

**Layout:** 4 KPI cards + pie chart 2:3 con tabla
**Gráficos:** PieChart Recharts (4 segmentos con Cell colors + Tooltip + Legend)
**Interacción:** Botón "Run Scoring" con spinner
**Colores:** Promotable (esmeralda), Persuadible (ámbar), Indeciso (azul), Opositor (rojo)
**Banner:** Nota de datos sintéticos (amber bg)
**Para revisar:** Pie chart podría complementarse con bar chart horizontal para mejor lectura.

### 10. Content Factory

**Layout:** Header + filtros formato/estado + lista de contenidos stacked
**Interacción:** Dialog generación (dirigente, formato, tema, tono), ContentCard con progresión de estados
**Para revisar:** ContentCard no se ve en el inventario — componente delegado. Revisar su diseño.

### 11. Compliance (Blindaje Legal)

**Layout:** 4 KPI cards + gastos tabla 3:2 con alertas + referencia electoral 3-col
**Interacción:** Import gastos dialog, Run Audit button
**Colores:** % del tope dinámico (rojo ≥90%, ámbar 70-89%, verde <70%). Alertas por severidad.
**Para revisar:** Cards de referencia electoral son estáticas — podrían ser más visuales.

### 12. Campañas WhatsApp

**Layout:** Lista campañas 3:2 con analytics panel
**Gráficos:** FunnelBar (custom visualization del funnel envío→entrega→lectura→respuesta)
**Interacción:** Dialog nueva campaña, click campana → analytics, polling 5s durante envío
**Para revisar:** FunnelBar es componente custom — revisar si sigue DS. Analytics panel podría tener gráfica temporal.

### 13. Participación Ciudadana

**Layout:** 4 KPI stats + breakdown horizontal por tipo + filtros + grid cards 2-col + paginación
**Interacción:** 3 filtros (tipo, estado, prioridad), paginación
**Colores:** Tipos: queja (rojo), petición (azul), propuesta (esmeralda), denuncia (ámbar), info (púrpura)
**Para revisar:** Breakdown bar usa hardcoded bg-[#FF6B00] — debería usar token CTA.

### 14. Electoral (Stub)

**Layout:** Solo icono Map + "Mapa en desarrollo"
**Para revisar:** Decidir si ElectoralMap existente (MVT tiles) se activa o se elimina del sidebar.

### 15. Settings

**Layout:** Cards stacked (cuenta, sistema, compliance, versión)
**Interacción:** Ninguna (display only)
**Para revisar:** Podría tener toggle dark mode, cambio de idioma, preferencias de notificación.

### 16. Onboarding Wizard

**Layout:** Delegado a OnboardingWizard component (3 pasos)
**Interacción:** Stepper/tabs, validación por paso, progress chain con polling
**Para revisar:** Verificar que sigue el patrón wizard del DS.

---

## Elementos del Design System NO utilizados

| Componente DS | Disponible | Usado en CRECE? |
|---|---|---|
| BentoGrid | Sí (tokens) | Parcial (CSS manual, no component) |
| StatCard shared | Sí | No — duplicado en 2 pages |
| ChartContainer | Sí | No — charts inline |
| StatusTimeline | Sí | No |
| ResponsiveTable | Sí | No — dual view manual |
| MobileFilterSheet | Sí | No — filtros stack sin Sheet |
| TouchActionBar | Sí | No |
| useBreakpoint hook | Sí | No |
| useReducedMotion hook | Sí | No (CSS media query sí) |
| GSAP animation presets | Sí | No — CSS @keyframes |
| Framer Motion | Sí | No |
| Lenis smooth scroll | Sí | No |
| ESLint a11y rules | Sí | No |

---

## Hallazgos de la auditoría que requieren opinión de diseño

1. **Fonts:** CRECE usa Instrument Sans + DM Sans. DS estándar es Satoshi + General Sans. ¿Mantenemos o migramos?
2. **Tablet breakpoint:** No hay `md:` en la mayoría de pages. Tablets reciben layout de phone. ¿Diseñar breakpoint intermedio?
3. **Canvassing mobile:** Filtros stack arriba del mapa, empujando el mapa debajo del fold. ¿Sheet collapsible o bottom drawer?
4. **Radar chart daltonismo:** Benchmark usa azul vs rojo sin patterns. ¿Agregar dashes/dots?
5. **Kanban sin drag-and-drop:** Botones "→" en vez de arrastrar. ¿Implementar @dnd-kit?
6. **Electoral page stub:** ¿Activar el mapa MVT existente o eliminar del sidebar?
7. **Health score gauge:** Bot detection muestra número grande. ¿Donut/gauge visual?
8. **StatCard duplicado:** Existe en canvassing + participación con firmas similares. ¿Extraer a componente compartido del DS?
9. **Animaciones:** Hoy son CSS puro. ¿Migrar a GSAP/Framer Motion para consistencia con DS?
10. **Smooth scroll:** ¿Implementar Lenis del DS para toda la app?

---

## Screenshots de referencia

- `.context/screenshots/canvassing-geo-map-v2.png` — Vista de clusters
- `.context/screenshots/canvassing-geo-map-v3-zoomed.png` — Puntos individuales coloreados
- `.context/screenshots/canvassing-geo-map-v4-bj-filter.png` — Filtro Benito Juárez

---

*Este brief es para revisión de diseño. No requiere cambios de código hasta que Enrique apruebe la dirección.*
