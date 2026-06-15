# PLAN — Automatización RADAR→CRECE (delta + producción automática) · 2026-06-11

**Estado:** Propuesto · espera GO del CEO. Cross-audit Gemini ejecutado (consulta 2026-06-11,
output en `/tmp/gemini-out-radar-crece.md`, hallazgos integrados). Conciliado con peer RADAR
(2026-06-11, acordó división de trabajo; su lado = ADR D-050 con este spec como anexo).
**Requerimiento CEO (2026-06-11):** cuando RADAR concluye una tarea → comunica a CRECE →
CRECE carga la data SOLA → arranca EN AUTOMÁTICO la producción que alimenta el front.
Clientes fijos = SOLO deltas, no la base completa.

---

## 1. Topología (corregida — diseño para Coolify, no para el Mac)

CRECE producción **ya corre en Coolify** (VPS, deploy por Carlos desde GH). RADAR **va a
estar** en el mismo Coolify. n8n ya corre ahí (`n8n.mdconsultoria-ti.org`, nodos
`n8n-nodes-crece` + 7 endpoints dual-auth). Los 3 comparten VPS/red.

## 2. Arquitectura — Orquestador-Obrero (recomendación Gemini, adoptada)

**n8n = cerebro (control plane) · Celery = brazo (data plane) · data viaja pull-based por MinIO.**

```
RADAR (Coolify) ─ al concluir tarea ─▶ 1. sube bundle delta a MinIO (bucket radar-handoffs/<slug>/<task_uuid>/)
                                       2. POST webhook a n8n: SOLO manifest (sin archivos)
n8n ───────────────────────────────▶ 3. valida (¿cliente activo? ¿schema_version soportada?)
                                       4. POST /api/v1/ingest/radar-handoff (backend CRECE, manifest+ruta MinIO)
CRECE backend ─────────────────────▶ 5. 202 + job_id → Celery chain:
                                          a. descarga bundle de MinIO, valida checksums + record_count
                                             (discrepancia > 0 → bundle "Tainted", se reporta, NO se ingesta)
                                          b. adapters en orden SOP (followers→posts→comments→reactors,
                                             idempotente UPSERT, ensure_author_hash PII)
                                          c. gate de cobertura por fecha (SOP §2.5) → hueco = job "partial"
                                          d. enrich automático (ver Fases §4)
                                          e. refresh diagnósticos B01-B18
                                       6. callback a n8n: éxito/parcial/falla → n8n notifica/reintenta/alerta
GET /api/v1/ingest/jobs/{id} ─ status consultable (RADAR, n8n, humano)
```

**Por qué así (y no las alternativas):**
- *Directo RADAR→CRECE sin n8n:* funciona, pero deja a Celery como caja negra; n8n da el
  audit-trail visual + retry + alertas sin código, y ya es infra de la casa.
- *Orquestador nuevo (Windmill/Kestra/Activepieces/Trigger.dev):* investigado 2026-06-11 —
  maduros, pero agregar un 3er orquestador con equipo de 1 humano = distracción (Gemini
  coincide). n8n ya desplegado cubre el rol.
- *POST multipart con archivos:* descartado — propenso a 413/timeouts. Pull-based MinIO
  (ya en stack CRECE) es atómico.

## 3. Contrato delta

**Watermark vive en CRECE** (su BD = única fuente de verdad de qué se persistió):
- `GET /api/v1/ingest/watermark/{slug}` → último `published_at`/`comment_ts` ingerido por
  plataforma. RADAR exporta solo lo posterior. Traslape inofensivo (adapters idempotentes).
  **Prioridad #1 de Gemini:** esto solo ya reduce 60-80% la carga para clientes fijos.

**Manifest (campos mínimos):**
```json
{
  "task_uuid":      "…",          // idempotencia de transporte: doble-push del mismo uuid = no-op
  "schema_version": "d041-v1",    // si CRECE no la soporta → rechaza ANTES de tocar BD
  "slug":           "saymi",
  "dirigente_id":   3,
  "window":         {"from": "…", "to": "…"},
  "files":          [{"name": "fb_posts.json", "sha256": "…", "record_count": 123}, …],
  "minio_path":     "radar-handoffs/saymi/<task_uuid>/"
}
```

**Auth:** bearer token compartido vía env de ambos servicios (Coolify env vars, nunca en git).

## 4. Profundidad de la cadena automática (3 fases)

| Fase | Qué corre | Gate |
|---|---|---|
| **1 — Auto siempre** | Ingest → NLP local (pysentimiento/spaCy, $0) → diagnósticos B01-B18 | ninguno (determinista/barato) |
| **2 — Auto con tope de costo** | Enrich LLM (tono político/target/emotions/topics) vía API batcheada — **requiere ADR-0008 aceptado + API key en VPS** | costo estimado del bundle < umbral (propuesta: $2 USD/dirigente) · si excede → `PENDING_APPROVAL` |
| **3 — Humano en el loop** | FODA / consolidación / contenido (generación LLM completa) | clic manual o webhook n8n tras revisar diagnósticos |

**Dependencia dura Fase 2:** el enrich actual usa `claude --print` en el host Mac
(suscripción CC) — NO existe en VPS. Camino: ADR-0008 (rutear textual→local, político→LLM
API batcheado). Decisión CEO pendiente: qué API key vive en el VPS + tope de gasto.

## 5. Guardrails (modos de falla, de Gemini)

