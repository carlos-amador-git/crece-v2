---
adr: 0001
title: Ollama OFF · Plan IA pausado · migración a Claude Code + Gemini CLI
status: Accepted
date: 2026-05-15
author: HUMAN ceo
deciders: [ceo]
informed: [linda, joy]
supersedes: null
superseded_by: null
legacy_id: D-PLAN-IA-CC-GEMINI-CLI-1
legacy_path: .context/DECISIONS.md:113
---

## Title

ADR-0001 · Ollama OFF · Plan IA pausado · migración a Claude Code + Gemini CLI

## Status

Accepted (2026-05-15)

## Context

Auditoría B3 (CRIT-PLAN-IA) descubrió que el pipeline de generación de planes IA en producción dependía de un servicio Ollama remoto en VPS Coolify (`http://163.245.208.96:11434`, modelo `gemma3:12b`) invocado vía Celery `plan_ia_generate_async` desde `backend/app/services/plan_ia/llm_pipeline.py`.

Estado real descubierto al momento de la decisión:

- `backend/app/services/plan_generator.py` con `_generate_claude` (Anthropic SDK) era **dead code** — ningún endpoint activo lo invocaba.
- Endpoint `POST /api/v1/plan-ia/generate/{dirigente_id}` invocaba el llm_pipeline → Ollama VPS.
- Histórico `planes_ia` en BD mostraba 9 modelos distintos, incluyendo 3 planes generados manualmente por CEO con `claude-opus-4.6+gemini-2.5-pro` (validación del patrón deseado).
- Coolify VPS no estaba dimensionado para sostener carga LLM con baja latencia ni alta disponibilidad.

El CEO clarificó textualmente: *"El binario es CC (Claude Code, tú) y Gemini CLI, Ollama está off hasta que no mejoremos el VPS o lo corramos programado en la madrugada. No hay API de ningún tipo."*

## Decision

**Pausar endpoint sin borrar código.** Tres acciones inmediatas:

1. `POST /api/v1/plan-ia/generate/{dirigente_id}` retorna HTTP 503 con mensaje explicativo "Feature pausada · refactor en curso".
2. `plan_generator.py` mantiene código con header `# DEAD MODULE` documentando refactor pendiente.
3. Frontend `/dashboard/planes` botón "Generar Plan" disabled con tooltip "Feature pausada · refactor a Claude Code + Gemini CLI pendiente".

**Refactor pendiente (sprint propio):**
- Reemplazar `_call_ollama` en `llm_pipeline.py` con `_call_cc_subprocess` (default) + `_call_gemini_cli_subprocess` (fallback).
- Mantener `_call_ollama` como tercer fallback dormant para uso futuro cuando VPS esté dimensionado.
- Tests E2E del pipeline con subprocess.

**Out of scope para esta pausa:** generador de reels (feature nueva con Groq tier gratuito, ver decisión hermana D-REELS-GROQ-1).

## Consequences

### Positivas
- **Cliente no ve fallos intermitentes** de timeout Coolify (B-26-01 cerrado).
- **CEO continúa generando planes manualmente** fuera del sistema (3 planes ya existentes confirman patrón).
- **Refactor no urgente** porque generación se hace por sprint operativo, no por demanda cliente.
- Decisión arquitectónica preserva la opción Ollama VPS para el futuro sin descartar trabajo previo.

### Negativas
- **`useGeneratePlan` hook FE roto.** El hook FE sigue apuntando a `/planes/generate` (no `/planes/generar`, ADR pendiente) Y al endpoint pausado. Doble falla serializada al usuario. Detectado por audit MAPA §4 (2026-05-28).
- **Endpoint pausado tiene comportamiento engañoso para integradores externos** que esperan funcionalidad LLM. Solución: tag `503` claro + tooltip FE.
- **3 endpoints muertos.** `plan_generator.py` queda con header `# DEAD MODULE` pero no se borra — riesgo de confusión futura.
- **Scripts batch** (`regen_consolidacion_v2.py`, `regen_contenido_v2.py`, `regen_plan_dirigente.py`) sostienen la operación. Mayor dependencia operativa de scripts manuales.

### Riesgos aceptados
- Si en algún momento el CEO retoma generación cliente-facing → tendrá que ejecutarse el refactor pendiente antes de despausar.
- Coolify VPS sigue gastando recursos por Ollama corriendo (si está prendido). No urgent shutdown porque otros productos lo comparten (ver `reference_coolify_services`).

## Confirmation

Verificado:
- Endpoint backend `POST /plan-ia/generate/{dirigente_id}` retorna 503 (test con `curl`).
- Tab Diagnóstico en `/dashboard/planes` removido posteriormente (D-PLANES-DIAGNOSTICO-REMOVED 2026-05-22 · MAPA §4.1).
- BD `planes_ia` no recibe inserts del endpoint pausado desde 2026-05-15 (verificable via `SELECT COUNT(*) FROM planes_ia WHERE created_at > '2026-05-15' AND modelo_ia LIKE '%ollama%'` → 0).
- Scripts batch productivos: `cc-consolidacion-v2-2026-05-21` (11 planes), `cc-contenido-v2-2026-05-21` (11), `cc-claude-inline-2026-05-27` (7).

## More Information

- Texto original: `.context/DECISIONS.md` línea 113-140.
- Memoria persistente: `~/.claude/projects/-Users-marxchavez-Projects-crece-v2/memory/feedback_demo_philosophy.md`.
- Cross-reference MAPA: §4 Planes IA · §4.6 Deuda · `useGeneratePlan` roto.
- Blocker relacionado: B-26-01 Plan IA timeout Coolify (cerrado por esta decisión).
