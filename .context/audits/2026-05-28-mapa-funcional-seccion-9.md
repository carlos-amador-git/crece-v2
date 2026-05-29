YOLO mode is enabled. All tool calls will be automatically approved.
YOLO mode is enabled. All tool calls will be automatically approved.
Ripgrep is not available. Falling back to GrepTool.
Attempt 1 failed: You have exhausted your capacity on this model. Your quota will reset after 1s.. Retrying after 5958ms...
# Auditoría sección §9 — Sección 9
**Fecha:** 2026-05-28
**Auditor:** Gemini
**Doc auditado:** .context/MAPA-FUNCIONAL.md
**Sección:** §9

## Citas verificadas
- ✅ `frontend/src/app/dashboard/sistema/metodologia/page.tsx` existe y es una vista informativa estática (confirmado por lectura de archivo).
- ✅ `frontend/src/app/dashboard/settings/analisis-politico/page.tsx` existe y es una vista informativa con UI gamificada (confirmado por lectura de archivo).
- ✅ `frontend/src/app/dashboard/settings/evaluacion-nlp/page.tsx` existe y renderiza el cliente HITL (confirmado por lectura de archivo).
- ✅ `frontend/src/app/dashboard/sistema/onboarding/page.tsx` existe y renderiza el `OnboardingWizard` (confirmado por lectura de archivo).
- ✅ `frontend/src/app/dashboard/settings/page.tsx` existe y consume `useSystemStatus` y `useKpiOverview` (confirmado por lectura de archivo).

## Citas sin verificar / inventadas
- ⚠️ §9.B afirma que `evaluacion-nlp/` tiene "(pendiente verificar interacciones)". Las interacciones han sido verificadas en esta auditoría: consumen `hitlApi` (`/hitl/*`), por lo que la cita de "pendiente" está desactualizada.

## Omisiones detectadas
- ❌ **Endpoints omitidos en §9:** El módulo "Evaluación NLP" (mencionado en §9.B) consume los endpoints `/hitl/sample`, `/hitl/comments/{id}`, `/hitl/comments/{id}/confirm`, `/hitl/posts/{id}`, `/hitl/posts/{id}/confirm` (definidos en `backend/app/api/v1/endpoints/hitl_evaluation.py`). Estos endpoints no aparecen en la sección §9 pese a ser el motor de una de sus páginas.
- ❌ **Hooks omitidos en §9:** El cliente de API `frontend/src/lib/api/hitl.ts` y sus tipos asociados no se mencionan en §9.
- ❌ **Componentes omitidos:** `EvaluacionNlpClient.tsx` y `OnboardingWizard` son componentes críticos para la funcionalidad de esta sección y no se listan en el desglose de vistas.

## Sesgo del redactor
- 🔍 **Falsos absolutos (Sub-regla #5):** La sección afirma en el concepto inicial que la mayoría de las páginas son "estáticas (sin hooks ni endpoints)". Sin embargo, 3 de las 5 páginas listadas (`settings`, `onboarding`, `evaluacion-nlp`) consumen hooks (`useAuth`, `useSystemStatus`, `useKpiOverview`, `useOnboarding*`) y endpoints dinámicos.
- 🔍 **Contradicción Cross-Sección:** El módulo HITL se clasifica en §10 como "Admin (no-cliente)" y "NO visibles al cliente", pero en §9 se documenta una página de configuración (`/dashboard/settings/evaluacion-nlp/`) que permite al dirigente (cliente) usar estos mismos endpoints para validar su propia actividad (confirmado por RBAC en `hitl_evaluation.py:20`).

## Veredicto
⚠️ **Pasa con ajustes**
1. Eliminar "(pendiente verificar interacciones)" de §9.B ya que se confirmaron vía `hitlApi`.
2. Corregir afirmación absoluta §9 "sin hooks ni endpoints" (solo aplica a 2 de 5 páginas).
3. Incluir tabla de endpoints/hooks para el submódulo Evaluación NLP en §9.2 o cross-referenciar a §10 corrigiendo el sesgo de "solo admin".
4. Declarar explícitamente el uso de `OnboardingWizard` y sus hooks/endpoints asociados en la subsección de Onboarding.
