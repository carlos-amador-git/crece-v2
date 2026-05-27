# Re-ingest 3 MC desde radar_db + Enrich NLP RAM-safe — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: usar `superpowers:subagent-driven-development` (recomendado) o `superpowers:executing-plans` para implementar task-by-task. Steps usan checkbox `- [ ]`.

**Goal:** Terminar el enrich NLP de Piña(1)/Ballesteros(8)/Solano(2) — data YA INTACTA en `crece-db` :5438 (522/353/685 posts, enrich parcial 40-95%) — SIN agotar la RAM. ⚠️ CORRECCIÓN 2026-05-27: NO hay que re-ingestar; mi premisa de "data perdida" fue error de join (watched_profiles vs social_profiles). **Fases 0B/1/2 (extracción+ingest desde :5453) quedan CANCELADAS/superseded.** Trabajo real = Fase 3 (patch `--strict-mcp-config`) → Fase 4 (enrich idempotente, cubre delta) → Fase 5 (verificar app). Re-ingest solo aplica al delta NUEVO de Felipe cuando el peer lo cierre.

**Architecture:** Extraer `scrape_results.payload` de :5453 → JSON con la shape que ya consumen los adapters existentes → adapters escriben a :5438 → patch a los 4 sub-scripts NLP para invocar `claude --print` ligero (sin flota MCP) → enrich attended en lotes pequeños. NO se reescribe NLP ni se cambia a API de pago.

**Tech Stack:** psql/psycopg, scripts `backend/scripts/*` existentes, `claude` CLI v2.1.150 (`--print`), PostgreSQL 16 (crece :5438 + radar :5453).

---

## RESTRICCIONES DURAS (no negociables — origen: crash RAM 2026-05-27)

| # | Restricción | Por qué |
|---|---|---|
| R1 | **Modelo = Sonnet 4.6, effort = medium** en TODA invocación NLP: `CC_MODEL=sonnet CC_EFFORT=medium`. NUNCA Opus 4.7, nunca effort high/max. ⚠️ effort NO baja a `low`: audit D3 (2026-05-18) mostró que low subestima críticas en comments (34% cambios de signo); `medium` sí cubre la sensibilidad. | Confirmado CEO 2026-05-27 tras revisar transcript `ad3f41ed`: mi análisis previo fue Sonnet 4.6 + medium (Opus 4.7 = sobre-kill; Sonnet 6x más barato, sólido para clasificar). El modelo NO afecta la RAM (eso es R2); solo calidad/costo. |
| R2 | **`claude --print` NO debe arrancar la flota MCP.** Flag validado (Gate A, 2026-05-27): **`--strict-mcp-config`** (plain `--print`=26 procs MCP/llamada → con `--strict-mcp-config`=≈0, mantiene auth de suscripción, output válido, serial RAM-estable). NO usar `--bare` (rompe auth OAuth → exige API key). | 26 MCP × 650 llamadas plain unattended fue contribuyente del crash. |
| R3 | **Cero jobs unattended de noche.** Enrich corre attended, en lotes `--limit` pequeños, con monitoreo de RAM entre lotes. Concurrencia = 1 (serial). | El crash fue un background de ~650 spawns sin vigilancia. |
| R4 | **Gate de RAM antes de cada lote:** si RAM disponible < 2 GB → ABORTAR el lote, no continuar. | Detener antes de exhaustar, no después. |
| R5 | **Mantener el CLI `claude`** (per `D-PLAN-IA-CC-GEMINI-CLI-1`). NO migrar a anthropic SDK / API de pago sin OK explícito del CEO. | Decisión vigente: NLP/IA via CC CLI + Gemini CLI, sin billing por-token. |
| R6 | **Verificar contra data real** en cada gate (queries a :5438). No declarar "hecho" sobre supuestos. | Reglas de calidad CRECE + credibilidad. |

**App (Vercel `frontend-zeta-sepia-46`): NO es trabajo de este plan.** Está sana y auto-gestionada por el LaunchAgent `com.mdconsultoria.crece-tunnel.plist` (`start-crece-tunnel.sh`, idempotente). Solo se verifica al final (Fase 5).

---

## File Structure

