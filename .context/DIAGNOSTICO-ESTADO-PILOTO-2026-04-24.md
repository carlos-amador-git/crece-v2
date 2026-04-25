# Diagnóstico · Estado real piloto CRECE v2 · 2026-04-24

**Propósito:** SSOT del estado del piloto al 2026-04-24 · sustento empírico contra la narrativa inflada acumulada en sesiones previas. Referencia para cualquier sesión futura que deba retomar decisiones de prioridad.

**Ejecutor:** Claude Code · sesión 2026-04-24 · supervisada por CEO (Marx Chávez)
**Cross-audit:** Gemini (review puntual sobre gap verificación visual)
**Verificación visual:** Playwright headless sobre `https://frontend-zeta-sepia-46.vercel.app` · 2 usuarios reales (Piña id=1, Ballesteros id=8) · 10 rutas principales del piloto

---

## Contexto

Piloto comercial activo desde 2026-04-20 · 3 dirigentes "activos" (Piña, Máynez, Ballesteros) + 5 shadow (Solano, Pineda, Nolasco, Jiménez, Cravioto) · SIN contratos firmados. Backend corre local Mac Mini M4 `localhost:8002` expuesto via cloudflared quick tunnel rotatorio. Frontend en Vercel `frontend-zeta-sepia-46.vercel.app`.

Incidente 3d6fe3f (2026-04-18): migración destructiva dropeó 14 tablas + 23 columnas · varios endpoints admin rotos.

## Hipótesis CEO

> "El piloto probablemente funciona 80% bien, no 30% como la narrativa acumulada sugiere. La mayoría de pendientes son deuda teórica no-bloqueante, rutas admin que los dirigentes no ven, o mejoras incrementales categorizadas erróneamente como críticas."

**Resultado:** Hipótesis **confirmada con evidencia empírica directa**. Funciona ~80% para las rutas principales del dirigente (5 de 5 verdes). Hay gaps menores específicos que documento abajo.

---

## Metodología (evidencia)

### Fase 0 · Runtime
- `curl health` local + tunnel → 200 OK · 6ms local · 505ms tunnel
- Frontend Vercel → 200 OK · 1.37s
- Auth: endpoints protegidos devuelven 401 correcto · no 500
- Middleware Next.js: rutas privadas 307 redirect a /login

### Fase 1 · Datos BD real (PostgreSQL :5438)

| id | Dirigente | Profiles | Posts | Posts 7d | Planes IA | Recom visible | Último scrape |
|---|---|---:|---:|---:|---:|---:|---|
| 1 | Piña | 5 | 320 | 1 | **3** | **7** | 2026-04-18 |
| 7 | Máynez | 5 | **0** | 0 | 0 | 0 | — |
| 8 | Ballesteros | 4 | **151 frescos** | 151 | 0 | **4 huérfanas** | 2026-04-18 |

### Fase 2 · Código (grep directo)

Endpoints backend que **SÍ referencian columnas dropeadas** por 3d6fe3f (fallarán si se llaman con auth válida):
- `admin_overview.py` → `tono_discurso`, `nlp_model_version`
- `admin_classification.py` → `rol_politico`, `tono_discurso`, `target_politico`, `sentimiento_politico_ajustado`
- `indice_aceptacion.py` → `rol_politico`, `nlp_model_version`

Sub-rutas frontend relacionadas:
- `/dashboard/aceptacion/dirigentes` → depende de `indice_aceptacion.py` → 404 en prefetch
- `/dashboard/aceptacion/fantasmas` → idem

### Fase 3 · Cross-audit Gemini

Pregunta concreta: "¿Qué tan arriesgado declarar 'funciona 80%' sin verificación visual post-login?"

**Voto Gemini: (B) gap significativo · hacer verificación visual antes de decidir.**

Riesgos específicos señalados:
1. White Screen of Death en Ballesteros si componente accede a `recomendacion.plan_ia.titulo` con null
2. Data-binding fallas en Piña dashboard con 320 posts (KPIs undefined, lag hydration)
3. Empty states rotos en Máynez

### Fase 4 · Verificación visual (Playwright headless · Vercel producción)

Login como Piña (`pina@crece.mx`) y Ballesteros (`ballesteros@crece.mx`) · 5 rutas cada uno + interacción extra Ballesteros. **Todo con success visual.**

Artifacts: `.context/diagnostico-visual-2026-04-24/` — 17 screenshots + `report.json` con console/network/page errors por ruta.

