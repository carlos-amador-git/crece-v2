# SPRINT-CURRENT — Sprint S2 Diagnóstico Tier 1 (Core MVP)

**Sprint actual:** S2 · **Status:** 🟢 EN EJECUCIÓN · autorizado CEO 2026-04-19 post-merge PR #24 + PR #25 (D-23 clarificada)
**Sprint previo cerrado:** S1 · 2026-04-19 · archivo `.context/archive/sprint-s1-2026-04-19.md` · reporte `backend/research/2026-04-19/SPRINT-S1-REPORTE-EJECUTIVO.md`
**Reporte ejecutivo S2:** `backend/research/2026-04-19/SPRINT-S2-REPORTE-EJECUTIVO.md` (al cierre)
**Decisiones vinculantes:** D-19 reescrita (matriz 5×5 · modificador temporal) · D-22 (competidores client-owned · usar proxies de desarrollo en S2) · D-23 (confirmación humana obligatoria · SERP opcional)

---

## Objetivo

Implementar los **10 bloques Tier 1 Core MVP** del diagnóstico digital. Cada bloque = backend service + endpoint REST + frontend card + test E2E contra data real de los 8 dirigentes piloto.

**Criterio acceptance:** `/dashboard/diagnostico/{dirigente_id}` muestra 10 cards vivas para Piña (id=1) con data real de scrapers. CEO navega y ve números coherentes.

---

## 10 bloques Tier 1 (MASTER §3.1)

| # | Bloque | Pregunta | Inputs críticos | Fuente |
|---|---|---|---|---|
| B01 | ER normalizado por estrato | ¿Mi ER está en rango? | posts.likes/comments/views + profile.followers + estrato + matriz 5×5 + modificador temporal D-19 | §3.1 #01 |
| B02 | Breakout Scale Brookings (Cat 1-6) | ¿Crucé fronteras algorítmicas? | posts.views + engagement_rate + baseline_er | §3.1 #02 |
| B03 | Matriz 2×2 contenido (4 cuadrantes) | ¿Qué posts amplificar/matar? | engagement_rate + sentiment + topic | §3.1 #03 |
| B04 | Benchmark competidores (proxies D-22) | ¿Cómo me comparo con rivales? | competidor_directo_ids (proxies S2) + últimas 4 semanas | §3.1 #04 |
| B05 | Sentiment Plutchik 6 emociones | ¿Qué siente mi audiencia? | sentiment_analysis + Gemma classifier extendido | §3.1 #05 |
| B06 | Crisis Spike detector | ¿Hay picos de crisis? | velocity de toxicity/anger en ventana 2h | §3.1 #06 |
| B07 | Growth attribution Time-Decay | ¿Qué contenido genera followers? | follower snapshots diarios + posts + sklearn regresión | §3.1 #07 |
| B08 | Share of Voice (SoV) | ¿Qué % del espacio ocupo? | menciones vs competidores proxies en topics | §3.1 #08 |
| B09 | Share/Like Ratio | ¿Mi contenido se propaga más que solo gusta? | shares / likes por post | §3.1 #09 |
| B10 | Humanización Score | ¿Mi perfil se percibe humano o corporativo? | % posts en 1ra persona + emojis + keywords personales | §3.1 #10 |

---

## Tareas (estructura)

### T1 — Backend services (10 services Python)
- [ ] `backend/app/services/diagnostico/` con 10 archivos: `er_service.py`, `breakout_service.py`, `matrix_2x2_service.py`, `benchmark_service.py`, `sentiment_plutchik_service.py`, `crisis_spike_service.py`, `growth_attribution_service.py`, `sov_service.py`, `share_like_ratio_service.py`, `humanizacion_service.py`
- [ ] Cada service con método async `compute(dirigente_id, org_id) -> dict`
- [ ] Tests unitarios por service en `backend/tests/diagnostico/`

