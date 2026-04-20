# SPRINT-CURRENT — Sprint S4 Plan IA con LLM + Cierre de Ciclo

**Sprint actual:** S4 · **Status:** 🟢 EN EJECUCIÓN autónoma · autorizado CEO 2026-04-19 post-merge PR #28 con 4 integraciones
**Sprint previo:** S3 · `.context/archive/sprint-s3-2026-04-19.md` · reporte `backend/research/2026-04-19/SPRINT-S3-REPORTE-EJECUTIVO.md`
**Decisiones vinculantes:** D-17 (cierre ciclo Plan IA 5 fases) · D-19 (matriz 5×5) · D-22 (competidores client-owned) · D-23 (HITL onboarding) · **D-24 (estructura prompt 8-bloques + changelog versionable)**

**Documento pre-requisitos aprobado:** `backend/research/2026-04-19/SPRINT-S4-PRE-REQUISITOS.md` · §3.6.1 MASTER

---

## Objetivo

Implementar **Plan IA con ciclo completo 5 fases** (D-17): generación → decisión → ejecución → seguimiento → cierre. Consumo de los 18 bloques del diagnóstico + RAG histórico + anatomía §2.6.7 obligatoria. Pipeline LLM Gemma 3:12b local + admin panel MD review HITL + UI cliente decisión + servicio seguimiento 14d + cierre automático + memoria #10.7.

**Criterio acceptance:** CEO recibe reporte semanal + flujo E2E: 1 recomendación generada → aprobada MD review → aprobada cliente → post publicado vinculado → seguimiento 14d → veredicto automático + edición cliente → aparece en memoria histórica.

---

## T-1 · Pre-requisitos aprobados CEO §9.8 previa (4 componentes)

### T-1.1 Seed 10 promesas Piña (MD arranque mínimo, resto Onboarding S5)
- [ ] Script `backend/scripts/seed_promesas_pina_s4.py` idempotente con 10 promesas realistas
- [ ] Endpoint admin `POST /api/v1/admin/promesas` minimal
- [ ] Verificar B16 Piña pasa de `insufficient_data` a `ok`

### T-1.2 Umbrales operativos documentados
- [ ] `backend/research/2026-04-19/UMBRALES-OPERATIVOS-S4.md`
  - Topic Drift delta ±15% vs baseline · calibración 30d (flag rate 15-40%)
  - CIB confidence ≥0.70 para recomendación Plan IA
  - Humanización target por perfil §1.5 (4 rangos)

### T-1.3 Prompt Plan IA v1 versionable
- [ ] `backend/research/2026-04-19/PROMPT-PLAN-IA-v1.md` con:
  - Frontmatter `version: "1.0" · fecha: 2026-04-19 · status: approved`
  - Changelog obligatorio al inicio
  - 8 bloques completos (rol + contexto + 18 bloques JSON + **delta B13 dinámica** + behavioral library + tarea + JSON schema + **constraint anti-vanidad**)
  - Schema JSON de salida mapeado a `recomendaciones_plan_ia` §6.3.2

### T-1.4 Anti-vanity validator post-generación
- [ ] `backend/app/services/plan_ia/anti_vanity_validator.py`
  - Rechaza recomendación si no cita ≥1 bloque B01-B18 + evidencia (post_id/métrica/ventana)
  - Re-solicita al LLM con feedback explícito cuando rechaza
  - Test unitario con casos positivos (cita válida) y negativos ("publica más contenido")

---

## S4 Core · 11 tareas D-17 (6-8 días)

### T1 · Pipeline LLM Gemma 3:12b
- [ ] `backend/app/services/plan_ia/llm_pipeline.py` consume 18 bloques + behavioral library + PROMPT v1
- [ ] temperature=0.2 · seed=42 · timeout 90s warm · 180s cold (D-21 SLO)
- [ ] Integra anti-vanity validator T-1.4 como post-processor

### T2 · Prompt engineering §2.6.7 obligatoria
- [ ] Verifica que cada recomendación tiene los 5 elementos de la anatomía
- [ ] Schema enforcement JSON estricto

