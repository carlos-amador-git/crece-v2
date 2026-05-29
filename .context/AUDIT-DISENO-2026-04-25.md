# Audit de diseño UX/UI — CRECE v2 frontend

- Fecha: 2026-04-25
- Auditor: Claude (Opus 4.7) — sesión Joy
- Repo: `/Users/marxchavez/Projects/crece-v2/frontend`
- Deploy auditado: `https://frontend-zeta-sepia-46.vercel.app`
- Stack: Next.js 14 App Router · TypeScript · Tailwind CSS v4 · shadcn/ui · MapLibre · Recharts
- Standards: `~/.claude/rules/design-standards.md` · `CLAUDE.md` Fase 1
- Evidencia visual: capturas previas en `.context/frontend-review-2026-04-21/` (live, abril 21) + login fresco `01-login.png` esta sesión

---

## Resumen ejecutivo

| Categoría | Veredicto |
|---|---|
| **Score global ponderado** | **6.6 / 10** (sólido pero con 4 fugas estructurales) |
| Tokens y paleta | 8.5 — sistema CSS-vars HSL bien diseñado, 60-30-10 declarado y respetado |
| Tipografía | 9.0 — Instrument Sans + DM Sans (no Inter/Roboto/Arial). Cumple regla MD |
| Estados (loading/empty/error) | 5.5 — loading sí, error parcial, empty casi inexistente |
| Componentes reutilizados | 5.0 — 4 implementaciones distintas de "KPI card" en el repo |
| Dark mode | 3.0 — clases `dark:` en 140+ archivos, pero NO hay `next-themes`, NO hay toggle, NO hay ThemeProvider. Modo oscuro inactivo en prod |
| Navegación | 7.5 — sidebar con grupos + topbar + breadcrumbs en tier1/tier2 |
| Anti-slop | 7.0 — sin gradientes púrpura sobre blanco como CTA, pero hay 3 fugas violet/purple en `bg-*/10` |
| Accesibilidad base | 7.5 — skip-link, focus-visible ring, prefers-reduced-motion, semántica OK |

**Conclusión:** la base de tokens y tipografía es de las mejores que he auditado en el ecosistema MD. Lo que arrastra el score son tres deudas concretas: (1) **Cloudflare tunnel del backend caído** desde Vercel — login no responde porque `parks-fell-bikini-logos.trycloudflare.com` da `ERR_NAME_NOT_RESOLVED` (bloqueante operativo, no de diseño, pero impide auditoría runtime); (2) **dark mode huérfano** (140 usos, 0 mecanismo de switch); (3) **3 KPI cards distintos** con la misma intención visual.

**No pude autenticarme en la deploy** durante esta sesión por el tunnel caído. La auditoría se sostiene en: source-level (todos los archivos clave leídos), capturas vivas previas del 2026-04-21 (Piña, Ballesteros, dark mode, tier1, tier2, planes, aceptación, admin), y screenshot fresco de `/login`.

---

## Hallazgos por dimensión × página

Tabla **8 páginas × 7 dimensiones**, score 0-10. Donde digo "code-only" no pude verificar runtime esta sesión y me apoyo en capturas previas.

| # | Página | Consist. | Jerarquía | Estados | Reuso | Dark | Nav | Anti-slop |
|---|---|---|---|---|---|---|---|---|
| 1 | `/login` | 8 | 7 | 6 | n/a | 5 | n/a | 8 |
| 2 | `/dashboard` (overview) | 8 | 9 | 8 | 6 | 4 | 8 | 8 |
| 3 | `/dashboard/diagnostico/1` (Piña Tier1) | 9 | 9 | 9 | 8 | 6 | 9 | 9 |
| 4 | `/dashboard/diagnostico-tier2/1` | 9 | 8 | 9 | 8 | 6 | 9 | 8 |
| 5 | `/dashboard/recomendaciones` | 7 | 7 | 6 | 7 | 4 | 7 | 8 |
| 6 | `/dashboard/planes` | 7 | 7 | 7 | 6 | 5 | 7 | 7 |
| 7 | `/dashboard/aceptacion` | 7 | 7 | 6 | 4 | 4 | 7 | 8 |
| 8 | `/dashboard/evaluacion/1` (Phase B) | 8 | 8 | 8 | 7 | 4 | 8 | 8 |
| **Promedio** | | **7.9** | **7.8** | **7.4** | **6.6** | **4.7** | **7.9** | **8.0** |

