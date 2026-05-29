# PLAN integrado · pre-reunión 2026-05-10
**Generado:** 2026-05-09 noche
**Origen:** observaciones CEO sobre `/aceptacion/dirigentes`, `/aceptacion/fantasmas`, plan v3 con lenguaje técnico, FODA invisible, encuestas demoscópicas sin exponer.

---

## A. BUGS DE SCOPE (regresión / scope incompleto)

### A.1 `/aceptacion/overview` muestra todos los dirigentes de la org · debería filtrar a SU dirigente cuando VIEWER

**Causa raíz**
- Commit previo `043a4eb` aplicó "Option A" (`d.id = current_user.dirigente_id` para VIEWER) **solo en `/fantasmas-por-plataforma`**.
- El commit message lo declaró explícito: *"Aplicar Option A SOLO en este endpoint; overview y por-dirigente quedan org-wide hasta que se discuta más adelante."*
- El frontend `aceptacion/dirigentes/page.tsx` y `aceptacion/fantasmas/page.tsx` ambos llaman `useAceptacionOverview()` que pega a `/aceptacion/overview` — endpoint sin scope filter A. Por eso Solano (VIEWER, dirigente_id=2) ve a Piña (id=1) y Ballesteros (id=8).

**Fix (un solo endpoint)**
- `backend/app/api/v1/endpoints/indice_aceptacion.py @get_aceptacion_overview` (líneas 265–342): replicar el patrón ternario de `043a4eb`:
  - admin → sin filtro
  - viewer con `dirigente_id` → `WHERE d.id = :dirigente_id`
  - resto (analyst, viewer sin dirigente) → `WHERE d.org_id = :org_id`

**Impacto**
- Solano ve solo su tarjeta. Idem Piña, Ballesteros.
- `total_corpus_comments` resultará dirigente-específico (no org-wide). Es lo correcto: un dirigente no debe ver el corpus de sus pares.
- ETA: 15 min · 1 archivo · sin cambios frontend.

---

## B. LENGUAJE TÉCNICO EN PLANES (visible al dirigente)

CEO: *"hay que tener un lenguaje político, que puedan entender los dirigentes, sin ser tan técnicos."*

| # | Token visible | Donde vive | Acción |
|---|---|---|---|
| B.1 | `CROSS` como tag de plataforma | `backend/app/schemas/plan_ia.py:61` (`PlataformaLiteral`) + frontend renderiza valor crudo | Mantener valor en BD (`CROSS`) pero **mapear en UI** a `Multiplataforma` (badge friendly). Single mapping function en `frontend/src/lib/labels.ts` |
| B.2 | `FODA[D]:`, `FODA[O]:`, `FODA[F]:`, `FODA[A]:` prefijos | `backend/scripts/generate_planes_v3_from_diagnostico.py` y/o `plan_generator.py` injectan los prefijos a la descripción de tareas | Reemplazar prefijo en UI por icono+chip color: `[D]→❗ Debilidad detectada`, `[O]→💡 Oportunidad`, `[F]→💪 Fortaleza`, `[A]→⚠️ Amenaza`. Texto descripción se muestra sin el prefijo crudo |
| B.3 | `auditar scraper`, `validar scraper`, `redesign editorial` | descripciones generadas por LLM con vocabulario técnico mío al promptearlo | Rewrite del prompt en `generate_planes_v3_from_diagnostico.py` para forzar lenguaje político. Glosario interno → externo: "scraper" → "datos de la plataforma", "engagement=0" → "audiencia que no interactúa", "redesign editorial" → "ajustar la línea de contenido" |
| B.4 | `% plataformas con engagement>0`, `% posts tono=personal` | metas medibles del plan v3 | Mismo rewrite + capa de label en frontend: la meta se renderiza como "audiencia activa: ___ de ___ plataformas" no como expresión SQL-like |
| B.5 | `MD TI + equipo comunicación` como owner | hardcoded en script de generación | Sustituir por roles políticos claros: "Equipo del dirigente", "Coordinador de comunicación", "Coordinador territorial" |
| B.6 | `Pendiente`, `Borrador` | estado visible en card del plan | OK. Esos sí son español plano. Sin cambio. |

