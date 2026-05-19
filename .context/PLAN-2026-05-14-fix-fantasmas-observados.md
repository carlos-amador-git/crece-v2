# PLAN · 2026-05-14 · Fix tab "Perfiles Observados" (fantasmas)

**Origen:** captura tomada en sesión activa mostrando dirigente Saymi (#3, org_id=2) cuando el usuario logueado es César Cravioto Romero (CC, org distinto).

**Cadena de razonamiento:**
1. Recon manual de código (`page.tsx`, `watched_profiles.py`, `watched-profiles-tab.tsx`).
2. Plan generado por Gemini CLI vía `~/.claude/bin/gemini-clean` (output guardado en `/tmp/gemini-fantasmas-output.md`).
3. Cross-audit por Claude (esta sección).
4. Plan final consolidado (este archivo).

---

## A · Diagnóstico de severidad

| # | Problema | Severidad | Justificación |
|---|----------|-----------|---------------|
| 1 | **Multi-tenant data leak en GET `/watched-profiles/`** (sin `_check_org`) | 🔴 **CRÍTICO** | Broken Access Control. Cualquier user autenticado puede pedir `?dirigente_id=X` y leer watched de otro org. Aplica también a `GET /summary`, `GET /suggestions`, `GET /{id}/engagement`. |
| 2 | **`observedDirigenteId` hardcoded a `3`** (`page.tsx:84`) | 🟠 **ALTO** | Tab inutilizable para usuarios fuera del org de Saymi. Selector queda desincronizado del query. |
| 3 | **Sugerencias muestran solo `author_hash`** (SHA256 one-way) | 🟠 **ALTO** | Funcionalidad inoperante. Usuario no puede decidir si etiquetar/observar a `b83d165e…`. |
| 4 | **Label "REACTIONS DETECTADAS" (card) vs "LIKES" (columna)** | 🟡 **MEDIO** | Métrica engañosa. La card suma like+love+care+haha (17). La columna podría estar sumando lo mismo o solo likes — inconsistencia semántica. |
| 5 | **Filtros redundantes:** "Todos 13 · Cliente 13 · Manual 0 · Sugeridos 0" | 🟢 **BAJO** | Carga cognitiva. Subgrupos en 0 ocupan espacio. |
| 6 | **Columna TAGS muestra literal "sin tags"** | 🟢 **BAJO** | UX descuidada. Estado vacío debe ser sutil (guion `—` o vacío). |
| 7 | **Doble título "Perfiles Observados"** (tab + section header) | 🟢 **BAJO** | Polish. Redundancia visual. |
| 8 | **Subtítulo card mezcla puntuación**: "8 activos · 5 sin actividad" debajo de "13" | 🟢 **BAJO** | Polish. |

**Cross-audit Claude:** Gemini consolidó 7 y 8 dentro del grupo "filtros redundantes". Los separo para tracking explícito — son fixes independientes de 2 líneas cada uno.

---

## B · Decisiones estratégicas

### C. Default del Select de dirigente

**Recomendación Gemini:** Opción **B con fallback a A** — defaultar a `user.dirigente_id` si existe en `dirigentesList`; si no, fallback a `dirigentesList[0]`.

**Cross-audit Claude:** Antes de implementar verificar:
- ¿Existe `user.dirigente_id` en el modelo `User`? (sidebar muestra "Dirigente IPD 4.9/10" sugiriendo que sí, pero hay que confirmar en `backend/app/models/user.py`).
- Si no existe, fallback puro a `dirigentesList[0]?.dirigente_id`.
- Edge case: `dirigentesList` vacío (admin sin dirigentes asignados) → empty state explícito "Sin dirigentes accesibles", NO hardcoded id.

**Aceptado con verificación previa.**

### D. Sugerencias con `author_hash`

**Recomendación Gemini:** Opción **C — workflow "Investigar/Revelar"** bajo demanda. NO almacenar `commenter_id` plain (LFPDPPP).

**Cross-audit Claude:** **PROBLEMA TÉCNICO** — el hash es SHA256 one-way, **no se puede revertir con scraping puntual**. La resolución requiere uno de tres caminos:

1. **Re-scrapear posts del dirigente** y, para cada comment encontrado, computar `SHA256(platform:commenter_id:SALT)` y matchear contra el hash buscado. Costoso pero viable.
2. **Almacenar mapping `author_hash → commenter_id`** en una tabla separada (`comment_author_lookup`) con TTL corto (~24h) y opt-out por dirigente. Cae en zona gris LFPDPPP si no hay base legal.
3. **Cachear `commenter_handle` (no `commenter_id`)** en `social_comments` desde el momento del scrape. Handle público es PII menor — LFPDPPP permite tratamiento con base legal de "interés legítimo" si el dato es accesible públicamente y el tratamiento es proporcional.

**Recomendación Claude:** Opción 3 (handle público) + opt-out por dirigente. Camino 1 (re-scrape) es defendible pero caro. Camino 2 expone más de lo necesario.

**Decisión a tomar con CEO** antes de Sprint 3.

---

## C · Sprints

### Sprint 0 · Verificación pre-fix (20 min · BLOQUEANTE)

**Objetivo:** confirmar premisas antes de tocar código.

1. Verificar `User` model tiene campo `dirigente_id` o equivalente:
   ```bash
   grep -n "dirigente_id\|dirigente_observador" backend/app/models/user.py
   ```
2. Listar endpoints exactos sin `_check_org` con grep:
   ```bash
   grep -B2 -A15 "@router.get" backend/app/api/v1/endpoints/watched_profiles.py | grep -E "@router|_check_org|async def"
   ```
3. Confirmar `social_comments` no tiene `commenter_handle` (decide camino opción 3):
   ```bash
   grep -A30 "class SocialComment" backend/app/models/*.py
   ```
4. Verificar que existe carpeta `e2e/` o setup Playwright en frontend (impacta Sprint 4):
   ```bash
   ls frontend/playwright.config* frontend/e2e/ 2>/dev/null
   ```

**Criterio done:** 4 respuestas documentadas. CEO confirma decisión D (camino 1, 2 o 3).

---

### Sprint 1 · Cerrar leak multi-tenant (🔴 CRÍTICO · 1.5h)

**Objetivo:** ningún endpoint GET en `watched_profiles.py` devuelve datos cross-org.

**Archivos:** `backend/app/api/v1/endpoints/watched_profiles.py`

**Cambios:**
1. Para cada endpoint `GET` que acepta `dirigente_id` (`/`, `/summary`, `/suggestions`, `/{id}/engagement`):
   - Antes del query, resolver `org_id` del dirigente: `SELECT org_id FROM dirigentes WHERE id = :did`.
   - Llamar `_check_org(user, drow.org_id)`.
   - Si `dirigente_id` no se pasa: filtrar por `user.org_id` (no devolver todo).
2. `GET /{id}/engagement` requiere paso extra: resolver `dirigente_observador_id` desde el watched, después `org_id`, después check.

**Test (curl):**
```bash
# Setup: tokens
TOK_CRAVIOTO=$(curl -sX POST $API/auth/login -d "username=cravioto@... &password=...")
TOK_PINA=$(curl -sX POST $API/auth/login -d "username=alejandro.pinha@... &password=...")

# Cravioto pide watched de dirigente #3 (Saymi, otro org) → 403
curl -sw "%{http_code}\n" -H "Bearer $TOK_CRAVIOTO" \
  "$API/aceptacion/watched-profiles/?dirigente_id=3"
# expect: 403

# Cravioto sin dirigente_id → solo su org
curl -s -H "Bearer $TOK_CRAVIOTO" "$API/aceptacion/watched-profiles/"
# expect: solo watched cuyo dirigente_observador_id ∈ org de Cravioto

# Cravioto pide su propio dirigente → 200
curl -sw "%{http_code}\n" -H "Bearer $TOK_CRAVIOTO" \
  "$API/aceptacion/watched-profiles/?dirigente_id={cravioto_dirigente_id}"
# expect: 200
```

**Test pytest:** `backend/tests/api/test_watched_profiles_scope.py` (nuevo).

**Dependencias:** Sprint 0.

---

### Sprint 2 · Fix UI default + labels (🟠 ALTO · 2h)

**Objetivo:** Cravioto entra → ve sus propios perfiles observados. Labels coherentes. Filtros limpios.

**Archivos:**
- `frontend/src/app/dashboard/aceptacion/fantasmas/page.tsx` (default state)
- `frontend/src/components/aceptacion/watched-profiles-tab.tsx` (labels, filtros, tags rendering)

**Cambios:**
1. Reemplazar `useState<number>(3)` por lógica derivada del `user`:
   ```ts
   const { user } = useAuth();
   const [observedDirigenteId, setObservedDirigenteId] = useState<number | null>(null);
   useEffect(() => {
     if (observedDirigenteId !== null) return;
     if (user?.dirigente_id && dirigentesList.find(d => d.dirigente_id === user.dirigente_id)) {
       setObservedDirigenteId(user.dirigente_id);
     } else if (dirigentesList[0]) {
       setObservedDirigenteId(dirigentesList[0].dirigente_id);
     }
   }, [user, dirigentesList, observedDirigenteId]);
   ```
2. Empty state cuando `dirigentesList.length === 0` y user no tiene dirigente → "Sin dirigentes accesibles. Contacta al admin de tu org."
3. Cabecera tabla: `"LIKES"` → `"REACCIONES"` (alineado a card y al hecho que `n_likes` agrupa los 4 tipos).
4. Columna TAGS: si `tags.length === 0` renderizar `<span className="text-muted-foreground">—</span>` (no string "sin tags").
5. Filtros: condicional `count > 0` antes de renderizar cada filtro. Si "Todos" y filtro único activo coinciden en count, ocultar barra de sub-filtros (es decir, si todos los demás filtros son 0).
6. Section header redundante: quitar el `<h2>` "Perfiles Observados · Dirigente #X" y dejar solo el subtítulo descriptivo (el tab activo ya lo indica). Mantener solo nombre dirigente como contexto.

**Test manual (Playwright opcional, ver Sprint 4):**
1. Login Cravioto → tab → selector muestra "César Cravioto Romero", título "Dirigente #cravioto_id" (o el nombre), 0 perfiles (esperado, no había watched suyos).
2. Login admin (sin dirigente asignado) → selector muestra `dirigentesList[0]`.
3. Login alejandro.pinha → su propio dirigente seleccionado.
4. Cambiar manualmente del selector → re-fetch en consecuencia.

**Dependencias:** Sprint 1 (sin él, selector funcional pero leak persiste).

---

### Sprint 3 · Resolver hash → handle en sugerencias (🟠 ALTO · estructural)

**Objetivo:** sugerencias muestran identidad accionable.

**BLOQUEO:** requiere decisión D (camino 1, 2 o 3 — ver sección B arriba). Sin esta decisión, sprint queda parado.

**Estimado por camino:**
- Camino 3 (cachear `commenter_handle` desde scrape): migración + update scrapers + endpoint refactor → 6h.
- Camino 1 (re-scrape + match): refactor sugerencias para llamar Apify por hash → 4h pero costo monetario por consulta.
- Camino 2 (lookup table TTL): migración + cron + endpoint resolver → 8h y exposición LFPDPPP.

**Dependencias:** Sprint 0 (verifica disponibilidad campo en model), decisión CEO sobre D.

**Deferible:** sí. El leak (Sprint 1) y la UX (Sprint 2) son inmediatos. Sprint 3 puede esperar a próxima sesión con decisión arquitectural.

---

### Sprint 4 · Tests E2E + redeploy (1h)

**Objetivo:** trabajo verificable en prod.

**Archivos:**
- `frontend/e2e/fantasmas.spec.ts` (nuevo, si Playwright ya está configurado)
- `backend/tests/api/test_watched_profiles_scope.py` (test del Sprint 1)

**Casos E2E:**
1. Login Cravioto → `/dashboard/aceptacion/fantasmas` tab observados → selector NO vacío + no contiene "Dirigente #3".
2. Curl directo `GET /watched-profiles/?dirigente_id=3` con token Cravioto → 403.
3. Columna "REACCIONES" presente, "LIKES" ausente.
4. Filtro "Manual 0" NO renderiza si count es 0.

**Redeploy:** `cd frontend && vercel deploy --prod --yes` después de merge.

**Dependencias:** Sprint 1 + Sprint 2 completos.

---

## D · Plan de test E2E consolidado

| Test | Setup | Action | Expect |
|------|-------|--------|--------|
| **Scope leak** | Login Cravioto | `GET /watched-profiles/?dirigente_id=3` | `403 Forbidden` |
| **Default OK** | Login Cravioto | Navegar a tab | Selector con su nombre, no vacío |
| **Admin global** | Login admin sin dirigente | Navegar a tab | Selector `dirigentesList[0]` |
| **Self-dirigente** | Login alejandro.pinha | Navegar a tab | Selector "Alejandro Piña" |
| **Label correcto** | Cualquier login válido | Render tabla | Header columna dice "REACCIONES" |
| **Filtros limpios** | Login con 0 manuales/sugeridos | Render filtros | "Manual 0" / "Sugeridos 0" NO presentes |
| **Tags empty** | Watched sin tags | Render fila | Celda renderiza `—`, no string "sin tags" |

---

## E · Out of scope (NO hacer)

- Refactor del modelo `watched_profiles` (tabla está bien).
- Features nuevos: deep linking, exportar CSV, bulk actions.
- Otras pestañas del tab (Resumen agregado, Por plataforma) — fuera del scope de este plan.
- Endpoint nuevos salvo `/reveal-hash` o equivalente si se opta por camino 1 del Sprint 3.
- Rediseño visual del tab (paleta, tipografía) — el bug está en datos y lógica, no en estilo.

---

## F · Orden de ejecución recomendado

```
Sprint 0 (verify, 20 min)
   ↓
Sprint 1 (backend scope, 1.5h)   ← bloquea Sprint 2
   ↓
Sprint 2 (frontend UI, 2h)       ← bloquea Sprint 4
   ↓
Sprint 4 (E2E + deploy, 1h)
   ↓
[CEO decide D] → Sprint 3 (resolución hash, 4-8h según camino)
```

**Tiempo crítico hasta piloto funcional (sin S3):** 4.5h.

**Próxima ventana piloto §9.8:** día 30 ≈ 2026-05-20 → tenemos 6 días, margen para S1+S2+S4 hoy/mañana, S3 antes del 19.

---

## G · Notas de cross-audit Claude → Gemini

- Gemini consolidó bugs 7+8 (títulos/subtítulos) en "filtros redundantes". Los separé.
- Gemini propuso para Sprint 3 "lookup temporal del hash" sin notar que SHA256 es **one-way**. Corregí con 3 caminos viables (re-scrape, lookup table, cachear handle).
- Gemini sugirió Playwright `e2e/` sin verificar existencia. Sprint 0 lo audita primero.
- Gemini omitió el caso edge `dirigentesList.length === 0` (admin sin dirigentes asignados). Lo agregué al Sprint 2.
- Tiempo total ajustado: Gemini estimó 9-13h, mi ajuste es 4.5h críticos + S3 deferido.
