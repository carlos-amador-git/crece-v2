# Reporte · Recovery post-crash Mac Mini · 2026-05-22 → cierre 2026-05-25

**Origen:** crash Mac Mini 2026-05-22 ~16:02 UTC (sesión `45b53fc8`) por 6 subprocess Claude `--print --effort high` paralelos. Plan original perdido en penúltima.
**Plan:** `.context/PLAN-2026-05-22-recovery.md` (F3.0 → F3.3)
**Operador cierre:** Linda (Claude Opus 4.7) · branch `feat/post-ingest-hugo-2026-05-20`

---

## Hallazgo principal del cierre

Entre 2026-05-22 (crash) y 2026-05-25 (cierre), sesiones intermedias del proyecto avanzaron de facto la mayoría de los pendientes del plan-22, sin actualizarlo. El plan estaba **3 días desactualizado**. Al re-verificar contra BD y código actual:

- F3.0 (limpieza BD): ya hecha
- F3.1 (NLP backfill): casi toda hecha · solo Saymi YT+TT topics pendiente (670 posts con content >10c)
- F3.2 (frontend lenguaje cliente): ya hecha por completo
- F3.3 (validación + deploy): pendiente al inicio del cierre

---

## Tabla G1-G5

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| G1 | Plan #73 stale eliminado · #76 vigente | ✅ | `SELECT id FROM planes_ia WHERE id IN (73,76)` devuelve solo 76 · `contenido ILIKE '%yesenia%'` = false |
| G2 | Ivette MORENA en BD | ✅ | `competitor_profiles.id=2.partido='MORENA'` |
| G3 | NLP gap < 10% por (dirigente, plataforma, columna) con content válido | ✅ | Pepe 100% IG+FB · Saymi 100% todas plataformas · 670/670 topics OK · 0 fails |
| G4 | B04/B05/B08 lenguaje cliente · B05 6 emociones | ✅ | Cards ya cliente-ready en commits previos · B05 Ekman 6 implementado (D-EKMAN-1 2026-05-12) |
| G5 | Cero crashes RAM durante F3.1 | ✅ | Batch único secuencial · `batch=10 posts` · effort=medium · subprocess Claude uno a la vez · 0 fails |

Pre-batch: TT topics 39.6% · YT topics 70%. Post-batch: TT 100% · YT 100% sobre posts con content válido.

---

## F3.0 · Limpieza BD · **ya hecha pre-cierre**

| Acción plan-22 | Estado al cierre | Verificación |
|---|---|---|
| DELETE plan #73 stale | ✅ ya borrado | `SELECT id FROM planes_ia WHERE id=73` → 0 rows |
| UPDATE Ivette partido='MORENA' | ✅ ya aplicado | `competitor_profiles.id=2.partido = 'MORENA'` |
| Commit WIP penúltima | ✅ absorbido en `975d09c` (commit del agente anterior 2026-05-25) | 8 archivos M + 1 ?? del git status inicial del 22 ya no aparecen |

---

## F3.1 · NLP backfill · ejecutado un único batch

### Estado pre-cierre (verificado por SQL con filtro `content > 10 chars`)

| Dirigente | Plataforma | Sin topics | Sin emotions |
|---|---|---:|---:|
| Pepe (57) | IG / FB | 0 / 0 | 0 / 0 |
| Saymi (3) | TW / IG / FB | 0 / 0 / 0 | 0 / 0 / 0 |
| Saymi (3) | YT | 30 | 0 |
| Saymi (3) | TT | 640 | 0 |

**Conclusión:** del plan-22 (que listaba ~3,000 gaps) sólo quedaban 670 con content real. El resto eran posts sin texto (reposts, solo media), que por diseño del script no se procesan.

### Batch ejecutado

```bash
backend/.venv/bin/python backend/scripts/extract_topics_saymi_cc.py \
  --dirigente-id 3 --limit 700
```

- Modelo: `cc-topics-v1-2026-05-21` (CC effort=medium)
- Política RAM: subprocess Claude `--print` uno a la vez · batch_size=10 · no paralelo
- ETA esperado: ~25 min
- Log: `backend/.context/topic_extract_20260525_1141.log`

### Resultado · ejecutado 2026-05-25 11:41 → 12:11 CDMX

