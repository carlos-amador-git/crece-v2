# HANDOFF — Sprint 0 E2E pipeline RADAR→CRECE + experimento destilación NLP · 2026-06-12

> **UPDATE cierre final (12:40):** tras 3 ciclos de corrección upstream (RADAR fix join reels
> + esquema dual D-044, yo regla cero-real en gate): **5/5 COMPLETED · 0 gaps · BD 404,862
> reactor-events** (jobs 12-16). El pipeline absorbió las 3 rondas sin intervención manual de
> datos. Branch en 8 commits (incluye `fix cero-real`). Stack detenido (stop limpio).

**Status:** cierre de ventana. Pipeline automatizado PROBADO E2E con data real. Stack detenido (stop limpio).
**Sesión:** Linda · Claude Opus 4.8 · 2026-06-11/12 (ventana RAM abierta por CEO, autonomía total).
**Branch:** `feat/auto-radar-ingest` (6 commits, SIN push — espera OK CEO).

## ⚠️ LEER PRIMERO
1. **El pipeline RADAR→CRECE FUNCIONA E2E** (PLAN-2026-06-11 Sprint 0 cerrado): MinIO→manifest→validación→adapters SOP→gate cobertura→NLP local→counts medidos. 6 jobs reales en `ingest_jobs`.
2. **Pendiente #2 (reactors 5 dirigentes) QUEDÓ HECHO de paso:** +9,287 reactor-events → BD 353,931. Sentiments drenados: 0 pendientes en los 5 dirigentes (cobertura total 7,529/8,121).
3. **Stack DETENIDO** (stop limpio, resucitador descargado — ver RUNBOOK-STOP-START-LOCAL-MAC.md). Relevantar: `docker start crece-db crece-redis crece-minio crece-backend crece-celery-worker` (+ bootstrap del LaunchAgent si se quiere el auto-resume).

## Qué se hizo (todo medido)
- **Receptor handoff completo:** watermark API + POST /ingest/radar-handoff (idempotente task_uuid, backpressure 503, Tainted gate sha256+record_count, capture_depth) + GET /ingest/jobs/{id} + Celery chain + lock Redis por dirigente + migración `ingest_jobs` (⚠️ autogenerate traía drift DESTRUCTIVO — drop social_comments — recortada a mano; NO aplicar autogenerate sin revisión en este repo).
- **E2E con los 5 exports frescos de RADAR (20260612):** felipe COMPLETED +3 · saymi COMPLETED +8,550 · pina/gaby/balles PARTIAL (+130/+444/+160, gaps FB reales de mayo, re-export quirúrgico ya pedido a RADAR: pina 05-16 · gaby 05-02+05-16 · balles 05-14+05-15 = 10 posts). Idempotencia re-push verificada. 12/12 unit tests.
- **Experimento destilación NLP (idea CEO):** MiniLM frozen+LogReg sobre 9,518 comments → random 70%, held-out por dirigente 56-70% → **NO pasa umbral 85-90%**. ADR-0008 (político→LLM batcheado) se sostiene. Posible v2: fine-tune BETO + features contexto. Report: `/tmp/distill_report_nlp_polaridad.json` (copiar a repo si se quiere conservar).
- **API key `radar-handoff-ingest`** creada (id=1, user admin). Raw en `/tmp/crece_radar_api_key.txt` (0600) — **compartir a RADAR por env var, NUNCA git; mover de /tmp a un lugar durable o regenerar si se reinicia la Mac.**
- **Bugs cazados:** FK social_comments=parent_post_id (no post_id) · PYTHONPATH pisado en subprocess · MINIO_ACCESS_KEY sin mapear (fix compose dev; **Coolify necesita esas env** — está en SPEC).

## PENDIENTES (orden)
1. **Workflow n8n** (webhook RADAR→validación→API CRECE→notificación) — n8n.mdconsultoria-ti.org, credenciales con el CEO.
2. **Merge `feat/auto-radar-ingest` a main** + push (OK CEO) → redeploy Carlos con env MinIO nuevas.
3. RADAR: cliente push D-050 (usa `scripts/e2e_push_handoff.py` como referencia) + re-export quirúrgico 10 posts.
4. NLP destilación v2 (fine-tune) — solo si el CEO quiere iterar; los números v1 no lo justifican aún.
5. Fase 2 enrich LLM batcheado en VPS: decisión CEO API key + tope $.

## Commits de la sesión (branch feat/auto-radar-ingest)
`f1473e9` docs plan+runbook · `7a847a8` receptor+chain · `22b9ee2` fix FK · `<capture_depth+spec>` · `<fix PYTHONPATH+minio+migración>` · `<experimento NLP>` — ver `git log`.

## PENDIENTE entrante (2026-06-12 · paquete RADAR LISTO en radar/exports/)
- **3 deltas listos para ingerir** (próxima ventana RAM · docker abajo por instrucción CEO):
  `felipe-reactors-v2-20260612.json` 8,339 · `pepe-reactors-v2-20260612.json` 30,814
  (**PRIMER reactors de Pepe, dirigente_id=57**) · `saymi-reactors-v2-20260612.json` 139,378.
  Shape D-041, match FB 100%. Cadena: `e2e_push_handoff.py --slug X --dirigente-id N`.
- IG-posts de Saymi desde 06-03 pendiente lado RADAR (throttle chatmx_oficial, completa
  al enfriar). Los 9 posts pina/gaby/balles YA quedaron resueltos en el v3 del mediodía.
- NOTA: el archivo de saymi/felipe SOBREESCRIBE el del mediodía (mismo nombre 20260612) —
  ingerir con task_uuid nuevo; idempotente.
