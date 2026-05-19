# Auditoría Responsive · CRECE v2 Frontend

**Fecha:** 2026-04-25
**Auditor:** Claude Code (frontend agent)
**Repo:** `/Users/marxchavez/Projects/crece-v2/frontend`
**Producción:** https://frontend-zeta-sepia-46.vercel.app
**Breakpoints:** 375×667 (Mobile · iPhone SE), 768×1024 (Tablet · iPad portrait), 1440×900 (Desktop)
**Técnica:** Chrome DevTools MCP + `Emulation.setDeviceMetricsOverride` (deviceScaleFactor 2 mobile/tablet, 1 desktop). Touch + mobile flags activos en mobile.

---

## Constraint encontrado durante el audit

El backend de producción **no respondió** a las requests de login durante la sesión:

| URL probada | Estado |
|---|---|
| `https://crece.mdconsultoria-ti.org/api/v1/auth/login` | CORS · `Access-Control-Allow-Origin` ausente |
| `https://api.crece.mdconsultoria-ti.org/api/v1/auth/login` | `ERR_CERT_AUTHORITY_INVALID` |
| `https://parks-fell-bikini-logos.trycloudflare.com/api/v1/auth/login` (extraído del bundle JS) | `Failed to fetch` (tunnel caído) |
| `https://crece-api.mdconsultoria-ti.org/api/v1/auth/login` | `ERR_CERT_AUTHORITY_INVALID` |

El layout `dashboard/layout.tsx:42-45` redirige a `/login` cuando `isAuthenticated=false` y `useAuth.fetchUser()` borra el token si `/auth/me` falla (`auth.ts:73-78`). Inyectar token sintético tampoco renderiza el shell — `fetchUser` lo limpia inmediatamente al recibir 4xx.

**Implicación**: las 4 páginas protegidas (`/dashboard`, `/dashboard/diagnostico/1`, `/dashboard/aceptacion`, `/dashboard/evaluacion/1`) no se pudieron capturar autenticadas. Los screenshots solicitados de esas rutas habrían sido copias del `/login`.

**Decisión del auditor**: combinar (a) las capturas vivas de `/login` (las únicas posibles), (b) auditoría de código fuente sobre los breakpoints declarados en cada página, y (c) hallazgo principal del único screenshot vivo en mobile. Reporto este compromiso transparentemente — no inventé datos sobre las rutas que no pude renderizar.

---

## Capturas (vivas)

| Ruta | Mobile 375 | Tablet 768 | Desktop 1440 |
|---|---|---|---|
| `/login` | `AUDIT-RESPONSIVE-2026-04-25/login-mobile.png` | `…/login-tablet.png` | `…/login-desktop.png` |
| `/dashboard` | redirige a `/login` (no capturado) | idem | idem |
| `/dashboard/diagnostico/1` | redirige a `/login` | idem | idem |
| `/dashboard/aceptacion` | redirige a `/login` | idem | idem |
| `/dashboard/evaluacion/1` | redirige a `/login` | idem | idem |

---

## Tabla scoring · 5 páginas × 3 breakpoints × 5 criterios

Score 0-10 por criterio. Página = promedio de breakpoints.
Para protegidas se evalúa **el código de la ruta** (clases Tailwind, breakpoints declarados), no el render. Marcado con `[code]`.

### `/login` (live)

| Criterio | Mobile 375 | Tablet 768 | Desktop 1440 |
|---|---|---|---|
| Layout no se rompe | **5** — overflow horizontal observable: "Inteligencia Politica e…" y subtitle del form aparecen clipados; el padding `px-8` y `text-4xl` del wordmark ocupan más ancho del viewport útil | 9 — banner colapsado arriba, form centrado abajo (vertical stack `flex-col` activado en mobile, `lg:flex-row` para desktop) | 10 — split 60/40 limpio |
| Touch targets ≥ 44px | **6** — inputs miden 36px (h-9 shadcn), botón submit 40px (h-10), link "olvidaste contraseña" 18px de altura | 7 (idem inputs/botón) | n/a |
| Texto legible ≥ 16px | 9 — body=16px, h1 mobile=36px (`text-4xl`) | 10 | 10 |
| Navegación accesible | 8 — solo form, no requiere nav | 8 | 8 |
| Tablas/mapas adaptables | n/a | n/a | n/a |
| **Score** | **7.0/10** | **8.5/10** | **9.3/10** |