### T3 · RAG histórico dirigente + competidores
- [ ] pgvector embeddings de posts + recomendaciones previas del Plan IA
- [ ] Bloque #10.7 Memoria inyectable al prompt

### T4 · Generación persistible `recomendaciones_plan_ia`
- [ ] `POST /api/v1/plan-ia/generate/{dirigente_id}` crea fila con `estado='propuesta'`
- [ ] Persiste principio conductual + evidencia + ventana + criterio éxito

### T5 · Admin panel `/dashboard/admin/plan-ia-review`
- [ ] Cola de recomendaciones `estado='propuesta'` para MD review
- [ ] Acciones: aprobar (→ cliente_visible), rechazar (→ descartada), modificar (→ editada)
- [ ] **Sin este panel, Plan IA NO sale a producción** (§3.6 MASTER HITL obligatorio)

### T6 · UI cliente `/dashboard/recomendaciones`
- [ ] Cliente ve las recomendaciones aprobadas
- [ ] Acciones: aprobar · rechazar · modificar con justificación

### T7 · Vinculación post ejecutor
- [ ] Cliente publica contenido → UI permite `post_ejecutor_id` FK a social_posts

### T8 · Servicio seguimiento 14d ventana
- [ ] Celery task diaria que actualiza `metricas_observadas` de recomendaciones en ventana
- [ ] UI bloque #10.5 con evolución métricas observadas vs predichas

### T9 · Servicio cierre automático
- [ ] Al vencer ventana: veredicto automático por `criterio_exito` numérico
- [ ] Opción edición cliente preservando `veredicto_original`

### T10 · Bloque #10.7 Memoria Plan IA
- [ ] Dashboard agregado con tasa de éxito por categoría + drill-down histórico
- [ ] Feedback loop: las recomendaciones exitosas sesgan el RAG T3 positivamente

### T11 · Reporte semanal MD/PDF
- [ ] Cron weekly que genera 1 pagina PDF para CEO + email configurable

---

## Observaciones operativas CEO integradas

1. **B13 Filtro Realidad delta dinámica** → bloque 4 del prompt NUNCA cableado al 16% de Piña, cada dirigente recibe su valor real calculado en `generate()` al inicio.
2. **Ninguna recomendación acciona bloqueo CIB sin HITL §3.6** → restricción dura en bloque 1 del prompt. Máxima recomendación sobre CIB: "revisar con MD las N cuentas flagged (confidence ≥0.70) antes de decidir acción".

---

## Paralelización operativa

- **Agent A** (backend-architect): T-1.1 + T-1.2 + T-1.3 + T-1.4 + T1 + T2 + T3 + T4 · Pipeline LLM completo backend
- **Agent B** (backend-architect): T8 + T9 + T10 + T11 · Servicios de seguimiento, cierre, memoria, reporte
- **Agent C** (frontend-architect): T5 + T6 + T7 · Admin panel + UI cliente + vinculación post

Clock estimado: **3-4 días wall-clock con 3 agents concurrentes** (vs 6-8 días serial D-17).

---

## Criterio acceptance del Sprint S4

Sprint S4 se declara completo cuando:

1. T-1 completo (seed promesas + umbrales + prompt v1 + validator)
2. Pipeline LLM genera recomendaciones con anatomía §2.6.7 completa (≥80% parse rate)
3. Admin panel operativo y utilizable por MD (al menos 1 recomendación aprobada a mano)
4. Flujo E2E completo: 1 recomendación generada → aprobada MD → aprobada cliente → post vinculado → seguimiento activo
5. Memoria #10.7 con ≥1 recomendación `completada` y su veredicto registrado
6. Reporte semanal generado correctamente al menos una vez

Con 5/6 → arranque Sprint S5 autorizado (Onboarding Wizard Meta OAuth).

---

## Protocolo cierre

Archivar a `.context/archive/sprint-s4-2026-04-19.md` + reset S5. Reporte ejecutivo `SPRINT-S4-REPORTE-EJECUTIVO.md` + revisión §9.8 CEO.
