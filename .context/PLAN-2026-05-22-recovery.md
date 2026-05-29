# PLAN · Recovery post-crash Mac Mini · 2026-05-22

**Origen:** crash Mac Mini ~16:02 UTC (10:02 CDMX) lanzando 6 subprocess Claude `--print --effort high` en paralelo (sesión previa `45b53fc8`). Plan original perdido en penúltima `e246bad9` (Diagnóstico+FODA+correcciones NLP+competencia Saymi sin Yesenia).

**Branch:** `feat/post-ingest-hugo-2026-05-20` (continúa · uncommitted son evidencia de la penúltima).

**Operador:** Linda (Claude Opus 4.7).

**Premisas CEO (textual 2026-05-22):**
- Calidad > Tiempo
- Eficiencia y operación de la app > Tiempo
- Autonomía total, sin pedir confirmación por fase salvo gate fallido

**Política RAM dura (regla nueva post-crash):**
- **Un subprocess Claude `--print` a la vez.** Nunca paralelo.
- Antes de lanzar cada job: `memory_pressure` debe ser verde (presión <60%).
- Cada batch de NLP en commits separados (checkpoint cada ≤200 posts procesados).
- Si swap > 4GB sostenido durante un job → ABORTAR job + reportar.

---

## Estado verificado (Fase 1+2 ya ejecutadas · read-only)

### Mac Mini · RAM
- vm_stat free 26 MB · swap 4.3/5 GB · memory_pressure: 50% (verde · normal en macOS)
- Cero procesos zombie de penúltima (PIDs 60404/60405/56278/57937 limpios post-restart)

### Docker · containers (uptime 14 min post-restart)
- `crece-backend` `crece-db` `crece-redis` `crece-minio` `crece-celery-beat` (healthy)
- `crece-celery-worker` `crece-flower` `crece-frontend` (up)
- `radar-scraper_*` también UP (Hugo · sesión paralela peer s2ryygne)

### BD · inventario tareas plan original

| # | CEO pidió (textual penúltima) | BD actual | Acción |
|---|---|---|---|
| 1 | Sidebar Diagnóstico → {Recepción, Diferenciadores, FODA} | ✅ Commit `0be5bf9` HEAD | Hecho |
| 2 | Plan Saymi sin Yesenia | ✅ Plan #76 25K chars · NO menciona Yesenia/Nolasco | Hecho |
| 3 | Borrar plan #73 stale (28K chars · ILIKE '%yesenia%' = true · ILIKE '%nolasco%' = true) | ❌ Existe | F3.0 |
| 4 | Ivette + Susana competidoras Saymi en MORENA | ⚠️ Susana OK · **Ivette quedó "Independiente"** en `competitor_profiles.id=2` | F3.0 |
| 5 | Pepe sin competidores | ✅ `competidor_directo_ids={}` | Hecho |
| 6 | Reacciones Ivette donde están | ✅ Encontradas: `dirigente_id=58` · 44 posts FB · 24,232 likes · 2,987 comments · `social_posts` (NO competitor_posts) | UI ya consume vía dirigentes |
| 7 | NLP Pepe 88 restantes | ❌ Real: 278 sin tono · 298 sin emotions · 257 sin topics | F3.1 |
| 8 | NLP Saymi resto redes | ❌ 280 sin tono · 841 sin emotions · 1,623 sin topics | F3.1 |
| 9 | B04 + B08 lenguaje técnico → cliente | ❌ Cards Tier 2 sin tocar | F3.2 |
| 10 | B05 sentimiento más allá Alegría/Enojo | ❌ Frontend usa solo 2 emociones del JSONB `emotions` | F3.2 |
| 11 | `topics_extracted` renombrar user-friendly | ❌ Pendiente label | F3.2 |

### Gaps NLP detallados

```
PEPE (57):
  IG    65 total ·  15 tono · 65 emotions · 65 topics                → 50 sin tono
  FB   388 total · 160 tono · 90 emotions · 131 topics               → 228 sin tono · 298 sin emotions · 257 sin topics
PEPE TOTAL: 278 sin tono · 298 sin emotions · 257 sin topics

SAYMI (3):
  TW   181 total · 137 tono · 162 emotions ·  32 topics              →  44 sin tono · 149 sin topics
  IG   130 total ·  80 tono ·  53 emotions ·  80 topics              →  50 sin tono · 77 sin emotions
  FB   573 total · 532 tono ·   4 emotions · 401 topics              →  41 sin tono · 569 sin emotions ⚠️
  TT  1189 total ·1114 tono ·1081 emotions ·  37 topics              →  75 sin tono · 1,152 sin topics ⚠️
  YT   100 total ·  30 tono ·  32 emotions ·   0 topics              →  70 sin tono · 100 sin topics
SAYMI TOTAL: 280 sin tono · 841 sin emotions · 1,623 sin topics
```

