YOLO mode is enabled. All tool calls will be automatically approved.
YOLO mode is enabled. All tool calls will be automatically approved.
Ripgrep is not available. Falling back to GrepTool.
(node:5149) [DEP0190] DeprecationWarning: Passing args to a child process with shell option true can lead to security vulnerabilities, as the arguments are not escaped, only concatenated.
(Use `node --trace-deprecation ...` to show where the warning was created)
# Auditoría sección §7 — Overview y Dirigentes
**Fecha:** 2026-05-28
**Auditor:** Gemini
**Doc auditado:** .context/MAPA-FUNCIONAL.md
**Sección:** §7

## Citas verificadas
- ✅ `dashboard.py:60` para `GET /dashboard/overview` (scoping por rol/org verificado).
- ✅ `dashboard.py:269` para `GET /dashboard/status` (valores hardcoded confirmados).
- ✅ `alerts_integration.py:20` para `GET /alerts/`.
- ✅ `use-overview.ts:14` para `useKpiOverview`.
- ✅ `use-overview.ts:50` para `useSystemStatus`.
- ✅ `use-overview.ts:42` para `useCrisisAlerts` (filtro high/crisis verificado).
- ✅ `use-overview.ts:22` para `useAlerts`.
- ✅ `use-overview.ts:58` para `useHealthCheck` (apunta a `/health/`).
- ✅ `use-overview.ts:31` para `useTopDirigentes` (reutilización de `/dirigentes/` verificada).
- ✅ `dirigentes.py:37` para `list_dirigentes`.
- ✅ `dirigentes.py:127` para `get_dirigente` (check de 403 por org/id verificado).
- ✅ `dirigentes.py:301` para `create_dirigente`.
- ✅ `dirigentes.py:319` para `update_dirigente`.
- ✅ `dirigentes.py:364` para `update_dirigente_pesos` (Mi Evaluación).
- ✅ `dirigentes.py:421` para `delete_dirigente`.
- ✅ `dirigentes.py:438` para `get_diagnostico` (legacy IPD).
- ✅ `dirigentes.py:453` para `get_flash_analysis` (SQL aggregations pure).
- ✅ `dirigentes.py:591` para `get_social_summary`.
- ✅ `dirigentes.py:861` para `get_crecimiento` (denormalized snapshots).
- ✅ `use-dirigentes.ts:12` para `useDirigentes`.
- ✅ `use-dirigentes.ts:35` para `useDirigente`.
- ✅ `use-dirigentes.ts:68` para `useDirigenteCrecimiento`.
- ✅ `use-dirigentes.ts:77` para `useCreateDirigente`.
- ✅ `use-dirigentes.ts:88` para `useUpdateDirigente`.
- ✅ `use-dirigentes.ts:101` para `useUpdateDirigentePesos`.
- ✅ `use-dirigentes.ts:112` para `useDeleteDirigente`.
- ✅ `dashboard/page.tsx:28-33` comentario sobre Mapa Electoral oculto (INE shapefiles dependency).
- ✅ Cobertura SQL (§7.D): 13 dirigentes en 5 orgs y 9 con diagnóstico reciente confirmados vía `crece-db`.

## Citas sin verificar / inventadas
- ⚠️ `dirigentes.py:665`: La cita es correcta, pero el path en la tabla dice `POST /dirigentes/{id}/...`. En el código es `POST /dirigentes/onboard` (sin `{id}`).
- ⚠️ `dirigentes.py:770`: La cita es correcta, pero la función está como placeholder `(action)`. El nombre real es `get_onboarding_progress`.

## Omisiones detectadas
- ❌ **Hooks de Onboarding:** `useOnboardDirigente` y `useOnboardingProgress` (en `frontend/src/lib/api/hooks/use-onboarding.ts`) no aparecen en §7B.1 ni en la tabla de endpoints, a pesar de que sus endpoints están listados como placeholders.
- ❌ **Onboarding Wizard:** Falta mencionar el componente `onboarding-wizard.tsx` o su ruta en §7B.1.

## Sesgo del redactor
- 🔍 **Sub-regla #5 (Absolutos):** La afirmación sobre el bypass de Admin en `get_dirigente` se verificó por lectura de código, pero no se ejecutó una prueba de penetración empírica para confirmar que un usuario `viewer` realmente recibe 403 al intentar acceder a otro `org_id` (se asume correcto por el decorador `RoleChecker` y los `if` de seguridad).
- 🔍 **Cobertura:** No se auditaron dirigentes fuera del "batch piloto" de 13 para la sección de Overview.

## Veredicto
⚠️ **Pasa con ajustes**
1. Corregir el path del endpoint de onboarding en la tabla §7B.2 (es `/dirigentes/onboard`).
2. Reemplazar los placeholders `(action)` y `(verificar)` en §7B.2 por los nombres reales de las funciones: `onboard_dirigente` y `get_onboarding_progress`.
3. Agregar los hooks `useOnboardDirigente` y `useOnboardingProgress` a la lista §7B.1.
4. Mapear brevemente la existencia del flujo de Onboarding Wizard en el frontend.