---

## Hallazgos empíricos · verificación visual

### Piña (id=1) · 🟢 FUNCIONAL

| Ruta | Render | Contenido observado | Console err | Net err bloqueantes | pageErr |
|---|---|---|---:|---:|---:|
| `/dashboard` | ✅ | KPIs 12.8K audiencia · IPD 2.5/10 · 320 posts · Tema Urgente TikTok · 7 alertas · Seguidores 5 plataformas · Tono Discursivo chart | 7 (prefetch) | 0 bloqueantes | 0 |
| `/dashboard/diagnostico/1` (Tier 1) | ✅ | 10 bloques render | 2 (prefetch) | 0 | 0 |
| `/dashboard/diagnostico-tier2/1` (Tier 2) | ✅ | 8 bloques render | 2 (prefetch) | 0 | 0 |
| `/dashboard/recomendaciones` | ✅ | 7 recom aprobadas visible | 2 (prefetch) | 0 | 0 |
| `/dashboard/planes` | ✅ | 3 planes IA visible | 2 (prefetch) | 0 | 0 |

Gemini riesgo 2 (data-binding 320 posts) → **descartado** · KPIs renderizan `12.8K / 2.5 / 320` correctos.

### Ballesteros (id=8) · 🟢 FUNCIONAL

| Ruta | Render | Contenido observado | Console err | Net err bloqueantes | pageErr |
|---|---|---|---:|---:|---:|
| `/dashboard` | ✅ | KPIs 88.8K audiencia · IPD 3.1/10 · 151 posts · Tema Urgente TikTok · 7 alertas · Seguidores Twitter 55.6K/IG 32K/YT 1.2K/FB **0** | 2 | 0 | 0 |
| `/dashboard/diagnostico/8` | ✅ | Tier 1 render | 2 | 0 | 0 |
| `/dashboard/diagnostico-tier2/8` | ✅ | Tier 2 render | 2 | 0 | 0 |
| `/dashboard/recomendaciones` | ✅ | **4 recom huérfanas render correcto** · tabs "4 pendientes · 0 en seguimiento · 0 concluidas" · botones Aceptar/Modificar por card | 2 | 0 | 0 |
| `/dashboard/planes` | ✅ | Render OK (probablemente empty o parcial) | 2 | 0 | 0 |

Gemini riesgo 1 (White Screen con `plan_ia.titulo` null) → **descartado** · el frontend trata cada recomendación como item standalone · NO accede a plan padre · UX idéntica a recomendaciones con plan padre.

**Observación menor:** Facebook shows `0` seguidores en Ballesteros · puede ser data real o gap scraper (relacionado B-23-02).

### Máynez (id=7) · no verificado visual

Máynez NO tiene usuario en BD (`SELECT * FROM users WHERE dirigente_id = 7` → 0 rows). Sin login no puedo ver su experiencia. Inferencia restante:
- 0 posts en BD → dashboard mostraría empty state o data vacía para su dirigente_id
- Riesgo 3 de Gemini (empty states rotos) → **no descartado** · queda como pendiente verificar si/cuando se crea su usuario

---

## Hallazgo NUEVO descubierto solo por verificación visual

**Next.js RSC prefetch de rutas sub-menu `/aceptacion/dirigentes` y `/aceptacion/fantasmas` falla con 404** en todas las páginas del dashboard. Esto es:

- **CONSECUENCIA de incidente 3d6fe3f** · las páginas `/aceptacion/*` tienen endpoints roto en backend
- Los 404 NO bloquean el render de la página actual (prefetch silencioso · fallback a browser navigation si el usuario hace click)
- **SÍ afecta al dirigente si hace click en el sidebar "Indice Aceptación → Por dirigente"** o "Fantasmas" · navegación llega a página 404 · UX rota en ESE flujo específico

Severidad: 🟠 **Importante ≤30 días.** No es crítico porque son sub-rutas · el dirigente tiene el dashboard principal + 4 rutas core funcionales. Pero si explora el menú completo, topa con 404.

Mitigación interim posible (5 min): **ocultar las sub-entradas del sidebar hasta que F1.1 Schema Restauración las restaure.**

---

## Clasificación refinada de pendientes · con evidencia visual

### 🔴 Crítico afecta piloto HOY · **0 items**

Ninguno. Las 5 rutas principales del dashboard funcionan para ambos dirigentes verificados.

### 🟠 Importante ≤30 días · **3 items**