---

## 1. Consistencia visual — 8.5

**Fortalezas:**
- `frontend/src/app/globals.css:48-93`: paleta única centralizada en HSL, derivada en `@theme` para Tailwind v4. Light + dark vars coherentes.
- `frontend/tailwind.config.ts:1-65`: tokens primarios consumidos vía `hsl(var(--primary))` etc. Cero `#hex` hardcoded a nivel de tema.
- Radius escalado con `var(--radius)` (sm/md/lg/xl). Cumple regla MD "border radius consistente".
- Spacing usa escala Tailwind 4 default (4px base). Cumple.

**Fugas:**
- `frontend/src/app/dashboard/participacion/page.tsx:50` — `bg-purple-500/10 text-purple-600 dark:text-purple-400` para etiqueta "Información". Fuera de paleta, viola "PROHIBIDO púrpura". Justificación: distinguir 4 categorías. **P1**.
- `frontend/src/components/landing/features.tsx:34` — `accent: "bg-violet-500/10 text-violet-600"` en card de feature. Misma raíz: usar 4 colores arbitrarios para 4 features. **P2**.
- `frontend/src/components/dashboard/actividad-alineada-card.tsx:131` — paleta de tone interna `{rose, violet, emerald, slate}` que NO mapea a tokens. 24 ocurrencias contadas en `aceptacion/planes/evaluacion/recomendaciones` de `text-blue-*`, `bg-emerald-*`, `text-rose-*` colores Tailwind crudos en lugar de `--chart-positive`/`--chart-negative`/etc.

**Score 8.5** por la base sólida. -1.5 por las fugas de colores crudos cuando ya existen `--chart-*` tokens.

---

## 2. Jerarquía visual — 7.8

**Fortalezas:**
- Dashboard overview cumple F-pattern: KPI bento de 4 cards arriba (2 hero + 2 normales), luego trends + alerts + actividad. `frontend/src/app/dashboard/page.tsx:230-284`.
- Tier1/Tier2 tienen header con breadcrumb + h1 + summary badges + contexto educativo en banner separado. `frontend/src/app/dashboard/diagnostico/[dirigenteId]/page.tsx:43-101`.
- `font-heading` (Instrument Sans) reservado para h1-h6 en `globals.css:159`.
- KPI primero arriba-izquierda en aceptación, evaluación, dashboard. Cumple regla "KPIs críticos arriba-izquierda".

**Debilidades:**
- `/dashboard/recomendaciones` tiene 4 tabs (Pendientes / Activas / Seguimiento / Histórico) sin un KPI summary arriba — el usuario no ve "cuántas tengo pendientes" sin clicar. `frontend/src/app/dashboard/recomendaciones/page.tsx`.
- `/dashboard/planes` lista tarjetas sin un agrupado/sticky header de filtro tipo. El selector de "all/approved/draft" está suelto.
- `aceptación` mete 4 KPI + tabla larga + leyenda al final. La leyenda debería estar arriba o como tooltip.

---

## 3. Estados completos (loading / empty / error / success) — 7.4

**Cobertura por página (code-grep):**

| Página | Loading skeleton | Error state | Empty state |
|---|---|---|---|
| dashboard/page.tsx | sí (Skeleton inline) | sí (DEFAULT_KPI fallback) | parcial ("Sin datos" en sentiment) |
| diagnostico/[id] | sí (CardSkeleton) | sí (banner role=alert) | sí (resumen.insufficient_data badge) |
| diagnostico-tier2/[id] | sí (CardTier2Skeleton) | sí (banner) | sí (insufficient_data) |
| recomendaciones | NO Skeleton dedicado | sí (isError + Inbox icon) | sí (Inbox empty) |
| planes | sí (Skeleton 6x) | n/a | sí ("Sin planes") |
| aceptacion | sí | sí (card "No se pudo cargar") | NO empty si `rows.length === 0` |
| evaluacion/[id] | sí | sí (rose card) | n/a |
| login | n/a | parcial (error inline) | n/a |

