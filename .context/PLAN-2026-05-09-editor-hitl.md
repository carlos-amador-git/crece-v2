# PLAN · Editor HITL evaluación NLP + pendientes integrados

**Fecha:** 2026-05-09
**Sprint:** Editor HITL + F-NLP-3 + ground truth · reunión 2026-05-10 con Solano/Piña/Ballesteros
**Owner:** Linda (CC sesión electoral) + dispatch a sub-agents en paralelo
**Tiempo objetivo:** 9-11h con paralelización
**Estado:** APROBADO CEO 2026-05-09 · arrancando

---

## Filosofía del flujo (CEO 2026-05-09)

```
SISTEMA PROPONE                      DIRIGENTE CONFIRMA O MODIFICA
─────────────────                    ─────────────────────────────
Runner Gemma + mapper v3             Solano/Piña/Ballesteros entran a
populan nlp_tono / nlp_target        /dashboard/settings/evaluacion-nlp
en social_comments y                 ven la propuesta del sistema en cada
social_posts (HOY ya pasa)           row, modifican lo que está mal.
                                     El edit aplica DIRECTO. No hay
                                     queue de approval intermedia.

                                     • Sin tocar = confirmación implícita
                                     • Modificación = audit log + recompute
                                     • Siempre opera sobre SU dirigente
```

**Por qué no hay queue de approval** (corregido 2026-05-09 tras feedback CEO): cada dirigente es la autoridad final sobre la clasificación de SUS posts y comments. Solano valida lo de Solano, Piña lo de Piña. La matriz política v2 con `rol='oposicion'` (todos MC) calcula score correcto desde la perspectiva del dirigente. No hay sesgo entre actores porque cada uno opera sobre datos disjuntos.

**Roster es 100% oposición.** MC = oposición frente a Morena. Todos los dirigentes del piloto computan con `rol_politico='oposicion'`. Diferencias entre dirigentes son de individuo (estilo, audiencia), no de rol. Capacidad técnica de oficialismo queda en `framework_matrix_defaults` para futuro tracking de Morena (no caso operativo presente).

---

## Sprints (8 sprints + 3 pendientes integrados)

### S1 · Schema + audit log (45 min) · backend-architect

Archivos:
- `backend/migrations/versions/dse_hitl_audit.py` (nueva)
- `backend/app/models/hitl_audit.py` (nuevo)

Cambios DB:
```sql
ALTER TABLE social_comments
  ADD COLUMN last_reviewed_by INT REFERENCES users(id),
  ADD COLUMN last_reviewed_at TIMESTAMP,
  ADD COLUMN review_status VARCHAR(20) DEFAULT 'unreviewed';
  -- unreviewed | confirmed (sin cambio) | edited (cambió label)

ALTER TABLE social_posts
  ADD COLUMN last_reviewed_by INT REFERENCES users(id),
  ADD COLUMN last_reviewed_at TIMESTAMP,
  ADD COLUMN review_status VARCHAR(20) DEFAULT 'unreviewed';

CREATE TABLE hitl_edits_log (
  id SERIAL PRIMARY KEY,
  entity_type VARCHAR(20) NOT NULL,  -- 'post' | 'comment'
  entity_id INT NOT NULL,
  dirigente_id INT NOT NULL REFERENCES dirigentes(id),
  from_tono VARCHAR(20),       -- propuesta del sistema
  to_tono VARCHAR(20),         -- decisión del dirigente
  from_target VARCHAR(30),
  to_target VARCHAR(30),
  off_topic BOOLEAN DEFAULT FALSE,
  actor_id INT NOT NULL REFERENCES users(id),
  source VARCHAR(30) NOT NULL DEFAULT 'hitl_settings_evaluacion_nlp',
  reason TEXT,
  edited_at TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT entity_type_check CHECK (entity_type IN ('post','comment'))
);

CREATE INDEX idx_hitl_edits_entity ON hitl_edits_log(entity_type, entity_id);
CREATE INDEX idx_hitl_edits_dirigente ON hitl_edits_log(dirigente_id, edited_at DESC);
CREATE INDEX idx_social_comments_review ON social_comments(review_status, parent_post_id);
```

