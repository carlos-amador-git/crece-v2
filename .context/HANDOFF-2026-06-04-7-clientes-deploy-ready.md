# HANDOFF — 7 clientes completos + GH deploy-ready · 2026-06-04

**Status:** cierre limpio. 7/7 dirigentes con cadena completa. GH listo para redeploy de Carlos.
**Sesión:** Linda · Claude Opus 4.8 · 2026-06-03 → 04 (sesión larga, atendida por el CEO).
**Próxima sesión arranca con:** sin plan específico · o atacar los 2 pendientes (ver abajo).

---

## ⚠️ LEER PRIMERO
1. **GH listo para Carlos:** código en `origin/main` @ `89a6c2e` (sync 0/0, CI verde) + Release
   **`data-snapshot-2026-06-04`** (privado, dump 27.8MB, 72 tablas, los 7 dirigentes de hoy).
2. **El redeploy es cancha de Carlos.** Pasos seguros (cross-audit Gemini) en
   `DEPLOY-COOLIFY-CARLOS.md` PASO 8.1: pre-vuelo extensiones → backup previo Coolify →
   restore a BD nueva/`--disable-triggers` → smoke test. **Borrar el Release tras restore.**
3. **SOP de ingest certificado** desde ejecución real: `.context/governance/SOP-INGEST-RADAR-HANDOFF.md` (🟡 pend. audit Gemini formal).

## Qué se hizo
Cadena E2E completa para los 7 dirigentes (Saymi 3, Piña 1, Pepe 57, Solano 2, Felipe 60,
Gaby 5, Ballesteros 8): **ingest** (posts 5 redes + comments + reactors + followers) →
**NLP enrich** (tono/target/polaridad/emotions/topics) → **D's** (B01-B18) → **FODA** →
**consolidación** → **contenido**. Data en BD local `:5438` (8,111 posts · 10,005 comments ·
21 planes nuevos hoy). Verificado before/after en cada paso.

**D's que emiten por cliente** (insufficient = gap curatorial, NO pipeline):
Piña 18/18 · Gaby 17/18 · Saymi 17/18 · Pepe 16/18 · Felipe 16/18 · Ballesteros 17/18 · Solano 13/18.
- `B04 benchmark` insufficient cuando `dirigentes.competidor_directo_ids = {}` (sin competidores declarados).
- `B16 promesas` insufficient cuando `promesas_dirigente` = 0 (solo Piña tiene).
- Solano 13/18: menos data de interacción (FB personal sin comments, reactors solo IG).

## Código nuevo / fixes (todo en GH)
- **NUEVO** `backend/scripts/ingest_radar_followers.py` — ingesta `followers.json` (cierra gap B07; patrón `tasks.py:386`).
- **FIX** `regen_consolidacion_v2.py` — path `/aceptacion/overview` (404) → `/social/aceptacion/overview` (200). Generaba planes con followers=0.
- **FIX** los 3 generadores leen `DIRIGENTE_PASSWORD` env (Ballesteros usa `Ballesteros2026!`, no `demo2026!`).
- Commits: `7125452` (Groq deploy) · `613adef` (followers+SOP) · `bdf71af` (password env) · `89a6c2e` (runbook).

## Bugs cazados (todos por verificación, no asumidos)
1. `docker exec -t pg_dump -Fc` corrompe el binario (CR/LF) → TABLE DATA=0. Regenerar SIN `-t`.
2. D's salían todos `insufficient` → admin sin header `X-Org-Id`. Pasar `X-Org-Id: <org>`.
3. Login 500 → Redis caído. `docker compose up -d redis`.
4. consolidación followers=0 → path overview 404 (arriba).
5. Ballesteros FODA 401 → password distinto (env fix).

## Decisiones de la sesión
- **Export canónico = per-plataforma** (`x_posts/yt_posts/tt_posts/fb_posts/ig_posts` shape gaby_delta), NO combinado. Hugo lo emite así.
- **Release privado sin GPG** (CEO aceptó el riesgo PII, consistente con 05-30).
- **NLP en paralelo funciona** — hasta 3 jobs LLM concurrentes, RAM nunca llegó a CRITICAL (pressure NORMAL; el WARN por swap es ruido de Antigravity).
- Reactors: esquema sha256/numérico mixto + overlap bajo entre exports es **histórico y normal** (no bug); Top Fans funciona.

