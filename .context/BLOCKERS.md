# CRECE v2 — BLOCKERS

Esta es la fila de riesgos/bloqueos formalmente reconocidos pero **diferidos**.
Actualizar al abrir cualquier PR que toque el área del riesgo.

---

## Activos

### B-23-01 · Downtime BD en piloto · riesgo no mitigado

- **Origen:** Gemini cross-audit 2026-04-23 sobre `PLAN-REVISADO.md` Sprint 23-B.
- **Texto original Gemini:** *"Ejecutar migraciones de Alembic (Sprint 23-B) en un entorno de producción (piloto) puede generar bloqueos de tabla. Esto requiere una ventana de mantenimiento programada."*
- **Status:** ✅ **MITIGADO evitando la migración.** Propuesta P1 (URL computada en schema sin migration) elegida sobre P2 (columna persistida).
- **Deuda residual:** Propuestas P2 (columna `url` persistida) y P3 (nullable counters para distinguir 0-real vs no-recolectado) documentadas en `frontend-review-2026-04-23/SPRINT-23B-INVESTIGACION.md`. Escaladas a §9.8 del 2026-05-20, con obligación de ventana de mantenimiento + plan de rollback al ejecutarse.

### B-23-02 · Fragilidad scrapers comment/share counts · riesgo reconocido

- **Origen:** Gemini cross-audit 2026-04-23.
- **Texto original Gemini:** *"Intervenir los scrapers para extraer comment_count y share_count requiere revalidación de límites de rate y estructuras de la plataforma origen (ej. Facebook/Twitter). Es un proceso inherentemente frágil que excede el tiempo estimado de 45 min y podría romper la recolección actual de datos del piloto."*
- **Status:** ⚠️ **DIFERIDO sin mitigación.** Los campos `comments`/`shares` siguen mostrando 0 en UI cuando el scraper no logra leerlos (ambigüedad 0-real vs no-recolectado). No se tocó código scraper en Sprint 23 — sería incompatible con piloto activo.
- **Impacto en piloto:** usuarios ven "0 comentarios" en posts donde sí hay comentarios reales que el scraper perdió. CEO ya lo señaló en F-23-05 con "aparecen cero comentarios".
- **Plan:** abordar dentro de §9.8 del 2026-05-20 junto con Propuesta P3 (nullable counters) para que BD distinga explícitamente los dos casos. Pre-requisito: inventario por plataforma de qué scrapers leen bien y cuáles no.

### B-23-03 · Motor sentimiento con afiliación no conectado al dashboard

- **Origen:** Findings F-23-01 + F-23-06 review CEO 2026-04-23.
- **Status:** 🔴 **ESTRUCTURAL §9.8.** Framework político 3-capas existe en `backend/app/services/political_framework.py` con matriz (rol, tono, target) → score_tenant, pero no está conectado a `tema_urgente`, `SentimentBadge`, ni Sentiment Prom. en ficha dirigente.
- **Mitigación interim (ejecutada 2026-04-23):** disclaimer role-aware en Tema Urgente que explicita que el sentimiento mostrado es crudo y que críticas al oficialismo pueden leerse distinto para oposición. Textos diferenciados por partido → rol federal CDMX.
- **Plan completo:** `SPRINT-23E-INVESTIGACION.md` — propuesta 4 fases para §9.8 del 2026-05-20.

### B-23-04 · F-23-10/11 rewrite estructural diferido

- **Origen:** CEO feedback 2026-04-23: *"F-23-10/11 dice CALIB pero el texto mismo reconoce patrón estructural pendiente. Eso no es cerrado, es cerrado-a-nivel-título."*
- **Status:** ⚠️ **PARCIAL.** Sprint 23-D cerró solo los renames de títulos (13 de 18 bloques). El patrón "qué mide / cómo te fue / qué hacer" queda pendiente.
- **Plan:** `frontend-review-2026-04-23/BACKLOG-SPRINT-24.md` con 4 fases + 3 preguntas de arquitectura para sesión dedicada.

### B-23-05 · Cloudflared tunnel rotatorio vs piloto activo · fragilidad del producto

- **Origen:** Diálogo CEO + Claude Code 2026-04-23 durante diagnóstico F0.1.
- **Status:** 🟠 **ABIERTO · producto.** El backend CRECE corre en `localhost:8002` del Mac Mini M4 expuesto vía `cloudflared tunnel --url http://localhost:8002 --no-autoupdate` (ad-hoc, URL rotatoria ~1h). LaunchAgent `com.mdconsultoria.crece-tunnel.plist` rota URL y auto-updatea `NEXT_PUBLIC_API_URL` en Vercel env vars. Durante la ventana de rotación, los 3 dirigentes activos del piloto (Piña, Máynez, Ballesteros) pueden ver pantalla rota / fetch failed hasta que Next.js re-lea env vars (requiere rebuild o re-fetch de config runtime).
- **Impacto en piloto:** microcortes de ~N segundos cada hora × 3 dirigentes = experiencia de producto inconsistente durante la ventana crítica del piloto comercial.
- **Mitigación propuesta:** migrar a **named tunnel con hostname estable** (p.ej. `api-crece-dev.mdconsultoria-ti.org`). Requiere (1) CNAME en Cloudflare DNS hacia tunnel UUID, (2) config.yml + credentials JSON en Mac Mini, (3) modificar LaunchAgent para apuntar a named, (4) fijar `NEXT_PUBLIC_API_URL` en Vercel a nuevo hostname estable. Estimado 30-45 min. Referencia: `D-GATE-05` en MASTER.
- **Pre-requisito de F0.1 monitor externo:** Better Stack no se configura hasta que named tunnel esté activo (URL rotatoria produciría falsos positivos horarios).
- **Asignado:** CEO directo (configuración UI Cloudflare + LaunchAgent) · no es trabajo del agente.

---

## Resueltos

(Mover aquí con fecha cuando se cierren.)