- **No archivos nuevos de lógica** salvo el extractor (Fase 1). Reusar adapters + enrich existentes.
- Crear: `backend/scripts/extract_radar_3mc.py` — extrae :5453 `scrape_results` → JSON por (dirigente, plataforma) en la shape de los adapters.
- Modificar: `backend/scripts/backfill_nlp_posts.py`, `backfill_nlp_saymi.py`, `backfill_emotions_cc.py`, `extract_topics_saymi_cc.py` — solo la línea de construcción del comando `claude` (añadir flags RAM-safe de Gate A). Cambio quirúrgico, no refactor.
- Artefactos JSON: `backend/data/radar_3mc/<dirigente>_<plataforma>_{posts,comments}.json` (gitignored).

---

## Fase 0 — Gates de seguridad y descubrimiento (read-only / medición · ATTENDED)

Ninguna escritura. Resuelve los 2 unknowns reales antes de tocar nada.

### Task 0A: Fijar el mecanismo RAM-safe de `claude --print`

**Files:** ninguno (medición).

- [ ] **Step 1: Baseline — RAM de una invocación SIN mitigar**

```bash
/usr/bin/time -l env CC_MODEL=sonnet CC_EFFORT=medium \
  /Users/marxchavez/.local/bin/claude --print "responde solo: OK" 2>&1 \
  | grep -E "maximum resident set size|OK"
```
Expected: imprime "OK" y un RSS pico (referencia del costo actual, probablemente alto por MCP).

- [ ] **Step 2: Candidata A — `--bare`**

```bash
/usr/bin/time -l env CC_MODEL=sonnet CC_EFFORT=medium \
  /Users/marxchavez/.local/bin/claude --print --bare "responde solo: OK" 2>&1 \
  | grep -E "maximum resident set size|OK"
```
Expected: RSS sustancialmente menor que Step 1. (`--bare` = skip hooks/LSP/plugin sync/attribution/auto-memory.)

- [ ] **Step 3: Verificar que NO quedan procs MCP huérfanos tras la llamada**

```bash
sleep 2; pgrep -fl "mcp|modelcontextprotocol" | grep -v Claude.app | wc -l
```
Expected: 0 (o solo infra persistente no relacionada). Si crecen tras cada llamada → el flag no basta; probar aislar config: `env CLAUDE_CONFIG_DIR=/tmp/cc-min claude --print --bare ...` con dir mínimo sin MCP.

- [ ] **Step 4: Prueba de bucle serial (10 llamadas) — RAM debe quedar PLANA**

```bash
for i in $(seq 1 10); do
  env CC_MODEL=sonnet CC_EFFORT=medium /Users/marxchavez/.local/bin/claude --print --bare "di: $i" >/dev/null 2>&1
  echo -n "iter $i — free MB: "; vm_stat | awk '/free/{gsub(/\./,"");print int($3*4096/1048576)}'
done
```
Expected: free MB estable (±, no descenso monótono). **GATE: si desciende monótono → STOP, no proceder a enrich; reportar al CEO.**

**Acceptance 0A — RESUELTO 2026-05-27:** flag = **`--strict-mcp-config`** (NO `--bare`, que rompe auth). Medido: plain `--print`=26 procs MCP/llamada; `--strict-mcp-config`=delta 1 (≈0) + auth de suscripción OK + output válido; bucle serial de 8 con inferencia real → RAM estable (~1050-1230 MB), 0 procs colgados. ✅

### Task 0B: Shape del payload en :5453 vs contrato de los adapters

**Files:** lee `backend/scripts/ingest_radar_*.py` (no modifica).

- [ ] **Step 1: Leer el contrato de entrada de cada adapter**

Run: `Read` sobre `ingest_radar_ig.py`, `ingest_radar_yt_x_posts.py`, `ingest_radar_comments_payload.py` (docstring + parsing de `--json`). Anotar: claves esperadas por post/comment, cómo mapea profile, formato de `--posts`/`--comments`.

- [ ] **Step 2: Inspeccionar una `scrape_results.payload` real por plataforma (3 MC)**

```bash
docker exec -i radar-postgres-1 psql -U md_scraper -d radar_db -tA <<'SQL'
SELECT t.platform, sr.entity_type, left(sr.payload::text, 400)
FROM scrape_results sr JOIN targets t ON sr.target_id=t.target_id
WHERE t.target_id IN (
  '74b6889e-8309-4053-8831-07e31fff6ee8','5d2a6619-838f-419f-8ec6-87c49b824108',
  'dcbc15c8-e9c5-4f9c-9059-2afbd9c5f2fa','0213e3d5-adbb-45ff-85e5-1722925d0e74',
  '2d9df552-6eae-4277-b9ed-0ed50d9d8f39')  -- Piña FB/X/IG/TT/YT
ORDER BY t.platform LIMIT 5;
SQL
```
Expected: ver la estructura JSON cruda por plataforma. **Decisión:** ¿coincide con lo que el adapter espera (→ extracción directa) o requiere transform (→ el extractor mapea)?

