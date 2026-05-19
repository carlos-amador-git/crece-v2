# PLAN · 2026-05-14 · War Room Personal — competidores light + nav redesign

## Contexto

CEO objetó las propuestas A/B/C iniciales (todas centradas en "dónde guardar la tabla")
y propuso un cambio de modelo conceptual: la plataforma es **del dirigente** ("War Room Personal"),
no un dashboard de admin. Los competidores son **referentes ligeros** que el cliente declara
para benchmark contextual — no clientes paga ni dirigentes con pipeline completo.

Gemini validó la dirección comercial. Cross-audit Claude detectó gaps técnicos
(curvas no-cruzables en Aceptación NLP, vista admin omitida, componente snapshot card vivo).
Las 5 decisiones de diseño quedaron cerradas:

1. ✅ Dropdown en Aceptación compara **solo métricas externas** (followers/engagement), no NLP.
2. ✅ Vista de ranking cross-dirigente **solo para roles admin** (`/dashboard/admin/ranking`).
3. ✅ Competidores los **carga MD desde admin** (no self-serve del dirigente).
4. ✅ Pepe Monroy se queda como dirigente (cliente PAZ paga, no es competidor de nadie).
5. ✅ Sprint C arranca en paralelo a este plan — ya cerrado.

---

## Modelo final

| Concepto | Tabla canónica | Campos clave | Pipeline |
|----------|---------------|--------------|----------|
| **Dirigente (cliente)** | `dirigentes` | `id, full_name, partido, estado, org_id, competidor_directo_ids[]` | Full: scraping completo + NLP + plan IA + diagnóstico + IPD |
| **Competidor (referente)** | `competitor_profiles` | `id, org_id, dirigente_objetivo_id, display_name, partido, platform, profile_external_id, profile_handle, verified` | **Light**: solo métricas externas mensuales (followers, post count, engagement promedio) |
| **Deprecada** | `competidores` (legacy) + `competidor_social_profiles` | — | Sin pipeline, queda solo por compat hasta el sprint final |

### Por qué `competitor_profiles` (la creada hoy) gana
- Ya tiene `dirigente_objetivo_id` (modela "competidor de quién").
- Ya tiene `org_id` para multi-tenant scope.
- Ya tiene `platform + profile_external_id + profile_handle` (suficiente para scraping).
- Las 2 filas actuales (Ivette + Susana) están bien estructuradas.
- Tabla `competitor_monthly` ya existe (migration cp2) para guardar métricas mensuales agregadas.

### Por qué `competidores` (legacy) se deprecia
- 7 filas con datos heterogéneos (Batres, Brugada, Taboada de CDMX para Saymi Oaxaca — cross-estado absurdo).
- `competidor_social_profiles` solo tiene 5 filas con handles parciales.
- Ningún scraper la alimenta hoy.
- Componente `competitor-snapshot-card.tsx` la lee y genera el bug de la imagen 3.

---

## Cambios de navegación

### Sidebar — antes vs después

**Antes (actual):**
```
PRINCIPAL
├ Overview
├ Dirigentes               ← lista global
├ Diagnóstico
├ Diferenciadores
├ FODA
├ Social
│  ├ Monitoreo
│  ├ Comentarios
│  ├ Clima Político
│  └ Benchmarks            ← ❌ huérfano (dropdown vacío, cross-estado)
├ Índice Aceptación
│  ├ Overview
│  ├ Por dirigente
│  └ Fantasmas
└ ...
```

**Después (war room personal):**
```
PRINCIPAL
├ Overview
├ Dirigentes               ← directorio del dirigente activo: SUS perfiles + SUS competidores declarados
├ Diagnóstico
├ Diferenciadores
├ FODA
├ Social
│  ├ Monitoreo
│  ├ Comentarios
│  └ Clima Político
│                          ← Benchmarks ELIMINADO
├ Índice Aceptación
│  ├ Overview
│  ├ Por dirigente         ← + dropdown lateral "Comparar con: [competidor]"
│  └ Fantasmas
└ ...

(solo rol admin):
ADMINISTRACIÓN
├ Ranking cross-dirigente  ← NUEVA · valor para MD/MC central
└ ...
```

### Vista "Por dirigente" del Índice de Aceptación

Agregar dropdown lateral con `competitor_profiles` filtrado por `dirigente_objetivo_id = current_dirigente_id`:

```
┌─────────────────────────────────────────────────────────┐
│ Saymi Pineda Velasco                  Comparar con:  ▾  │
│ Índice de Aceptación 11.3%            [Ivette · 25K]    │
│ ┌────────────────────────────┐        [Susana · 89K]    │
│ │ [línea Saymi]              │        ───              │
│ │                            │       (solo metricas      │
│ │      [si competidor sel.]  │        externas: followers│
│ │      [línea competidor]    │        + engagement)      │
│ └────────────────────────────┘                          │
└─────────────────────────────────────────────────────────┘
```