## Pendientes (NO perder)
1. **NLP eficiente en tokens** (CEO 2026-06-03): el enrich es LLM-por-item (~3-6s/item × cientos × 7) → gasto alto. Buscar solución (clasificador batch/local, modelo barato, solo-delta). **PRIORIDAD del CEO.**
2. **SOP-INGEST-RADAR-HANDOFF.md** pendiente de auditoría Gemini independiente (regla MODELO §5).
3. Menor: reactors IG de Piña no enlazaron (events_in_db=0, formato media_id) — métrica secundaria, flagueado.
4. Carlos ejecuta el redeploy cuando el CEO coordine.

## Lección de la sesión (para el error notebook)
Patrón recurrente cazado por el CEO ~8 veces: **inventar problemas-fantasma** (afirmar sin
verificar) — RAM "alerta" sin medir, "adapters rotos" leyendo el equivocado, "re-export"
innecesario, contadores reportados como neto-nuevo. Regla reforzada: **verificar en silencio
ANTES de surfacear; reportar resultados, no sospechas; ningún claim sin evidencia pegada.**
El monitoreo activo (Monitor tool por job) reemplazó el "espero pasivo".

## Cómo retomar
- SessionStart carga STATUS/DECISIONS/BLOCKERS/PLAN + este handoff.
- Si CEO pide eficiencia NLP → ese es el pendiente #1.
- Si Carlos reporta el redeploy → verificar smoke test (counts del runbook) y borrar el Release PII.

---

## Actualización post-cierre (deploy verificado + override + blocker dedup)

### Estado de las apps desplegadas (medido, no asumido)
- **Vercel** (`frontend-zeta-sepia-46.vercel.app`) = la que usamos **nosotros + Carlos para VER**.
  Apunta al **backend LOCAL** vía túnel persistente (LaunchAgent `com.mdconsultoria.crece-tunnel.plist`
  → `start-crece-tunnel.sh` → quick-tunnel a `:8002`, auto-sincroniza URL a Vercel cada hora).
  **Tiene la data de HOY** (verificado: FODA Saymi id=122/06-03). **Depende de que el LOCAL esté ARRIBA.**
- **Coolify** (`crece.mdconsultoria-ti.org`, backend `api-crece...`) = demo de Carlos, instancia
  separada. **Tiene data VIEJA** (FODA id=96/05-27). Carlos restauró un snapshot anterior al `06-04`.
  → Carlos debe re-restaurar el Release **`data-snapshot-2026-06-04`** (runbook ya apunta ahí).
- **CRECE local quedó ARRIBA** a propósito (si se pausa, la Vercel pierde la vista de hoy).

### Override Misael re-impuesto (CEO 2026-06-04)
- Pedro Carlock (top real Saymi FB) creció a **378** post-ingest → override 320 quedó debajo.
- Subido a **400** en `vip-overrides.ts` (>378 real, <**765** techo de posts FB — defendible, NO pasa el techo).
- **ADR-0007** creado (supersedes ADR-0005, que quedó `Superseded`). Desplegado a Vercel (`vercel deploy --prod`).

### 🔴 BLOCKER NUEVO: posts duplicados mismo-plataforma (B-SAYMI-DUP / patrón B-FELIPE-FB-DUP-9)
- Las cards "Recepción del público" muestran posts 2× (ej. 12-may Mundial) por **duplicados reales en BD**.
- Confirmados ejemplos cross-scheme same-platform: `5609/5314` (FB-FB), `7531/9697` (IG-IG).
- **Magnitud NO confirmada:** conteo por prefijo de contenido da ~228 filas, pero **over-cuenta**
  (posts legítimos que comparten prefijo). El dup REAL = mismo post bajo `platform_post_id` distinto.
- **NO borrar a ciegas.** Sprint dedicado: (1) análisis preciso cross-scheme por `platform_post_id`,
  (2) distinguir dup-real vs prefijo-colisión vs cross-plataforma (legítimo IG+FB), (3) backup, (4) OK CEO, (5) DELETE redundantes (keep 1).
- Cross-plataforma (mismo contenido IG+FB) NO es dup — son posts distintos, no tocar.

### Commits de la sesión (todos en origin/main)
`7125452` Groq · `613adef` followers+SOP · `bdf71af` password env · `89a6c2e` runbook ·
`feat(vip)` Misael 400+ADR-0007 · `docs(handoff)` este archivo.

### Pendientes actualizados (orden de prioridad)
1. **NLP eficiente en tokens** (CEO) — el grueso del gasto del día.
2. **Dedup posts duplicados** (blocker nuevo, arriba) — afecta cards de recepción.
3. **Coolify de Carlos:** restaurar Release `06-04` (su cancha).
4. SOP de ingest pendiente de audit Gemini formal.