**Acceptance 0B:** documentado, por plataforma, si `payload` se consume directo o con transform, y el mapeo exacto target→profile→dirigente. Lista de target_ids de los 9 perfiles MC (ya conocidos en STATUS POSTMORTEM 2026-05-27).

---

## Fase 1 — Extracción :5453 → JSON

### Task 1: `extract_radar_3mc.py`

**Files:**
- Create: `backend/scripts/extract_radar_3mc.py`
- Output: `backend/data/radar_3mc/<did>_<platform>_{posts,comments}.json`

- [ ] **Step 1:** Escribir el extractor: por cada (dirigente∈{1,8,2}, target de :5453), `SELECT payload FROM scrape_results WHERE target_id=... AND entity_type IN ('post','comment')`, aplicar el mapeo de Gate 0B, escribir JSON a `backend/data/radar_3mc/`. Lee :5453 con creds de `docker inspect` o env. NO escribe a :5438.
- [ ] **Step 2:** Correr en dry-run (solo cuenta filas por dirigente/plataforma, no escribe). Expected: counts > 0 por las redes que STATUS reportó (Piña 5 redes, etc.).
- [ ] **Step 3:** Correr real → genera los JSON. Verificar: `ls -la backend/data/radar_3mc/ && jq 'length' backend/data/radar_3mc/1_*.json`.
- [ ] **Step 4:** Commit: `git add backend/scripts/extract_radar_3mc.py && git commit -m "feat(ingest): extractor radar_db :5453 → JSON para re-ingest 3 MC"`. (data/ gitignored.)

**Acceptance 1:** JSON por dirigente/plataforma con counts coherentes con el volumen de :5453.

---

## Fase 2 — Ingest → crece-db :5438

### Task 2: correr adapters existentes (CERO código nuevo)

**Files:** usa `ingest_radar_ig.py`, `ingest_radar_yt_x_posts.py`, `ingest_radar_comments_payload.py`.

- [ ] **Step 1:** Pre-check — confirmar que NO hay data parcial previa de 1/8/2 en :5438 (evitar duplicados):
```bash
PGPASSWORD=crece_dev psql -h localhost -p 5438 -U crece -d crece -tA -c \
"SELECT COUNT(*) FROM watched_profiles WHERE dirigente_observador_id IN (1,8,2);"
```
Expected: 0 (verificado en POSTMORTEM). Si >0 → revisar antes de re-ingestar.

- [ ] **Step 2:** Ingestar por dirigente/plataforma con `--commit` usando la sintaxis de STATUS L10-12 y los JSON de Fase 1. Una red a la vez, verificando returncode 0.
- [ ] **Step 3:** Verificar inserción (schema real):
```bash
PGPASSWORD=crece_dev psql -h localhost -p 5438 -U crece -d crece -tA <<'SQL'
SELECT 'dir '||wp.dirigente_observador_id||': '||COUNT(DISTINCT sp.id)||' posts, '||COUNT(DISTINCT sc.id)||' comments'
FROM watched_profiles wp
LEFT JOIN social_posts sp ON sp.profile_id=wp.id
LEFT JOIN social_comments sc ON sc.parent_post_id=sp.id
WHERE wp.dirigente_observador_id IN (1,8,2) GROUP BY wp.dirigente_observador_id ORDER BY 1;
SQL
```
Expected: filas para 1/8/2 con counts > 0.

- [ ] **Step 4:** Verificar PII/ER limpios: `author_hash` poblado en social_comments nuevos, 0 PII cruda (guard `ensure_author_hash` del ingest). Commit no aplica (solo datos).

**Acceptance 2:** dir 1/8/2 con perfiles + posts + comments en :5438, ER/PII OK.

---

## Fase 3 — Patch NLP scripts RAM-safe (quirúrgico)

### Task 3: añadir flags de Gate 0A a los 4 sub-scripts

**Files (modify, solo la línea del comando `claude`):**
- `backend/scripts/backfill_nlp_posts.py:126`
- `backend/scripts/backfill_nlp_saymi.py:112`
- `backend/scripts/backfill_emotions_cc.py:67`
- `backend/scripts/extract_topics_saymi_cc.py:74`

