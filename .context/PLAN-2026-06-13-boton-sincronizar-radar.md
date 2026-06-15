# PLAN — Botón "Sincronizar con RADAR" (admin) + Badge de frescura (dirigente) · 2026-06-13

**Estado:** aprobado para ejecución en autonomía (perímetro abajo). Diseño cerrado con análisis
propio + cross-audit Gemini (`/tmp/gemini-out-quien-actualiza.md`).
**Origen:** corrección de fondo del CEO 2026-06-13 — construí el plumbing de ingest (endpoint +
Celery) pero NO la cara en el front, que es lo que el operador usa. Esto cierra esa brecha.

## Principio rector (modelo de gobernanza del CEO)
**En CADA fase: (1) leer la gobernanza que aplica ANTES de tocar nada · (2) si no existe,
documentarla · (3) al cierre, con visión general, consolidar.** Y **verificar en la APP**, no en SQL.

## Diseño cerrado (quién hace qué)
- **Trigger = ADMIN/ANALYST, exclusivo.** Es entrega de servicio (SLA ConsultoríaMD), no
  self-service del cliente. Consistente con el RBAC actual (la activación ya es admin/analyst-only).
- **Dirigente (VIEWER):** ve un **badge de frescura** ("Corte: <fecha>") + "Actualizando…" si hay
  proceso activo. CERO botones de disparo. CERO "solicitar" (genera tickets manuales).
- **El botón "ingiere el último bundle disponible"** (en MinIO), NO jala RADAR en vivo (RADAR es
  atendido). Si no hay nada nuevo → lo dice, no falla en silencio. Reporta el **delta real**
  ("0 posts nuevos, 450 likes nuevos") — anti-placebo.
- **Es override permanente** (caso crisis: escándalo hoy → operador corre RADAR → refleja ya),
  complemento de la automatización futura (pendiente #1), no deuda.

## Perímetro de autonomía
- ✅ Autónomo: backend/frontend/scripts/tests, migraciones nuevas, ADRs `Proposed`, commits
  locales, levantar/probar stack, verificar en app.
- ⛔ Requiere OK escrito del CEO: **push remoto / merge a main** (dispara deploy Carlos).
- Gate RAM (`ram-gate.sh`) antes de levantar stack / correr ingest.

## Fases

### Fase 0 — Gobernanza + fix bloqueante
- **Leer:** `SOP-INGEST-RADAR-HANDOFF.md` completo · `MAPA-FUNCIONAL` §seguidores/fans · RBAC
  (`core/security.py`, `core/scope.py`).
- **Documentar:** ADR `Proposed` "Quién dispara la actualización de datos" (admin/analyst;
  dirigente solo frescura). Es contrato externo → ADR (AGENTS §7).
- **Fix bug actual** (el que cazó el CEO): `ingest_radar_yt_x_posts.py` (y hermanos) revientan
  `No profile for (N, PLATFORM)` si el dirigente no tiene ese perfil. → **guard de skip** con log
  (no es error: Felipe no tiene Twitter). Aplica también en el worker `_run_sop_chain`.
- **Verificar:** re-ingerir Felipe (bundle completo) → COMPLETED, salta plataformas sin perfil.

### Fase 1 — Endpoint puente "sincronizar"
- `POST /api/v1/ingest/sync/{dirigente_id}` (admin/analyst) → localiza el último bundle del
  dirigente en MinIO → si no hay posterior a la última ingesta: 200 `{"sin_novedades": true}` →
  si hay: encola `process_radar_handoff` → devuelve job_id + delta esperado.
- `GET .../sync/status/{dirigente_id}` → estado del proceso para el badge "Actualizando…".
- **Supuesto declarado:** el bundle vive en MinIO. Quién lo sube: hoy el operador con
  `e2e_push_handoff.py`; futuro RADAR D-050. El botón opera sobre lo que esté en MinIO.
- **Verificar:** test + curl → "sin novedades" y, con bundle, job encolado + delta.

### Fase 2 — UI admin (el botón)
- Botón **"Sincronizar con RADAR"** en `/dashboard/dirigentes/[id]` (vista admin) → progress
  (Ingiriendo → Analizando → Diagnóstico) → toast con el delta real.
- Guard concurrencia: deshabilitado si hay proceso activo para ese dirigente.
- **Verificar EN LA APP:** levantar front, login admin, abrir dirigente, apretar, ver el delta.

### Fase 3 — UI dirigente (badge de frescura)
- Badge "Corte: <fecha>" junto al nombre del dirigente + "Actualizando…" si hay proceso activo.
- **Decisión CEO (default si no responde):** frescura **por-red** (FB 03-jun, IG 12-jun…) —
  más honesto que un solo corte; el dato real de RADAR ya viene con `as_of_by_platform`.
- Overlay bloqueante mientras ingiere: **default NO bloqueante** (badge "Actualizando…" basta;
  bloquear todo el dashboard es intrusivo) — revisable con el CEO.
- **Verificar EN LA APP:** login como dirigente (viewer), ver el badge.

### Fase 4 — Cierre / consolidación (visión general)
- `make test` verde + `pnpm type-check`/`lint`/`check:no-mocks` verde.
- Consolidar: ADR Fase 0 → a `Accepted` (con OK CEO) · actualizar `MAPA-FUNCIONAL` con la nueva
  pieza · handoff.
- **NO push** sin OK escrito del CEO.

## Decisiones del CEO pendientes (con default declarado)
1. Badge frescura **por-red** (default) vs corte general único.
2. Overlay **no-bloqueante** (default) vs bloqueante durante ingest.

## Definition of Done
El operador abre la app, entra a un dirigente, aprieta "Sincronizar con RADAR", **ve** los
seguidores/fans actualizarse en pantalla con el delta reportado; el dirigente **ve** su badge de
frescura. Todo verificado en la app, no en SQL. Cero push sin OK.

## Cross-audit
Gemini revisará el plan + cada fase (sprint-implement integra cross-audit). Veredicto de diseño
ya incorporado (`/tmp/gemini-out-quien-actualiza.md`).