Aceptación: `alembic upgrade head` limpio + reversible · constraint funciona · seed audit row de prueba.

### S2 · Endpoints HITL backend (1.5h) · backend-architect

Archivo nuevo: `backend/app/api/v1/endpoints/hitl_evaluation.py` (router `/hitl`)

Endpoints (RBAC: VIEWER solo opera sobre `user.dirigente_id`; ADMIN sobre cualquiera):

```
GET  /hitl/sample
     ?dirigente_id=X
     &scope=cronologico|estratificado    (default cronologico)
     &days=30                            (default 30)
     &platform=all|x|ig|fb|tt|yt         (default all)
     &include_reviewed=false             (default false)
     &n_comments=50&n_posts=20

     → Returns:
        { posts: [...20], comments: [...50],
          progress: { reviewed_total, pending_total },
          system_proposal_summary: { tono_dist, target_dist } }

PATCH /hitl/comments/{id}
     body: { tono?, target?, off_topic?, reason? }
     → UPDATE social_comments SET nlp_tono=..., review_status='edited',
                                  last_reviewed_by, last_reviewed_at
     → INSERT hitl_edits_log
     → call recompute_score_comment(id)
     → return updated comment + new score

POST  /hitl/comments/{id}/confirm
     → UPDATE social_comments SET review_status='confirmed',
                                  last_reviewed_by, last_reviewed_at
     → INSERT hitl_edits_log con from=to (confirmación implícita)
     → return ok

PATCH /hitl/posts/{id}            (análogo a comments)
POST  /hitl/posts/{id}/confirm    (análogo)

GET  /hitl/audit/{dirigente_id}
     ?since=2026-05-09
     → Returns audit history (read-only, para Linda/CEO ver actividad)
```

Tests: `backend/tests/api/test_hitl_evaluation.py` (≥10 tests)
- Happy path edit comment con cambio
- Happy path confirm comment sin cambio
- 403 cross-dirigente VIEWER
- 401 sin auth
- 200 ADMIN edita cualquier dirigente
- audit log poblado con from→to correctos
- recompute_score_comment llamado en edit
- sample estratificado distribuye uniforme
- sample cronologico ordena DESC
- include_reviewed=false oculta los confirmados/editados

Aceptación: tests pasan + smoke con curl contra contenedor.

### S3 · Recompute helper (30 min) · python-expert

Archivo nuevo: `backend/app/services/score_recompute.py`

```python
async def recompute_score_comment(db: AsyncSession, comment_id: int) -> int:
    """Re-aplica matriz v2 sobre 1 comment usando rol_politico del dirigente padre.
    Idempotente. Sub-segundo. Retorna score nuevo o 0 si no hay match."""

async def recompute_score_post(db: AsyncSession, post_id: int) -> int:
    """Análogo para post."""

async def recompute_dirigente_aggregate(db: AsyncSession, dirigente_id: int) -> dict:
    """Recalcula actividad_politica_alineada para un dirigente.
    Usar después de batch grande, no por cada edit."""
```

Tests: `backend/tests/services/test_score_recompute.py` (≥6 tests)

Aceptación: tests verdes + integrado en S2 endpoint approve flow.

### S4 · Frontend evaluador (3h) · frontend-architect

Archivos:
- `frontend/src/app/dashboard/settings/evaluacion-nlp/page.tsx` (nueva)
- `frontend/src/components/evaluacion/EvaluacionNlpClient.tsx` (nueva)
- `frontend/src/components/evaluacion/CommentEvaluator.tsx` (nueva)
- `frontend/src/components/evaluacion/PostEvaluator.tsx` (nueva)
- `frontend/src/components/evaluacion/EvaluacionConfig.tsx` (filtros)
- `frontend/src/lib/api/hitl.ts` (cliente)