### Uncommitted en branch (evidencia penúltima)
- `M backend/scripts/ingest_competencia_saymi.py` (8 líneas)
- `M backend/scripts/regen_diagnostico_v2.py` (15 líneas)
- `?? backend/scripts/backfill_emotions_cc.py` (script nuevo HOY · ya usado en penúltima)
- `?? backups/` `?? e2e/` `?? .context/exports/`
- `?? frontend/e2e/validate-aceptacion-dedupe.spec.ts`
- `?? frontend/e2e/validate-fans-perfiles-isolated.spec.ts`
- `M .context/HANDOVER-AI.md` (limpieza -119 líneas)
- `D test-results/.../error-context.md` × 4 (artefactos viejos)

---

## FASE 3.0 · Limpieza segura (~10 min · sin riesgo crash)

**Objetivo:** dejar BD consistente con lo que CEO pidió en la penúltima + commit los WIP.

### Acciones

1. **Verificar plan #73 contenido** (NO borrar todavía si no es el broken esperado)
   ```sql
   SELECT id, dirigente_id, created_at, LENGTH(contenido), modelo_ia,
     SUBSTRING(contenido, 1, 200) AS preview
   FROM planes_ia WHERE id = 73;
   ```

2. **Backup plan #73 a disco** antes de borrar
   ```bash
   docker exec crece-db psql -U crece -d crece -c \
     "COPY (SELECT * FROM planes_ia WHERE id=73) TO STDOUT" \
     > backups/plan_73_pre_delete_$(date +%Y%m%d_%H%M%S).tsv
   ```

3. **DELETE plan #73 + recomendaciones asociadas**
   ```sql
   DELETE FROM recomendaciones_plan_ia WHERE plan_id = 73;
   DELETE FROM planes_ia WHERE id = 73;
   ```

4. **UPDATE Ivette partido MORENA** (en `competitor_profiles` Saymi target)
   ```sql
   UPDATE competitor_profiles
   SET partido = 'MORENA', updated_at = NOW()
   WHERE id = 2  -- Ivette Morán de Murat, dirigente_objetivo_id=3
   RETURNING id, display_name, partido;
   ```

5. **Commit uncommitted con mensaje WIP**
   - Excluir `backups/` del commit (gitignore o staging selectivo)
   - Mensaje: `wip(recovery-2026-05-22): scripts NLP penúltima + limpieza HANDOVER + e2e specs`

### Gate Fase 3.0
- Plan #73 ya no aparece en `planes_ia`
- `recomendaciones_plan_ia` no tiene FK huérfana plan_id=73
- Ivette `partido='MORENA'` en BD
- `git status` limpio (excepto backups/)
- Tests frontend `npm run check:no-mocks` verde
- Tests backend `pytest` smoke verde

Si gate falla → reportar + parar.

---

## FASE 3.1 · NLP Backfill secuencial (~4-6h walltime · político ejecutar fuera de sesión interactiva)

**Política dura:** un subprocess Claude `--print` a la vez. Verificar `memory_pressure` antes de cada job. Si swap >4GB sostenido → abortar.

### Orden de ejecución (de menor a mayor riesgo de saturar RAM)

