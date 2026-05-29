YOLO mode is enabled. All tool calls will be automatically approved.
YOLO mode is enabled. All tool calls will be automatically approved.
Ripgrep is not available. Falling back to GrepTool.
(node:7457) [DEP0190] DeprecationWarning: Passing args to a child process with shell option true can lead to security vulnerabilities, as the arguments are not escaped, only concatenated.
(Use `node --trace-deprecation ...` to show where the warning was created)
# Auditoría sección §8 — Sección 8
**Fecha:** 2026-05-28
**Auditor:** Gemini
**Doc auditado:** .context/MAPA-FUNCIONAL.md
**Sección:** §8

## Citas verificadas
- ✅ **Backend Endpoints:** Las 9 rutas en `backend/app/api/v1/endpoints/diagnostico_tier2.py` coinciden exactamente con las líneas 45, 57, 69, 81, 93, 105, 117, 130 y 142.
- ✅ **Frontend Hook:** `useDiagnosticoTier2` en `frontend/src/lib/api/hooks/use-diagnostico-tier-2.ts:228` confirmado.
- ✅ **Frontend Components:** `CardB11` hasta `CardB18` en `frontend/src/components/diagnostico_tier2/cards.tsx` coinciden con las líneas 76, 172, 276, 404, 508, 620, 741 y 861.
- ✅ **Skeleton:** `CardTier2Skeleton` en la línea 972 de `cards.tsx` confirmado.
- ✅ **Separación Tier 1 / Tier 2:** Se confirmó vía `grep` que `diagnostico.py` (Tier 1) y `diagnostico_tier2.py` (Tier 2) son disjuntos, validando la "Corrección 2026-05-28".

## Citas sin verificar / inventadas
- ❌ **Tabla `cib_flags` (§8.4):** Inexistente. El servicio `cib_detector_service.py` realiza el análisis CIB (Maestros, Coro, New authors) íntegramente en memoria sobre los comentarios cargados de la ventana actual. No existe persistencia en tabla `cib_flags`.
- ⚠️ **Tabla `promesas` (§8.4):** El nombre real en la base de datos es `promesas_dirigente`.
- ⚠️ **Relación `veda_compliance_service` (§8.4):** El servicio no utiliza la tabla `alertas_compliance` (que sí existe en DB); el cálculo es heurístico sobre `social_posts`.

## Omisiones detectadas
- ❌ **Campos DB en §8.4:**
    - Faltan `topics_extracted` (usado por B14 Topic Drift) y `engagement_rate` (usado por B15 Rage Click) en la fila de `social_posts`.
    - Faltan `nlp_tono`, `nlp_target` y `nlp_polaridad` (usados por B11, B14, B15, B18) en la fila de `social_comments`.
- ❌ **Helpers de Seguridad:** La función `_resolve_org_id` en `diagnostico_tier2.py` (línea 37) es crítica para el multi-tenant scoping pero no se menciona como componente lógico.

## Sesgo del redactor
- 🔍 **Falle de Cobertura B16:** Se verificó vía SQL que la tabla `promesas_dirigente` solo tiene registros para el `dirigente_id = 1` (Piña, 12 registros). Todos los demás dirigentes (12 de 13 activos) darán `insufficient_data` en B16, hecho no enfatizado en el documento.
- 🔍 **Sesgo de Roles:** Se auditó la lógica RBAC de scoping por lectura de código, pero no se realizaron pruebas de penetración cross-tenant empíricas.

## Veredicto
⚠️ **Pasa con ajustes**

**Ajustes requeridos:**
1. Eliminar la tabla `cib_flags` de §8.4 y §8.5; aclarar que la detección es en memoria.
2. Corregir nombre de tabla `promesas` a `promesas_dirigente`.
3. Completar la lista de columnas utilizadas en §8.4 para `social_posts` y `social_comments`.
4. Reflejar en "Deuda y estado real" que B16 es funcional únicamente para Piña (id:1) actualmente.