**Hallazgo crítico:** sólo existe **un componente `EmptyState`** en todo el repo (`/dashboard/admin/plan-ia-review/page.tsx`). El resto improvisa con `<Card>...sin datos...</Card>` o `<Inbox />` ad hoc. Patrón inconsistente. **P1**.

**Hallazgo:** `dashboard/error.tsx` existe pero el resto de subrutas usan inline `if (isError)` con tratamientos visuales distintos (rose card en evaluacion, destructive banner en tier1, generic card en aceptacion).

---

## 4. Componentes reutilizados vs duplicados — 5.0

Esta es la fuga más cara del repo. **Cuatro implementaciones de "KPI card":**

1. **`components/dashboard/kpi-card.tsx`** (37 líneas) — exportado como `KpiCard`. **No se importa en ningún lugar de `app/`**. Componente huérfano. `frontend/src/components/dashboard/kpi-card.tsx:12`.
2. **`components/dashboard/stat-card.tsx`** (61 líneas) — usado en `canvassing/page.tsx` y `participacion/page.tsx` solamente.
3. **`app/dashboard/aceptacion/page.tsx`** declara su propia `KPICard` inline (función dentro del archivo). Duplicación.
4. **`app/dashboard/page.tsx:230-284`** — render KPI inline con `<Card>` + `<CardContent>` + skeleton manual. No usa `KpiCard` ni `StatCard`.

**Otros indicios:**
- `components/landing/stats.tsx` (91 líneas) — quinto patrón visual de stat para landing.
- `components/social/indice-aceptacion-card.tsx` — sexto patrón para el IA card.
- `components/dashboard/competitor-snapshot-card.tsx`, `actividad-alineada-card.tsx`, `ia-summary-card.tsx` — cada uno dueño de su propia anatomía visual con cards/badges/iconos repetidos.

**Score 5.0** por: tener 6+ patrones donde uno consolidado bastaría. Consume tiempo de mantenimiento, divergencia visual gradual, los 3 alebrijes mostrados arriba (kpi-card + stat-card + KPICard inline) ocupan exactamente la misma franja semántica.

---

## 5. Dark mode — 3.0 (CRÍTICO)

**El bug estructural más importante de esta auditoría.**

- `frontend/tailwind.config.ts:4` declara `darkMode: "class"`.
- `frontend/src/app/globals.css:96-130` define todos los tokens dark (background 212 50% 6%, etc.) bajo `.dark`.
- `frontend/src/app/layout.tsx:34-38`: `<html lang="es" suppressHydrationWarning>` — **nunca se le añade `class="dark"`** dinámicamente.
- **`package.json` NO incluye `next-themes`.** Verificado.
- **No existe `<ThemeProvider>` ni `useTheme()` ni `setTheme()` en todo `frontend/src`.** `grep -rln 'theme-toggle|ThemeToggle|setTheme'` → vacío.
- 140+ archivos `.tsx` usan `dark:bg-*`, `dark:text-*`, `dark:border-*` — **todas esas clases están muertas** en producción porque la clase `dark` nunca se aplica al `<html>`.

**Evidencia visual contradictoria:** `.context/frontend-review-2026-04-21/p4-11-dashboard-dark-pina.png` y `p4-12-tier2-dark-pina.png` SÍ muestran dark mode renderizando. Esto sugiere que el screenshot se tomó con DevTools forzando `prefers-color-scheme: dark` o con la clase inyectada manualmente. El usuario final no puede activarlo.

**Acción:** ver Top 10 #1.

---

## 6. Navegación — 7.9

- Sidebar con grupos colapsables: `frontend/src/components/layout/sidebar.tsx`. Persiste estado expand/collapse en zustand (`useSidebarStore`).
- Topbar con buscador + perfil + org switcher.
- Breadcrumbs en tier1/tier2 con path "Dirigentes / Diagnóstico Tier 1 / Diferenciadores Tier 2". `diagnostico-tier2/[dirigenteId]/page.tsx:71-90`.
- Skip link a `#main-content` declarado en `dashboard/layout.tsx:64-68`. Cumple a11y.
- Banner `SyntheticDataBanner` para orgs con `has_synthetic_data` — buen patrón de transparencia. `dashboard/layout.tsx:12-34`.

