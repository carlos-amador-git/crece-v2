# PLAN · Ingesta dump RADAR (Hugo) + validación coherencia + NLP audit + IA recomendaciones · 2026-05-20

**Mandato CEO (2026-05-20):**
- Ejecutar en autonomía cuando Hugo entregue dump RADAR (peer s2ryygne · cwd `/Users/marxchavez/Projects/radar`).
- **Saymi prioridad #1** (dirigente_id=3, piloto principal · cliente_seed 13 perfiles · Misael Fan #1 con 40 reactions / 12 comments per D-MISAEL-VIP-40).
- **Pepe Monroy prioridad #2** (dirigente_id=57).
- Loop de verificación y validación por fase: cada fase tiene **gate** que DEBE pasar antes de avanzar a la siguiente. Gate fallido = parar + reportar al CEO.
- Cross-audit Gemini sobre este plan ANTES de arrancar Fase 0.

**Branch sprint:** `feat/post-ingest-hugo-2026-05-20` (desde main · post PR #55 audit-full cierre).

---

## Contexto operativo

### Pre-condiciones (ya cumplidas)
- PR #55 mergeado (`cd3e408e75`). Backend con rate limit + sanitizer LLM + PII stripper. Frontend con filtros /hub + ErrorBoundary + sidebar "Fans y Perfiles" restaurado.
- Deploy prod `frontend-zeta-sepia-46.vercel.app` aliased al último build. Backend Mac Mini :8002 + Cloudflare tunnel activos.
- Schema CRECE con `tono_discurso` (matriz polaridad v2) + `sentiment_label` (legacy 3 buckets, sigue alimentado por NLP).
- Pipeline NLP backfill probado: `backend/scripts/audit_cc_effort_high.py` + `backend/scripts/backfill_nlp_saymi.py` (CC subprocess `--effort high`, timeout 600s + Gemini CLI fallback per D-PLAN-IA-CC-GEMINI-CLI-1).
- VIP overrides intactos en `frontend/src/lib/api/utils/vip-overrides.ts` (Misael 40/12).
- Veda middleware activo: validar fechas dump vs ventanas veda MX.

### Lo que CEO repetidamente ha marcado como crítico
1. **"Posts desconectados entre vistas"** — han visto N veces que el mismo post muestra likes/reactions/comments distintos en /hub vs /fantasmas vs /top vs /fans. **Fase 2 dedicada a cerrar esto.**
2. **"Errores de clasificación NLP"** — falsos positivos como Alebrijes campeones (logro deportivo +) clasificado negativo (-0.21), Día del Niño (positivo DIF) clasificado -1.00. **Fase 3 con deep-search ground-truth.**
3. **"Misael #1 en fans"** — VIP override BD-mockup en frontend. NO se toca. NO regresa a 80 reactions. **Verificación en Fase 5.**
4. **"Verificar fuente primaria antes de scoring"** — error notebook con 7+ misses. Aplica a TODO este sprint: NO afirmar sin evidencia empírica.

---

## Roles

| Actor | Responsabilidad |
|---|---|
| **Hugo** (peer `s2ryygne`) | Entregar dump RADAR (formato y endpoint TBD · clarifica al contactar) |
| **Yo** (Linda · Claude) | Ingest pipeline + NLP audit + cross-app validation + planes IA + recomendaciones + reporte |
| **Gemini CLI** | Cross-audit pre-arranque + clasificación dual labels para ground truth NLP (D-NLP-MAPPER-C) |
| **CEO** | GO/NO-GO final · validación cliente-facing · ajustes de plan tras Gemini review |

---

## Criterios de éxito globales (definición de "OK" para todo el sprint)

| # | Criterio | Cómo se mide |
|---|---|---|
| G1 | Dump Hugo ingerido sin pérdida de datos | Checksums Hugo declarados = checksums BD post-ingest. 0 NULLs en campos requeridos. 0 `data_source='UNKNOWN'` |
| G2 | Posts coherentes cross-app | Sample 30 posts Saymi: mismo `id` muestra mismos `likes/reactions/comments` en feed/top/comentarios/fans/fantasmas |
| G3 | NLP false positive rate <10% | Sample 50 posts Saymi clasificados humano (ground truth Linda) vs CC effort=high. Discrepancia <10% |
| G4 | Planes IA generados (Saymi + Pepe) sin PII expuesto | Output planes NO contiene `[email]`/`[tel]`/`[curp]`/`[rfc]` raw. Sanitizer activo. |
| G5 | Recomendaciones por post con parámetros definidos | 3+ ejemplos concretos cada categoría ("viral positivo", "alta crítica", "polarizado") con post real + recomendación accionable |
| G6 | Misael #1 visible en `/hub?tab=fans` y `/aceptacion/fantasmas?tab=observados` con 40r/12c | Playwright smoke confirma en prod |
| G7 | 0 errores 5xx / pageerror en flujo cliente | Playwright headless contra prod URL real |

Sprint **NO declarado OK** si cualquier G1-G7 falla.

---

## FASE 0 · Pre-ingesta (preparación · ~30 min)

**Objetivo:** preparar el ambiente para no perder datos ante incidente.

### Acciones
1. **Snapshot BD CRECE** (postmortem S-8.1 lesson · NUNCA ingest sin backup):
   - `docker exec crece-db pg_dump -U postgres crece > /tmp/crece-snapshot-pre-hugo-$(date +%Y%m%d-%H%M%S).sql`
   - Verificar tamaño >0, gzip, guardar path en bitácora.
2. **Métricas baseline Saymi/Pepe** (capturar ANTES de ingest):
   ```sql
   SELECT 'baseline-saymi' AS marker,
     (SELECT COUNT(*) FROM social_posts sp JOIN social_profiles sprof ON sp.profile_id=sprof.id WHERE sprof.dirigente_id=3) AS posts,
     (SELECT COUNT(*) FROM watched_like_events wle JOIN social_posts sp ON wle.post_id=sp.id JOIN social_profiles sprof ON sp.profile_id=sprof.id WHERE sprof.dirigente_id=3) AS reactors,
     (SELECT COUNT(*) FROM post_comments pc JOIN social_posts sp ON pc.post_id=sp.id JOIN social_profiles sprof ON sp.profile_id=sprof.id WHERE sprof.dirigente_id=3) AS comments,
     (SELECT COUNT(*) FROM social_posts sp JOIN social_profiles sprof ON sp.profile_id=sprof.id WHERE sprof.dirigente_id=3 AND sp.tono_discurso IS NOT NULL) AS tono_clasificados;
   ```
   - Idem para `dirigente_id=57` (Pepe).
   - Guardar en bitácora.
3. **Coordinación con Hugo** (claude-peers `send_message` to peer `s2ryygne`):
   - Pedir: formato dump (JSON masivo / SQL dump / endpoint POST), volumen estimado (#posts, #comments, #eventos), schema RADAR (mapear a schema CRECE), si necesita pre-procesamiento.
   - **No arrancar Fase 1 hasta tener respuesta.**

### Gate F0
- ✅ Snapshot creado, tamaño >0, path documentado.
- ✅ Baseline metrics guardados en bitácora.
- ✅ Hugo respondió con formato + volumen.

**Loop verificación F0:**
- Si snapshot vacío o falla → STOP. Investigar Docker/Postgres. Reportar al CEO.
- Si Hugo no responde en 30 min → STOP. Pingear de nuevo. Si no responde en 2h → reportar al CEO + escalar.

---

## FASE 1 · Ingesta (Saymi → Pepe · ~1-3h dep volumen)

**Objetivo:** dump Hugo dentro de BD CRECE con integridad verificada. Saymi primero (riesgo si rompe = menor que doble break).

### Acciones
1. **Adaptar script ingest** según formato Hugo:
   - Si JSON → script Python con `asyncpg` batch insert.
   - Si SQL dump → `pg_restore` selectivo.
   - Si endpoint API → wrapper script con auth.
   - **Idempotencia obligatoria:** UPSERT on `platform_post_id` + UNIQUE constraints. Re-correr no debe duplicar.
2. **Ingest Saymi** (dirigente_id=3):
   - Ejecutar script con dry-run primero (no commit), revisar count esperado.
   - Si dry-run OK → commit.
   - Capturar logs completos.
3. **Validar checksums + counts vs lo que Hugo declaró:**
   - posts ingestados = posts declarados Hugo
   - reactors = reactors declarados
   - comments = comments declarados
   - 0 NULLs en `published_at`, `platform`, `content`
   - 0 `data_source='UNKNOWN'` (regla CLAUDE.md · NUNCA `UNKNOWN`)
4. **`audit_data_quality --verbose`** post-ingest Saymi.
5. **Repetir 2-4 para Pepe** (dirigente_id=57).

### Gate F1
- ✅ Counts coinciden con declaración Hugo (tolerancia ±0.5%).
- ✅ Audit data quality sin warnings rojos.
- ✅ Idempotencia verificada (segunda corrida = 0 nuevos inserts).
- ✅ Veda check: si dump trae posts en fechas veda activa → marcar con flag `veda_aware=true` (verificar con `app/services/veda.py`).

**Loop verificación F1:**
- Si counts no coinciden → STOP. Logs + diff Hugo vs BD. Decidir: re-import (rollback snapshot + retry) o aceptar gap documentado (requiere CEO).
- Si NULLs detectados → STOP. Mapping incorrecto. Ajustar script.
- Si veda flag necesario y NO existe → crear migration ALTER TABLE + columna + re-evaluar fechas.

---

## FASE 2 · Coherencia cross-app (~1-2h)

**Objetivo:** mismo post muestra mismos números en TODAS las vistas. CEO marcó esto como crítico repetidamente.

### Acciones
1. **Seleccionar sample 30 posts Saymi** (mix: 5 high-engagement, 5 con reactors, 5 con comments, 5 mixtos, 5 sin RTs, 5 viejos pre-RADAR).
2. **Para cada post, capturar valores VIA endpoint** (no via UI):
   ```python
   # Pseudocódigo
   for post_id in sample:
       feed = GET /api/v1/posts/unified?dirigente_id=3&view=feed&...filter_to_specific_id
       top = GET /api/v1/posts/unified?dirigente_id=3&view=top&...
       comentarios = GET /api/v1/posts/unified?dirigente_id=3&view=comentarios&...
       fans = GET /api/v1/posts/unified?dirigente_id=3&view=fans&...
       fantasmas = GET /api/v1/aceptacion/fantasmas/... (endpoint Watched Profiles)
       # comparar likes/comments/shares/views entre los 5 que devuelven ese post_id
   ```
3. **Tabla de discrepancias:** por cada post, columna por vista, fila por métrica. Discrepancias en color.
4. **Para cada discrepancia:**
   - Caso A · datos esperados diferentes (ej. `reactors_capturados` solo en /fans, `engagement_rate` solo en /top) → DOCUMENTAR semántica, NO es bug.
   - Caso B · misma métrica con valores distintos (ej. `likes_publicos` = 100 en /feed pero 95 en /top) → BUG. Trazar query backend, identificar inconsistencia, fix.
5. **Caso especial Misael:**
   - `/hub?tab=fans` → Misael #1, 40 reactions, 12 comments (vip-overrides.ts intacto)
   - `/aceptacion/fantasmas?tab=observados` → Misael visible en cliente_seed sin vip-override (data real)
   - DOCUMENTAR explícitamente la divergencia frontend-only (es decisión, no bug).

### Gate F2
- ✅ Sample 30 posts: discrepancias categorizadas en A (semántica esperada) o B (bug).
- ✅ Bugs categoría B: FIX antes de avanzar O documentados con razón explícita.
- ✅ Misael: divergencia frontend-only documentada como D-MISAEL-VIP-40 reiterada.

**Loop verificación F2:**
- Por cada bug B encontrado, escribir test pytest reproducible en `backend/tests/api/v1/test_cross_app_coherence.py`.
- Si bug B requiere refactor de >100 LOC → STOP. Reportar al CEO. Decidir: fix ahora vs sprint dedicado.
- Si discrepancias >50% del sample → STOP. Problema sistémico (probable schema drift). Reportar.

---

## FASE 3 · Validación NLP deep-search (~2-3h)

**Objetivo:** NLP framework no produce false positives críticos como los visto antes (Alebrijes/Día del Niño clasificados Negativos cuando son Positivos).

### Acciones
1. **Sample 50-80 posts Saymi balanceado:**
   - 15 positivos obvios (logros, celebraciones, agradecimientos)
   - 15 negativos obvios (críticas a oposición, denuncias de problemas)
   - 10 mixtos (logros con caveat, propuestas con crítica)
   - 10 neutros (informativos puros, anuncios)
   - 10 RTs (idealmente excluidos por filtro pero deben estar en sample para verificar exclusión)
2. **Ground truth humano (Linda):** clasifico manualmente con razones explícitas en CSV.
3. **CC effort=high** sobre los mismos 50:
   - `python backend/scripts/audit_cc_effort_high.py --dirigente_id 3 --sample-ids <lista>` o equivalente.
   - **Test cost ratio check** (memoria 2026-05-14): costo NLP deep-search debe ser ≤15-20% del costo de extracción del dump Hugo. Si supera, reportar.
4. **Comparar:**
   - Por post: ¿coincide tono (positivo/negativo/neutro/mixto)?
   - Por post: ¿coincide signo polaridad (>0, <0, ≈0)?
   - Por post: ¿coincide target (propio/oficialismo/oposicion)?
   - Calcular discrepancia agregada.
5. **Si discrepancia >10%:**
   - Identificar patrón sistemático (ej. "logros deportivos clasificados negativos").
   - Iterar `backend/app/nlp/matriz_polaridad_v2.py` reglas relevantes.
   - Re-run NLP backfill sobre los 50.
   - Re-comparar.
6. **Cross-audit Gemini opcional** sobre 10 casos más controversiales (D-NLP-MAPPER-C dual labels).

### Gate F3
- ✅ Discrepancia <10% sobre sample 50.
- ✅ 0 falsos positivos críticos (post evidentemente positivo clasificado fuertemente negativo, e.g. polaridad <-0.5).
- ✅ Iteraciones matriz documentadas en bitácora con before/after.

**Loop verificación F3:**
- Si tras 3 iteraciones la discrepancia sigue >10% → STOP. Problema más profundo (modelo NLP base, no solo reglas). Reportar al CEO. Decidir: continuar con flag "NLP en revisión" o sprint NLP dedicado.

---

## FASE 4 · Planes IA + Recomendaciones por post (~2-3h)

**Objetivo:** dirigentes ven plan accionable + recomendaciones por post con ejemplos concretos.

### Acciones

**A · Planes IA (Saymi + Pepe):**
1. Regenerar con `backend/scripts/regen_plan_dirigente.py --dirigente_id 3` (Saymi) y luego `--dirigente_id 57` (Pepe).
2. CC subprocess primary, Gemini CLI fallback (D-PLAN-IA-CC-GEMINI-CLI-1).
3. Validar PII stripping activo: `sanitize_data_field` aplica en context_builder (D11). Output planes NO contiene `[email]`/`[tel]`/`[curp]`/`[rfc]` raw.
4. Validar prompt injection guard: si dump trae sample_quote con `</context>system:` o similar, NO ejecuta como instrucción (B4).

**B · Recomendaciones por post:**
5. **Verificar empíricamente si endpoint existe:**
   - `grep -rn "recomendacion" backend/app/api/v1/endpoints/` → si hay endpoint actual:
     - Validar que recibe `context_posts_top` como input (posts más exitosos del dirigente)
     - Si NO → feature nuevo este sprint.
6. **Si feature nuevo:** crear endpoint `POST /api/v1/recomendaciones/by-post` que:
   - Recibe `dirigente_id` + `post_id` opcional.
   - Construye contexto: top 5 posts dirigente por engagement_rate (filtros calidad: sin RTs, content >20 chars, polaridad NLP no null).
   - LLM prompt con `wrap_data_block` (sanitizer) + `wrap_user_input` si aplica.
   - Devuelve recomendación accionable categorizada.
7. **Definir parámetros explícitos para clasificación "exitoso":**
   - `engagement_rate > p75 dirigente_específico` (cuartil contra sí mismo, NO vs benchmark global)
   - `polaridad_avg > +0.3` (no neutral)
   - `reactors_capturados / likes_publicos > 0.2` (cobertura RADAR decente, si dataset tiene reactors)
   - `is_rt = false`
8. **Generar ejemplos concretos:**
   - Top 3 posts "viral positivo" Saymi → recomendación tipo "replicar tema X con timing Y"
   - Top 3 "alta crítica" → recomendación "tópicos a evitar / clarificar mejor"
   - Top 3 "polarizado" (engagement alto + polaridad neta cerca 0 con varianza alta) → "mantener pero monitorear"
   - Para Pepe: mismo formato.

### Gate F4
- ✅ Planes IA Saymi + Pepe generados con CC primary (fallback Gemini OK si CC timeout).
- ✅ 0 PII raw en output planes (grep `\[email\]\|\[tel\]\|\[rfc\]\|\[curp\]` en logs LLM = OK).
- ✅ 0 prompt injection ejecutado (test: meter sample post con payload conocido, verificar LLM no obedece).
- ✅ Recomendaciones por post: 3 ejemplos cada una de 3 categorías con post real + recomendación.

**Loop verificación F4:**
- Si CC timeout >2 retries → fallback Gemini CLI (per D-PLAN-IA-CC-GEMINI-CLI-1).
- Si Gemini también falla → STOP. Reportar al CEO. Decidir: outage proveedor o intentar tercer fallback (Ollama local descartado por D-1 · re-evaluar SOLO si CEO autoriza).
- Si feature recomendaciones-por-post >4h adicionales: descartar a sprint dedicado, documentar en backlog, continuar.

---

## FASE 5 · Validación UI Playwright (~30-60 min)

**Objetivo:** lo que el cliente ve está coherente, sin errores 5xx, con los datos nuevos visibles.

### Acciones
1. **Script Playwright** contra `frontend-zeta-sepia-46.vercel.app` (prod cliente):
   - Login Saymi (`pineda@crece.mx` / `demo2026!`).
   - `/dashboard/hub` con cada tab (feed/comentarios/top/fans): contar posts visibles, capturar screenshot.
   - `/dashboard/aceptacion/fantasmas?tab=observados`: verificar KPIs Saymi, Misael en lista cliente_seed.
   - `/dashboard/aceptacion/fantasmas?tab=resumen` y `?tab=por-plataforma`: verificar coherencia con dump nuevo.
   - `/dashboard/diagnostico/3` Saymi: cards Tier 1 + Tier 2 con datos nuevos.
   - `/dashboard/planes/{plan_id_nuevo}` Saymi: plan regenerado visible.
   - **Cross-verificación Misael #1:** screenshot `/hub?tab=fans` muestra Misael primero con 40 reactions / 12 comments.
2. **Repetir login Pepe** (credenciales TBD · pedir al CEO si no recuerdo).
3. **0 errores 5xx / pageerror durante toda la sesión.**

### Gate F5
- ✅ Todas las rutas critical-path responden 200, sin 5xx, sin pageerror.
- ✅ Datos Saymi visibles incluyen volumen de dump Hugo (no quedó solo el pre-ingest).
- ✅ Misael #1 con 40/12 en /hub?tab=fans (screenshot evidencia).
- ✅ Plan IA nuevo visible en `/dashboard/planes`.

**Loop verificación F5:**
- Si pageerror detectado → STOP. Stack trace + screenshot. Diagnosticar si es regresión del PR #55 o nuevo bug por datos Hugo.
- Si Misael NO #1 → STOP. vip-overrides.ts comprometido o data RADAR sobreescribiendo. Verificar.

---

## FASE 6 · Reporte cliente + cierre (~30-45 min)

**Objetivo:** entregable que CEO puede revisar/presentar a Saymi y Pepe.

### Acciones
1. **Reporte Saymi** (`.context/REPORTE-SAYMI-{fecha}.md`):
   - KPIs antes/después (volumen, reactors, comments, tono distribution).
   - Top 5 posts éxito + recomendación para cada uno.
   - Top 5 posts riesgo + acción sugerida.
   - Fans destacados (Misael #1 + top 10).
   - Plan IA generado con N tareas accionables.
   - Discrepancias residuales (honestas si las hay).
2. **Reporte Pepe** (mismo formato).
3. **Bitácora del sprint** (`.context/BITACORA-2026-05-20-post-ingest-hugo.md`):
   - Cronología fase por fase con timestamps reales.
   - Decisiones tomadas durante ejecución.
   - Loops de verificación que dispararon STOP + cómo se resolvieron.
   - Métricas finales vs criterios G1-G7.
4. **Actualizar `.context/STATUS.md`** con resumen ejecutivo.
5. **Commit + push** branch + abrir PR para revisión CEO + mergear post-aprobación.

### Gate F6
- ✅ G1-G7 todos verdes.
- ✅ Reportes Saymi + Pepe escritos y revisables.
- ✅ Bitácora completa y honesta (incluye fallos parciales si los hay).
- ✅ CEO aprueba para mostrar al cliente.

**Loop verificación F6:**
- Si CEO solicita cambios en reportes → iterar máx 2 veces antes de pedir clarificación.
- Si algún G1-G7 quedó rojo → reporte explícito de qué quedó pendiente y por qué (no ocultar).

---

## Riesgos identificados

| # | Riesgo | Probabilidad | Mitigación |
|---|---|---|---|
| R1 | Volumen dump > capacidad NLP backfill en ventana de tiempo | Media | NLP en background paralelo a Fases 2/4 (no bloqueante) |
| R2 | Schema RADAR ≠ schema CRECE (drift) | Media | Fase 0 confirma con Hugo antes de ingestar |
| R3 | NLP false positives persisten >10% tras 3 iteraciones | Media-alta (precedente Alebrijes/Día del Niño) | Gate F3 explícito · reportar al CEO antes de pasar a F4 |
| R4 | Bugs cross-app coherence requieren refactor >100 LOC | Media | Gate F2 con escalamiento explícito |
| R5 | Hugo dump trae PII real que sanitizer NO filtra | Baja-media | Fase 0 inspeccionar primeros 100 registros antes de batch full |
| R6 | Vercel deploy frontend rompe por cambios paralelos | Baja | NO desplegar frontend en este sprint · solo backend si necesario |
| R7 | Misael accidentalmente sobreescrito por data RADAR | Baja | vip-overrides.ts es frontend-only · BD jamás se toca · gate F5 verifica |

---

## Rollback plan

Si algo crítico falla en cualquier fase:

1. **Restore BD** desde snapshot Fase 0:
   ```bash
   docker exec -i crece-db psql -U postgres -c "DROP DATABASE crece;"
   docker exec -i crece-db psql -U postgres -c "CREATE DATABASE crece;"
   docker exec -i crece-db psql -U postgres crece < /tmp/crece-snapshot-pre-hugo-{ts}.sql
   ```
2. **Restart backend container** para limpiar cualquier caché.
3. **Verificar baseline metrics** = lo que se capturó pre-ingest.
4. **Reportar al CEO** con root cause + propuesta de re-intento o cambio de approach.

NO ejecutar rollback sin reportar antes al CEO (destructivo · per regla CLAUDE.md acciones destructivas).

---

## Cosas que CEO NO mencionó pero recomiendo agregar

(Sujeto a Gemini cross-audit · si CEO ajusta, eliminar lo que no aplique)

| # | Item | Por qué |
|---|---|---|
| A | **Veda electoral middleware activo** | Si dump trae fechas en veda, contenido debe etiquetarse (regla MX). Verificar `app/services/veda.py` se aplica al ingest. |
| B | **`audit_data_quality --verbose` post-ingest** | Detecta NULLs sospechosos, UNKNOWN data_source, duplicados (regla CLAUDE.md proyecto) |
| C | **Test PII stripper sobre dump real** | Validar sanitize_data_field filtra emails/teléfonos REALES del dump antes de mandar al LLM |
| D | **Comparar distribución tono_discurso pre/post ingest** | Si distribución cambia >10% → indicación drift NLP o cambio composición posts |
| E | **Backup Vercel env vars antes de ajustar** | Si por alguna razón hay que tocar NEXT_PUBLIC_API_URL · NO hacerlo sin backup |
| F | **Bitácora append-only durante ejecución** | NO esperar al final para escribir bitácora · loggear cada decisión en tiempo real |

---

## Próximos pasos (orden de ejecución)

1. **AHORA:** este plan a Gemini para cross-audit (CEO ejecuta).
2. **Tras Gemini OK:** arrancar Fase 0 (snapshot + baseline + coordinar con Hugo).
3. **Fase 0 → 1 → 2 → 3 → 4 → 5 → 6** en orden, con gate por fase.
4. **Reportar al CEO** SOLO en: (a) gate fallido que requiere decisión, (b) cierre Fase 6 con reportes listos.
5. **Si CEO interrumpe durante ejecución** → pausar fase actual, atender, retomar desde último gate verde.

---

## Bitácora de ejecución (append-only · llenar durante sprint)

### Fase 0 · pre-ingesta
- [ ] Snapshot BD creado · path: __________
- [ ] Baseline Saymi: posts=__, reactors=__, comments=__, tono_clasificados=__
- [ ] Baseline Pepe: posts=__, reactors=__, comments=__, tono_clasificados=__
- [ ] Hugo respondió: formato=__, volumen=__, schema=__
- [ ] Gate F0 ✅ o ✗ (razón)

### Fase 1 · ingesta
- [ ] Saymi ingestado · counts match Hugo: si/no
- [ ] Pepe ingestado · counts match Hugo: si/no
- [ ] audit_data_quality: 0 warnings rojos
- [ ] Gate F1 ✅ o ✗

### Fase 2 · coherencia cross-app
- [ ] Sample 30 posts analizado
- [ ] Bugs categoría B encontrados: __ · fixes: __
- [ ] Gate F2 ✅ o ✗

### Fase 3 · NLP validación
- [ ] Ground truth 50 posts: __
- [ ] CC effort=high run · discrepancia inicial: __%
- [ ] Iteraciones matriz polaridad v2: __
- [ ] Discrepancia final: __%
- [ ] Gate F3 ✅ o ✗

### Fase 4 · planes IA + recomendaciones
- [ ] Plan Saymi · plan_id=__ · n_tareas=__
- [ ] Plan Pepe · plan_id=__ · n_tareas=__
- [ ] 0 PII raw en outputs: confirmado
- [ ] Endpoint recomendaciones-by-post: existe / creado
- [ ] Ejemplos generados: viral_positivo=__, alta_critica=__, polarizado=__
- [ ] Gate F4 ✅ o ✗

### Fase 5 · UI validation
- [ ] Smoke Saymi: __/__ checks pass
- [ ] Smoke Pepe: __/__ checks pass
- [ ] Misael #1 verificado: si/no
- [ ] 0 errores 5xx/pageerror: si/no
- [ ] Gate F5 ✅ o ✗

### Fase 6 · reporte cliente
- [ ] Reporte Saymi escrito: path=__
- [ ] Reporte Pepe escrito: path=__
- [ ] Bitácora completa: path=__
- [ ] G1-G7 verdes: __
- [ ] CEO GO/NO-GO: __
- [ ] Gate F6 ✅ o ✗

---

**Estado actual:** plan formalizado · pendiente cross-audit Gemini antes de arrancar.
**Branch:** `feat/post-ingest-hugo-2026-05-20`
**Peer Hugo:** `s2ryygne` · esperando dump.
