# PLAN integral revisado · cierre pre-reunión 2026-05-10
**Autor:** Linda · **Generado:** 2026-05-09 ~23:50pm · **Cross-audited Gemini:** 2026-05-10 00:05am
**Mandato CEO:** *"para y dame el /plan completo y revisalo con /gemini. No dejes nada afuera. Revisa, no supongas."*

---

## 1. AUDIT VERIFICADO (no suposiciones)

### 1.1 Roster real en BD

| id | nombre | rol | org | posts/clasif | comments/clasif | DIAG | CONS |
|---:|---|---|---|---:|---:|:-:|:-:|
| 1 | Alejandro Piña | oposición | MC CDMX | 355 / 36 | 406 / 406 | 1 | 2 |
| 2 | Rafael Solano | oposición | MC CDMX | 233 / 36 | 24 / 24 | 1 | 2 |
| 3 | Saymi Pineda | oficialismo | Gob Oaxaca | 1448 / **0** | 179 / 179 | 1 | 2 |
| 4 | Yesenia Nolasco | oficialismo | Gob Oaxaca | 381 / **0** | 120 / 120 | 1 | 2 |
| 5 | Gabriela Jiménez Godoy | oficialismo | CDMX Indep | 1366 / **0** | 1054 / 1054 | 1 | 2 |
| 6 | César Cravioto | oficialismo | CDMX Indep | 586 / **0** | 129 / 129 | 1 | 2 |
| 7 | Máynez | oposición | (sin org) | 0 / 0 | 0 / 0 | 0 | 0 |
| 8 | Laura Ballesteros | oposición | MC CDMX | 420 / 40 | 784 / 784 | 2 | 0 |

### 1.2 Editor HITL · estado

- `hitl_edits_log = 0 rows` → **persistencia EDIT/CONFIRM no probada end-to-end** (solo se cargó la página).
- 60 posts clasificados con `claude+gemini-2way-recent-2026-05-09` (top 20 × 3 piloto).
- 4 oficialistas con 0 posts clasificados.

### 1.3 Vercel deploy gap

- Último deploy: SHA `043a4eb` (~30h atrás). HEAD: `d36c58a`. **23 commits sin desplegar.**
- 2 ediciones locales pendientes esta noche (scope filter overview + sidebar).

### 1.4 Branches not-merged

- 18 confirmadas. `feat/eval-benchmark-v1` tiene archivos `D` (deletes) sobre archivos que existen en main → **mergear a ciegas DESTRUYE main**. Solo cherry-pick selectivo.

### 1.5 Encuestas demoscópicas

- `encuestas_publicas`: 4,540 rows. Sin endpoint REST, sin UI. CSVs CEO (50+1078+6304) pendientes de ingestar.

### 1.6 Lenguaje técnico en `plan_tareas` (verificado SQL)

- 30 tareas en planes v3 con: `plataforma='CROSS'` (4/5), prefijos `FODA[D]:`, `"scraper"`, `"engagement=0"`, `responsable: MD TI + equipo comunicación`, `% posts tono=personal`.

### 1.7 Sidebar visibility (post edit local pendiente)

- Sección "Configuración" NUEVA visible al VIEWER. **Riesgo identificado por Gemini:** lógica `clientOnly && isAdmin → false` puede ocultar al admin. **Verificar.**

### 1.8 Background jobs

- PID 4766 (Gemma triangulación CSV-only) corriendo desde 04:02. OK.
- PID 3351 (Gemma classify_posts_gemma_coolify, bug R3) zombie desde 02:30. **Killar en Sprint 0.**

---

## 2. PLAN REVISADO POST-GEMINI · 11 sprints

### Cambios respecto a v1 (post audit Gemini):

1. **Deploy temprano** (Sprint 2) — antes de pulir.
2. **Smoke HITL real adelantado** (Sprint 3) — validar persistencia antes de invertir en lenguaje.
3. **Sprint lenguaje político PODADO** — solo mappers frontend, NO regenerar planes BD vía LLM.
4. **Sidebar admin verification** integrado a Sprint 1.
5. **Si CEO elige Opción B**: solo 2 oficialistas (Jiménez + Cravioto, mismos org-tipo CDMX Independiente).

---

### Sprint 0 · Limpieza pre-ejecución (10 min) 🔴

- Killar PID 3351 zombie.
- Verificar PID 4766 sigue produciendo CSV.
- Snapshot estado: `git status`, `git log -1`.

**ETA:** 0:10

---

### Sprint 1 · Bug scope + sidebar admin verification (45 min) 🔴