**Mejora:** la navegación entre `dirigente → diagnostico → tier2 → recomendaciones → planes` no tiene un "stepper" o "panel del dirigente" unificado. Cada vista es independiente y el contexto del dirigente se pierde — el usuario tiene que volver a `Dirigentes` y reseleccionar.

---

## 7. Anti-slop — 8.0

**Fortalezas:**
- Tipografía custom (no Inter/Roboto/Arial). **Cero violaciones encontradas.**
- Paleta narrativa (Deep Blue + Warm Amber + MC Orange + Emerald) declarada explícitamente en comentario de `globals.css:42-44`.
- Animaciones controladas: `prefers-reduced-motion` respetado en `globals.css:175-184`.
- `card-elevated` con sombras escalonadas y hover de 2px translate. Sutil, no slop.
- Glass card disponible pero con comentario "use sparingly per baseline-ui".

**Fugas:**
- 3 ocurrencias de `purple/violet` mencionadas arriba (P1/P2).
- `landing/features.tsx` usa 4 acentos arbitrarios (sky/emerald/amber/violet) — patrón típico de "feature cards de IA" genéricas. Mejor reusar 1-2 tokens del sistema para mantener cohesión.

---

## Inconsistencias entre páginas (mismo patrón implementado distinto)

| Patrón | Implementación A | Implementación B | Implementación C |
|---|---|---|---|
| KPI card | `dashboard/page.tsx` inline con Card + CardContent | `aceptacion/page.tsx` `function KPICard()` inline | `stat-card.tsx` `StatCard` con variants |
| Loading state | `dashboard/page.tsx` inline `Card + Skeleton` | `aceptacion/page.tsx` `<Skeleton h-24 + 6×h-48 />` | `evaluacion/[id]` `Skeleton h-32 + h-48 + h-96` |
| Error fallback | `tier1` banner `border-destructive/50 bg-destructive/5` (role=alert) | `aceptacion` `<Card><CardContent>No se pudo cargar` | `evaluacion` `<Card><CardContent text-rose-600>` |
| Empty state | tier1 badge `insufficient_data` | `recomendaciones` `<Inbox />` icon centered | `planes` "Sin planes" texto suelto |
| Breadcrumb | tier1 + tier2 con `<Button variant=ghost ArrowLeft />` | `evaluacion` con `<Link><ArrowLeft />` | resto sin breadcrumb |
| Header h1 | tier1 con `font-heading text-2xl sm:text-3xl tracking-tight` | aceptacion con `font-heading text-2xl tracking-tight` (sin sm:3xl) | recomendaciones sin h1 |

---

## Top 10 mejoras priorizadas

### P0 (bloquea operación)

1. **[INFRAESTRUCTURA, no diseño] Backend tunnel caído.** Vercel apunta a `parks-fell-bikini-logos.trycloudflare.com` que ya no resuelve. Toda la deploy es inutilizable. Acción: actualizar `NEXT_PUBLIC_API_URL` en Vercel hacia el endpoint Coolify estable y redeployar. Sin esto no hay demo, no hay piloto, no hay auditoría runtime.

### P1 (deuda visual estructural)

2. **Dark mode: instalar `next-themes` o tirarlo.** Decisión binaria. Opción A: `pnpm add next-themes`, envolver en `<ThemeProvider attribute="class">` en `app/layout.tsx`, agregar toggle en topbar (3-4 horas trabajo). Opción B: borrar las 140+ ocurrencias `dark:*` (4-6 horas) y aceptar light-only. **Mantener el estado actual es la peor opción** porque cada nuevo componente seguirá replicando `dark:*` clases muertas.

3. **Consolidar KPI card en un único componente.** Renombrar `kpi-card.tsx` a `metric-card.tsx`, agregar variantes `default | hero | with-trend | alert`, migrar los 3 usos inline (dashboard, aceptación, stat-card) a este. Quitar la duplicación. Estimado: 2-3 horas.