NLP/aceptación del competidor **no se muestra** (no se calcula). Las curvas que cruzan son
followers/engagement, NO % aceptación.

### Vista "Dirigentes" reusada como Directorio Personal

Lo que ve el dirigente individual:
- Sus perfiles sociales (los 5 platforms con sus handles)
- Sus competidores declarados (cards livianas: foto, nombre, partido, métricas externas)
- Botón "Agregar competidor" → SOLO visible para admins/analystas, abre modal de creación.

Lo que ve el admin:
- Vista actual de "Dirigentes" como lista global, sin cambios.
- Nueva sección `Administración → Ranking cross-dirigente` para benchmark transversal.

---

## Sprints estructurados

### Sprint W0 · Verificación pre-fix (15 min · BLOQUEANTE)

**Objetivo:** confirmar premisas antes de tocar código.

1. `competitor_profiles.dirigente_objetivo_id` ya tiene FK a `dirigentes.id`? → `\d competitor_profiles`.
2. `competitor_monthly` schema esperado (followers_total, posts_count, engagement_avg)? → `\d competitor_monthly`.
3. ¿Hay otro componente además de `competitor-snapshot-card.tsx` que lea `competidores` (legacy)? → grep.
4. ¿Rol `admin` en `Role` enum tiene check `.role == "admin"` o `Role.ADMIN`? → verificar en `core/security.py`.

**Criterio done:** 4 respuestas confirmadas.

---

### Sprint W1 · Backend competidores (3h)

**Objetivo:** endpoints para listar/crear/editar/borrar competidores del dirigente, scoped por org.

**Archivos:**
- `backend/app/api/v1/endpoints/competitors.py` (ya existe parcial, revisar y completar)
- `backend/app/api/v1/__init__.py` (registrar router si no está)

**Cambios:**

1. `GET /api/v1/dirigentes/{id}/competidores` o `GET /competitor-profiles?dirigente_objetivo_id=X`:
   - Aplica `_assert_dirigente_access(db, user, dirigente_id)` (mismo helper del Sprint 1 anterior).
   - SELECT desde `competitor_profiles` con LEFT JOIN a `competitor_monthly` para últimos 3 meses.
   - Devuelve display_name, partido, platform, profile_handle, verified, followers_total, posts_count, engagement_avg.

2. `POST /competitor-profiles` (solo admin/analyst):
   - Validar `dirigente_objetivo_id` pertenece al org del user.
   - Crear fila con verified=false por default.

3. `PATCH /competitor-profiles/{id}` (solo admin/analyst):
   - Editar display_name, partido, cargo, profile_handle, tags.
   - Validar org via `dirigente_objetivo_id`.

4. `DELETE /competitor-profiles/{id}` (solo admin/analyst):
   - Soft delete (is_active=false).

5. `GET /admin/competidor-rankings` (rol admin solo):
   - Endpoint nuevo. Cross-org ranking de competidores agregados.
   - Devuelve lista paginada de todos los `competitor_profiles` con métricas, sin filtro de org.

**Test:**
```bash
TOK_PINEDA=$(login pineda@crece.mx)
curl -H "Bearer $TOK_PINEDA" "$API/dirigentes/3/competidores"
# expect: 200 con 2 items (Ivette + Susana)

TOK_CRA=$(login cravioto@crece.mx)
curl -H "Bearer $TOK_CRA" "$API/dirigentes/3/competidores"
# expect: 403 (Cravioto org 3, dirigente_id=3 org 2)

TOK_ADMIN=$(login admin@consultoriamd.com)
curl -H "Bearer $TOK_ADMIN" "$API/admin/competidor-rankings"
# expect: 200 con todos los competidores cross-org

curl -H "Bearer $TOK_PINEDA" "$API/admin/competidor-rankings"
# expect: 403 (rol VIEWER)
```

**Dependencias:** Sprint W0.

---

### Sprint W2 · Scraper light competidores (4h · gated por saldo Apify)

**Objetivo:** poblar `competitor_monthly` con métricas externas mensuales.

**Archivos:**
- `backend/scripts/scrape_competitors_light.py` (nuevo)
- Reusar `backend/app/services/apify_pool.py` para rotar tokens.

**Comportamiento:**
1. Para cada `competitor_profile` activo, llamar actor Apify mínimo (`apify/facebook-pages-scraper` o `apify/instagram-profile-scraper`) que devuelve **solo metadata pública del perfil** (followers, post count, engagement promedio últimos 30 días).
2. NO entra a comments, NO computa NLP, NO genera plan/diagnóstico.
3. UPSERT en `competitor_monthly (competitor_profile_id, year_month, followers_total, posts_count, engagement_avg)`.
4. Cron mensual (Celery beat) — costo estimado: ~$0.05 por competidor/mes.