Estructura de pantalla:
```
┌──────────────────────────────────────────────────┐
│ Evaluación NLP de tu actividad                   │
│ ┌────────────────────────────────────────────┐   │
│ │ Filtros: [30 días▾] [Todas plat▾]          │   │
│ │ Modo: ◉ Últimos  ○ Estratificado           │   │
│ │ ☑ Solo pendientes                          │   │
│ └────────────────────────────────────────────┘   │
│                                                  │
│ Progreso: ████████░░░░ 23/70  pendientes:47      │
│                                                  │
│ ── TUS POSTS (20) ──                             │
│ [PostEvaluator card × 20]                        │
│                                                  │
│ ── COMENTARIOS A TUS POSTS (50) ──               │
│ [CommentEvaluator row × 50]                      │
└──────────────────────────────────────────────────┘
```

Cada CommentEvaluator row:
- texto del comment + meta (autor, fecha, plataforma, post padre)
- nuestra propuesta visible: `tono: critica` `target: gobierno` (badges)
- dropdown tono (7 valores v2) + dropdown target (7 valores v2)
- ☑ "off-topic / ruido"
- textarea opcional "razón" (para auditoría)
- botones: "✓ Confirmar como está" · "💾 Guardar cambio"
- estado visual: gris=unreviewed, verde=confirmado, azul=editado

Optimistic UI con rollback en 4xx. Skeletons mientras carga sample.

Aceptación:
- Probado en browser con `solano@crece.mx` (VIEWER)
- Edita 5 comments, confirma 3, marca 1 off-topic
- Verifica que en BD aparecen los audit_log rows
- Verifica que en `/dashboard/aceptacion/{dirigente_id}` los KPIs cambiaron
- Screenshot adjunto al plan para mañana

### S5 · UI dual labels opción B en dashboards existentes (1.5h) · frontend-architect

Pendiente del paquete §5 decisiones CEO 2026-05-08. Mientras esté disponible el evaluador, también dejar visible en el dashboard normal qué labels son de sistema vs editados por humano.

Cambios:
- En `/dashboard/social/page.tsx` y `/dashboard/aceptacion/[dirigente_id]/page.tsx` añadir badge:
  - 🤖 "Sistema" si `review_status='unreviewed'`
  - ✓ "Confirmado" si `review_status='confirmed'`
  - 👤 "Editado por [nombre]" si `review_status='edited'` con tooltip al hover mostrando from→to
- Filtro toggle "Solo etiquetas validadas por humano" (oculta unreviewed)

Aceptación: badges renderizan correctamente, tooltip muestra audit, filtro funciona.

### S6 · Script batch review HITL → Claude+Gemini (1h) · python-expert

Archivo nuevo: `backend/scripts/hitl_review_batch.py`

Genera reporte cada vez que se ejecute (manual desde IDE):
- Matriz confusión `from_tono` (sistema) vs `to_tono` (humano) — ver dónde el sistema se equivoca más
- Matriz confusión target
- Top 20 patrones repetidos: "sistema dijo X+Y → humano dijo X'+Y' (N veces)"
- Lista off-topic flagged → candidatos a blacklist runner Gemma o regex pre-filter
- Tasa de "confirmación implícita" vs "edit" — métrica de calidad del sistema
- Sugerencias automáticas:
  - Si humano cambia ≥5 veces "ataque"→"informativo" para target=ciudadania → posible regla mapper G6
  - Si humano marca ≥10% off-topic en runner=`autopromocion`+target=ciudadania → revisar runner
  - Si confusión entre `propositivo` y `celebratorio` >20% → ambigüedad de criterio, considerar merge

Output:
- `/tmp/HITL-REVIEW-PATTERNS-{date}.md` (legible para Linda/CEO)
- `/tmp/HITL-REVIEW-PATTERNS-{date}.json` (input para Claude+Gemini)

Aceptación: ejecuta sobre BD con ≥10 audit rows y produce MD + JSON consistentes.

