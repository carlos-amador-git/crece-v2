# Auditoría sección §2 — Recepción / Diagnóstico Tier 1 (B01-B10)
**Fecha:** 2026-05-28
**Auditor:** Gemini
**Doc auditado:** .context/MAPA-FUNCIONAL.md
**Sección:** §2

## Citas verificadas
- ✅ **Endpoint agregado `/diagnostico/{id}`**: confirmado en `diagnostico.py:196`. Implementa la ejecución secuencial de los 10 services sobre la misma sesión de DB para evitar contención.
- ✅ **Citas de endpoints individuales (B01-B10)**: confirmadas en `diagnostico.py` líneas 47, 60, 72, 84, 96, 108, 120, 132, 145, 157.
- ✅ **Endpoint drill-down Humanización**: confirmado en `diagnostico.py:169`.
- ✅ **Endpoint FODA**: confirmado en `diagnostico.py:442`.
- ✅ **Hooks FE**: `useDiagnosticoTier1` (`use-diagnostico-tier1.ts:212`) y `useHumanizacionExamples` (`use-diagnostico-tier1.ts:222`) verificados con rutas y tipos correctos.
- ✅ **Catálogo de componentes CardB01-CardB10**: confirmados en `cards.tsx` con las líneas citadas (81, 196, 254, 329, 437, 501, 544, 627, 681, 726, 840).
- ✅ **Services backend**: los 10 services existen en `backend/app/services/diagnostico/` y sus docstrings coinciden con las citas en §2.3.
- ✅ **Cobertura DB Global**: query SQL ejecutada contra `crece-db`. `engagement_rate` (93%), `sentiment_score` (72%), `emotions` (89%), `topics_extracted` (81%). Coincide exactamente con §2.5.
- ✅ **Cobertura Felipe (60) y Saymi (3)**: verificado por query SQL. Felipe 197 posts / 135 sentiment (69%). Saymi 2,173 posts / 1,335 sentiment (61%). Coincide exactamente con §2.5.
- ✅ **Precondición `social_profiles=0`**: verificado en `_common.py` y su uso en 8 de 10 services (excluyendo Benchmark y SoV que usan motivos específicos).
- ✅ **Deuda B04 Benchmark**: verificado en `benchmark_service.py` docstring sobre `competidor_directo_ids=[]` en piloto S2.
- ✅ **Deuda B07 Growth Attribution**: verificado en comentarios de código y memoria sobre dependencia de timeseries de followers.

## Citas sin verificar / inventadas
- *Ninguna. Todas las citas en esta sección fueron validadas contra el código y la base de datos.*

## Omisiones detectadas
- *Ninguna. Se revisaron todos los endpoints de `diagnostico.py`, todos los hooks de `use-diagnostico-tier1.ts` y todos los componentes de `cards.tsx`. Todo lo relevante está documentado en la sección.*

## Sesgo del redactor
- **Focalización en Dirigentes**: El redactor explícitamente declara haber verificado cobertura solo para el "Golden Set" (dirigentes 1,2,3,5,8,57,60). Dirigentes 4, 6, 7, 58 y 59 están en DB pero no fueron auditados en este pase de cobertura.
- **Modelo de Tópicos**: La mención a "Gemma 3:12b" para tópicos es coherente con los handoffs y el `OLLAMA_MODEL` configurado, aunque en DB la versión aparece como `cc-topics-v1-2026-05-21` (nombre de la corrida de batch).

## Veredicto
✅ **Pasa**