**Source**: `frontend/src/app/login/page.tsx:107` — `flex h-dvh flex-col lg:flex-row`. Brand panel `px-8 py-10 lg:w-[60%] lg:px-16 lg:py-16`. Lista de features `hidden ... lg:block` (oculta en <1024px, correcto). Dot grid `hidden lg:block`.

### `/dashboard` `[code]`

| Criterio | Mobile 375 | Tablet 768 | Desktop 1440 |
|---|---|---|---|
| Layout no se rompe | 8 — header `flex-col gap-4 sm:flex-row`, KPI grid `grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 w-full min-w-0`, sección secundaria `md:grid-cols-2 lg:grid-cols-5` | 9 — 2 columnas KPI a partir de sm | 10 — 4 columnas KPI desde xl |
| Touch targets ≥ 44px | 7 — usa shadcn Button por defecto (h-10 = 40px en `size="default"`) — al límite | 7 | n/a |
| Texto legible ≥ 16px | 9 — body 14-16px en cards, KPI 24px+ | 9 | 10 |
| Navegación accesible | **8** — hamburger funciona (`topbar.tsx:145` `lg:hidden`), drawer `w-[260px]` con backdrop (`sidebar.tsx:489-505`); breadcrumb oculto en mobile | 8 — sigue siendo drawer (lg=1024 > 768) | 10 — sidebar fijo con `lg:block` |
| Tablas/mapas adaptables | 6 — Recharts usan `ResponsiveContainer` (correcto). Mapa electoral comentado/oculto. Cards `w-full min-w-0` previenen overflow. Sin scroll-x explícito en feed posts | 7 | 9 |
| **Score** | **7.6/10** | **8.0/10** | **9.5/10** |

**Source**: `frontend/src/app/dashboard/page.tsx:230` `grid gap-4 grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 w-full min-w-0`; `:412` `grid gap-6 md:grid-cols-2 lg:grid-cols-5`.

### `/dashboard/diagnostico/[dirigenteId]` `[code]`

| Criterio | Mobile 375 | Tablet 768 | Desktop 1440 |
|---|---|---|---|
| Layout no se rompe | 9 — grid `grid-cols-1 md:grid-cols-2 xl:grid-cols-3` (10 cards B01-B10) | 9 — 2 columnas desde md | 10 — 3 columnas desde xl |
| Touch targets ≥ 44px | 7 — usa cards con CTA dentro, depende del componente CardB10WithDrilldown | 7 | n/a |
| Texto legible ≥ 16px | 8 — h1 `text-2xl sm:text-3xl`, body 14px en badges es subóptimo | 9 | 9 |
| Navegación accesible | 8 — header con back button, drawer del shell | 8 | 10 |
| Tablas/mapas adaptables | n/a (cards con visualizaciones ResponsiveContainer Recharts) | n/a | n/a |
| **Score** | **8.0/10** | **8.3/10** | **9.7/10** |

**Source**: `frontend/src/app/dashboard/diagnostico/[dirigenteId]/page.tsx:131,143`.

### `/dashboard/aceptacion` `[code]`

| Criterio | Mobile 375 | Tablet 768 | Desktop 1440 |
|---|---|---|---|
| Layout no se rompe | 7 — KPIs `grid-cols-1 md:grid-cols-2 lg:grid-cols-4`, summary cards `md:grid-cols-2 xl:grid-cols-3` | 9 | 10 |
| Touch targets ≥ 44px | 7 — Cards interactivas con CTAs estándar | 7 | n/a |
| Texto legible ≥ 16px | 9 | 9 | 9 |
| Navegación accesible | 8 | 8 | 10 |
| Tablas/mapas adaptables | **6** — tabla de 9 columnas con `overflow-x-auto` (`page.tsx:124`); en mobile el scroll horizontal es correcto pero la UX en 375px de leer "Followers / Comentaristas / Comments / Activ.% / Fantasma% / Aprob.% / Rech.%" requiere mucho swipe | 8 | 10 |
| **Score** | **7.4/10** | **8.2/10** | **9.7/10** |

**Source**: `frontend/src/app/dashboard/aceptacion/page.tsx:18,72,110,124`.

### `/dashboard/evaluacion/[id]` `[code]`

