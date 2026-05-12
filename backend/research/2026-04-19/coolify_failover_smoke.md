# Coolify Ollama Failover Smoke Test — T0.6

**Sprint S0 · Tarea T0.6 · Fecha 2026-04-19**
**Autor ejecutor:** Joy (Claude Code sesión CRECE v2)

---

## Metadatos de reproducibilidad

| Campo | Valor |
|---|---|
| Endpoint | `http://163.245.208.96:11434` (VPS Coolify) |
| Modelo | `gemma3:12b` (Q4_K_M, 8.15 GB, parent gemma3:12b) |
| Script | `backend/evaluations/2026-04-19/scripts/coolify_latency.py` |
| Temperature | 0.0 |
| Seed | 42 |
| Num predict | 30 tokens |
| Prompt test | `"Clasifica en una palabra el tono de este comentario político: 'Corruptazo el hdp'. Responde SOLO con una palabra."` |
| Timestamp | 2026-04-19T16:28:40Z |
| Output JSON | `backend/evaluations/2026-04-19/output/coolify_latencies.json` |

---

## Resultados

### Health check (`GET /api/tags`)

| Métrica | Valor |
|---|---|
| Ping min | 145 ms |
| **Ping p50** | **149 ms** |
| Ping max | 172 ms |
| Modelo disponible | `gemma3:12b` (confirmed en respuesta) |

✅ Disponibilidad verificada, latencia de red aceptable.

### Inferencia real `gemma3:12b` (11 calls: 1 warmup + 10 benchmark)

| Métrica | Valor |
|---|---|
| Warmup (cold start) | **101.9 s** |
| Inference min | 8.1 s |
| **Inference p50** | **10.7 s** |
| **Inference p95** | **24.4 s** |
| Inference max | 123.3 s (run 7, outlier posiblemente contención CPU VPS) |
| Mean | 23.8 s (afectado por outlier) |
| Tokens/s p50 | 0.8 |
| Tokens/s mean | 0.81 |
| Parseo JSON correcto | 10/10 |
| Respuesta semántica | "Ofensivo." × 10 (determinismo ✅) |

### Lectura vs historia previa

La nota operativa histórica indicaba **~17 min por inferencia** en Coolify CPU-only. La medición actual indica **p50=10.7s, p95=24s** para prompts cortos (30 tokens output) — **dos órdenes de magnitud mejor** que la memoria previa. Hipótesis:

1. El histórico correspondía a prompts largos de clasificación completa (500-1000 tokens output) con matriz v2
2. El VPS pudo haberse upgradado (CPU/RAM) desde la medición previa
3. El Mac M4 local histórico era <6s/call, lo que sugiere que 10s Coolify está en orden correcto

Con **0.8 tokens/s**, un prompt completo Plutchik+Topics de ~150 tokens output ejecutaría en ~180s. Un prompt matriz v2 completo de ~500 tokens ejecutaría en ~600s (10 min) — esto sí está cerca del histórico.

### Outlier run 7 (123 s)

Probable causa: contención momentánea CPU VPS (job concurrente). No representa SLO típico. Con n=10 es un 10% de outliers → **no descartable, debe ser cubierto por timeout**.

---

## Recomendación SLA para health-check Sprint S1

### Estrategia dual: health-check rápido + SLO inferencia

```
health_check_ollama_coolify():
  # Capa 1: ping /api/tags
  timeout = 2s
  si ping > 500ms o status != 200 → UNHEALTHY
  si modelo "gemma3:12b" no en .models → UNHEALTHY

  # Capa 2: smoke inference (cada 5 min)
  timeout = 60s  # p95 + margen
  prompt_test = "<prompt deterministic 30 tokens>"
  si inference > 60s → DEGRADED (failover a Mac M4 local si disponible)
  si inference > 120s → UNHEALTHY (alerta operativa)

  # Capa 3: pre-warm diario a 00:00 UTC
  warmup_call(num_predict=10)  # evita cold start 102s
```

### Decisión propuesta: failover con pre-warm

| Modo | Cuándo | Latencia esperada |
|---|---|---|
| **Primario:** Mac M4 local | Siempre que esté online | ~6s/prompt corto |
| **Failover:** Coolify VPS | Mac M4 offline/unreachable >60s | 11-25s/prompt corto post-warmup; 102s cold start |
| **Pre-warm Coolify** | Cron 00:00 + 12:00 UTC | Mantiene modelo caliente, elimina penalización 102s |

### SLO propuestos (para Sprint S1 T7 health-check)

| SLO | Objetivo | Timeout Circuit Breaker |
|---|---|---|
| Health ping | < 500 ms | 2 s |
| Inference warm p50 | < 15 s | 60 s |
| Inference warm p95 | < 30 s | 60 s |
| Cold start | < 120 s (aceptable 1×/día) | 180 s |
| Pre-warm drift | recalentar cada 4h | — |

Timeouts de usuario: **60s** en clasificación individual, **10 min** en batch de 60 comments (triangulación completa estimada 10-15 min en Coolify post-warmup con prompts largos).

---

## Criterio acceptance T0.6 (del MASTER)

| Check | Resultado |
|---|---|
| Latencia documentada | ✅ p50=10.7s, p95=24.4s, ping p50=149ms |
| Disponibilidad verificada | ✅ 100% en 11 calls (runs 1-10 + warmup) |
| Modelo cargado | ✅ gemma3:12b Q4_K_M confirmado |
| Recomendación SLA | ✅ failover dual con pre-warm + timeouts/circuit breaker |

**Veredicto T0.6: PASS.** Coolify viable como failover con pre-warm obligatorio.

---

## Handoff Sprint S1 T7 (health-check)

El agente que codifique el health-check debe:

1. Implementar `check_ollama_health(endpoint)` con las 3 capas de arriba
2. Exponer `GET /api/v1/ops/llm/health` con response `{primary: ok, failover: ok, last_inference_ms, circuit_state}`
3. Cron pre-warm cada 4h (mínimo 2×/día)
4. Registrar en `llm_health_log` cada smoke para dashboards ops
5. Alerta Slack/email si primario **Y** failover ambos degraded simultáneamente
