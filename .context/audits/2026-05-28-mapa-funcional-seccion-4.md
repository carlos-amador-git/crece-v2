YOLO mode is enabled. All tool calls will be automatically approved.
YOLO mode is enabled. All tool calls will be automatically approved.
Ripgrep is not available. Falling back to GrepTool.
# Auditoría sección §4 — Planes IA
**Fecha:** 2026-05-28
**Auditor:** Gemini
**Doc auditado:** .context/MAPA-FUNCIONAL.md
**Sección:** §4

## Citas verificadas
- ✅ **§4.1 Vistas FE:** `/dashboard/planes/page.tsx` existe y utiliza `usePlanes` y `useDirigentes`.
- ✅ **§4.1 Vistas FE:** `/dashboard/planes/[id]/page.tsx` existe y utiliza `usePlan` y `PlanTareasList`.
- ✅ **§4.1 Vistas FE:** `/dashboard/planes/[id]/kanban/page.tsx` existe y contiene la lógica de redirección por tipo de plan documentada.
- ✅ **§4.2 Endpoints:** `POST /planes/generar` existe en `planes.py:75` (doc cita 72) con limitador `5/hour`.
- ✅ **§4.2 Endpoints:** `GET /planes/` existe en `planes.py:125` con paginación y filtrado por `org_id`.
- ✅ **§4.3 Tablas:** La tabla `plan_tareas` tiene las columnas documentadas (`plataforma`, `formato`, `metrica_objetivo`, etc.).
- ✅ **§4.4 Cobertura SQL:** Los counts y porcentajes de `estructura_json` (DIAGNOSTICO 60%, CONSOLIDACION/CONTENIDO 100%) coinciden exactamente con la realidad de la DB.
- ✅ **§4.6 Deuda:** Se confirma el mismatch FE-BE en `useGeneratePlan`, `useApprovePlan` y `useRejectPlan`.

## Citas sin verificar / inventadas
- ⚠️ **§4.1 Estructura de Tabs:** El doc afirma que hay 3 tabs (Diagnóstico, Estrategia, Contenido). **Cita errónea/desfasada:** En `page.tsx:43`, un comentario indica `D-PLANES-DIAGNOSTICO-REMOVED-2026-05-22` y el código solo define `const TAB_VALUES = ["estrategia", "contenido"]`. El tab de Diagnóstico no existe en la UI actual.
- ⚠️ **§4.2 Líneas de código:** Las líneas citadas en `planes.py` están desplazadas (ej. `list_tareas` en 214 vs 228 citado). Requiere actualización de punteros.

## Omisiones detectadas
- ❌ **Botones muertos:** §4.1 afirma que existen acciones Approve/Reject en el detalle del plan. Si bien los botones aparecen en `[id]/page.tsx:210`, **no tienen handlers `onClick`**, por lo que son inoperantes. El doc no menciona que son placeholders visuales.
- ❌ **Enum mismatch:** §4.3 lista `DOING` como valor de `estado_tarea_enum`. El valor real en la DB y en `plan_ia.py:32` es `IN_PROGRESS`.
- ❌ **Tipo de Plan omitido:** En `plan_ia.py:24` existe el tipo `CRISIS`, el cual no aparece mencionado en §4 como parte de los tipos posibles en `planes_ia`.

## Sesgo del redactor
- 🔍 **Cobertura de datos:** Las queries SQL de cobertura se ejecutaron sobre el total de la tabla, pero el análisis de "modelos únicos" (16) no distingue cuáles están activos vs. legacy.
- 🔍 **RBAC:** Se verificó la existencia de decoradores `RoleChecker`, pero no se probó empíricamente el aislamiento entre organizaciones (se asume correcto por el código).

## Veredicto
⚠️ **Pasa con ajustes**
1. Actualizar §4.1 para reflejar que solo existen **2 tabs** (Estrategia y Contenido) tras la remoción del tab Diagnóstico el 2026-05-22.
2. Corregir el valor del enum en §4.3 de `DOING` a `IN_PROGRESS`.
3. Documentar en §4.6 que los botones Approve/Reject en la vista de detalle son actualmente **placeholders sin lógica** (deuda técnica de UI).
4. Corregir los punteros de línea en §4.2.
5. Agregar el tipo `CRISIS` a la lista de tipos de planes en §4.