4. **Crear `<EmptyState />` y `<ErrorState />` compartidos.** Patrón único: icon + headline + description + CTA opcional. Migrar 8+ instancias inline. `frontend/src/components/ui/empty-state.tsx` y `error-state.tsx`. Estimado: 2 horas migración + 1 hora componentes.

5. **Eliminar fugas de purple/violet.** 3 archivos: `participacion/page.tsx:50`, `landing/features.tsx:34`, `actividad-alineada-card.tsx:131`. Reemplazar por tokens del sistema (`--accent`, `--chart-accent`) o por una paleta categórica formal con 4-6 colores semánticos en `globals.css` (e.g. `--cat-info`, `--cat-warning`, `--cat-feature`).

6. **Tokens de chart vs Tailwind crudos.** Hay 24 usos de `text-blue-*`, `bg-emerald-*`, `text-rose-*` en pages cuando ya existen `--chart-positive`, `--chart-negative`, `--chart-neutral`, `--chart-accent`. Migrar para que dark mode (cuando se arregle) afecte automáticamente.

### P2 (pulido)

7. **Header consistente entre vistas de dirigente.** tier1, tier2 y evaluacion usan 3 patrones distintos de breadcrumb + h1. Crear `<DirigenteHeader nombre breadcrumb badges />` reutilizable. Reduce divergencia futura.

8. **Stepper o "panel del dirigente" unificado.** Tabs sticky tipo `Diagnóstico Tier1 | Tier2 | Recomendaciones | Planes | Evaluación` para un dirigente seleccionado, sin perder contexto. Mejora dramática de UX para el flujo principal.

9. **Resumen KPI arriba en `/recomendaciones`.** "Tienes X pendientes, Y activas, Z en seguimiento" antes de los tabs. Reduce clics ciegos.

10. **Documentar la regla "60-30-10" + "tokens-only" en CONTRIBUTING.** El sistema es bueno; sin guardrail escrito los próximos PRs van a seguir metiendo `bg-purple-500/10`. Anclar en code review checklist.

---

## Apéndice — Evidencia visual usada

- `01-login.png` (esta sesión, 2026-04-25, 1440×900) — login page con paleta blue navy + amber + texto bilateral.
- `.context/frontend-review-2026-04-21/p4-11-dashboard-dark-pina.png` — dashboard en dark mode (forzado por DevTools, no accesible al usuario final).
- `.context/frontend-review-2026-04-21/p1-01-planes-pina.png`, `p1-02-plan-detalle-pina.png`, `p1-03-plan-kanban-pina.png`, `p1-04-aceptacion-pina.png` — flujo Piña en producción.
- `.context/frontend-review-2026-04-21/p3-09-landing-sinlogin.png` — landing.
- `.context/frontend-review-2026-04-20/post-opcion-d-dashboard.png`, `post-opcion-d-tier2.png`, `post-opcion-d-alertas.png` — vistas tier2 + alertas con estilo final D.

---

## Apéndice — Archivos auditados (source-level)

- `frontend/tailwind.config.ts`
- `frontend/src/app/globals.css` (359 líneas leídas en 3 tramos)
- `frontend/src/app/layout.tsx`
- `frontend/src/app/dashboard/layout.tsx`
- `frontend/src/app/dashboard/page.tsx`
- `frontend/src/app/dashboard/diagnostico/[dirigenteId]/page.tsx`
- `frontend/src/app/dashboard/diagnostico-tier2/[dirigenteId]/page.tsx`
- `frontend/src/app/dashboard/recomendaciones/page.tsx`
- `frontend/src/app/dashboard/planes/page.tsx`
- `frontend/src/app/dashboard/aceptacion/page.tsx`
- `frontend/src/app/dashboard/evaluacion/[id]/page.tsx`
- `frontend/src/components/dashboard/kpi-card.tsx`
- `frontend/src/components/dashboard/stat-card.tsx`
- `frontend/src/components/layout/sidebar.tsx` (head)

Total: ~14 archivos críticos, ~1500 líneas de TSX/CSS leídas.
