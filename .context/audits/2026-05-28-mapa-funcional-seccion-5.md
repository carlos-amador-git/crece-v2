# Auditoría sección §5 — Clima Político
**Fecha:** 2026-05-28
**Auditor:** Gemini
**Doc auditado:** .context/MAPA-FUNCIONAL.md
**Sección:** §5

## Citas verificadas
- ✅ **Vista FE:** `/dashboard/social/clima/` mapea correctamente a `frontend/src/app/dashboard/social/clima/page.tsx`.
- ✅ **Hook FE:** `useClimaPolitico(metrica)` definido en `frontend/src/lib/api/hooks/use-clima-politico.ts:19` con `staleTime: 5 min` y llamada a `/social/clima-politico`.
- ✅ **Endpoint Backend:** `GET /social/clima-politico` localizado en `backend/app/api/v1/endpoints/social.py:473`.
- ✅ **Filtro de fuentes:** La sentencia SQL en `social.py:503` confirma el whitelist de `Demoscopía Digital`, `Oraculus poll-of-polls` y `Mitofsky`.
- ✅ **Lógica de agregación:** Se verificó el uso de `AVG(valor_pct)` y el agrupamiento por actor/ámbito/entidad/municipio/fecha en `social.py:496-508`.
- ✅ **Dedup en Python:** Se confirmó el uso de `seen` dict con clave triple para alcaldes y doble para otros en `social.py:516-521`.
- ✅ **Cobertura DB:** La query SQL del §5.3 fue ejecutada contra la DB real, arrojando resultados idénticos a los documentados (~19,328 filas totales de las 3 fuentes).
- ✅ **CRUD Simétrico:** Se confirmó vía `grep` que no existen endpoints POST/PUT/DELETE para `encuestas_publicas`, tal como indica el §5.5 ("no expuesto por API actual").

## Citas sin verificar / inventadas
- (Ninguna. Todas las referencias a líneas de código y resultados de DB coinciden con el estado actual del repo).

## Omisiones detectadas
- (Ninguna. El módulo de `encuestas` (operación territorial) está correctamente diferenciado del módulo de `clima-politico` (encuestas públicas), cumpliendo la advertencia del §5: "NO `encuestas` ni `encuestas_resultados`").

## Sesgo del redactor
- 🔍 **Hardcoding incompleto:** El §5.4 menciona que `EXPRESIDENTES` incluye "AMLO, EPN, FCH", pero la implementación real en `page.tsx:46` también incluye a "Vicente Fox Quesada" y "Ernesto Zedillo Ponce de León".
- 🔍 **Métrica "ambas":** Se verificó que el endpoint efectivamente retorna el doble de filas cuando `metrica=ambas`, pero no se detectó impacto en performance con el volumen actual de datos (~400 puntos por actor).

## Veredicto
✅ **Pasa**

El documento es un reflejo fiel de la implementación técnica y el estado de la data. La diferenciación entre los dos sistemas de encuestas (campo vs. público) es correcta y evita confusiones críticas de arquitectura.
