# PLAN integral · cierre pre-reunión 2026-05-10
**Generado:** 2026-05-09 noche
**Mandato CEO:** *"Solo quiero ver mañana la app corriendo eficientemente."*
**Sesión activa:** Linda (peer uji6x64w · CRECE-electoral)
**Branch trabajo:** `feat/phase-b-pesos-editables`

---

## OBJETIVO REUNIÓN 2026-05-10

Solano · Piña · Ballesteros entran a producción y:
1. **Editor HITL** (`/dashboard/settings/evaluacion-nlp`) — anotan 20 posts + N comments cada uno con AI suggestion lista. Confirmar/editar persiste a BD.
2. **Plan IA** (`/dashboard/planes/[id]`) — leen su plan v3 con lenguaje político (sin CROSS, sin FODA[D], sin scraper).
3. **Aceptación por dirigente / fantasmas** (`/dashboard/aceptacion/dirigentes`, `/aceptacion/fantasmas`) — VEN SOLO SU TARJETA, no la de sus pares.
4. **Diagnóstico FODA** (`/dashboard/diagnostico/[id]/foda`) — cuadrante 2×2 legible.
5. **Clima Político** (`/dashboard/social/clima`) — series temporales de aprobación gubernamental con datos Demoscopía + Oraculus + Mitofsky (≈19,400 rows totales tras ingesta CSVs CEO).

---

## TRADEOFF CRÍTICO QUE EL CEO DEBE VER

**CEO pidió "recupera todos los branches y luego evaluamos qué dejamos".** Honestamente: 18 ramas not-merged, varias con alembic split-head, una con secret leaked (eval-benchmark-v1 — CEO ya autorizó NO rotación porque cuenta es free), el merge masivo en una noche tiene riesgo alto de:

- conflictos de migrations no resolubles sin perder data
- regresiones funcionales que no pueda detectar antes de la reunión
- Vercel build falla por dep nueva no compilable

**Mi recomendación honesta — divido en 2 oleadas:**

| Oleada | Cuándo | Qué se entrega |
|---|---|---|
| **Hoy noche (críticos pre-reunión)** | 9 sprints, ETA ~9h | Sprints 1–9: editor HITL final, bug scope, lenguaje político, FODA dedicado, Clima Político con CSVs Demoscopía, Vercel deploy, smoke triple cuenta |
| **Mañana post-reunión / próximo sprint** | sesión separada, ETA 1-2 días | Branches recovery completo (18 ramas) + auditoría items E.1–E.12 |

Si CEO insiste en branches-recovery-tonight: lo hago, pero declaro que la entrega "app corriendo eficientemente mañana" se vuelve probabilística. El editor HITL ya está listo para mañana — recovery masivo arriesga romperlo.

**Asumo Oleada 1 hasta que CEO me corrija.**

---

## OLEADA 1 · esta noche · 9 sprints secuenciales

### Sprint 1 · Bug scope `/aceptacion/overview` (15 min) 🔴

**Acción**
- `backend/app/api/v1/endpoints/indice_aceptacion.py:265–281` (`get_aceptacion_overview`).
- Replicar patrón ternario de `043a4eb`:
  ```python
  if current_user.role == "admin":
      pass
  elif current_user.role == "viewer" and current_user.dirigente_id:
      org_filter = "WHERE d.id = :dirigente_id"
      params["dirigente_id"] = current_user.dirigente_id
  else:
      if not current_user.org_id:
          raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin org asignada")
      org_filter = "WHERE d.org_id = :org_id"
      params["org_id"] = current_user.org_id
  ```

**Criterio aceptación**
- Login Solano → `/aceptacion/dirigentes` muestra 1 tarjeta (Solano).
- Login Piña → muestra 1 tarjeta (Piña).
- Login admin → muestra todas.
- Tests existentes siguen pasando.

---

### Sprint 2 · Lenguaje político en planes (2h) 🔴

**Acción**
- Crear `frontend/src/lib/labels.ts` con:
  - `mapPlataforma(p)`: `CROSS → "Multiplataforma"` (con icono `LayoutGrid`)
  - `mapFODATag(prefijo)`: `[D] → "❗ Debilidad"`, `[O] → "💡 Oportunidad"`, `[F] → "💪 Fortaleza"`, `[A] → "⚠️ Amenaza"`
  - `mapTonoLabel(t)`, `mapTargetLabel(t)`, `mapAmbitoLabel(a)`
