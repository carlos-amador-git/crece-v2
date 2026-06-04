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
