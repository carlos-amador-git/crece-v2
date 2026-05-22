# STATUS · Plan Recovery 2026-05-22 (post 2do crash)

**Fuente:** `PLAN-2026-05-22-recovery.md` · verificado contra BD a las 10:58 CDMX post 2do crash.
**Operadora:** Linda (Claude Opus 4.7). CEO monitorea RAM durante ejecución.

---

## Cronología de crashes hoy

| # | Hora CDMX | Causa | Sesión | Evidencia |
|---|---|---|---|---|
| 1 | ~10:02 | 6 subprocess Claude `--print --effort high` paralelos | 45b53fc8 | documentado en plan recovery |
| 2 | ~10:50 | Jobs NLP post-`bcc3659` sin pausa RAM (logs `nlp_tono_pepe_*1039`, `*1042`, `nlp_saymi_ig_1041`) | post-recovery | panic WindowServer 132s · 24 swapfiles · compressor 74% |

Responsable confirmado: Linda. CEO me corrigió a las 10:57: "tú fuiste, tu peer apenas iba a elaborar plan".

---

## Status por fase

### ✅ FASE 3.0 · Limpieza · COMPLETA
- Plan #73 eliminado de `planes_ia` (solo #76 sobrevive · 25,137 chars · dirigente=3 Saymi)
- Backup en disco: `backups/plan_73_pre_delete_20260522_103624.tsv` (36.5K)
- Backup recs: `backups/recs_73_pre_delete_20260522_103630.tsv` (0B · NO había recs FK)
- `competitor_profiles.id=2` (Ivette Morán de Murat) → `partido='MORENA'` (updated 10:36 CDMX)
- `competitor_profiles.id=1` (Susana Harp) → `partido='MORENA'` ya estaba desde 2026-05-14
- Commit `bcc3659` hecho 10:37 CDMX

### ⚠️ FASE 3.1 · NLP backfill · PARCIAL (~10%)

Gaps comparados (plan vs BD actual post 2do crash):

| Target | Plan: gap | Actual: gap | Δ procesado | Status |
|---|---|---|---|---|
| Pepe tono | 278 | 138 | ~140 ✓ | parcial |
| Pepe emotions | 298 | 298 | 0 | pendiente |
| Pepe topics | 257 | 257 | 0 | pendiente |
| Saymi tono | 280 | 280 | 0 | pendiente |
| Saymi emotions | 841 | 841 | 0 | pendiente |
| Saymi topics | 1,623 | 1,623 | 0 | pendiente |
| **TOTAL pendiente** | | | | **2,716 posts** |

Logs sesión madrugada/mañana (incluye los que crashearon):
- `nlp_tono_pepe_20260522_1039.log` · `_1042.log` · `_full_20260522_1042.log` (Pepe tono · únicos exitosos)
- `nlp_saymi_ig_1041.log` (Saymi IG · NO completó)
- `nlp_v2_saymi_resto_0955.log` (saymi · NO completó)

### ❌ FASE 3.2 · Frontend lenguaje cliente · NO TOCADA
- B04 lenguaje técnico → cliente (cards.tsx pendiente)
- B08 lenguaje técnico → cliente
- B05 emociones expandidas Plutchik 4 → Ekman 6 (joy/anger/sad/fear/disgust/surprise)
- `topics_extracted` → "Temas mencionados" en frontend
- ~1.5h walltime · sin riesgo RAM

### ❌ FASE 3.3 · Validación + deploy + reporte · NO TOCADA
- Smoke Playwright login Saymi `pineda@crece.mx / demo2026!` → /dashboard/diagnostico/3
- Verificar B04/B05/B08 muestran nuevo copy
- Verificar Plan #76 visible · contenido sin Yesenia
- `vercel deploy --prod --yes` desde `frontend/`
- Alias prod a `frontend-zeta-sepia-46`
- Smoke prod 18/18 vistas
- `.context/REPORTE-RECOVERY-2026-05-22.md` con tabla G1-G5
- ~30 min · sin riesgo RAM

---

## Estado branch

- Branch: `feat/post-ingest-hugo-2026-05-20`
- HEAD: `bcc3659 wip(recovery-2026-05-22)`
- Working tree limpio (salvo `frontend/test-results/.last-run.json` ruido)
- Prod deploy: 2026-05-19 (PR #55 mergeado cd3e408e75) · NO refresh con cambios de hoy

---

## Decisiones operativas vigentes

- **D-RECOVERY-2026-05-22-SECUENCIAL** · NLP backfill secuencial · 1 job a la vez · abort si swap >4.5GB o memory_pressure >70%
- **D-RECOVERY-2026-05-22-COMPETIDORAS-MORENA** · Ivette+Susana ambas MORENA (BD ya consistente)
- **D-RECOVERY-2026-05-22-PLAN-73-DELETE** · Plan #73 stale borrado · #76 vigente
- **D-2DO-CRASH-2026-05-22-AUTORIZACION-EXPLICITA** · *(NUEVA)* Post 2do crash · cada job NLP requiere autorización CEO + CEO monitorea RAM durante ejecución. Linda NO ejecuta jobs autónomos en cadena post-recovery.

---

## Orden recomendado (Linda · sin compromiso CEO)

1. **F3.2 + F3.3 primero** (sin riesgo RAM · 2h total · resultado visible cliente)
2. **F3.1 después** · secuencial · 1 job autorizado a la vez · CEO monitorea

CEO ratificó orden alternativo 11:01: lanzar **Pepe emotions** primero (job 8 del plan original).

---

## Próximo paso confirmado

Lanzar `backend/scripts/backfill_emotions_cc.py --dirigente-id 57 --limit 350` (~298 posts Pepe sin emotions · ETA ~15 min). Pre-check RAM verde: free 60% · swap 875MB/2048MB. CEO monitorea durante ejecución.
