# SPEC — Endpoint receptor de handoff RADAR→CRECE · v1 (2026-06-12)

**Para:** peer RADAR (anexo de su ADR D-050). **Código CRECE:** branch `feat/auto-radar-ingest`
(commits `7a847a8` + `22b9ee2`), pendiente E2E + merge. **Contrato base:**
`.context/PLAN-2026-06-11-auto-radar-crece.md` §2-3. Shape de archivos = **D-041 @ radar 2a775ba**.

## Flujo
1. RADAR sube bundle delta a MinIO de CRECE: bucket `crece-v2`, prefix `radar-handoffs/<slug>/<task_uuid>/`.
2. RADAR POSTea el manifest al webhook n8n (workflow pendiente de construir) → n8n llama a CRECE.
   Mientras no exista el workflow, el POST directo a CRECE funciona igual (mismo contrato).
3. CRECE valida, encola, procesa (Celery) y expone status.

## Auth
Header `X-API-Key: <key>` (tabla `api_keys` de CRECE, rol ADMIN). La key se genera en CRECE y
se comparte por env var de Coolify (NUNCA en git). Pendiente: emitirla en la ventana E2E.

## Endpoints

### `GET /api/v1/ingest/watermark/{dirigente_id}`
Último timestamp ingerido por plataforma. **RADAR exporta solo lo posterior** (traslape OK, idempotente).
```json
200 {"dirigente_id": 3,
     "posts":    {"FACEBOOK": "2026-06-05T18:22:00Z", "INSTAGRAM": null, ...},
     "comments": {"FACEBOOK": "2026-06-04T10:01:00Z", ...}}
404 dirigente no existe
```

### `POST /api/v1/ingest/radar-handoff` → `202`
```json
{
  "task_uuid": "string 8-64 chars, único por corrida (idempotencia)",
  "schema_version": "d041-v1",
  "slug": "saymi",
  "dirigente_id": 3,
  "window": {"from": "ISO8601", "to": "ISO8601"},
  "files": [{"name": "fb_posts.json", "sha256": "<64 hex>", "record_count": 123}],
  "minio_path": "radar-handoffs/saymi/<task_uuid>/",
  "capture_depth": {"FACEBOOK": "full", "TIKTOK": "posts_only"}
}
```
- `files[].name` ∈ {x,yt,tt,fb,ig}_posts.json · {fb,ig}_comments.json · reactors.json · followers.json.
  Solo declarar los que el bundle trae; CRECE corre solo esos pasos (orden SOP).
- `record_count`: items reales del archivo (lista→len; reactors→len(payload.reactors);
  followers→# plataformas). Discrepancia o sha256 mal → job **TAINTED**, NO se ingesta.
- `capture_depth` (opcional): redes en `posts_only` se EXCLUYEN del gate de cobertura
  (heads-up RADAR 2026-06-12 — no es gap, es configuración).
- **Idempotencia:** re-POST del mismo `task_uuid` → 202 con el job existente, NO re-procesa.
- **Backpressure:** ≥4 jobs en curso → `503` + `Retry-After: 300` (reintentar con backoff).
- `422`: schema_version no soportada / dirigente inexistente / manifest malformado.

Respuesta 202:
```json
{"id": 17, "task_uuid": "…", "status": "RECEIVED", "slug": "saymi",
 "dirigente_id": 3, "counts": null, "error": null, "created_at": "…", "finished_at": null}
```

### `GET /api/v1/ingest/jobs/{id}`
Mismo shape. `status` ∈ `RECEIVED → RUNNING → COMPLETED | PARTIAL | TAINTED | FAILED`.
- `PARTIAL` = ingest OK pero el gate detectó días con posts FB/IG sin reactors (`counts.coverage_gaps`).
- `counts` al terminar: `{"steps": [...], "db_delta": {...}, "db_after": {...},
  "coverage_gaps": [...], "nlp_local_queued": N}` — counts medidos contra BD, no inferidos.

## Garantías CRECE-side
- Adapters idempotentes (UPSERT/DO NOTHING) — re-push inofensivo.
- `ensure_author_hash` al ingerir (PII nunca cruda; RADAR NO pre-hashea).
- Lock por dirigente: nunca 2 bundles del mismo dirigente concurrentes (el 2º espera/reintenta).
- Followers se ingieren ANTES que posts (ER correcto, SOP §2).

## Pendientes para activar (ventana E2E, RAM gate SAFE)
migración `ingest_jobs` · API key emitida · E2E 1 dirigente · workflow n8n · merge a main → deploy Carlos.
