# Auditoría — MAPA-FUNCIONAL.md, §1 — Aceptación + Fans y Perfiles
**Fecha:** 2026-05-28
**Auditor:** Gemini
**Doc auditado:** /Users/marxchavez/Projects/crece-v2/.context/MAPA-FUNCIONAL.md
**Sección:** §1

## Citas verificadas
- ✅ Línea 46: `frontend/src/app/dashboard/aceptacion/page.tsx` existe y usa `useAceptacionOverview`.
- ✅ Línea 54: `frontend/src/app/dashboard/aceptacion/[dirigente_id]/page.tsx` existe.
- ✅ Línea 65: `frontend/src/app/dashboard/aceptacion/fans-y-perfiles/page.tsx` existe.
- ✅ Línea 78: `backend/app/api/v1/endpoints/indice_aceptacion.py` contiene los 4 endpoints listados con sus decoradores `@router` correspondientes.
- ✅ Línea 82: `GET /social/dirigentes/{dirigente_id}/ia-summary` verificado en `indice_aceptacion.py:155`.
- ✅ Línea 83: `GET /social/aceptacion/overview` verificado en `indice_aceptacion.py:228`.
- ✅ Línea 84: `GET /social/aceptacion/fantasmas-por-plataforma` verificado en `indice_aceptacion.py:313`.
- ✅ Línea 87: Fórmula de fantasmas `pct_fantasma = 100 - pct_activados` verificada en `indice_aceptacion.py:352`.
- ✅ Línea 99: `backend/app/api/v1/endpoints/watched_profiles.py` contiene los 11 endpoints listados en la tabla (excepto uno, ver omisiones).
- ✅ Línea 112: Tabla `dirigentes`, `social_profiles`, `social_posts`, `social_comments`, `watched_profiles`, `watched_like_events` verificadas en DB.
- ✅ Línea 118: `watched_profiles` tiene 17 columnas (verificado con `\d watched_profiles`).

## Citas sin verificar / inventadas
- ⚠️ Línea 62: `useWatchedTimeline` y `useWatchedSummary` no se usan directamente en `[dirigente_id]/page.tsx`, sino en sus componentes hijos (`timeline-chart.tsx` y `watched-profiles-tab.tsx`).
- ❌ Línea 70: Hook `useCreateWatched` NO existe en `frontend/src/lib/api/hooks/use-watched-profiles.ts`. No se encontró definición de `useMutation` para POST en dicho archivo.

## Omisiones detectadas
- ❌ Endpoint `POST /api/v1/aceptacion/watched-profiles/ingest-reactions-bulk` existe en `watched_profiles.py:726` pero no aparece en la tabla §1.2.
- ❌ Hook `useIAPost` existe en `use-indice-aceptacion.ts:40` pero no está documentado en la tabla §1.2.

## Sesgo del redactor
- 🔍 El doc declara explícitamente en §1.4 que la cobertura solo fue verificada para los dirigentes in-scope (1, 2, 3, 5, 8, 57, 60). Se confirmó en DB que existen otros dirigentes (4, 6, 7, 58, 59) que no son mencionados en el análisis de gaps.

## Veredicto
⚠️ Pasa con ajustes (lista):
1. Eliminar o corregir referencia a `useCreateWatched` (no existe).
2. Agregar `POST /ingest-reactions-bulk` a la tabla de endpoints de Watched Profiles.
3. (Opcional) Agregar `useIAPost` a la tabla de Índice de Aceptación para completitud.
