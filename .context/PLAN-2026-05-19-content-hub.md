# PLAN · Content Hub CRECE v2 · 2026-05-19 · v3 (status post-ejecución hoy)

**Status:** ✅ APROBADO POR CEO (v2 + 8 decisiones del plan general).
**Origen:** CEO 2026-05-19 OBS-3 + retomar post merge PR #50. /plan via /orchestrator.
**Clasificación Loki Mode:** ESTRATÉGICA.
**Nivel proyecto:** CRECE v2 = Nivel 2 (gobierno electoral).
**Modo ejecución:** Single Session + Sequential Thinking (7 pasos · v1) + Cross-audit Gemini integrado.

**Actualización v2 → v3 (2026-05-19 noche):**

Tras sesión maratón post-piloto autorizada por CEO + 8 decisiones aprobadas (Linda↔Gemini convergencia 7/8), las fases F0-F3 cambiaron de status. Solo F4 queda como pendiente significativo.

## Status actual (post sesión maratón 2026-05-19)

| Fase | Status | Comentario |
|---|---|---|
| **F0** Sidebar group "Contenido" | ⏸️ **OBSOLETO** | D13.5=A aprobada (single ítem "Contenido" si F4 se hace · no agrupar 3 sub-items). F0 cosmético se vuelve innecesario porque F4 lo absorbe directamente. **No se ejecuta.** |
| **F1** UnifiedPostCard + adapters + ruta dev oculta | ✅ **COMPLETO** | Commit `4b6e6acb` · 3 variants + Skeleton + 3 empty states + tooltips disonancia + adapters · ruta `/dashboard/dev/unified-card` admin-only |
| **F2** Refactor /social/Monitoreo + /content/top | 🟡 **PARCIAL** | Monitoreo migrado a UnifiedPostCard ✓ · Top Posts mantiene fixes P0-P2 específicos (consolidación viene en F4) |
| **F3** Refactor Fans y Perfiles TopPostsCards | ⏸️ **DECISIÓN SCOPE** | TopPostsCards mantiene quotes modal único (feature valioso). UnifiedPostCard no aporta · F4 absorbe |
| **F4** Posts Workspace `/dashboard/contenido` | 📋 **PENDIENTE** | **Este es el sprint grande restante.** Detalle abajo. |

## F4 · Posts Workspace · sprint dedicado (16-24h)

**Objetivo final:** consolidar las 4 vistas que muestran posts en un solo Workspace unificado con vistas conmutables + redirects 308 de las rutas viejas.

### Decisiones aplicables (las 8 aprobadas)

| ID | Decisión | Aplicada en F4 |
|---|---|---|
| D13.1 | Estrategia: **C mixto** | F1-F3 ya ejecutados parcial · F4 = ahora el "según feedback piloto" |
| D13.2 | Ruta: **`/dashboard/contenido`** | Confirmado · path final |
| D13.3 | Backend: **endpoint unificado** `/api/v1/posts/unified?view=feed\|comentarios\|top\|fans` | Implementar |
| D13.4 | Comentarios: **tab interno con `?tab=`** | Deep-linking compartible |
| D13.5 | Sidebar: **single ítem "Contenido"** | Reemplazar 4 entradas actuales por 1 group nuevo |

### Scope técnico F4

#### Backend (~6-8h)

1. **Nuevo endpoint** `GET /api/v1/posts/unified` (puerto `social.py`):
   - Query params: `dirigente_id` (required), `view` (feed|comentarios|top|fans), `platform`, `date_from`, `date_to`, `sentiment_filter`, `data_source` (apify|radar|all), `page`, `per_page`
   - Response shape: paginado, items con `PostUnified` shape canónico (mismo que el componente frontend)
   - Logic por view:
     - `feed` → equivalente a `useSocialPosts` actual (posts del dirigente, recientes)
     - `comentarios` → join con `social_comments`, agrupado por post padre, exponer top quotes
     - `top` → equivalente a `useTopPosts` actual (ranking por engagement_rate)
     - `fans` → equivalente a watched_profiles activity (posts con reactors capturados RADAR)
   - Tests pytest: ~10-12 tests cubriendo cada view + filtros + paginación + auth
2. **Schema `PostUnifiedItem`** Pydantic en `app/schemas/posts.py` (nuevo · alinear con frontend `PostUnified` type)
3. **Endpoint admin opcional** `GET /api/v1/posts/unified/stats` para verificar shape antes de migración

#### Frontend (~6-8h)

1. **Nueva ruta** `frontend/src/app/dashboard/contenido/page.tsx`:
   - Layout: sidebar de filtros izquierda (Filter rail tipo shadcn) + grid central con UnifiedPostCard
   - Tabs internos con `?tab=feed|comentarios|top|fans` (deep-linking · D13.4)
   - Filtros globales: rango fecha, plataforma, dirigente (si admin), sentiment_filter, data_source
2. **Hook nuevo** `useUnifiedPosts(filters)` que consume `/api/v1/posts/unified`
3. **Sidebar update**:
   - Remover entradas: Monitoreo, Comentarios, Top Posts, Fans y Perfiles (4 entradas)
   - Agregar **single ítem "Contenido"** apuntando a `/dashboard/contenido`