**Test:** smoke con la cuenta Apify que tenga saldo (~$0.14 actual). Si vacío, deferir hasta 2026-06-13.

**Dependencias:** Sprint W1 + saldo Apify.

**NOTA:** este sprint puede deferirse. Las 2 filas Ivette+Susana tienen handles pero sin métricas mensuales hoy. Mientras tanto, UI muestra "Sin datos mensuales" como empty state.

---

### Sprint W3 · Frontend dropdown Aceptación (2h)

**Objetivo:** integrar el selector "Comparar con" en `/dashboard/aceptacion/[dirigente_id]`.

**Archivos:**
- `frontend/src/app/dashboard/aceptacion/[dirigente_id]/page.tsx`
- `frontend/src/lib/api/hooks/use-competitors.ts` (ya existe, verificar contrato del endpoint)
- Nuevo `frontend/src/components/aceptacion/competitor-comparison-chart.tsx`

**Cambios:**

1. Llamar `GET /dirigentes/{id}/competidores` al cargar la vista.
2. Render del dropdown lateral con avatares + nombres de competidores.
3. Al seleccionar uno, query `competitor_monthly` últimos 6 meses y graficar contra los followers/engagement del dirigente en la misma gráfica (Recharts líneas).
4. Empty state si no hay competidores declarados: "Aún no se han declarado competidores. Contacta a tu administrador."

**Test:** smoke Playwright. Login Pineda → vista Aceptación de Saymi → dropdown muestra Ivette y Susana. Click Ivette → curva se grafica.

**Dependencias:** Sprint W1.

---

### Sprint W4 · Eliminar `/dashboard/benchmark` + reorganizar sidebar (1.5h)

**Objetivo:** limpiar la página rota del benchmark global y mover el item del sidebar.

**Archivos:**
- Eliminar `frontend/src/app/dashboard/benchmark/page.tsx`
- Eliminar `frontend/src/lib/api/hooks/use-benchmark.ts`
- `frontend/src/components/layout/sidebar.tsx` (quitar item Benchmarks del menu Social)
- Eliminar endpoint backend `GET /benchmark/ranking` si no se usa en otro lado (verificar primero)

**Cambios sidebar:** quitar `<NavItem>Benchmarks` bajo Social. El item ya no existe en navegación.

**Riesgo:** si algún componente sigue importando `useBenchmark`, falla compile. Grep antes de borrar.

**Test:** `tsc --noEmit` limpio + smoke browser: navegar /dashboard/benchmark devuelve 404 esperado.

**Dependencias:** Sprint W3 (ya hay path nuevo en Aceptación).

---

### Sprint W5 · Vista admin /dashboard/admin/ranking (2h)

**Objetivo:** nueva vista para roles admin/analyst con ranking cross-dirigente.

**Archivos:**
- Nuevo `frontend/src/app/dashboard/admin/ranking/page.tsx`
- `frontend/src/components/layout/sidebar.tsx` (agregar sección "Administración" condicional a rol)
- Hook nuevo `frontend/src/lib/api/hooks/use-admin-rankings.ts`

**Cambios:**

1. Página lista todos los dirigentes con métricas (followers, posts, engagement, IPD) + sus competidores asociados.
2. Filtros: por estado, partido, org.
3. Visible solo si `user.role IN ('admin', 'analyst')`. RoleChecker en backend + filtro en sidebar.

**Test:** Login admin → ve sección Administración → ranking cross-org visible. Login VIEWER → sección no aparece, navegación directa retorna 403.

**Dependencias:** Sprint W1 (endpoint admin/competidor-rankings).

---

### Sprint W6 · Eliminar componente snapshot card legacy (1h)

**Objetivo:** matar el bug de la imagen 3 (Saymi vs Taboada cross-estado).

**Archivos:**
- `frontend/src/components/dashboard/competitor-snapshot-card.tsx`
- Encontrar dónde se importa y reemplazar con el nuevo flujo (probable: vista de dirigente).

**Cambios:**

1. Grep `competitor-snapshot-card` para encontrar callers.
2. Si la vista necesita un widget similar, reusar el nuevo `competitor-comparison-chart` del Sprint W3.
3. Si era solo "decoración" sin valor real, eliminar el card sin reemplazar.

**Test:** smoke browser de la vista que lo usaba. NO más "Santiago Taboada" para Saymi.

**Dependencias:** Sprint W3.

---