| Criterio | Mobile 375 | Tablet 768 | Desktop 1440 |
|---|---|---|---|
| Layout no se rompe | 7 — DobleKpiHero `grid gap-3 md:grid-cols-2`, PresetSelector `grid gap-2 md:grid-cols-2` con preset "personalizado" expandiendo a `md:col-span-2`. `grid grid-cols-5 gap-1` para 5 sliders dentro de cada categoría → en mobile cada celda es ~60px de ancho útil | 9 | 10 |
| Touch targets ≥ 44px | **5** — `preset-selector.tsx:155` `grid grid-cols-5 gap-1` en cada categoría → 5 botones de selección de peso en una franja de 311px (375 - padding) → ~62px por botón pero con `gap-1` hace cada botón clickeable de ~50-55px útil. Aceptable pero apretado en mobile | 7 | n/a |
| Texto legible ≥ 16px | 8 — body OK, pero descriptive text en preset cards a 12px (`text-xs`) es subóptimo | 9 | 9 |
| Navegación accesible | 7 — back button + save fixed, no sticky en scroll | 7 | 10 |
| Tablas/mapas adaptables | 8 — KPI hero adapta. Sin tablas | 9 | 10 |
| **Score** | **7.0/10** | **8.2/10** | **9.7/10** |

**Source**: `frontend/src/app/dashboard/evaluacion/[id]/page.tsx`, `frontend/src/components/evaluacion/preset-selector.tsx:79,115,155`, `frontend/src/components/evaluacion/doble-kpi-hero.tsx:46,82`.

---

## Score consolidado

| Página | Mobile | Tablet | Desktop | Promedio |
|---|---|---|---|---|
| `/login` (live) | 7.0 | 8.5 | 9.3 | **8.3** |
| `/dashboard` (code) | 7.6 | 8.0 | 9.5 | **8.4** |
| `/dashboard/diagnostico/[id]` (code) | 8.0 | 8.3 | 9.7 | **8.7** |
| `/dashboard/aceptacion` (code) | 7.4 | 8.2 | 9.7 | **8.4** |
| `/dashboard/evaluacion/[id]` (code) | 7.0 | 8.2 | 9.7 | **8.3** |
| **Promedio** | **7.4** | **8.2** | **9.6** | **8.4** |

Patrón claro: el frontend está bien optimizado para desktop (9.6), aceptable en tablet (8.2), y con puntos débiles en mobile (7.4) — sobre todo touch targets y densidad de información en tablas/grids 5-col.

---

## Top 10 issues (priorizados)

