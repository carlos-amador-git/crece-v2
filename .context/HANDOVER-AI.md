# HANDOVER-AI — Decisiones extraídas por Sonnet
## Sesión: 52523 | Compactación: 2026-04-13_20:25:21

## Session Transcript Extraction

### 1. ARCHITECTURAL DECISIONS

**Pipeline de clasificación NLP: MANUAL en lugar de automatizado con LLMs**
- Descartado: Gemma 12B batch (5+ min/post, 3,709 posts = inviable)
- Descartado: Upload .md por cliente (fricción alta + riesgo privacidad datos políticos)
- Descartado: APIs Claude Haiku + Gemini + Perplexity ($40-60/mes)
- **Adoptado**: Pipeline MANUAL donde MD Consultoría genera prompt → Claude/Gemini clasifica → admin sube JSON batch. Costo $0 infraestructura.

**Framework político 3 capas como motor de scores**
- Los dirigentes NO interactúan con LLMs directamente
- Framework traduce clasificación manual → scores, auditables y reproducibles

**Badge "3 IAs deliberaron" como diferenciador comercial**
- Transparencia: cliente ve que 3 IAs analizaron, sin exponer el proceso interno

**Cadencia de clasificación: semanal (o bajo demanda)**
- No por post en tiempo real — arranca ad-hoc, se formaliza con feedback de uso real

**Admin dashboard: separado del dashboard de cliente**
- Dashboard actual del admin = dashboard cliente con tenant switcher (MAL)
- Necesita `/dashboard/admin/overview` con vista operativa de flota (pendiente implementar)

---

### 2. REJECTED ALTERNATIVES

| Alternativa | Razón de rechazo |
|---|---|
| Gemma 12B batch automático 3,709 posts | 5+ min/post = horas de cómputo inviable |
| Cliente sube archivo .md con estrategia | Fricción 6-7 pasos, privacidad: estrategia política pasa por logs OpenAI/Google |
| APIs externas de LLM (Haiku, Gemini, Perplexity) | Decisión CEO: costo cero en infraestructura |
| Manipulación del .md por el cliente | Riesgo de inyección / datos inválidos |
| Fine-tuning propio de LLM para clasificación | Deuda técnica, costo, mantenimiento |

---

### 3. ASSUMPTIONS MADE (to verify)

- Los 95 posts clasificados manualmente son representativos del corpus total (3,709 posts) — **no verificado estadísticamente**
- El re-download del topics model xlm-roberta (~2GB) se completó sin error durante el batch background — **ETA estimado 26 min, no confirmado completado**
- El batch de 3,449 posts NLP corrió hasta completarse en background — **estado desconocido post-sesión**
- `analyze_full()` puede procesar 3,449 posts sin OOM o timeout — **asumido, no probado a escala completa**
- Cobertura 2-7% (30-35 posts por org) es suficiente para scores útiles — **asunción metodológica no validada con cliente**
- Scores políticos (oficialismo +0.47 a +1.00, oposición -0.09 a +0.38) son coherentes y no artifacts del framework — **requiere validación humana**

---

### 4. BLOCKERS / OPEN QUESTIONS

| # | Blocker | Estado |
|---|---|---|
| B-01 | NLP batch Sprint 2 — ¿completó las 3,449 posts? | Abierto — corrió en background, no confirmado |
| B-02 | Sprint 3 Scrapers encuestas (Oraculus + Demoscopía) | Pendiente siguiente sesión |
| B-04 | Admin dashboard operativo (`/admin/overview`) | Identificado al final, NO implementado |
| B-05 | Cobertura clasificación baja (2-7%) — ¿suficiente? | Decisión metodológica pendiente |

**Pregunta abierta:** ¿El admin panel debe mostrar alertas de cobertura baja automáticamente o solo métricas pasivas?

---

### 5. KEY PEER MESSAGES

**De peer md-research (08rystzm):**
- Oraculus embebe dataset completo como **JSON inline** en HTML de `/aprobacion-presidencial/` — scraper trivial ~30 líneas. Fuentes incluidas: Mitofsky, Parametría, Enkoll, Reforma, Financiero, Buendía, De las Heras, GEA-ISA con modelo Bayesiano MCMC.
- Demoscopía Digital confirmada para CDMX (`/aprobacionEstado/ciudad-de-mexico/`) y Oaxaca (`/aprobacionEstado/oaxaca/`)
- **Plan total Sprint 3**: Federal (Oraculus) 1-2h + CDMX + Oaxaca (Demoscopía) 2h cada uno = 5-6h estimadas

**De peer Perplexity (crítica al plan original):**
- 5 problemas críticos identificados: fricción alta → adopción baja, privacidad/leyes MX, manipulación del .md, dependencia de LLMs externos, costo mensual
- Estos puntos fueron aceptados y llevaron al pivot hacia pipeline manual $0

---

### 6. NEXT STEPS (planned, not executed)

| # | Tarea | Sprint | Estimado |
|---|---|---|---|
| 1 | **Admin dashboard operativo** `/dashboard/admin/overview` — vista flota: orgs, cobertura, alertas, acciones rápidas | New | 2-3h |
| 2 | **Sprint 3: Scrapers encuestas** — Oraculus (JSON inline) + Demoscopía CDMX + Demoscopía Oaxaca | 3 | 5-6h |
| 3 | **Verificar completitud NLP batch** — confirmar que los 3,449 posts se procesaron, revisar errores | 2 | 30 min |
| 4 | **Clasificar más posts** — llegar de 95 a ~180 posts (60 por org) para cobertura mínima viable | 1 (ext) | 1-2h |
| 5 | **Scrapers encuestas integrados al dashboard** — mostrar aprobación Sheinbaum/Brugada/Jara en contexto benchmark | 4 | 2-3h |

**Commits de sesión para contexto:**
- `385aad5` — Sprint 1 completo: 95 posts clasificados + Sprint 2 NLP iniciado
- `118ce13` — Framework político 3 capas + admin panel + charts-lab
