# CRECE v2.0 — Diagnóstico Unificado
## Fecha: 2026-04-05
## Fuentes: func-audit en vivo + feedback CEO + inventario técnico

---

## A. SCORE FUNCIONAL (probado en vivo)

| Módulo | Score | Funciona en demo? | Problema principal |
|--------|-------|-------|-------------|
| Auth + Usuarios | 41/50 | SI | Falta reset-password real |
| Diagnóstico IPD | 37/50 | SI (seed) | Datos no son de scraping real |
| **Planes IA** | **13/50** | **NO** | Claude API no configurada. Sin fallback Ollama automático. |
| **Content Factory** | **10/50** | **NO** | Hardcoded a Claude. Sin soporte Ollama. |
| Dashboard Overview | 36/50 | SI | IPD es proxy, no cálculo real |
| Monitoreo Social | 29/50 | SI (seed) | 6 posts seed, scrapers nunca ejecutados |
| **Benchmarking** | **5/50** | **NO** | Endpoint crashea (500) |
| Electoral + Geo | 32/50 | SI | Sin geometries (mapa vacío) |
| Voter Scoring | 12/50 | VACÍO | Pipeline ML nunca ejecutado |
| Campañas/Canv./Part. | 23/50 | VACÍO | Canvassing: ruta mismatch frontend↔backend |
| **TOTAL** | **238/500** | | |

---

## B. REQUISITOS DEL CEO (no negociables)

### B1. Zero mockups en demos
> "No quiero datos mockup con los posibles clientes."

**Estado:** VIOLADO. Todo lo que se muestra viene de `seed.py`. Posts son inventados, plan IA es texto hardcodeado, métricas son estimadas.

**Requerido:** Demo en vivo — ingresar un nombre real y que el motor trabaje.

### B2. Evaluación de Ollama vs Claude vs Gemini
> "Quiero evaluar el poder de Ollama. Que Claude y Gemini elaboren las recomendaciones, luego comparamos con Ollama."

**Método acordado:**
1. **Claude** (yo, en esta conversación) → analizo diagnóstico de Piña/Solano → escribo plan de mejora
2. **Gemini** (desde terminal CLI) → mismo input → escribe plan de mejora
3. **Ollama/Gemma4** (desde CRECE backend, local) → genera plan con endpoint `/planes/generar`
4. Comparamos los 3: calidad, profundidad, accionabilidad

**Estado:** Pendiente. Requiere que Ollama esté corriendo + endpoint funcione con `AI_PROVIDER=ollama`.

### B3. Generación de videos
> "Necesitamos opciones para la generación de videos."

**Estado:** CRECE no genera videos. Solo scripts de texto para Reels/TikTok. Existe skill `/video` (Remotion) para videos programáticos pero no está integrado.

### B4. Plan de mejora para clientes
> "El plan específico de mejora para los clientes, cómo está configurado?"

**Estado:** Arquitectura buena (4 tipos de plan, prompt con datos reales, streaming SSE), pero **nunca ha funcionado en vivo** porque:
- Claude API key es placeholder (`sk-ant-xxx`)
- Ollama no es fallback automático
- Content Factory hardcoded a Claude (no soporta Ollama)

### B5. Landing vinculada al sistema
> "Evaluar si dejamos la landing con datos de Piña y Solano pero vinculadas al sistema. Debe ser real."

**Estado:** Landing tiene datos estáticos en React. NO consulta al backend. Cambio de datos en BD no se refleja en landing.

**Requerido:** Endpoint público que sirva datos sanitizados → landing consume vía fetch.

### B6. Plan original — herramientas faltantes
> "Del plan original, qué nos falta. Teníamos muchas herramientas y no veo que estén incluidas."

**Estado:** No verificado aún. Plan original en `/Users/marxchavez/Downloads/Reporte_Consolidado_CRECE_v2_Final.md`. Se necesita gap analysis completo.

### B7. Fase 2 completa
> "Teníamos incluida una Fase 2, tienes el plan?"

**Estado:** Fase 2 se implementó en batches 5A-5B-6-7 (Voter Scoring, Content Factory, Blindaje, Campañas, Canvassing, Participación). Pero muchos módulos están vacíos o rotos. El plan está en `.context/PLAN-current.md`.

---

## C. DIAGNÓSTICO POR PERFIL DE CLIENTE

### Alejandro Piña Medina — IPD 3.7/10

**Datos reales verificados:**
- Twitter @Alejandro_Pinha: 3,100 seguidores
- Instagram @alejandro.pinha: 2,231 seguidores
- Facebook alejandropinamedina: 1,800 seguidores
- Total: 7,131 seguidores en 3 plataformas (50% cobertura)

**Métricas del sistema:**
- IPD: 3.7/10 (bajo para un coordinador estatal)
- Engagement promedio: 3.74% (aceptable)
- Frecuencia posting: 0.17/día (1 cada 6 días — muy bajo)
- Sentimiento: 68% positivo, 12% negativo (basado en 6 posts seed)

**Brechas:**
- Sin TikTok, YouTube, Bluesky (3 plataformas faltantes)
- Competidor Martí Batres tiene 285,000 seguidores (40x más)
- Frecuencia insuficiente para mantener relevancia algorítmica

### Rafael Solano Pérez — IPD 1.68/10

**Datos reales verificados:**
- Instagram @rafasolanoperez: 450 seguidores
- Twitter @rafasolanoperez: 170 seguidores
- Total: 620 seguidores en 2 plataformas (33% cobertura)

**Métricas del sistema:**
- IPD: 1.68/10 (mínimo — perfil casi inexistente digitalmente)
- Engagement: 4.7% (alto — audiencia pequeña pero comprometida)
- Frecuencia posting: 0.03/día (1 cada 33 días)

**Brechas:**
- Sin Facebook, TikTok, YouTube, Bluesky (4 plataformas faltantes)
- Presencia LinkedIn 170 (no trackeada por CRECE)
- Alto engagement orgánico = oportunidad de crecimiento rápido

---

## D. BLOQUEANTES PARA DEMO EN VIVO

| # | Bloqueante | Severidad | Fix estimado |
|---|-----------|-----------|-------------|
| 1 | **Planes IA no genera** — necesita Ollama como provider default | P0 | Cambiar AI_PROVIDER=ollama + verificar Ollama corre |
| 2 | **Content Factory hardcoded Claude** — agregar soporte Ollama | P0 | Refactor provider en content_factory.py |
| 3 | **Benchmark crashea** — 500 en /competidores | P0 | Debug serialización modelo Competidor |
| 4 | **Canvassing ruta mismatch** — frontend /rutas vs backend /routes | P1 | Alinear rutas |
| 5 | **Landing datos estáticos** — no vinculada al sistema | P1 | Crear endpoint público showcase |
| 6 | **Voter Scoring vacío** — ML pipeline nunca ejecutado | P2 | Ejecutar scoring con datos seed |

---

## E. PRÓXIMOS PASOS ACORDADOS

1. **Claude (yo)** elabora plan de mejora para Piña basado en diagnóstico real
2. **Gemini (terminal)** elabora el mismo plan con el mismo input
3. **Ollama** genera plan via CRECE (requiere fix P0 #1 y #2)
4. **Comparamos** los 3 → evaluamos fortalezas/debilidades de Ollama
5. **Fix P0s** para que la demo funcione en vivo
6. **Gap analysis** del plan original vs implementación actual
7. **Evaluar** opciones de video (Remotion, etc.)