**Edits ya hechos local:**
- `backend/app/api/v1/endpoints/indice_aceptacion.py` (scope filter A en `get_aceptacion_overview`)
- `frontend/src/components/layout/sidebar.tsx` (nuevas entries Configuración + Mi Evaluación)

**Acción restante:**
1. Tests existentes pasan: `docker exec crece-backend pytest tests/test_indice_aceptacion.py -x` (si existen).
2. **Verificar admin sidebar:** simular admin (revisar `clientOnly && isAdmin` línea 406 de sidebar.tsx). Decisión:
   - Si admin pierde acceso a Configuración (Precisiones + Metodología) → mantener sección "Sistema" original visible para admin.
   - Solo nueva "Configuración" para VIEWER (sin viewerHide); "Sistema" admin-solo (con viewerHide).
3. Patch sidebar si necesario.

**Criterio:** Solano/Piña/Ballesteros ven solo SU tarjeta en /aceptacion/dirigentes; ven "Mi Evaluación" + "Configuración" en sidebar. Admin sigue viendo "Sistema" + "Admin MD" + ahora también "Configuración" (sin pérdida).

**ETA:** 0:45 → acumulado 0:55

---

### Sprint 2 · Deploy TEMPRANO (Vercel) + smoke baseline (30 min) 🔴

**Justificación Gemini:** *"Dejar el despliegue al Sprint 8 es 'todo o nada'. Cualquier fallo de compilación dejará la app caída antes de la reunión."*

**Acción:**
- Commit + push de Sprint 1 a `feat/phase-b-pesos-editables`.
- `cd frontend && vercel deploy --prod --yes`.
- Verificar build OK (~1-2 min).
- Smoke baseline post-Sprint 1: login Solano → /aceptacion/dirigentes solo SU tarjeta + sidebar muestra Configuración + Mi Evaluación.
- **Si build falla:** rollback al deploy actual `043a4eb` que SÍ funciona, debug local sin bloquear plan.

**Criterio:** deploy READY + smoke 1 cuenta verde.

**ETA:** 0:30 → acumulado 1:25

---

### Sprint 3 · Smoke HITL real (EDIT/CONFIRM persiste) (1h) 🔴

**Justificación Gemini:** *"Es prioritario verificar que la persistencia en BD funciona ANTES de invertir 3h en pulir lenguaje."*

**Acción:**
- Login Solano + Piña + Ballesteros (3 cuentas). Por cada uno:
  - Abrir `/dashboard/settings/evaluacion-nlp`.
  - Verificar 20 posts cargan con AI suggestion.
  - Hacer 1 EDIT real (cambiar tono → propositivo).
  - Hacer 1 CONFIRM real (otro post).
  - Refresh página.
  - Verificar badge "✓ Confirmado" / "✏️ Editado".
- Verificar BD: `SELECT * FROM hitl_edits_log WHERE actor_id IN (5,6,11) ORDER BY edited_at DESC LIMIT 10;` debe tener ≥6 rows.
- **Si falla persistencia:** debug del endpoint POST `/api/v1/hitl/edit` o `/confirm` antes de continuar.

**Criterio:** 3/3 dirigentes EDIT+CONFIRM persiste; 6 rows en `hitl_edits_log`.

**ETA:** 1:00 → acumulado 2:25

---

### Sprint 4 · Lenguaje político PODADO (frontend mappers solo) (1.5h) 🔴

**Justificación Gemini:** *"Delegar 'traducción' a un LLM sin validación humana puede generar recomendaciones absurdas. Reducir a mappers frontend ahorra 2.5h críticas."*

**Acción:**
- `frontend/src/lib/labels.ts` (NUEVO):
  - `mapPlataforma(p)`: `CROSS → "Multiplataforma"` con icono `LayoutGrid`.
  - `mapFODATag(prefijo)`: parser `[D]/[O]/[F]/[A]` → `{tag, label, icon, color}`.
  - `mapTonoLabel`, `mapTargetLabel`, `mapAmbitoLabel`, `mapResponsable` (`MD TI` → `Equipo de la organización`), `mapMetrica` (regex `% plataformas con engagement>0` → `Plataformas con audiencia activa`).
- `frontend/src/app/dashboard/planes/[id]/page.tsx` patch: usar mappers en card de tarea + descripción + métrica + responsable.
- **NO regenerar planes BD vía LLM hoy** — diferido a Oleada 2 post-reunión.
- Test: render de plan id=13 (Piña) muestra "Multiplataforma" no "CROSS", chip "❗ Debilidad" no "FODA[D]:", "Equipo de la organización" no "MD TI".