**Implementación**
- 1 archivo nuevo: `frontend/src/lib/labels.ts` con `mapPlataforma()`, `mapFODATag()`, `mapTonoLabel()`, `mapTargetLabel()`.
- 1 archivo modificado: `frontend/src/app/dashboard/planes/[id]/page.tsx` para usar los mappers.
- 1 script modificado: `generate_planes_v3_from_diagnostico.py` con prompt + glosario.
- Re-generar 6 planes v3 sobre los mismos 6 diagnósticos para reflejar lenguaje nuevo (no destructivo: planes v3 anteriores quedan archivados).

ETA: ~2h.

---

## C. FODA — vista propia y legible

**Estado actual:** el FODA existe en BD como **DIAGNOSTICO** (`planes_ia` tipo=DIAGNOSTICO, `versión foda-v1`, 6 dirigentes, 2.1–2.5K chars cada uno) generado por `generate_diagnostico_dirigentes.py` el 14-abr. **No tiene vista dedicada** — solo se observa parcialmente embebido en el plan v3 que lo deriva.

**Acción**
- Endpoint nuevo `GET /api/v1/diagnostico-foda/{dirigente_id}` que retorne:
  - `fortalezas: list[str]`
  - `debilidades: list[str]`
  - `oportunidades: list[str]`
  - `amenazas: list[str]`
  - `kpi_baseline: dict` (audiencia, % activación, etc. del baseline)
- Página `/dashboard/diagnostico/[dirigenteId]/foda` (o tab dentro de `/diagnostico/[id]`) con **cuadrante 2×2** clásico FODA (positivo/negativo × interno/externo).
- Lenguaje político en cada cuadrante (sin `[D]`, sin `engagement=0`).

ETA: ~3h.

---

## D. CLIMA POLÍTICO (encuestas demoscópicas) — recuperar y ampliar

**Lo que existe hoy en `feat/eval-benchmark-v1` (huérfano):**
- `frontend/src/app/dashboard/social/clima/page.tsx` — vista con tabla + LineChart de aprobación gubernamental por actor × ámbito.
- `frontend/src/lib/api/hooks/use-clima-politico.ts` — hook de consumo.
- `backend/app/api/v1/endpoints/social.py` líneas 322–385 — endpoint `GET /social/clima-politico` que agrega `encuestas_publicas` (Demoscopía+Oraculus+Mitofsky) con scope por `org.estado`.
- Schemas `ClimaPoliticoSerie` y `ClimaPoliticoPoint`.

**Lo que CEO acaba de extraer (`Downloads/`):**
- `presidenta_historico_2024_2026.csv` (50 filas)
- `gobernadores_historico_2022_2026.csv` (1,078 filas, 31 gobernadores oct-2022→abr-2026)
- `alcaldes_historico_2021_2026.csv` (6,304 filas)

**Acción**
1. Migration `add_municipio_to_encuestas_publicas` (ALTER TABLE ADD COLUMN `municipio` VARCHAR NULL).
2. Cherry-pick 4 archivos de `feat/eval-benchmark-v1` → HEAD (page, hook, endpoint section, schemas).
3. Patch endpoint:
   - Filtro `ambito IN ('estatal','municipal')` aplica scope `org.estado` (org CDMX solo ve municipios CDMX).
   - SELECT incluye `municipio` y se devuelve en serie.
4. Patch frontend: card de alcalde muestra `actor_nombre + municipio + estado`.
5. Script ingesta `ingest_demoscopia_api_csvs.py` idempotente:
   - Lee 3 CSVs.
   - Cada fila genera 2 rows (`metrica='aprobacion'` y `metrica='desaprobacion'`).
   - `fuente='Demoscopía Digital'` (matchea filtro existente del endpoint).
   - Upsert por `(fuente, actor_nombre, entidad, municipio, fecha_publicacion, metrica)`.
6. Sidebar entry `Social → Clima Político` (verificar si existía en eval-benchmark-v1).
7. Cerrar tarea #27 E.5b como **descartada** (API directa supera scraper Flourish).

ETA: ~2h.

---

## E. LO QUE FALTA EN LA APP (pasa al CEO al revisar)

