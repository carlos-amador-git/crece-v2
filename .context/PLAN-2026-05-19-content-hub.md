# PLAN · Content Hub CRECE v2 · 2026-05-19 · v2 (post cross-audit Gemini) · APROBADO

**Status:** ✅ APROBADO POR CEO 2026-05-19 post cross-audit Gemini.
**Origen:** CEO 2026-05-19 OBS-3 + retomar post merge PR #50. Petición: "/plan para esto" vía /orchestrator.
**Clasificación Loki Mode:** ESTRATÉGICA (arquitectura IA cross-módulo · afecta UX cliente · alto riesgo regresión).
**Nivel proyecto:** CRECE v2 = Nivel 2 (gobierno electoral).
**Modo ejecución:** Single Session + Sequential Thinking (7 pasos) + Cross-audit Gemini integrado.

**Aclaración CEO 2026-05-19:** "hoy más tarde" se reinterpreta como **después del piloto §9.8** (concern Gemini F0 absorbido). Ninguna fase se ejecuta antes del 2026-05-20 piloto.

## Cambios v1 → v2 (post cross-audit Gemini)

Gemini emitió `approve_with_changes` con 2 blocking concerns + 5 observations. Cambios integrados:

| Concern Gemini | Cambio v2 |
|---|---|
| F0 rompe code freeze pre-piloto (severity high) | **F0 se pospone a post-piloto Semana 1.** El valor de hoy era cosmético; el riesgo de desorientar a Misael en la demo de mañana es real. CEO autorización "hoy más tarde" se reinterpreta como "después del piloto". |
| F1 asume Storybook configurado pero no existe (severity medium) | **F1 reemplaza Storybook por ruta dev oculta `/dashboard/dev/unified-card`** (protegida por role check admin). Mismo objetivo de aprobación visual CEO sin overhead de instalar Storybook desde cero con App Router + Tailwind. |
| F1-F3 sin mención explícita de data adapters | **F1 spec incluye hooks adapters** (`useSocialPostsUnified`, `useTopPostsUnified`, etc) que mapean shapes backend al `PostUnified` canónico antes de F4. |
| F1 sin mecanismos para mitigar disonancia semántica | **F1 requisito duro:** UnifiedPostCard incluye tooltips shadcn explicando likes_publicos (snapshot público Apify) vs reactors_capturados (RADAR Hugo) + badge data_source visible. |
| Missing: caché/revalidación | **Sección nueva en F1:** estrategia React Query (`staleTime`, `gcTime`, `refetchOnWindowFocus`) explícita por hook. |
| Missing: skeleton states / CLS | **F1 entregable:** UnifiedPostCardSkeleton con dimensiones idénticas → diff CLS <0.05. |
| Missing: empty states | **F1 entregable:** tres empty states (sin posts, sin reactors, sin polaridad). |

## Problema real (no síntoma)

El sidebar tiene 4 entradas que muestran posts (Monitoreo, Comentarios, Top Posts, Fans y Perfiles), cada una con UI/hooks/filtros distintos. **Fragmentación IA + disonancia semántica:** A/B/C usan `social_posts.likes` (snapshot público Apify) y D usa `watched_like_events` (reactors individuales RADAR). De ahí OBS-1 (Panini 2.8K vs 1.3K) y OBS-2 (cero reactions abril).

**Objetivo Content Hub:** unificar el lenguaje de "post" en toda la app con campos canónicos visibles y fuente de verdad documentada. NO es solo agrupar entradas en una sub-carpeta del sidebar — eso es cosmético.

## Sub-decisiones cerradas

| # | Decisión | Razón |
|---|---|---|
| D-1 | Plan ejecutable HOY: solo F0 (cosmético, 30 min). El refactor real es post-piloto. | "Calidad > Tiempo" pero no romper pre-piloto §9.8. |
| D-2 | F0 NO incluye Fans y Perfiles en el nuevo grupo Contenido. Queda en Indice Aceptacion donde Misael lo memorizó hoy. | Preservar mental model que cliente piloto usará mañana. Mover sólo con feedback empírico post-piloto. |
| D-3 | Visión a 4-6 semanas: Posts Workspace unificado (`/dashboard/contenido`) con endpoint backend `/api/v1/posts/unified`. NO se ejecuta en este plan, queda como F4 backlog. | Magnitud ~16-24h backend + frontend + redirects. Justifica decisión arquitectural separada. |
| D-4 | Cross-audit Gemini ANTES de ejecutar F0. | Patrón dual-AI para decisiones estratégicas IA. |