| # | Target | Script | Args | ETA | Checkpoint |
|---|---|---|---|---|---|
| 1 | Tono Pepe IG (50 posts) | `backfill_nlp_posts.py` | `--dirigente-id 57 --platform INSTAGRAM --limit 100` | ~5 min | commit |
| 2 | Tono Pepe FB (228 posts) | `backfill_nlp_posts.py` | `--dirigente-id 57 --platform FACEBOOK --limit 300` | ~20 min | commit |
| 3 | Tono Saymi YT (70 posts) | `backfill_nlp_posts.py` | `--dirigente-id 3 --platform YOUTUBE --limit 100` | ~7 min | commit |
| 4 | Tono Saymi TT (75 posts) | `backfill_nlp_posts.py` | `--dirigente-id 3 --platform TIKTOK --limit 100` | ~7 min | commit |
| 5 | Tono Saymi TW (44 posts) | `backfill_nlp_posts.py` | `--dirigente-id 3 --platform TWITTER --limit 100` | ~5 min | commit |
| 6 | Tono Saymi IG (50 posts) | `backfill_nlp_posts.py` | `--dirigente-id 3 --platform INSTAGRAM --limit 100` | ~5 min | commit |
| 7 | Tono Saymi FB (41 posts) | `backfill_nlp_posts.py` | `--dirigente-id 3 --platform FACEBOOK --limit 100` | ~5 min | commit |
| 8 | Emotions Pepe (298 posts) | `backfill_emotions_cc.py` | `--dirigente-id 57 --limit 350` | ~15 min | commit |
| 9 | Emotions Saymi FB (569 posts) | `backfill_emotions_cc.py` | `--dirigente-id 3 --platform FACEBOOK --limit 600` | ~25 min | commit |
| 10 | Emotions Saymi IG (77 posts) | `backfill_emotions_cc.py` | `--dirigente-id 3 --platform INSTAGRAM --limit 100` | ~5 min | commit |
| 11 | Topics Saymi TT (1,152) | `extract_topics_saymi_cc.py` | `--dirigente-id 3 --platform TIKTOK --limit 1200` | ~45 min | commit |
| 12 | Topics Saymi YT (100) | `extract_topics_saymi_cc.py` | `--dirigente-id 3 --platform YOUTUBE --limit 150` | ~7 min | commit |
| 13 | Topics Pepe FB (257) | `extract_topics_saymi_cc.py` | `--dirigente-id 57 --platform FACEBOOK --limit 300` | ~15 min | commit |
| 14 | Topics Saymi TW (149) | `extract_topics_saymi_cc.py` | `--dirigente-id 3 --platform TWITTER --limit 200` | ~10 min | commit |

**Total ETA secuencial:** ~3h walltime puro · ≥4h con checkpoints + verificación.

### Wrapper bash de ejecución con guardarrail RAM

`backend/scripts/run_nlp_sequential.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
JOB_NAME="$1"
SCRIPT="$2"
shift 2

# Pre-check RAM
PRESSURE=$(memory_pressure 2>&1 | awk '/System-wide memory/ {print $4}' | tr -d '%')
SWAP_USED_MB=$(sysctl vm.swapusage | awk '{print $7}' | tr -d 'M')

if (( ${PRESSURE%.*} > 70 )); then
  echo "ABORT: memory_pressure ${PRESSURE}% > 70%"
  exit 2
fi
if (( ${SWAP_USED_MB%.*} > 4500 )); then
  echo "ABORT: swap ${SWAP_USED_MB}MB > 4500MB"
  exit 2
fi

# Run job in foreground (NOT nohup background — un job a la vez)
echo "===== ${JOB_NAME} START $(date) ====="
.venv/bin/python "${SCRIPT}" "$@"
echo "===== ${JOB_NAME} END $(date) ====="
```

### Política checkpoint post-batch
1. Verificar conteo BD post-batch coincide con limit declarado
2. `git add backend/.context/*.log && git commit -m "checkpoint(nlp): ${job_name} batch complete"`
3. RAM check: si swap >4.3GB → pausar 60s antes de siguiente

### Gate Fase 3.1
- Todos los gaps `IS NOT NULL` >= 90% por (dirigente, plataforma, columna)
- 0 jobs abortados por RAM
- Logs `backend/.context/nlp_*.log` indican `0 fails` por job

---

## FASE 3.2 · Frontend lenguaje cliente (~1.5h)

**Objetivo:** correcciones CEO 13:23 (B04/B08 técnico) + 13:34 (B05 sentimiento más allá Alegría/Enojo) + topics_extracted label.

### Sub-tareas

#### F3.2-A · B04 lenguaje técnico → cliente
- Archivo: `frontend/src/components/diagnostico_tier2/cards.tsx` (B04 detail)
- Cambios: revisar términos como "topics_extracted", "engagement_rate", "estrato_micro", reemplazar con copy entendible por administrador político no-técnico.
- Validar con screenshot Playwright pre/post.

#### F3.2-B · B08 lenguaje
- Mismo archivo, sección B08.
- Términos "share of voice", "menciones contextualizadas" → "qué porcentaje de la conversación es sobre ti".