**Criterio:** 0 ocurrencias visibles de tokens técnicos en planes/[id]/page.tsx render para VIEWER.

**ETA:** 1:30 → acumulado 3:55

---

### Sprint 5 · Deploy intermedio + smoke triple (30 min) 🔴

**Acción:** push + vercel deploy → smoke con 3 cuentas verificar Sprint 4 (lenguaje político visible) + Sprint 3 persiste.

**Criterio:** 6 checkpoints × 3 cuentas = 18 verde.

**ETA:** 0:30 → acumulado 4:25

---

### Sprint 6 · FODA vista dedicada (2.5h) 🟡

**Acción:**
- Backend: extender `app/api/v1/endpoints/diagnostico.py` con `GET /diagnostico-foda/{dirigente_id}`.
  - Parser markdown del campo `contenido` para extraer F/D/O/A.
  - Scope: VIEWER → solo su dirigente.
- Frontend: `app/dashboard/diagnostico/[dirigenteId]/foda/page.tsx` con cuadrante 2×2.
- Sidebar: añadir "Mi Diagnóstico FODA".
- Smoke con 3 cuentas.

**Criterio:** Solano ve FODA con datos reales DIAGNOSTICO id=8.

**ETA:** 2:30 → acumulado 6:55

---

### Sprint 7 · Clima Político (cherry-pick + ingesta CSVs) (3.5h) 🟡

**Justificación Gemini:** ETA realista subido a 3.5h por typos en CSVs (ingesta de fuentes externas siempre toma más).

**Acción:**
1. Migration `add_municipio_encuestas_publicas` (ALTER TABLE ADD COLUMN nullable).
2. Cherry-pick **selectivo** (no merge):
   - **Copiar manualmente** archivos `A` de `feat/eval-benchmark-v1`:
     - `frontend/src/app/dashboard/social/clima/page.tsx`
     - `frontend/src/lib/api/hooks/use-clima-politico.ts`
     - schemas `ClimaPoliticoSerie/Point` → `backend/app/schemas/social.py`
     - sección `/clima-politico` líneas 322–385 → `backend/app/api/v1/endpoints/social.py`
3. Patch endpoint scope: `ambito IN ('estatal','municipal')` aplica `org_estado`.
4. Patch frontend: card alcalde muestra `actor_nombre · municipio, entidad`.
5. Sidebar: entry `Social → Clima Político`.
6. Script `backend/scripts/ingest_demoscopia_api_csvs.py`:
   - Lee 3 CSVs (`/Users/marxchavez/Downloads/`).
   - Cada fila → 2 rows (`metrica='aprobacion'`, `metrica='desaprobacion'`).
   - `fuente='Demoscopía Digital'`. Upsert idempotente.
   - **Limpieza nombres/entidades:** función `normalize_actor()` y `normalize_entidad()` para evitar duplicados.

**Criterio:** ≈14,800 rows nuevas. Solano (CDMX) → tab estatal Brugada, tab municipal solo alcaldes CDMX.

**ETA:** 3:30 → acumulado 10:25

---

### Sprint 8 · Auditoría pantallas VIEWER (1h) 🟡

Verificar como Solano cada ruta visible. Ocultar las rotas si las hay. Lista en plan v1.

**Criterio:** 0 pantallas con error 500/404 visibles.

**ETA:** 1:00 → acumulado 11:25

---

### Sprint 9 · Branches recovery selectivo (2h) 🟡

Por cada rama not-merged: identificar archivos `A` exclusivos huérfanos. Decisión por rama documentada en DECISIONS.md. NUNCA `git merge` directo. Material valioso desconocido → consultar CEO.

**Criterio:** 18 ramas evaluadas, decisión por rama, ninguna mergeada que rompa main.

**ETA:** 2:00 → acumulado 13:25

---

### Sprint 10 · Deploy final + smoke E2E completo (45 min) 🔴

Push final + vercel deploy + smoke 8 checkpoints × 3 cuentas:
1. Login OK
2. /dashboard
3. /aceptacion/dirigentes (solo SU)
4. /settings/evaluacion-nlp (20 posts AI)
5. /planes/[id] (lenguaje político)
6. /diagnostico/[id]/foda (cuadrante)
7. /social/clima (series)
8. EDIT+CONFIRM persiste

**Criterio:** 24/24 checkpoints verde.

**ETA:** 0:45 → acumulado 14:10

---

### Sprint 11 · Docs + brief (45 min) 🟢

STATUS.md, DECISIONS.md (D-UX-1, D-FODA-1, D-CLIMA-1, D-AC-1, D-BR-2..N), HANDOVER-AI.md, brief CEO con métricas.