4. **Redirects 308** desde rutas viejas:
   - `/dashboard/social` → `/dashboard/contenido?tab=feed`
   - `/dashboard/social/comentarios` → `/dashboard/contenido?tab=comentarios`
   - `/dashboard/content/top` → `/dashboard/contenido?tab=top`
   - `/dashboard/aceptacion/fans` → `/dashboard/contenido?tab=fans`
   - Implementación: Next.js `middleware.ts` o `next.config.js` redirects
5. **Mantener Fans y Perfiles en sidebar grupo `Indice Aceptacion`** como espejo opcional (decisión final del CEO durante ejecución según preview UX)

#### Tests (~2-3h)

1. Pytest backend: ~10-12 tests del endpoint unificado (mismo patrón `test_tono_discurso.py` y `test_watched_profiles_dashboard.py`)
2. Playwright E2E: validar las 4 vistas conmutables + redirects 308 + filtros + deep-linking

#### Documentación + migración (~1-2h)

1. Actualizar `BLOCKERS.md` resolviendo #13
2. `DECISIONS.md` D-CONTENT-HUB-EJECUTADO con detalle del rollback plan
3. Bitácora Obsidian: `obsidian-md/productos/gobierno/crece-v2/bitacora/YYYY-MM-DD-content-hub-cierre.md`
4. Rollback plan: si feedback cliente negativo en primera semana, revert sidebar + remover redirects (rutas viejas siguen funcionando si NO se las elimina del codebase)

### Gate de entrada F4

**Originalmente plan v2 decía:** "F1-F3 cerrados + feedback piloto de ≥2 ciclos demuestra que la UX actual aún confunde al cliente. Si piloto + F0-F3 son suficientes → F4 queda como aspiracional, no se ejecuta."

**Status hoy:**
- F1 ✓ · F2 parcial · F3 decisión scope
- Piloto ejecutado HOY (§9.8 día 30 · 2026-05-20)
- **Feedback piloto formal pendiente del CEO post-demo**

**Decisión CEO requerida ANTES de ejecutar F4:**
1. ¿Hay feedback piloto que justifica F4 ahora? (alternativa: diferir hasta que feedback empírico lo amerite)
2. Si SÍ → arrancar F4 con todo el scope detallado arriba (~16-24h)
3. Si NO → cerrar plan Content Hub con F1+F2 parcial entregado · F4 queda como deuda backlog 4-6 sem con plan aterrizado listo para ejecutar cuando se decida

### Tiempo estimado F4

| Tramo | Horas |
|---|---|
| Backend endpoint + tests | 6-8h |
| Frontend ruta + hook + sidebar + redirects | 6-8h |
| Tests E2E + docs + rollback plan | 3-4h |
| Cross-audit Gemini + ajustes | 1-2h |
| **Total F4** | **16-24h** |

Calendario: 1 sprint dedicado de ~3 días si se ejecuta linealmente, o ~1 semana escalonada.

### Riesgos F4

| ID | Riesgo | Mitigación |
|---|---|---|
| R-1 | Endpoint unificado se vuelve monolito difícil de mantener | Schema PostUnifiedItem estricto + view handlers separados internamente · cada view como función con tests independientes |
| R-2 | Redirects 308 rompen bookmarks externos de clientes piloto | Mantener rutas viejas funcionando primer mes (sin remover code) · solo agregar redirects nuevos · permite rollback fácil |
| R-3 | Cliente piloto pierde mental model si sidebar cambia | Migración split: agregar "Contenido" arriba, MANTENER 4 entradas viejas marcadas legacy primera semana, observar telemetría · si nadie usa las viejas → remover en sprint posterior |
| R-4 | Tab interno con `?tab=` rompe en mobile con hidratación Next.js | Validar con Playwright responsive xs/sm/md/xl |

### Cross-audit Gemini de F4

Recomendado ANTES de arrancar (per patrón aplicado en todos los sprints estratégicos hoy). Prompt similar a los anteriores con scope F4 específico.

## Reporting estado

| Fase | Resultado entregable |
|---|---|
| F0 | Obsoleto (D13.5 lo absorbe en F4) |
| F1 | ✅ UnifiedPostCard 3 variants + adapters + ruta dev `/dashboard/dev/unified-card` (commit `4b6e6acb`) |
| F2 | 🟡 /social/Monitoreo migrado · /content/top mantiene fixes P0-P2 |
| F3 | ⏸️ TopPostsCards mantiene quotes modal único · F4 absorbe |
| F4 | 📋 Pendiente decisión CEO sobre feedback piloto |

## Pendiente CEO antes de ejecutar F4

1. **Confirmar feedback piloto:** ¿la consolidación es prioridad ahora o se difiere?
2. Si arranca:
   - Autorizar 16-24h de trabajo
   - Confirmar cross-audit Gemini previo
   - Confirmar rollback plan (mantener rutas viejas primera semana)
3. Si se difiere:
   - Plan queda aterrizado listo para ejecutar cuando feedback piloto lo justifique

## Trazabilidad

- v1: plan original (5 fases, F0 hoy)
- v2: post cross-audit Gemini (2 blocking + 5 observations integrados)
- **v3 (HOY 2026-05-19 noche):** status post-ejecución hoy · F1 cerrado · F2 parcial · F3 decisión scope · F0 obsoleto por D13.5 · F4 detallado con scope específico