### T2 — Endpoints REST
- [ ] `backend/app/api/v1/endpoints/diagnostico.py` con 10 endpoints: `GET /diagnostico/{dirigente_id}/{bloque}` (er_normalizado, breakout_scale, matriz_2x2, benchmark, sentiment_plutchik, crisis_spike, growth_attribution, sov, share_like_ratio, humanizacion)
- [ ] Endpoint agregado `GET /diagnostico/{dirigente_id}` devuelve todos los 10 bloques en 1 call
- [ ] Auth obligatoria por JWT · org_id scoping

### T3 — NLP Plutchik extensión (para B05)
- [ ] Extender `backend/app/services/sentiment_service.py` con método `classify_plutchik_6(text) -> dict[emocion, score]` usando Gemma 3:12b + prompt S0 T0.4 (kappa 0.810 validado)
- [ ] Batch process: procesar 200+ posts existentes y poblar `sentiment_analyses.emotions` con 6 emociones Plutchik

### T4 — Frontend 10 cards
- [ ] `frontend/src/app/dashboard/diagnostico/[dirigenteId]/page.tsx` con grid de 10 cards
- [ ] Cada card con: título del bloque + pregunta · métrica headline · gráfico representativo · badge `data_fidelity_tier` por plataforma relevante
- [ ] Responsive mobile-first · loading skeletons · empty states · error states

### T5 — Integración + tests E2E
- [ ] Playwright E2E: navegar a `/dashboard/diagnostico/1` (Piña) → verificar 10 cards renderizan con datos · 0 errores consola
- [ ] 1 test por bloque que valida el número del card coincide con el endpoint
- [ ] CI hook: los 10 endpoints tienen success_rate ≥90% contra data real piloto

---

## Paralelización operativa

- **Bloque A (backend compute-heavy):** B01 + B02 + B07 + B10 (servicios con cálculos numéricos/estadísticos)
- **Bloque B (backend NLP-dependiente):** B03 + B05 + B06 + B08 (dependen de sentiment/topics)
- **Bloque C (benchmark + ratios):** B04 + B09
- **Bloque D (NLP Plutchik extensión T3):** paralelo a Bloques A-C
- **Bloque E (frontend T4):** arranca cuando haya ≥5 endpoints funcionales (backend A completado)
- **Bloque F (E2E T5):** cierre final

Clock estimado: **6-10h con 4-5 agents concurrentes** (vs 1-2 semanas serial del MASTER §5 S2).

---

## Proxies de desarrollo D-22 (para bloque #04)

Los 8 dirigentes del piloto NO tienen competidor_directo_ids reales (el cliente los declara en Onboarding S5). Para que bloque #04 funcione en S2, usamos los otros dirigentes del piloto como proxies:

```
Piña (id=1) → proxies: [2, 5, 6]  # Solano, Jiménez, Cravioto
Solano (id=2) → proxies: [1, 5, 8]
Pineda (id=3) → proxies: [4]       # Nolasco (otra secretaria Oaxaca)
...
```

Documentado como fixture explícito en `backend/scripts/seed_proxies_desarrollo_s2.py`. Esta lógica NO sale a producción — es solo para que el bloque #04 tenga datos con qué computar durante el desarrollo S2.

---

## Criterio acceptance del Sprint S2

Sprint S2 se declara completo cuando:

1. 10 services Python operativos con tests unitarios pasando
2. 10 endpoints REST devolviendo data coherente para los 7 dirigentes con data (Piña mínimo)
3. 10 cards frontend renderizando con datos reales en `/dashboard/diagnostico/1`
4. 1 test E2E por bloque cerrando con data de Piña
5. Plutchik 6 emociones poblado en ≥200 posts del corpus

Con 4/5 dura + dashboard Piña navegable → arranque Sprint S3 autorizado.

---

## Protocolo de actualización

Al cierre de cada bloque: `- [x]` + link al output. Al cerrar sprint: archivar a `.context/archive/sprint-s2-YYYY-MM-DD.md` + reset para Sprint S3.