### Sprint W7 · Deprecar tabla `competidores` legacy (1.5h · ALTAMENTE OPCIONAL)

**Objetivo:** quitar la tabla legacy si nadie la lee.

**Archivos:**
- `backend/migrations/versions/sc2_drop_competidores_legacy.py` (nuevo)
- Verificar via grep que **ningún** endpoint / script / modelo activo la lee.

**Cambios:**
1. Pre-flight: backup de las 7 filas a `.context/legacy/competidores_backup_2026-05-14.json`.
2. Migration: drop FK `competidor_social_profiles.competidor_id` → drop `competidor_social_profiles` → drop `competidores`.
3. Eliminar `backend/app/models/competidor.py` si existe.

**Riesgo:** si un endpoint admin aún la lee (ej. `/benchmark/competidores`), rompemos. Sprint W7 es el ÚLTIMO en orden — solo después de Sprints W1-W6 y validar que nada usa.

**Dependencias:** todos los anteriores. Plus: confirmar CEO no quiere mantener los datos legacy.

---

## Test plan consolidado E2E

| Test | Setup | Action | Expected |
|------|-------|--------|----------|
| Competidores scope | Pineda (org 2) | GET `/dirigentes/3/competidores` | 200 con 2 items (Ivette, Susana) |
| Cross-org block | Cravioto (org 3) | GET `/dirigentes/3/competidores` | 403 |
| Admin all | admin | GET `/admin/competidor-rankings` | 200 con todos los competidores |
| Viewer admin block | Pineda | GET `/admin/competidor-rankings` | 403 |
| Dropdown render | Pineda → Aceptación | Click dropdown | Lista Ivette + Susana |
| Curva cruzada | Pineda → seleccionar Ivette | Render | Recharts con 2 líneas (Saymi followers vs Ivette followers) |
| Benchmark 404 | Cualquier user | GET `/dashboard/benchmark` | 404 (página eliminada) |
| Sidebar limpio | Cualquier user | Inspeccionar nav | No hay item "Benchmarks" bajo Social |
| Admin nav | admin | Inspeccionar nav | Aparece sección "Administración → Ranking" |
| Viewer nav | Pineda | Inspeccionar nav | NO aparece sección "Administración" |
| Snapshot card legacy | Pineda → vista que tenía el card | Inspeccionar | NO aparece "Santiago Taboada" |

---

## Out of scope (NO hacer)

- Promoción competidor → dirigente: dejar este flujo para sprint posterior (decisión D del plan anterior, deferida).
- Self-serve para que dirigente declare sus competidores: el CEO confirmó "MD los carga". Mantener.
- NLP sobre comments de competidores: por diseño NO. Si el cliente lo pide explícitamente, se promueve.
- Reescribir scrapers FB/IG/TW/TT/YT para captar handle: ya hecho parcialmente en Sprint C (apify_refresh_all + playwright_ig_comments). Los demás se actualizan lazily cuando se toquen.
- Migración masiva de comments históricos para llenar `commenter_handle`: deferido a renovación Apify 2026-06-13 (decisión cerrada con CEO esta sesión).

---

## Orden recomendado de ejecución

```
W0 (verify, 15m)
  ↓
W1 (backend, 3h)
  ↓
W3 (dropdown Aceptación, 2h)   W5 (admin ranking, 2h)
  ↓                               ↓
W4 (eliminar /benchmark, 1.5h)
  ↓
W6 (snapshot card, 1h)
  ↓
[opcional] W7 (drop competidores legacy, 1.5h)
[gated por $] W2 (scraper light, 4h)
```

**Tiempo crítico hasta UI funcional (W0+W1+W3+W4+W5+W6):** 10h. Distribuible en 2 sesiones.

**W2 (scraper light)** queda en cola post-renovación Apify (2026-06-13) o si el CEO consigue saldo nuevo.

---

## Decisiones de diseño que registrar en `.context/DECISIONS.md` al cierre

### D-MODEL-WAR-ROOM-1 · Competidores como referentes light
Distinción canónica: `dirigentes` (clientes paga + full pipeline) vs `competitor_profiles`
(referentes light, sin NLP/plan/diagnóstico). `competidores` legacy se deprecia.

### D-NAV-PERSONAL-PLATFORM-1 · Plataforma personal del dirigente, no admin
Sidebar redesign: quitar "Benchmarks" de Social. Vista admin con ranking cross-dirigente
en `/dashboard/admin/ranking` solo visible a roles admin/analyst.

### D-COMPARE-EXTERNAL-METRICS-ONLY-1 · Comparativa externa, no NLP
El dropdown de comparación en Índice de Aceptación compara solo métricas externas
(followers, engagement). NO % aceptación NLP del competidor (no se computa por diseño).