#### F3.2-C · B05 emociones expandidas
- Archivo: `frontend/src/components/diagnostico_tier2/cards.tsx` (B05)
- Estado actual: solo Alegría/Anticipación/Tristeza/Miedo (Plutchik subset).
- Cambio: usar `emotions` JSONB Ekman 6 (joy, anger, sadness, fear, disgust, surprise + others) que `backfill_emotions_cc.py` ya populó en BD.
- Componente: agregar `disgust` (asco) + `surprise` (sorpresa) al gauge/radar chart.
- Hook: `useDiagnosticoTier2()` o equivalente debe traer `emotions` del backend response.

#### F3.2-D · topics_extracted user-friendly
- Frontend label "topics_extracted" → "Temas mencionados"
- Grep todas las ocurrencias: `frontend/src/**/*.tsx` + `frontend/src/lib/**/*.ts`

### Gate Fase 3.2
- `npx tsc --noEmit` verde
- `npm run check:no-mocks` verde
- Playwright screenshot B04/B05/B08 muestra copy nuevo
- Cero strings "topics_extracted" visible al usuario

---

## FASE 3.3 · Validación + deploy + reporte (~30 min)

### Acciones
1. Smoke Playwright login Saymi (`pineda@crece.mx` / `demo2026!`) → /dashboard/diagnostico/3
2. Verificar B04/B05/B08 muestran nuevo copy
3. Verificar B05 muestra 6 emociones (disgust/surprise visibles)
4. Verificar Plan #76 visible en /dashboard/planes/3 · contenido sin Yesenia
5. Verificar Ivette en `/dashboard/aceptacion/3` (comparativa competidoras) muestra partido MORENA
6. `vercel deploy --prod --yes` desde `frontend/`
7. Alias prod a `frontend-zeta-sepia-46`
8. Smoke prod 18/18 vistas (mismo barrido que `PLAN-2026-05-19-deuda-tests` Bloque A)
9. Reporte final en `.context/REPORTE-RECOVERY-2026-05-22.md` con tabla G1-G5

### Criterios G1-G5 sprint
| # | Criterio | Cómo se mide |
|---|---|---|
| G1 | Plan #73 stale eliminado · #76 vigente · BD consistente | psql query devuelve solo #76 |
| G2 | Ivette MORENA en BD | psql + UI muestra MORENA |
| G3 | NLP gap por (dirigente, plataforma, columna) <10% | conteo SQL contra total |
| G4 | B04/B05/B08 lenguaje cliente · B05 6 emociones | screenshot Playwright |
| G5 | Cero crashes RAM durante todo F3.1 | logs sin "ABORT" |

---

## Rollback por fase

| Fase | Rollback |
|---|---|
| F3.0 | Restore plan #73 desde `backups/plan_73_pre_delete_*.tsv` · UPDATE Ivette partido='Independiente' |
| F3.1 | Per-batch: SQL `UPDATE social_posts SET tono_discurso=NULL WHERE id IN (...)` con IDs del log del job |
| F3.2 | `git revert` commits frontend |
| F3.3 | `vercel rollback` al deploy previo (alias `frontend-zeta-sepia-46` apunta al anterior) |

---

## Decisiones registradas

- **D-RECOVERY-2026-05-22-SECUENCIAL** · NLP backfill ejecuta secuencial, nunca paralelo. Política RAM activa: abort si swap > 4.5GB o memory_pressure > 70%.
- **D-RECOVERY-2026-05-22-COMPETIDORAS-MORENA** · Ivette y Susana ambas MORENA en `competitor_profiles` (Susana ya estaba, Ivette pendiente UPDATE). Coincide con CEO 14:04 penúltima.
- **D-RECOVERY-2026-05-22-PLAN-73-DELETE** · Plan #73 stale (menciona Yesenia + Nolasco) se borra. Plan #76 (sin Yesenia) es el vigente.

---

## Pendientes diferidos (no en este sprint)

- Bot detection en competidoras (`B-FOLLOWERS-BOT-1` ya cerrado para YT, podría extenderse)
- Re-evaluar tabla `competidores` vs `competitor_profiles` (B-COMPETIDORES-MODELO-1 sigue diferido)
- Backfill matriz polaridad v2 sobre Saymi 595 posts legacy (sigue diferido del sprint 20-may)
- Sprint mobile audit completo (B-MOBILE diferido)