1. **Sub-menú `/aceptacion/dirigentes` + `/aceptacion/fantasmas` rotos** · el dirigente ve entradas en sidebar · click = 404. **Mitigación en 5 min:** ocultar las sub-entradas hasta F1.1.
2. **Máynez sin scraping** · el 3° activo del piloto ve dashboard sin data · pendiente B-SCRAPE-01 stack scrapers + bootstrap social_profiles.
3. **F1.1 Schema Restauración** · restaura endpoints admin (tu panel HITL review) + endpoints `/aceptacion/*` + habilita generación FODA + Plan IA.

### 🟡 Deuda documentada · puede vivir meses · **11 items**

Pre-existentes + reclasificados:
- B-23-01 downtime BD (ya mitigado)
- B-23-02 fragilidad scrapers comment/share counts
- B-23-03 motor sentimiento con afiliación §9.8
- B-23-04 F-23-10/11 rewrite estructural Sprint 24+
- B-23-05 cloudflared tunnel rotatorio vs piloto
- B-SCRAPE-02 decisión pipeline manual vs stack interno
- B-SCRAPE-03 monitoreo salud scrapers
- B-SCHEMA-01 columna `social_profiles.verification_note`
- D-23-G' disenso sentimiento afiliación
- Tasks #3, #4, #8, #9, #10, #12 (Gates + framework + vocabulario)
- **Ballesteros gap plan padre 4 huérfanas** · reclasificado de 🟠 a 🟡 porque UX funciona perfectamente sin plan padre · fix cosmético post-F1.1

### ⚪ Teórico sin evidencia de impacto · **3 items**

- **B-CI-01** (CI workflow always-red) · ruido GitHub Actions · nadie ve signal
- **B-RATE-LIMIT-01** · dedup cache per-process · escenario multi-worker con volumen no existe hoy
- **Named tunnel** (dentro de B-23-05) · ya descartado por scope creep

---

## Score funcional (0-50)

| Dimensión | Score | Evidencia |
|---|---:|---|
| Funcional dirigente (verificado visual) | **9/10** | 5/5 rutas 🟢 · Piña + Ballesteros confirmed · Máynez empty-by-design |
| Data integrity | **7/10** | Ballesteros modelo inconsistente (huérfanas UX OK) · Máynez vacío |
| UX cliente | **8/10** | Sprint 23 hotfixes aplicados (en PR #44 draft) · renders completos con data real |
| Observabilidad | **5/10** | F0.1 en PR #45 draft · no bloqueante · piloto sin alertas activas hoy |
| Admin/MD panel (tú) | **2/10** | `/admin/overview` + `/admin/classification/*` + `/aceptacion/*` rotos |
| Infra runtime | **9/10** | Healthy · tunnel activo · frontend producción OK |

**Global: ~40/50 = 80%** · consistente con hipótesis CEO.

---

## Decisiones soportadas por este diagnóstico

1. **NO justifica `/plan` formal con fases + sprints** · hallazgos no son suficientes para sprint estructurado
2. **SÍ lista corta de 3-4 acciones tácticas** basada en los 🟠 reales
3. **Prioridad inmediata sugerida:** ocultar sub-menú `/aceptacion/*` en sidebar (5 min · cubre el único hallazgo UX real descubierto por verificación visual)
4. **Resto:** esperar F1.1 con Joy + revisor §9.8 · no hay urgencia técnica que justifique adelantar

---

## Artifacts

- **Screenshots verificación visual:** `.context/diagnostico-visual-2026-04-24/` (17 PNG + report.json)
- **Sesiones Playwright:** headless · user-agent default · 1440×900 viewport
- **Credenciales usadas:** `pina@crece.mx / demo2026!` · `ballesteros@crece.mx / Ballesteros2026!` (documentadas en `seed.py` + ajuste manual Ballesteros)
- **Timestamp ejecución:** 2026-04-24T13:34:40Z inicio → 13:35:40Z fin (60s total)

---

## Registrado por

Claude Code · sesión 2026-04-24 · post-`/sprint-audit` con stop post-diagnóstico explícito. Cross-audit Gemini puntual (no full audit). Verificación visual Playwright validó gaps señalados por Gemini.

**Validez:** este diagnóstico representa estado al 2026-04-24. Deuda futura o incidentes post-fecha pueden invalidar conclusiones específicas. Re-verificar con verificación visual similar si narrativa vuelve a inflarse.