- Patch `frontend/src/app/dashboard/planes/[id]/page.tsx`:
  - Reemplazar render de plataforma por `mapPlataforma(...)` con badge.
  - Strip prefix `FODA[X]:` de descripción y renderizar como chip arriba.
  - Strip technical metric (`% plataformas con engagement>0`) — UI render con label friendly: "Audiencia activa: X de Y plataformas".
- Patch script `backend/scripts/generate_planes_v3_from_diagnostico.py`:
  - Glosario internal→external en system prompt: `"scraper" → "datos de la plataforma"`, `"engagement=0" → "audiencia que no interactúa"`, `"redesign editorial" → "ajustar la línea de contenido"`, `"MD TI + equipo comunicación" → "Equipo del dirigente"`.
  - Forzar tono accesible al dirigente (no técnico).
- Re-generar 6 planes v3 sobre los mismos 6 diagnosticos (idempotent — los planes anteriores quedan con `superseded_by_v4`).

**Criterio aceptación**
- Card de tarea muestra "Multiplataforma" con icono, no "CROSS".
- Descripción inicia con chip `❗ Debilidad detectada` (color rojo) en lugar de `FODA[D]:`.
- Meta dice "Audiencia activa: 0 de 4 plataformas" en lugar de "% plataformas con engagement>0".
- Owner dice "Equipo del dirigente" no "MD TI + equipo comunicación".
- Cero ocurrencias de "scraper", "engagement=0", "redesign editorial" en planes regenerados.

---

### Sprint 3 · FODA vista dedicada (2.5h) 🟡

**Acción**
- Backend: nuevo endpoint `GET /api/v1/diagnostico-foda/{dirigente_id}` en `app/api/v1/endpoints/diagnostico.py` (extender existente):
  - Lee `planes_ia` con `tipo='DIAGNOSTICO'` y `dirigente_id`.
  - Parsea `estructura_json.foda` → `{fortalezas[], debilidades[], oportunidades[], amenazas[]}`.
  - Retorna también `kpi_baseline` (audiencia, % activación, etc.).
  - Scope: VIEWER → solo su dirigente; admin → cualquier.
- Frontend: nueva ruta `frontend/src/app/dashboard/diagnostico/[dirigenteId]/foda/page.tsx`:
  - Cuadrante 2×2 (Fortalezas/Oportunidades arriba, Debilidades/Amenazas abajo).
  - Color positivo (verde) para Fortalezas+Oportunidades, negativo (rojo) para Debilidades+Amenazas.
  - Cada item con icono + texto plano.
  - Botón "Ver mi plan derivado de este FODA" con link a `/dashboard/planes/[id]`.
- Sidebar: añadir entry "Diagnóstico → FODA" debajo de "Diagnóstico" existente.

**Criterio aceptación**
- Solano entra a `/dashboard/diagnostico/2/foda` y ve cuadrante 2×2 con su FODA.
- Cada cuadrante con ≥2 items reales (no placeholder).
- Click en "Ver plan" navega a su plan v3.

---

### Sprint 4 · Clima Político recovery (3h) 🟡

**Acción**
1. Migration `h9c0d1e2f3g4_add_municipio_encuestas_publicas.py`:
   ```sql
   ALTER TABLE encuestas_publicas ADD COLUMN municipio VARCHAR(255);
   CREATE INDEX ix_encuestas_publicas_municipio ON encuestas_publicas(municipio);
   ```
2. Cherry-pick desde `feat/eval-benchmark-v1`:
   - `frontend/src/app/dashboard/social/clima/page.tsx` (page)
   - `frontend/src/lib/api/hooks/use-clima-politico.ts` (hook)
   - `backend/app/api/v1/endpoints/social.py` líneas 322–385 (endpoint `/clima-politico`)
   - Schemas `ClimaPoliticoSerie` + `ClimaPoliticoPoint` en `backend/app/schemas/social.py`
3. Patch endpoint `/clima-politico`:
   - SELECT incluye `municipio`.
   - Filtro scope: `if ambito IN ('estatal', 'municipal') and org_estado and entidad and entidad != org_estado: continue`
4. Patch frontend page:
   - Card de alcalde muestra `actor_nombre + " · " + municipio + ", " + entidad`