## Fases

### F0 · Agrupar 3 entradas en sidebar grupo "Contenido" (~~HOY~~ → Post-piloto Semana 1 · 30-45 min)

**Scope:**
- Crear `group("contenido", "Contenido", FileText, [...])` en `frontend/src/components/layout/sidebar.tsx`.
- Mover dentro del grupo: `leaf(/dashboard/social, "Monitoreo")` + `leaf(/dashboard/social/comentarios, "Comentarios")` + `leaf(/dashboard/content/top, "Top Posts")`.
- **NO mover Fans y Perfiles** (D-2 · queda en Indice Aceptacion).
- Auto-expandir el grupo "Contenido" si pathname inicia con `/dashboard/social` o `/dashboard/content/top` (mitigación R-0.1).

**Cambios:**
- 1 archivo: `sidebar.tsx` (mover 3 leafs dentro de un nuevo group).
- 0 archivos de rutas, 0 hooks, 0 componentes.

**Validación obligatoria:**
- TS check verde.
- Playwright: login Saymi → sidebar muestra grupo "Contenido" expandido (porque /dashboard es default) → click cada sub-item → cada uno carga sin 5xx ni "Dirigente no encontrado".

**Deploy:**
- Branch nueva desde main (NO desde feature antigua, lección de hoy).
- PR + CI smoke + Vercel preview.
- Merge a main.
- **`cd frontend && vercel --prod --yes`** (NO confiar en auto-deploy GitHub, sirve otro proyecto Vercel · lección de hoy).
- Validar prod con Playwright.

**Criterio aceptación F0:**
- [ ] Sidebar muestra grupo "Contenido" con 3 sub-items.
- [ ] Indice Aceptacion sigue con 4 sub-items (incluye Fans y Perfiles).
- [ ] Cada sub-item carga su página sin 5xx ni 4xx.
- [ ] Playwright pasa contra `frontend-zeta-sepia-46.vercel.app`.

**Riesgos:**
| ID | Riesgo | Mitigación |
|---|---|---|
| R-0.1 | Grupo colapsado por default oculta entradas | Auto-expandir si pathname matchea sub-rutas |
| R-0.2 | Usuario VIEWER (Saymi) podría no ver el grupo si tiene viewerHide | Verificar el `viewerHide` actual del grupo Social no se hereda · sino no aplica |

**Tiempo:** 30-45 min incluyendo PR + deploy + Playwright.
**Reversible:** sí, en <5 min revirtiendo el commit del sidebar.

---

### F1 · UnifiedPostCard component + ruta dev oculta (Post-piloto · Semana 1-2 · 3-4h)

**Scope:**
- Crear `frontend/src/components/posts/UnifiedPostCard.tsx`.
- Props canónicos: `post: PostUnified`, `variant: "feed" | "ranking" | "compact"`, `onClick?`.
- Type `PostUnified` con campos:
  - `id`, `published_at`, `platform`, `content`, `url`
  - `likes_publicos` (snapshot Apify)
  - `reactors_capturados` (count `watched_like_events`)
  - `cobertura_pct` (calc)
  - `comments_total`, `comments_classified_pct`
  - `polaridad_avg`, `polaridad_label`
  - `data_source` (`apify` | `radar` | `manual`)
- **Tooltips shadcn explícitos sobre disonancia semántica** (concern Gemini):
  - `likes_publicos`: tooltip "Snapshot público FB · captura del momento del scrape · puede haber cambiado"
  - `reactors_capturados`: tooltip "Reactors individuales capturados por RADAR · puede ser menor que likes públicos por cobertura del scraper"
  - `data_source` badge: tooltip explicando qué garantiza cada fuente
- `UnifiedPostCardSkeleton` con dimensiones idénticas → diff CLS <0.05 (concern Gemini).
- 3 empty states: sin posts, sin reactors, sin polaridad clasificada (concern Gemini).