| # | Severidad | BP afectado | Descripción | Componente / archivo | Recomendación |
|---|---|---|---|---|---|
| 1 | **Alta** | Mobile 375 | Login muestra overflow horizontal: el wordmark `text-4xl` "CRECE" con `px-8` ocupa el ancho útil; el subtitle "Inteligencia Politica en Tiempo Real" no wrappea limpio y se ve clipado. Confirmado en screenshot. | `frontend/src/app/login/page.tsx:115,120,123` | Reducir `text-4xl` a `text-3xl` en mobile (mantener `lg:text-5xl`) o usar `text-balance` + `break-words`; reducir `px-8` a `px-6` en mobile |
| 2 | **Alta** | Mobile 375 | Inputs y botones del shadcn quedan en h-9/h-10 (36-40px), bajo el mínimo iOS 44px de Apple HIG | `frontend/src/components/ui/input.tsx`, `frontend/src/components/ui/button.tsx` (config global shadcn) | Forzar `min-h-[44px]` en mobile vía variant `size="touch"` o sobrescribir `Input` height a `h-11` (44px) |
| 3 | **Media** | Mobile 375 | `/dashboard/aceptacion` tabla de 9 columnas funciona con `overflow-x-auto` pero requiere mucho swipe. UX de comparación se pierde | `frontend/src/app/dashboard/aceptacion/page.tsx:124` | Card-view en mobile (1 dirigente por card vertical) en lugar de tabla scrollable; switch a tabla desde `md:` |
| 4 | **Media** | Mobile 375 | PresetSelector en evaluación: grid `grid-cols-5` para selección de pesos (5 botones pegados en 311px) genera touch targets ~50-55px con gap-1, marginal | `frontend/src/components/evaluacion/preset-selector.tsx:155` | En mobile usar `grid-cols-3` (con wrap) o radio group vertical; mantener `grid-cols-5` desde `sm:` o `md:` |
| 5 | **Media** | Mobile 375 | Link "¿Olvidaste tu contraseña?" tiene altura 18px, debajo de cualquier estándar de touch target | `frontend/src/app/login/page.tsx` (form footer) | Padding vertical extra `py-3` para alcanzar 44px tappable |
| 6 | **Media** | Mobile 375, Tablet 768 | Sidebar usa `lg:hidden` (≥1024) — tablet 768 obtiene drawer en vez de sidebar fijo. Decisión válida pero limita densidad de info en iPad | `frontend/src/components/layout/sidebar.tsx:499,508` | Mantener — pero considerar `md:` (≥768) si se quiere sidebar collapsable en iPad portrait |
| 7 | **Media** | Mobile 375 | Search bar `hidden ... sm:block` (`topbar.tsx:177`) oculta búsqueda en mobile, pero no provee CTA alternativa (icono lupa) | `frontend/src/components/layout/topbar.tsx:177` | Agregar botón con icono `Search` que abra modal full-screen en mobile |
| 8 | **Baja** | Mobile 375 | Body text en `text-xs` (12px) en preset cards, badges, footer notes — bajo del mínimo legible recomendado para mobile (16px) | múltiples (`evaluacion`, `diagnostico` footers) | Subir a `text-sm` (14px) en mobile, mantener xs para metadata secundaria |
| 9 | **Baja** | Tablet 768 | Lista de features del login (`hidden lg:block`, `page.tsx:127`) no aparece en tablet, dejando el banner azul vacío con espacio considerable | `frontend/src/app/login/page.tsx:127` | Cambiar breakpoint a `md:block` para mostrar features desde 768 |
| 10 | **Baja** | Mobile 375 | El wordmark "CRECE" en `/login` ocupa visualmente la mitad superior del viewport, empujando el form below the fold en iPhone SE (form aparece al hacer scroll) | `frontend/src/app/login/page.tsx:107-148` | Reducir altura del banner mobile (cambiar `py-10` a `py-6`) o usar `min-h-screen` en form para asegurar ambos visibles inicialmente |

---

## Recomendación general

**Estado actual: Aceptable con fixes mobile.** El frontend está construido con patrones responsive correctos (mobile-first grids, sidebar drawer, ResponsiveContainer en charts, overflow-x en tablas). Los breakpoints están **declarados consistentemente** en el código.

**Veredicto por categoría:**
- **Desktop 1440**: producción. No requiere trabajo.
- **Tablet 768**: aceptable con 2-3 ajustes menores (sidebar como sidebar collapsible vs drawer; mostrar features en login). No bloquea.
- **Mobile 375**: requiere **Sprint Mobile** de ~1-2 días enfocado en:
  1. Touch targets globales (Input/Button shadcn → 44px min)
  2. Tabla aceptación → cards en mobile
  3. Login overflow del wordmark + features visibles desde md
  4. Body text floor 14px en mobile

**No es necesario un mobile-first redesign**: la arquitectura responsive es sólida. Son fixes localizados, no reescritura.

**Sprint sugerido** (post-piloto Ballesteros, no prioridad):
- F-1: shadcn input/button size variant `mobile` (h-11) — 2h
- F-2: aceptación tabla → card view <md — 4h
- F-3: login mobile typography + spacing fix — 1h
- F-4: preset selector grid mobile fix — 2h
- F-5: search modal mobile — 3h
- F-6: features list breakpoint md → lg downgrade en login — 30min
- **Total estimado**: ~13 horas dev (1.5 días)

---

## Notas metodológicas

- **No se ejecutó Lighthouse** (instrucción explícita).
- **No se aplicaron fixes** (instrucción explícita).
- Score asignado por evaluación experta + reglas Tailwind verificables en código + un screenshot mobile vivo.
- Las páginas protegidas no se pudieron renderizar autenticadas; el código fuente (clases Tailwind + breakpoints declarados) es la fuente de evidencia para esos casos. Cualquier divergencia entre código y runtime se manifestaría solo después de un fix de backend que permita login en prod.
- Backend de prod debe arreglarse antes de hacer captura visual confirmatoria (`crece.mdconsultoria-ti.org` con CORS + cert válido, o reactivar el cloudflare tunnel `parks-fell-bikini-logos.trycloudflare.com`).