### S7 · F-NLP-3 · Recompute actividad_politica_alineada global (30 min) · python-expert

Pendiente alto impacto desde D+0. Aplica matriz v2 + 7 reglas nuevas sobre los 2696 comments populated y actualiza agregaciones.

Archivo nuevo: `backend/scripts/recompute_actividad_alineada_global.py`

Pasos:
1. SELECT 2696 comments con `nlp_tono IS NOT NULL`
2. Para cada uno, llamar `recompute_score_comment(id)` (de S3)
3. Agregar por dirigente: contar score>0, score<0, score=0
4. UPDATE en `dirigentes` o tabla `actividad_politica_alineada` (verificar schema actual)
5. Output: `/tmp/RECOMPUTE-GLOBAL-{date}.md` con tabla pre/post por dirigente

Aceptación: dashboard `/dashboard/aceptacion/{dirigente_id}` refleja scores reales no-cero · MD presentable a CEO con tabla pre/post.

### S8 · Ground truth 100 rows seed=42 (1h) · python-expert + Linda

Pendiente del paquete §5. Generar la muestra estratificada que servirá de baseline humano contra mapper.

Archivo nuevo: `backend/scripts/sample_ground_truth_100.py`

Estratificación: por (tono_runner × target_runner) con seed=42, top 100 con cobertura proporcional de las celdas más frecuentes.

Output: `backend/evaluations/ground_truth/2026-05-09-100rows.csv` con columnas:
- comment_id, content, runner_tono, runner_target, mapper_tono_v2, mapper_target_v2, dirigente_rol, score_actual
- columnas vacías para anotación: `humano_tono`, `humano_target`, `humano_off_topic`, `nota`

Linda anota 30 rows como semilla. Solano/Piña/Ballesteros completan en la reunión via el evaluador frontend (S4) — esos van a `hitl_edits_log`, no al CSV. Después script `merge_ground_truth.py` (S6 lo hace implícito vía batch review) une CSV anotaciones + audit_log para alimentar Claude+Gemini.

Aceptación: CSV existe + 30 rows anotadas por Linda + MD con plan de cómo se cruza con audit log.

### S9 · Tests E2E + smoke con perfil real (1h) · test-backend + Linda

Archivos:
- `backend/tests/e2e/test_hitl_evaluation_flow.py` (nuevo)
- Smoke manual:
  1. Login `solano@crece.mx` (VIEWER)
  2. GET `/hitl/sample?dirigente_id=2` → recibe 20 posts + 50 comments
  3. PATCH `/hitl/comments/{id}` con cambio
  4. POST `/hitl/comments/{id+1}/confirm`
  5. GET `/dashboard/aceptacion/2` → score reflejado
  6. Login `admin@crece.mx` → GET `/hitl/audit/2` → ve los 2 audit rows

Aceptación: E2E pasa + smoke ✓ + screenshot del flujo + grabación 30s para mostrar mañana.

### S10 · Documentación + handoff (30 min) · Linda

- Update `.context/STATUS.md` con sección "Editor HITL evaluación NLP operativo"
- Crear `docs/HITL-EVALUACION-NLP.md` (1 página) con diagrama del flujo + cómo usar el script batch + cómo Claude+Gemini procesan el reporte
- Update `.context/DECISIONS.md` con D-HITL-1: "Sistema propone, dirigente confirma/edita. Sin queue de approval. Audit log inmutable."
- Commit final con mensaje: `feat(hitl): editor evaluación NLP en /settings + recompute global + ground truth 100`

---

## Dependencias y secuencia

```
S1 (schema)
  └──> S2 (endpoints)
        ├──> S3 (recompute helper)
        ├──> S4 (front evaluador)
        └──> S5 (front dual labels)
                └──> S9 (E2E)
                      └──> S10 (docs)

S6 (batch script) ─── independiente, paralelo a S4/S5
S7 (recompute global) ─── independiente, paralelo a S2 (usa la misma S3)
S8 (ground truth 100) ─── independiente
```