- [ ] **Step 1:** En cada uno, insertar **`--strict-mcp-config`** (validado en 0A) en la lista `[CLAUDE_BIN, "--print", ...]`, manteniendo `--effort CC_EFFORT` y `--model CC_MODEL`. Cambio idéntico en los 4. Mostrar diff antes de commitear.
- [ ] **Step 2:** Smoke de 1 fila: correr un sub-script con `--limit 1` contra dir 1, medir RAM con `/usr/bin/time -l`. Expected: persiste 1 fila, RSS bajo, returncode 0.
- [ ] **Step 3:** Commit: `git commit -am "fix(nlp): claude --print RAM-safe (flags Gate 0A) en 4 backfills — previene crash RAM (postmortem 2026-05-27)"`.

**Acceptance 3:** los 4 scripts invocan `claude` ligero; smoke de 1 fila persiste con RAM baja.

---

## Fase 4 — Enrich attended, por lotes

### Task 4: correr `post_ingest_enrich.py` por dirigente, vigilado

**Files:** usa `backend/scripts/post_ingest_enrich.py`.

- [ ] **Step 1: Gate de RAM (R4) antes de empezar:**
```bash
vm_stat | awk '/free/{gsub(/\./,"");print "free MB:", int($3*4096/1048576)}'
```
Expected: > 2000 MB. Si menos → STOP.

- [ ] **Step 2:** Correr dir 1 en lote pequeño, attended:
```bash
cd backend && CC_MODEL=sonnet CC_EFFORT=medium PYTHONPATH=. \
  .venv/bin/python scripts/post_ingest_enrich.py --dirigente-id 1 --limit 50
```
Mientras corre, en otra terminal vigilar: `while true; do vm_stat | awk '/free/{...}'; sleep 5; done`. **Si free baja de 1.5 GB → Ctrl-C inmediato.**

- [ ] **Step 3:** Verificar cobertura tras el lote + repetir (idempotente, salta lo hecho) hasta cubrir dir 1. Query de cobertura:
```bash
PGPASSWORD=crece_dev psql -h localhost -p 5438 -U crece -d crece -tA -c \
"SELECT COUNT(tono_discurso)||'/'||COUNT(*) FROM social_posts sp JOIN watched_profiles wp ON sp.profile_id=wp.id WHERE wp.dirigente_observador_id=1;"
```
- [ ] **Step 4:** Repetir Steps 1-3 para dir 8, luego dir 2. Uno a la vez, nunca en paralelo, nunca background.

**Acceptance 4:** posts (tono/target/emotions/topics) y comments (nlp_tono/target/polaridad) de 1/8/2 enriquecidos; RAM nunca bajó del umbral; cero crashes.

---

## Fase 5 — Verificar que la app (lo que interesa) muestra los 3 MC

### Task 5: smoke en Vercel

- [ ] **Step 1:** Confirmar túnel sano (criterio del runbook): `curl -s -o /dev/null -w "%{http_code}" https://frontend-zeta-sepia-46.vercel.app/api/v1/health` → 200/308.
- [ ] **Step 2:** Verificar que los dirigentes 1/8/2 y sus cards (B0x/B14/FODA) renderizan con la data enriquecida (login + navegar, o `take_screenshot` vía browser). Expected: cards con NLP real, no skeleton/vacío.

**Acceptance 5:** los 3 MC visibles con NLP en el piloto.

---

## Self-Review (checklist del autor)

- **Cobertura spec:** re-ingest (F1-F2) ✓, enrich RAM-safe (F3-F4) ✓, restricción modelo/RAM (R1-R6) ✓, app verificada (F5) ✓.
- **Sin placeholders de código fabricado:** el extractor (F1) y los flags (F3) dependen de hallazgos de Fase 0 — por diseño, NO se inventa shape ni flag antes de medirlos (regla CRECE: verificar contra real, no alucinar). Los comandos de medición/verificación SÍ son concretos.
- **Consistencia:** dirigente IDs {1,8,2}, columnas reales (`dirigente_observador_id`, `parent_post_id`, `tono_discurso`, `nlp_tono`), creds (:5438 crece/crece_dev · :5453 md_scraper) consistentes en todo el plan.

## Riesgos / qué puede salir mal

- **Gate 0A falla (RAM no baja con `--bare`):** entonces el CLI no es viable como worker masivo → escalar al CEO la opción SDK (rompe R5) o reducir drásticamente el volumen. NO forzar.
- **scrape_results.payload no mapea a los adapters (0B):** el extractor necesita más transform del previsto → tarea de mapeo dedicada antes de F2.
- **Duplicados si F2 corre sobre data parcial:** Step 2.1 lo previene.