5. Sidebar: añadir entry "Social → Clima Político" (verificar si existía en eval-benchmark-v1; si sí, traerla).
6. Script ingesta `backend/scripts/ingest_demoscopia_api_csvs.py`:
   - Lee 3 CSVs de `/Users/marxchavez/Downloads/`
   - Cada fila → 2 rows (`metrica='aprobacion'`, `metrica='desaprobacion'`)
   - `fuente='Demoscopía Digital'`, `url_fuente='https://api.demoscopiadigital.com.mx'`
   - `fecha_publicacion = date(anio, mes, 1)`
   - Para alcaldes: `actor_tipo='alcalde'`, `ambito='municipal'`, `entidad=<estado>`, `municipio=<municipio>`
   - Para gobernadores: `actor_tipo='gobernador'`, `ambito='estatal'`, `entidad=<estado>`, `municipio=NULL`
   - Para presidenta: `actor_tipo='presidente'`, `ambito='federal'`, `entidad='México'`, `municipio=NULL`
   - Upsert idempotente por `(fuente, actor_nombre, entidad, municipio, fecha_publicacion, metrica)` — si ya existe con mismo valor_pct, skip.
7. Cerrar tarea #27 E.5b como descartada.

**Criterio aceptación**
- BD: ≈14,800 rows nuevas insertadas (50×2 + 1078×2 + 6304×2 = 14,864).
- Login Solano → `/dashboard/social/clima` carga.
- Tab federal: ve serie Sheinbaum.
- Tab estatal: ve serie del gobernador de su org_estado (si org=CDMX → Brugada).
- Tab municipal: ve solo alcaldes de su org_estado.

---

### Sprint 5 · Verificar editor HITL para Piña + Ballesteros (45 min) 🔴

**Acción**
- Smoke E2E con cada cuenta:
  - `pina@crece.mx / demo2026!`
  - `ballesteros@crece.mx / demo2026!` (verificar credencial)
- Por cada uno:
  - Navegar a `/dashboard/settings/evaluacion-nlp`
  - Verificar que carga 20 posts + N comments
  - Verificar que cada post muestra "Sistema: tono / target" (NO "—/—")
  - Hacer 1 EDIT (cambiar tono de un post)
  - Hacer 1 CONFIRM (otro post)
  - Refresh la página
  - Verificar que el edited+confirmed persisten con badge correcto
- Verificar audit log: `SELECT * FROM hitl_edits_log WHERE actor_id IN (...) ORDER BY edited_at DESC LIMIT 5;`

**Criterio aceptación**
- 3/3 dirigentes pueden ver, editar, confirmar, persistir.
- Audit log captura cada acción con `from→to`.

---

### Sprint 6 · Auditoría rápida items E.1–E.12 críticos (1h) 🟡

**Acción** — solo verificar funcionamiento, no construir:

| Item | Verificación | Acción si rota |
|---|---|---|
| E.4 Heatmap territorial `/dashboard/electoral` | Carga? Muestra secciones reales? | Si rota, ocultar para VIEWER (no debe ver pantalla rota mañana) |
| E.5 Alertas `/dashboard` (banner 7 alertas Solano) | Razonables? Threshold OK? | Si son ruido, bajar threshold o filtrar |
| E.8 Recomendaciones `/dashboard/recomendaciones` | Hay contenido? | Si vacío, ocultar o llenar con placeholder |
| E.9 Benchmark `/dashboard/benchmark` | Compara MORENA vs MC? | Verificar seeds/datos |
| `/dashboard/social/comentarios` | Funciona con scope filter aplicado en sprint 1? | OK por consecuencia |

**Criterio aceptación**
- Cero pantallas con error 500/404 visibles a VIEWER mañana.
- Las pantallas funcionales se mantienen; las rotas se ocultan en sidebar para VIEWER.

---

### Sprint 7 · Vercel deploy + smoke E2E triple (45 min) 🔴

**Acción**
- Commit + push de todo el sprint a `feat/phase-b-pesos-editables`.
- `cd frontend && vercel deploy --prod --yes` desde Mac Mini.
- Verificar build OK + alias `frontend-zeta-sepia-46.vercel.app` apunta al nuevo deploy.
- Smoke con las 3 cuentas (Solano, Piña, Ballesteros):
  - Login OK
  - `/dashboard` carga sin errores
  - `/dashboard/aceptacion/dirigentes` muestra solo SU tarjeta
  - `/dashboard/settings/evaluacion-nlp` carga 20 posts con sugerencia
  - `/dashboard/planes/[id]` muestra plan v3 con lenguaje político
  - `/dashboard/diagnostico/[id]/foda` cuadrante visible
  - `/dashboard/social/clima` series visibles