1. **Lock de concurrencia por slug** (Redis): nunca 2 bundles del mismo dirigente a la vez.
2. **Backpressure:** cola Celery > N → endpoint devuelve 503 → n8n reintenta con backoff.
3. **Tainted bundle:** `record_count` del manifest vs ingerido; discrepancia → no se acepta en silencio.
4. **RAM del VPS:** pysentimiento (BERT) + todo lo demás en el mismo fierro → enrich serial
   (concurrencia 1), modelo se carga lazy, y medir RAM del VPS antes del rollout.
5. **Push durante deploy:** task_uuid + MinIO hacen el handoff re-entregable; n8n reintenta.

## 6. División de trabajo

| Lado | Entregable | Estado |
|---|---|---|
| **CRECE (este repo)** | endpoint handoff + watermark API + Celery chain + bucket MinIO + workflow n8n de ingest | a construir (Sprint 0 abajo) |
| **RADAR (peer)** | al concluir export: subir bundle a MinIO + POST manifest a n8n · ADR D-050 con este spec como anexo · **commit versionado del shape D-041** (sin eso no hay firma) | conciliado 2026-06-11, espera spec + GO CEO |
| **CEO** | GO general · decisión API key LLM en VPS + tope $ (Fase 2) · GO D-049 lado RADAR | pendiente |

## 7. Orden de ejecución (Sprint 0 primero — lección postmortem S-8.1)

1. **Sprint 0:** watermark API + endpoint handoff + chain Fase 1, probado E2E con **1 dirigente**
   en local (stack levantado ad-hoc), con SLO cuantitativo (cobertura % + counts cuadrados).
2. Workflow n8n (webhook→validación→API CRECE→notificación).
3. Push a GH → Carlos redeploya CRECE en Coolify (su cancha).
4. RADAR conecta su lado (D-050 aprobado) → piloto 1 dirigente en VPS.
5. Fan-out a todos los clientes fijos + Fase 2 (cuando ADR-0008 esté aceptado).

## 7.1 Decisión de orquestador — CERRADA 2026-06-11 (convergencia 5/5)

n8n se queda como control plane. Cinco fuentes independientes convergen en "quédate con n8n":
(1) Gemini cross-audit, (2) investigación web propia, (3) deep-research CEO #1, (4) deep-research
CEO #2 (fuentes citadas; tabla de umbral: NINGÚN candidato cumple ≥2x en criterio 1 o 2 sin
empeorar otro), (5) deep-research CEO #3 (Compass, `~/Downloads/compass_artifact_wf-c18d3438-*.md`
— el más riguroso: declara "no hay dato idle medido" para Windmill/Kestra/Trigger.dev/Inngest/
Hatchet/Temporal; baseline idle de n8n inconsistente entre fuentes 100MB-1.1GB; Node-RED ~128MB
y Activepieces ~350MB técnicamente cruzan 2x pero reconstruir nodos custom + audit-trail reactiva
el criterio 6 y anula la ganancia a este volumen). Discrepancias menores de RAM entre reportes
no afectan el veredicto. NO se re-abre salvo disparadores abajo.

**Operativa n8n adoptada del deep-research #3 (gestión del incumbente):**
1. **Pin de versión Docker** (NO `latest`) — n8n 2.0 salió dic-2025 con breaking changes (task
   runners default, Code node sin env vars) y cadencia anunciada 1-2 majors/año. Antes de saltar
   1.x→2.x: Migration Report tool (Settings → Migration Report, ≥1.121.0) + staging.
2. **Límite de RAM al contenedor** (`--memory=1g` en Coolify) contra el memory creep reportado.
3. **Disparadores explícitos de reevaluación** (lo ÚNICO que re-abre la decisión):
   - *Recursos:* idle n8n sostenido >1.5-2GB presionando al resto del VPS → pilotear Node-RED.
   - *Licencia:* endurecimiento de la Sustainable Use License o features usadas movidas a
     `.ee`/Enterprise → migrar a Activepieces (MIT, UX más cercana).
   - *Volumen:* cientos/miles de eventos por minuto → considerar durable execution (Hatchet/Inngest).
4. **Defensa en profundidad:** retries con backoff también en el cliente RADAR (patrón
   `2**retries`), no solo en n8n — complemento, no reemplazo del audit-trail.
⚠️ Los puntos 1-2 tocan el n8n COMPARTIDO del VPS → cambio de infra coordinado (CEO/Carlos).

**Sub-tarea adoptada del deep-research — hardening de memoria del n8n del VPS:**
`EXECUTIONS_DATA_PRUNE=true` + retención corta (72-168h) + `DB_SQLITE_VACUUM_ON_STARTUP=true`
→ idle ~200-450MB. ⚠️ Matiz: NO aplicar `EXECUTIONS_DATA_SAVE_ON_SUCCESS=none` (mataría el
audit-trail visual, que es la razón de elegir n8n). ⚠️ Ese n8n es infra COMPARTIDA (chatmx,
otros productos) → el cambio de env vars se coordina como cambio de infra (CEO/Carlos), no se
aplica unilateral.

## 8. Qué NO hace este plan

- NO automatiza el scrape de RADAR (fuera de alcance; lane de RADAR).
- NO mete orquestador nuevo (Windmill/Kestra/etc. — descartados con investigación).
- NO backup continuo (CEO 2026-06-11: backups bajo demanda; hecho `crece-20260611-1908.dump`
  en `/Volumes/Proyects/crece-backups/`).
- NO toca `PLAN-current.md` (ACTIVE apunta a cards) — el CEO decide si este plan lo supersede.