**ETA:** 0:45 → acumulado 14:55

---

## 3. ETA REVISADO

| Sprint | ETA | Acumulado |
|---|---:|---:|
| 0 limpieza | 0:10 | 0:10 |
| 1 scope + sidebar | 0:45 | 0:55 |
| 2 **deploy temprano** | 0:30 | 1:25 |
| 3 **smoke HITL real** | 1:00 | 2:25 |
| 4 lenguaje frontend mappers | 1:30 | 3:55 |
| 5 deploy intermedio + smoke | 0:30 | 4:25 |
| 6 FODA dedicado | 2:30 | 6:55 |
| 7 Clima Político | 3:30 | 10:25 |
| 8 auditoría pantallas | 1:00 | 11:25 |
| 9 branches recovery | 2:00 | 13:25 |
| 10 deploy final + smoke triple | 0:45 | 14:10 |
| 11 docs + brief | 0:45 | 14:55 |

**Total: ≈15 horas.** Arranque ~00:30am → terminado ~3:30pm.

**Reality-check Gemini:** *"Si la reunión es matutina, el plan no es viable sin recortes."*

**Punto de corte natural si tiempo escasea:**
- Sprints 0–5 (≈4.5h, hasta ~5am) entregan: scope fix, sidebar, deploy, HITL persistente, lenguaje político visible. **Mínimo viable mañana.**
- Sprints 6–7 (≈6h adicionales) entregan: FODA dedicado, Clima Político con encuestas. **Showcase nuevo.**
- Sprints 8–11 (≈4.5h adicionales) entregan: auditoría, branches, deploy final, docs.

---

## 4. RIESGOS DECLARADOS · post-Gemini

| Riesgo | Probabilidad | Mitigación |
|---|:-:|---|
| Sidebar admin pierde acceso a Configuración/Metodología (Gemini) | Media | Verificar línea 406 sidebar.tsx en Sprint 1. Mantener sección "Sistema" admin-only paralela. |
| LLM regenera planes con texto absurdo (Gemini) | Alta si se hiciera | **Mitigado:** podado, no se regenera vía LLM. |
| Saturación VPS por Gemma + ingesta paralela (Gemini) | Baja | Sprint 0 valida; killar Gemma si afecta. |
| Sprint 7 cherry-pick rompe build | Media | Copy-paste manual. Deploy intermedio Sprint 5 garantiza baseline funcional. |
| Sprint 3 detecta bug POST endpoint HITL no probado | Media | Si rota, fixear inmediato (bloqueante reunión). |
| Sprint 4 mappers no cubren todos los tokens | Baja | Iterar con grep en producción para detectar tokens visible en UI. |
| 4 oficialistas sin posts clasificados → sample vacío | Alta | Decisión §5 pendiente CEO. |

---

## 5. DECISIÓN PENDIENTE CEO

**Pregunta:** los 4 oficialistas (Pineda, Nolasco, Jiménez, Cravioto) NO tienen posts clasificados. **3 opciones:**

| Op | Acción | ETA adicional | Tradeoff |
|---|---|---:|---|
| **A** | Excluirlos mañana — solo Solano + Piña + Ballesteros | 0 | Pierde 4 dirigentes ya credenciados |
| **B (Gemini recomienda subset)** | Incluir solo Jiménez Godoy + Cravioto (CDMX Independiente, comunidad de Solano/Ballesteros) — clasificar sus posts hoy con Claude+Gemini | +2h en Sprint 0.5 paralelo a otros | Sample completo para 5 dirigentes; Pineda/Nolasco quedan a Oleada 2 |
| **C** | Incluir todos pero con sample vacío — clasifican desde cero | 0 | Ground truth puro pero más trabajo de anotación para ellos |

**Mi recomendación:** **B subset** (Jiménez + Cravioto). Gemini lo respalda. Pineda + Nolasco tienen menos prioridad estratégica (Oaxaca vs CDMX donde está la reunión).

**Default si CEO no responde en 15 min:** A (excluir 4 oficialistas).

---

## 6. RECOMENDACIÓN GEMINI INTEGRADA

✅ Cherry-pick selectivo branches → validado
✅ Deploy temprano post-Sprint 1 → integrado
✅ Smoke HITL antes de pulir lenguaje → integrado (Sprint 3 antes de Sprint 4)
✅ Sprint 2 podado a frontend mappers → integrado (regeneración LLM diferida)
✅ Decisión §5 Opción B subset (2 oficialistas) → recomendado

---

## 7. PRÓXIMO PASO

CEO: confirmar decisión §5 + luz verde plan v2. Arranco Sprint 0 inmediato.
