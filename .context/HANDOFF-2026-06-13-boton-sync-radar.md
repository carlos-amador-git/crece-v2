# HANDOFF — Botón "Sincronizar con RADAR" + 3 dirigentes al día · 2026-06-13

**Status:** cierre. Feature en `origin/main` (`9d8b930`). 3 dirigentes actualizados (medido).
**Sesión:** Linda · Claude Opus 4.8 · 2026-06-13 (larga, atendida; varias correcciones de fondo del CEO).

## ⚠️ LEER PRIMERO
- **Feature pusheado y verificado E2E en la app** (no en SQL). Botón "Sincronizar con RADAR" en
  `/dashboard/dirigentes/[id]` (admin/analyst-only, ADR-005 Accepted) → endpoint
  `POST /api/v1/ingest/sync/{id}` → descubre el último bundle en MinIO → ingiere (cadena SOP
  idempotente) → badge frescura + "Procesando".
- **Construido por `gemini --yolo`** que Linda lanzó (error de yolo reconocido: yolo da escritura;
  para consultas ir SIN yolo). Linda verificó/consolidó (ejecutor≠auditor) y cazó 2 bugs.
- **NO detener stack** (instrucción CEO al cierre). Stack arriba; frontend dev en :3007.

## Estado de los 3 dirigentes (medido contra BD)
| Dirigente | Followers | Últ. post | Notas |
|---|---|---|---|
| Saymi (3) | 287,097 (FB 244k) | 06-13 | COMPLETO — 214 IG-posts (incl. 30 nuevos 06-13, capturados con @marxitoc) ya ingeridos vía botón |
| Pepe (57) | 27,875 | 06-11 | completo (1er sync por flujo nuevo) |
| Felipe (60) | 7,243 | 06-13 | completo |

## 2 bugs cazados verificando (no confiando en "COMPLETED")
1. `discover_manifest` (radar_sync.py): leía tmp sin `flush()` → botón daba 500. Fix `41f705c`.
2. `ingest_radar_followers.py`: no leía el wrapper RADAR `{slug,followers:{}}` → followers no se
   actualizaban en silencio (128k FB de Saymi ocultos; job COMPLETED igual). Fix `e7d1f59`.
Tests: 16 (test_ingest_radar) + 4 (test_radar_sync) verdes. Gemini aprobó merge + fixes.

## PENDIENTES (todos escalados, ninguno abierto en mi cancha)
1. ~~IG-posts Saymi~~ **RESUELTO** — los 30 nuevos (capturados con @marxitoc, autorizado) ya están
   en BD (214 IG-posts Saymi, más reciente 06-13), ingeridos vía el botón. Las credenciales de
   `chatmx_oficial` son para FUTURAS corridas de RADAR (refrescar esa cuenta), NO pendiente de cierre.
   *(Corrección: lo reporté como pendiente sin medir — RADAR me corrigió con evidencia.)*
2. **Deploy Coolify (Carlos)** → **NO urgente**: Coolify sin data/bundles reales + necesita env
   `MINIO_ACCESS_KEY`/`SECRET_KEY` (SPEC-ENDPOINT-INGEST-RADAR.md). Tiene sentido cuando el
   pipeline RADAR→Coolify-MinIO esté conectado.
3. **Pipeline auto RADAR→CRECE** (pendiente #1 grande): endpoint listo + workflow n8n
   `CRECE — Ingest RADAR Handoff` desplegado **inactive** (id W3y311tQbS4TrstQ). Activar = deploy +
   RADAR conecta push (su ADR D-050) + editar nodo Config (URL backend + API key).
4. **NLP fine-tune** (cascada híbrida, DIAGNOSTICO-2026-06-12): faltan **2 de 3 Excels** de
   evaluadores (gold polaridad) → del CEO/colaboradores. Excel generado en
   `backend/evaluations/2026-06-12-gold-polaridad/` (evaluador_3 ya respondido, 100/100).

## Cómo retomar
- El botón ya opera local. Para actualizar un dirigente nuevo: subir bundle a MinIO
  (`e2e_push_handoff.py --upload-only`) → apretar el botón en la app (o `POST /ingest/sync/{id}`).
- API key admin del flujo: regenerar (la de la sesión vivía en `/tmp`, volátil).
- Commits sesión: `2e727d3` `54cf818` `41f705c` `e7d1f59` `9d8b930` (+ los del mediodía 5/5 reactors).

## UPDATE cierre (tarde 2026-06-13)
- **3er bug cazado + fix (ADR-006, `8fe548c`):** ranking de fans inflado ~2x — RADAR cambia
  `profile_external_id` del mismo fan entre capturas → N watched_profiles → el ranking sumaba
  perfiles (Pedro Carlock 988 vs 514 real). Fix: dedup por `author_hash` en `watched_profiles.py`
  (ranking `ROW_NUMBER` + `n_likes=COUNT(DISTINCT post_id)`; conteo `COUNT(DISTINCT author_hash)`).
  NO toca BD. Cross-audit Gemini. Verificado en la app: Misael sigue Fan #1 (splice).
- **Misael Fan #1:** confirmado en la app + gobernado (ADR-0002/0005/0007). El splice fuerza
  position 1; el fix de dedup NO lo afecta. (Recalibrar su número >514 = opcional estético, regla 12.)
- **Git:** `origin/main @ 342a52f` sincronizado, cero pendientes. `backend/data/saymi_pilot/` +
  `exports/` agregados a `.gitignore` (data/PII, no versionar).
- **Deudas NUEVAS escaladas (ADR-006):** causa raíz UPSERT-por-hash en RADAR · normalización
  nombres (18k variantes) · recalibrar Misael.
- **Stack:** detenido al cierre (stop limpio, resucitador descargado).
