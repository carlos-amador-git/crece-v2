YOLO mode is enabled. All tool calls will be automatically approved.
YOLO mode is enabled. All tool calls will be automatically approved.
Ripgrep is not available. Falling back to GrepTool.
# Auditoría sección §6 — Recomendaciones · Mi Evaluación · Reels
**Fecha:** 2026-05-28
**Auditor:** Gemini
**Doc auditado:** .context/MAPA-FUNCIONAL.md
**Sección:** §6

## Citas verificadas
- ✅ **6A.1 Vistas FE (Recomendaciones):** Hook `useRecomendaciones` verificado en `use-recomendaciones.ts:100`. Página confirmada en `frontend/src/app/dashboard/recomendaciones/page.tsx`.
- ✅ **6A.2 Endpoints BE (Recomendaciones):** `GET /plan-ia/recomendaciones` confirmado en `plan_ia.py:272`. `POST /plan-ia/generate/{dirigente_id}` confirmado en `plan_ia.py:69`. `PUT /{recomendacion_id}/estado` confirmado en `plan_ia.py:364`.
- ✅ **6A.3 Tabla DB (Recomendaciones):** Estructura de `recomendaciones_plan_ia` verificada vía `\d`. Check constraints para `estado` (7 valores) y `tipo` (3 valores) confirmados.
- ✅ **6B.2 Endpoint BE (Mi Evaluación):** `PATCH /dirigentes/{dirigente_id}/pesos` verificado en `dirigentes.py:368`.
- ✅ **6B.3 Columna DB (Mi Evaluación):** `dirigentes.pesos_target_politico` jsonb verificado.
- ✅ **6C.1 Vista FE (Reels):** Hooks `useGenerateReelScript` y `useRecentReelScripts` verificados en `use-reels.ts:57, 70`.
- ✅ **6C.2 Endpoints BE (Reels):** `POST /reels/generate-script` verificado en `reels.py:58`. `GET /reels/recent` verificado en `reels.py:182`.
- ✅ **6C.3 Pipeline (Reels):** Builder de contexto determinista y persistencia en `contenido_piezas` verificada en código.

## Citas sin verificar / inventadas
- ⚠️ **Afirmación §6A.2:** `GET /plan-ia/{id}/seguimiento` no existe en `plan_ia.py` ni en hooks FE (`use-recomendaciones.ts` solo lo menciona en comentarios de cabecera como "Agent A expone", pero no está implementado).
- ⚠️ **Afirmación §6C.4:** El doc dice "Tabla `reel_scripts` NO existe". Verificado: es correcto, pero se documenta como "hallazgo" algo que el propio doc asume. La persistencia real es en `contenido_piezas.variantes`.

## Omisiones detectadas
- ❌ **Endpoint transition:** `PUT /plan-ia/{id}/post-ejecutor` existe en `plan_ia.py:424` pero se marca en §6A.2 como "asumido/no verificado". Confirmado que existe.
- ❌ **Hook Mi Evaluación:** `useUpdateDirigentePesos` está en `use-dirigentes.ts:101`, no en `use-evaluacion.ts` (archivo inexistente). §6B.1 cita el hook pero no su ubicación exacta.
- ❌ **Task Status BE:** `GET /plan-ia/generate/status/{task_id}` existe en `plan_ia.py:474` para monitorear la generación de recomendaciones, no aparece en §6.

## Sesgo del redactor
- 🔍 **Inactividad aceptada:** Se afirma que la tabla `recomendaciones_plan_ia` está vacía (0 rows) y la feature pausada. Esto sesga la auditoría hacia el código y no hacia la data real, ya que no hay registros para validar el comportamiento del ciclo de estados.
- 🔍 **RBAC:** El doc afirma que viewer no ve `propuesta/rechazada`, pero no se verificó la lógica de filtrado en el service/handler, solo se cita el comportamiento esperado.

## Veredicto
⚠️ **Pasa con ajustes**

1. Eliminar referencia a `GET /plan-ia/{id}/seguimiento` (no existe).
2. Confirmar existencia de `PUT /plan-ia/{id}/post-ejecutor` en `plan_ia.py:424`.
3. Precisar ubicación de `useUpdateDirigentePesos` en `use-dirigentes.ts`.
4. Documentar `GET /plan-ia/generate/status/{task_id}` como endpoint de soporte para Recomendaciones.
