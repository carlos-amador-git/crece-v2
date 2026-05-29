YOLO mode is enabled. All tool calls will be automatically approved.
YOLO mode is enabled. All tool calls will be automatically approved.
Ripgrep is not available. Falling back to GrepTool.
(node:973) [DEP0190] DeprecationWarning: Passing args to a child process with shell option true can lead to security vulnerabilities, as the arguments are not escaped, only concatenated.
(Use `node --trace-deprecation ...` to show where the warning was created)
# Auditoría sección §3 — FODA
**Fecha:** 2026-05-28
**Auditor:** Gemini
**Doc auditado:** .context/MAPA-FUNCIONAL.md
**Sección:** §3

## Citas verificadas
- ✅ `/dashboard/diagnostico/foda/` -> `frontend/src/app/dashboard/diagnostico/foda/page.tsx` (redirige según JWT).
- ✅ `/dashboard/diagnostico/[dirigenteId]/foda/` -> `frontend/src/app/dashboard/diagnostico/[dirigenteId]/foda/page.tsx`.
- ✅ Hook `useFoda` (inline) en `[dirigenteId]/foda/page.tsx:36-44` con `staleTime: 5min`.
- ✅ Response type `FodaResponse` en `[dirigenteId]/foda/page.tsx:24-34`.
- ✅ Endpoint `GET /diagnostico/foda/{dirigente_id}` en `backend/app/api/v1/endpoints/diagnostico.py:442`.
- ✅ Lógica de handler `get_diagnostico_foda` en `diagnostico.py:442-520` verificada (incluye scope check, fallback parsing y link a plan derivado).
- ✅ Tabla `planes_ia` schema y columnas verificado vía `\d planes_ia`.
- ✅ Cobertura DB: 35 registros `DIAGNOSTICO`. Saymi (8), Pepe (5), Felipe (1), etc. coincide con §3.4.
- ✅ Generadores en `backend/scripts/` verificados. `regen_consolidacion_v2.py:153` usa efectivamente `riesgos` como key de validación.

## Citas sin verificar / inventadas
- (Ninguna. Todas las rutas y líneas citadas existen y contienen lo afirmado).

## Omisiones detectadas
- ❌ **Endpoint de generación:** No se menciona `POST /api/v1/planes/generar` (en `planes.py:84`) como vía de la API para disparar la generación de un nuevo FODA (`tipo=DIAGNOSTICO`). Solo se listan scripts en §3.5.
- ❌ **Inconsistencia de keys:** Aunque se menciona la deuda en §3.6, no se especifica que 14 de los 35 registros (40%) en `planes_ia` tienen `estructura_json` como NULL, lo que hace que el fallback `_parse_foda` sea crítico para la retrocompatibilidad, no solo una "legacy safety net" para casos raros.

## Sesgo del redactor
- 🔍 **Dirigentes omitidos:** La tabla §3.4 omite mencionar a los dirigentes que NO tienen FODA (id 7: Máynez, 58: Ivette, 59: Susana, 56: RSS Bot). 4 de 13 dirigentes están fuera del radar de esta sección.
- 🔍 **Felipe (60):** Se afirma que tiene 1 FODA pre-ingest. Verificado SQL: creado 2026-05-27 23:37. Correcto.

## Veredicto
⚠️ **Pasa con ajustes**

**Ajustes requeridos:**
1. Agregar el endpoint `POST /api/v1/planes/generar` a la tabla de endpoints o a la sección de generadores.
2. Cuantificar la deuda de `estructura_json`: 40% de los registros actuales dependen del parser markdown.
3. Mencionar explícitamente qué dirigentes faltan por procesar (Máynez, Ivette, Susana) para completar la cobertura.