**Criterio aceptación**
- 3/3 dirigentes pasan los 6 checkpoints.

---

### Sprint 8 · Documentar todo (30 min) 🟢

**Acción**
- Update `.context/STATUS.md` con bloque "2026-05-09 noche · cierre pre-reunión integral".
- Update `.context/DECISIONS.md` con D-UX-1 (lenguaje político), D-FODA-1 (vista dedicada), D-CLIMA-1 (recovery + ingesta), D-AC-1 (scope fix overview).
- Update `.context/HANDOVER-AI.md` con handoff post-reunión.
- Marcar tarea #27 como descartada (E.5b obsoleto).
- Crear tareas pendientes para Oleada 2: Branches recovery completo (#46, #47, #48 ya existen).

---

### Sprint 9 · Brief CEO post-cierre (15 min) 🟢

**Acción**
- Reporte final con métricas:
  - LOC añadidas / archivos modificados
  - Rows insertadas (encuestas Demoscópicas)
  - 6 planes v3 regenerados con lenguaje político
  - 4 nuevas vistas (FODA, Clima Político, mappers UI)
  - Tests E2E pasando
- Lista de items diferidos a Oleada 2 (post-reunión).

---

## OLEADA 2 · post-reunión 2026-05-10 · sesión separada

### S2.1 Branches recovery completo (1-2 días)
- 18 ramas inventariadas en Fase 1.
- Por rama: merge a main (no cherry-pick), resolver conflictos, validar tests, mergear o archivar.
- 5 ramas docs → archivar (ya decidido en D-BR-1).
- Ramas con alembic split-head → reconciliar manualmente.
- Rama eval-benchmark-v1 → ya cherry-pickeada parcial en Sprint 4 (Clima); el resto se evalúa.

### S2.2 Auditoría completa E.1–E.12 (post-reunión)
- E.1 Calendario editorial (sprint dedicado)
- E.3 Reporte ejecutivo semanal automático
- E.7 Calendario fechas políticas
- E.10 Score visibilidad mediática
- E.12 Segmentación audiencia / top voceros

---

## ETA TOTAL OLEADA 1

| Sprint | ETA | Acumulado |
|---|---:|---:|
| 1 Bug scope | 0:15 | 0:15 |
| 2 Lenguaje planes | 2:00 | 2:15 |
| 3 FODA dedicado | 2:30 | 4:45 |
| 4 Clima Político | 3:00 | 7:45 |
| 5 Smoke Piña + Ballesteros | 0:45 | 8:30 |
| 6 Auditoría rápida E.* | 1:00 | 9:30 |
| 7 Vercel deploy + smoke triple | 0:45 | 10:15 |
| 8 Documentar | 0:30 | 10:45 |
| 9 Brief final | 0:15 | 11:00 |

**Total: ≈11 horas.** Trabajable hasta ≈ 8 a.m. con arranque ahora (≈ 9 p.m.).

---

## RIESGOS DECLARADOS

| Riesgo | Mitigación |
|---|---|
| Sprint 4 cherry-pick rompe build | Hacer en branch separada, validar build antes de merge |
| Re-generar 6 planes v3 toma más de 2h (LLM lento) | Generar en paralelo con `asyncio.gather()` en script |
| Ingesta CSVs detecta duplicados con encuestas existentes Mitofsky | Upsert idempotente — `created_at` permanece, `valor_pct` se actualiza si difiere |
| Vercel build falla por nueva dep | Plan B: rollback al deploy actual (`d36c58a` ya OK), cherry-pick más ligero |
| Smoke 3 cuentas detecta regresión que no preví | Cada sprint deja commit independiente — bisect rápido |

---

## EJECUCIÓN

Asumiendo luz verde, arranco con Sprint 1 inmediatamente. Reporto al cierre de cada sprint con su criterio de aceptación cumplido o blocker explícito. Sin más preguntas hasta Sprint 7 (deploy) salvo blocker grave.

¿Luz verde **Oleada 1** (los 9 sprints, ≈11h)? O ¿quieres branches-recovery-todo-tonight (≈ +6h) y aceptas el riesgo declarado?