Identificado tras revisar todas las rutas del frontend + endpoints backend + scripts. Cada item declara estado actual y tradeoff de prioridad.

| # | Funcionalidad | Estado actual | Recomendación |
|---|---|---|---|
| E.1 | **Calendario editorial / agenda de publicaciones** del dirigente | NO existe vista. Hay tabla `social_posts` con histórico, pero ningún calendario forward-looking | Sprint dedicado post-piloto. ROI alto: el dirigente planifica su mes |
| E.2 | **Compliance INE / modo veda** funcional para VIEWER | Hay `core/veda.py` (bloqueo POSTs en periodo de veda), `/dashboard/compliance` page existe, pero VIEWER no la ve en sidebar (¿por permiso?) | Verificar permisos + revisar que dirigente vea calendario de vedas vigentes y futuras |
| E.3 | **Reporte ejecutivo semanal** auto-generado para el dirigente | NO existe. Plan v3 es manual on-demand | Bot semanal vía email/PDF con: % aprobación, top post, top crítica, alerta crisis. Sprint mediano |
| E.4 | **Heatmap territorial CDMX** (alcaldía / sección electoral) | `/dashboard/electoral` existe. ¿Funcional con datos reales? Verificar | Auditar — puede que ya esté listo |
| E.5 | **Alertas de crisis** en tiempo real | API `alerts` existe, hay 7 alertas activas para Solano en /dashboard. ¿Realmente útiles? Filtros razonables? | Auditar quality + threshold de las alertas con dirigente real |
| E.6 | **WhatsApp Business** / canal masivo | NO existe. Mencionado en commits antiguos como Fase 2 | Diferir. No es bloqueante 2026 |
| E.7 | **Calendario de fechas políticas** (precampañas, debates, registro candidaturas) | NO existe | Sprint corto. ROI medio. Los dirigentes lo necesitan para planear |
| E.8 | **Recomendaciones diarias accionables** ("qué hacer hoy") | `/dashboard/recomendaciones` existe. Auditar contenido y frecuencia | Auditar primero, luego decidir |
| E.9 | **Comparativo vs competidores** funcional | `/dashboard/benchmark` existe. ¿Tiene MORENA tracking? | Verificar — los 4 MORENA en BD (Pineda/Nolasco/Jiménez/Cravioto) deberían ser comparables |
| E.10 | **Score de visibilidad mediática** (cuántas veces sale en medios) | Parcial — hay clipping pero no dashboard | Sprint mediano. Útil cuando se acerca elección |
| E.11 | **Editor HITL para POSTS** (no solo comments) — el dirigente anota su propio contenido | EN CURSO — sample listo para reunión 2026-05-10 | ✅ Cubierto |
| E.12 | **Análisis de comunidad / segmentación de audiencia** (quién comenta, cuántos son críticos repetidos, "top fans" / "top haters") | Parcial — `unique_commenters` existe, pero sin perfil de comentarista recurrente | Sprint mediano. Útil para identificar voceros reales y trolls |

---

## ORDEN DE EJECUCIÓN PROPUESTO (antes de la reunión 2026-05-10)

| Prioridad | Item | ETA | Bloquea reunión? |
|---|---|---:|---|
| 🔴 1 | A.1 Fix scope `/aceptacion/overview` | 15 min | SÍ (Solano lo verá mañana) |
| 🔴 2 | B.1–B.6 Lenguaje político en planes (mappers UI + glosario script) | 2h | SÍ (planes son material de demo) |
| 🟡 3 | C FODA vista dedicada | 3h | NO (puede ser fase post-reunión) |
| 🟡 4 | D Clima Político (cherry-pick + ingesta CSVs) | 2h | NO (CEO lo trae como showcase nuevo, depende de su prioridad) |
| 🟢 5 | E.1–E.12 lista de verificación / nuevos sprints | post-reunión | NO |

**Recomendación de mí:** ejecutar 🔴 1 + 🔴 2 antes de mañana (≈2.25h). 🟡 3+4 dependen de cuánta noche el CEO quiera invertir (≈5h adicionales). 🟢 5 es backlog.

¿Procedo con prioridad 1 + 2 ya, y consulto antes de 3+4?