**Hooks adapters (concern Gemini):**
- `frontend/src/components/posts/adapters.ts`:
  - `adaptSocialPost(rawFromUseSocialPosts) → PostUnified`
  - `adaptTopPost(rawFromUseTopPosts) → PostUnified`
  - `adaptWatchedTopPost(rawFromAceptacion) → PostUnified`
- Tests unitarios de los 3 adapters con fixtures reales BD.

**Estrategia caché React Query (concern Gemini):**
- `staleTime: 60_000` para feeds (refresca al minuto).
- `gcTime: 300_000` (cache 5 min).
- `refetchOnWindowFocus: false` excepto en /dashboard/dev/unified-card (donde sí, para iteración rápida).
- Documentar en `frontend/src/lib/api/hooks/CACHE_POLICY.md` (nuevo).

**Ruta dev oculta** (reemplaza Storybook · concern Gemini):
- `frontend/src/app/dashboard/dev/unified-card/page.tsx`
- Protegida por role check `admin` (si no admin → 404 visible).
- Renderiza 6 ejemplos lado a lado:
  - feed variant · post Apify-only · post Apify+RADAR · post Apify+RADAR+NLP
  - ranking variant · idem
  - compact variant · idem
  - Skeleton states variants
  - Empty states variants
- CEO valida visualmente entrando a `/dashboard/dev/unified-card` con su login admin.

**Sin uso productivo todavía.** Solo el componente + adapters + tests + ruta dev.

**Criterio F1:**
- [ ] Componente con 3 variants funcionales.
- [ ] Hooks adapters con tests unitarios.
- [ ] Tooltips shadcn presentes para mitigar disonancia semántica.
- [ ] Skeleton + empty states render OK.
- [ ] TS check verde.
- [ ] CEO aprueba visual de `/dashboard/dev/unified-card` ANTES de F2.

**Tiempo:** 3-4h (subido de 2-3h por scope ampliado).

---

### F2 · Refactor /social/Monitoreo + /content/top a UnifiedPostCard (Post-piloto · Semana 2 · 3-4h)

**Scope:**
- Reemplazar `PostCard` en `/dashboard/social/page.tsx` por `UnifiedPostCard variant="feed"`.
- Reemplazar component de ranking en `/dashboard/content/top/page.tsx` por `UnifiedPostCard variant="ranking"`.
- Adapters en `useSocialPosts` y `useTopPosts` para mapear shape backend al `PostUnified`.

**Validación:**
- Playwright snapshot ANTES (capturar HTML/screenshots de las dos rutas con datos reales).
- Refactor.
- Playwright snapshot DESPUÉS · diff visual menor al 5% (typography/spacing OK, contenido idéntico).

**Criterio F2:**
- [ ] Feed muestra mismos datos que pre-refactor.
- [ ] Top Posts muestra mismo ranking, mismos números.
- [ ] Nuevos badges de `data_source` visibles.
- [ ] Sin regresiones en filtros existentes (search, platform, metric).

**Tiempo:** 3-4h.

---

### F3 · Refactor Fans y Perfiles TopPostsCards (Post-piloto · Semana 3 · 3-4h)

**Scope:**
- Reemplazar `TopPostsCards` interno de `WatchedProfilesTab` por `UnifiedPostCard variant="compact"` para los 3 ganadores + 3 negativos.
- Cuestionar (con feedback piloto en mano): ¿mover Fans y Perfiles al grupo Contenido del sidebar?
  - Si CEO + cliente dicen "sí, encaja mejor ahí" → mover.
  - Si dicen "no, lo queremos en Aceptacion" → dejarlo.

**Criterio F3:**
- [ ] TopPostsCards muestran mismos posts ganadores/negativos.
- [ ] Polaridad y quotes intactos.
- [ ] Decisión sobre move-or-stay documentada en DECISIONS.md.

**Tiempo:** 3-4h.

---

### F4 · Posts Workspace unificado (Backlog · 4-6 semanas · 16-24h)

**Scope (alto nivel · no detalle de implementación todavía):**
- Backend: nuevo endpoint `GET /api/v1/posts/unified` con filtros (dirigente, plataforma, rango fecha, sentiment, data_source, métrica orden) + paginación obligatoria.
- Frontend: nueva ruta `/dashboard/contenido` con UI tipo "explorador" (filtros laterales + grid central usando UnifiedPostCard).
- Migrar las 4 rutas viejas a redirects 308 hacia `/dashboard/contenido?view=feed|comentarios|top|fans`.
- Comentarios sigue siendo página separada (muestra comments, no posts), pero linkea a UnifiedPostCard en modal.