Paralelización máxima:
- **Wave 1 (ahora):** S1 (backend-architect) + S6 (python-expert) + S8 (python-expert)
- **Wave 2 (post S1):** S2 + S3 (backend-architect + python-expert) + S7 (python-expert)
- **Wave 3 (post S2):** S4 + S5 (frontend-architect en paralelo)
- **Wave 4:** S9 (test-backend) + S10 (Linda)

## Asignación de agentes

| Sprint | Agente | Modo |
|---|---|---|
| S1 | backend-architect | direct |
| S2 | backend-architect | direct |
| S3 | python-expert | direct |
| S4 | frontend-architect | direct |
| S5 | frontend-architect | direct |
| S6 | python-expert | direct |
| S7 | python-expert | direct |
| S8 | python-expert | direct |
| S9 | test-backend + Linda | direct |
| S10 | Linda | direct |

Linda coordina, hace commits intermedios, valida E2E presencial.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Solano edita "demasiado optimista" su propio contenido | Audit log inmutable + batch review detecta sesgo · diff humano vs runner se reporta a CEO como métrica |
| Recompute lento si el sample es grande | Aprobación es row-by-row, recompute es 1 SQL UPDATE — sub-segundo |
| Conflictos con migration f7a8b9c0d1e2 (orphan) | S1 usa `IF NOT EXISTS`/`IF EXISTS` para schema · alembic chain ya consolidado D+0 |
| Mañana ve bugs en evaluación | S9 obligatorio antes de demo · grabación 30s sirve de respaldo |
| F-NLP-3 cambia números en dashboards en vivo durante reunión | Correr S7 ANTES de la reunión, no en vivo · disclaimer "scores recomputados con matriz reparada" |
| Ground truth 100 incompleto si la reunión apura | S8 produce CSV vacío con stratificación · si reunión llena 30, batch sirve · CEO puede completar D+1 |

## Criterio de éxito (mañana en reunión)

1. ✅ Solano/Piña/Ballesteros entran a `/dashboard/settings/evaluacion-nlp`
2. ✅ Cada uno ve sus últimos 50 comments + 20 posts con propuesta del sistema
3. ✅ Cada uno modifica/confirma al menos 30 rows
4. ✅ Dashboard refleja los nuevos scores en vivo
5. ✅ CEO ve el reporte `RECOMPUTE-GLOBAL-{date}.md` con tabla pre/post
6. ✅ Linda corre `hitl_review_batch.py` al final → MD presentable
7. ✅ Cierre con commitment: D+1 Linda alimenta MD a Claude+Gemini para iterar mapper

## Plan B si algo falla mañana

- Si S5 dual labels no está → demo sin badges, suficiente con S4
- Si S4 frontend tiene bugs → Linda anota en su lugar via SQL UPDATE en vivo
- Si S7 falla → mostrar reporte D+0 (`REPORTE-DELTA-SCORE-2026-05-09.md`) ya generado
- Si recompute global tarda > 5 min → preparar pre-recomputado el día anterior
- Si E2E S9 falla → screenshots y video preparados

## Decisiones cerradas (no preguntar)

1. ✅ Ubicación: `/dashboard/settings/evaluacion-nlp` (en línea con settings existentes)
2. ✅ Default: últimos 50 comments + 20 posts del dirigente del usuario (configurable)
3. ✅ Sin queue approve — edit aplica directo
4. ✅ Recompute por edit individual + global con S7
5. ✅ Audit log inmutable, alimenta batch script Claude+Gemini
6. ✅ RBAC: VIEWER solo su dirigente, ADMIN cualquiera
7. ✅ Roster MC = oposición = todos rol='oposicion' en matriz

---

**Tiempo total estimado con paralelización:** 9-10h calendario (S1+S2+S3+S4 son ruta crítica = ~6.25h; S5/S6/S7/S8 corren en paralelo).