- **Posts procesados:** 670 / 670 · 67 batches × 10 posts
- **Failures:** 0 · 100% éxito
- **Walltime:** 1801.4s (30 min) · rate sostenido 0.37 posts/s
- **Política RAM:** verificada · 0 abortos · 0 crashes

Cobertura post-batch Saymi sobre posts con content > 10 chars:

| Plataforma | Total | Con topics | Coverage |
|---|---:|---:|---:|
| TWITTER | 181 | 181 | 100% |
| INSTAGRAM | 130 | 130 | 100% |
| FACEBOOK | 573 | 573 | 100% |
| TIKTOK | 1189 | 1189 | 100% |
| YOUTUBE | 100 | 100 | 100% |

Posts sin content válido (reposts solo media, fragmentos) quedan `topics_extracted=NULL` por diseño del script (filtro `LENGTH(TRIM(content)) > 10`). No representan gap NLP, son posts sin texto para analizar.

---

## F3.2 · Frontend lenguaje cliente · **ya hecha pre-cierre**

| Sub-tarea plan-22 | Hallazgo | Acción cierre |
|---|---|---|
| F3.2-A · B04 lenguaje | Cards ya cliente-ready · cero términos técnicos visibles | sin cambios |
| F3.2-B · B08 lenguaje | Cards ya cliente-ready · "Tu peso en la conversación" · "qué % de la conversación es sobre ti" | sin cambios |
| F3.2-C · B05 6 emociones | `PLUTCHIK_ORDER=[joy,anger,sadness,fear,disgust,surprise]` ya implementado D-EKMAN-1 2026-05-12 · labels español ya presentes | sin cambios |
| F3.2-D · topics_extracted user-friendly | `card-shell.tsx:59` ya pretty-mapea raw → "Análisis de temas aún no calculado para este dirigente" · cero raw strings visibles | sin cambios |

Verificación calidad:
- `npx tsc --noEmit` → No errors found
- `bash scripts/check-no-mocks.sh` → Sin patrones de hardcoded fallback detectados

---

## F3.3 · Validación + deploy · ya iniciada pre-cierre

| Acción | Estado |
|---|---|
| `vercel deploy --prod --yes` | ✅ ejecutado 2026-05-25 11:30 CDMX · `frontend-40trzlntx-marxs-projects-bb530f2b.vercel.app` |
| Alias `frontend-zeta-sepia-46` | ✅ aliased al deploy |
| CEO validó local | ✅ Pedro Carlock #2 con 312 likes FB visible |
| Smoke Playwright vs prod post-batch | TODO post-batch |

---

## Decisiones registradas

- **D-RECOVERY-2026-05-22-SECUENCIAL** (heredada): NLP backfill secuencial · subprocess Claude `--print` uno a la vez. Confirmada en el batch del cierre.
- **D-RECOVERY-2026-05-22-COMPETIDORAS-MORENA** (heredada): Ivette y Susana ambas MORENA en `competitor_profiles`.
- **D-RECOVERY-2026-05-22-PLAN-73-DELETE** (heredada): Plan #73 borrado · #76 vigente.
- **D-RECOVERY-CIERRE-2026-05-25-PLAN-DESACTUALIZADO**: planes post-incidente caducan rápido. Lección: antes de re-ejecutar un plan de recovery >3 días viejo, verificar estado real contra BD y código primero · evita re-trabajo del 90%.

---

## Pendientes diferidos (no en este sprint)

- Backfill matriz polaridad v2 sobre Saymi 595 posts legacy (sigue diferido del sprint 20-may · `tono_discurso` Saymi usa vocab v1 no v2)
- Sprint mobile audit completo (B-MOBILE diferido)
- Tríada crítica pre-cliente del audit-full 2026-05-19 (NO se cerró en este sprint):
  - `.env.scraping-keys` tracked en git (rotar + purgar historia)
  - Rate limit ausente `/posts/unified`
  - Sin filtros en `/hub` (regresión vs /social viejo)
- 51 commits acumulados en `feat/post-ingest-hugo-2026-05-20` sin merge a `main` · 5ta sesión consecutiva deployando vía `vercel --prod` directo

---

## Métricas del sprint

- **Tiempo total cierre:** ~1.5h (verificación + batch único + reporte)
- **Tiempo evitado por verificar primero:** ~3-4h (no se re-ejecutaron acciones ya hechas)
- **Crashes RAM:** 0
- **Tests rotos:** 0
- **Deploy prod:** 1 · alias preservado