**Gate de entrada F4:** F1-F3 cerrados + feedback piloto de ≥2 ciclos demuestra que la UX actual aún confunde al cliente. Si piloto + F0-F3 son suficientes → F4 queda como aspiracional, no se ejecuta.

**Tiempo:** 16-24h estimadas. Plan dedicado separado cuando se aterrice.

---

## Gating entre fases

```
F0 (hoy) ──gate piloto OK──→ F1 (sem 1) ──gate CEO aprueba storybook──→ F2 (sem 2)
F2 ──gate prod estable 3d──→ F3 (sem 3) ──gate feedback piloto──→ F4 (backlog)
```

**NO avanzar a siguiente fase sin gate cerrado.** Si una fase muestra regresión → revertir + revisar plan.

## Plan de validación (Playwright)

Obligatorio en F0, F2, F3, F4. F1 solo Storybook + tests unitarios.

Script template (referencia hoy validado contra prod):
```js
1. login pineda@crece.mx / demo2026!
2. navigate a la ruta refactoreada
3. assert: sin 5xx en network, sin pageerror, contenido esperado en DOM
4. screenshot fullPage
5. compare contra baseline pre-refactor
```

## Plan de deploy (lección de hoy)

**Two-project Vercel setup:**
- `crece-v2` (auto-deploy desde GitHub main) — NO sirve la URL del cliente.
- `frontend` (manual `vercel --prod`) — SÍ sirve `frontend-zeta-sepia-46.vercel.app`.

**Flujo correcto post-merge:**
```bash
cd frontend
vercel --prod --yes
# wait deploy ~1min
# validar Playwright contra https://frontend-zeta-sepia-46.vercel.app
```

NO confiar en GitHub status `main: success` (es de proyecto crece-v2).

## Recursos

- **F0-F3:** Linda (yo). Sin Hugo, sin backend.
- **F4:** Linda + decisión CEO + cambio backend interno a CRECE (no requiere RADAR).
- **Cross-audit:** Gemini en cada fase (`~/.claude/bin/gemini-clean` o equivalente).

## Total esfuerzo (v2)

| Tramo | Horas | Cuándo |
|---|---|---|
| F0 (sidebar agrupado) | 0.5-0.75h | Post-piloto Semana 1 (no hoy · concern Gemini) |
| F1 (UnifiedPostCard + adapters + ruta dev) | 3-4h | Post-piloto Semana 1-2 |
| F2 (refactor Feed + Top) | 3-4h | Sem 2-3 post-piloto |
| F3 (refactor Fans y Perfiles) | 3-4h | Sem 3-4 post-piloto |
| F0-F3 total | **9.5-12.75h** escalonadas en ~4 semanas | |
| F4 (Posts Workspace + backend nuevo) | 16-24h | Backlog 4-6 semanas |

## Anti-patrones · veredicto Gemini

| Anti-patrón | Status |
|---|---|
| Big Bang Rewrite | EVITADO (refactor progresivo · strangler pattern en UI · gates estrictos) |
| Deploys falsos positivos | EVITADO (aislamiento manual de Vercel `frontend` project) |
| Cambios cosméticos pre-demo | DETECTADO en plan v1 · CORREGIDO en v2 (F0 pospuesto) |

## Pendiente CEO antes de ejecutar cualquier fase

1. Aprobar plan v2 o pedir ajustes adicionales.
2. Confirmar que **F0 se pospone a post-piloto** (cambio v1 → v2 por concern Gemini).
3. Confirmar D-2 (Fans y Perfiles NO se mueve · sigue en Indice Aceptacion).
4. Cuando arranque F1 post-piloto: luz verde para crear ruta dev oculta + invitación al CEO para validar visual en `/dashboard/dev/unified-card`.

## Trazabilidad

- v1: plan original (5 fases, F0 hoy).
- v2: post cross-audit Gemini (2 blocking concerns + 5 observations integrados).
- Cross-audit raw: `/tmp/gemini_plan_audit_response.txt` (no committeado).
