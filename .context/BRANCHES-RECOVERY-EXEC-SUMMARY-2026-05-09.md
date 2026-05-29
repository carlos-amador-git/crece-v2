# Resumen ejecutivo · Branches Recovery · 2026-05-09

**Para:** CEO MD Consultoría TI · **De:** Linda · **Asunto:** Consolidar 18 branches not-merged

---

## TL;DR
- 18 branches not-merged · 5 alembic-críticas · 6 conflict HIGH/MEDIUM · 2 con secret hardcoded git
- Crítico: árbol `backend/eval/layer2_benchmark/` (~33 archivos, evidencia §5) solo en eval-v1/backup/scrapling-v2
- Riesgo: CI nunca corrió en 17/18; 11 env vars sin documentar
- Total: ~14-18h (T1 2h · T2 3h · T3 6-8h · T4 2h · pre-flight 2h)
- Bloqueante CEO: (a) rotar `SCRAPECREATORS_API_KEY`, (b) cherry-pick `0681153`, (c) archive sin merge `crece-v2-full`

---

## Fase 1 — inventario por rama

| Rama | Estado | Acción | Razón |
|---|---|---|---|
| feat/phase-b-pesos-editables | ACTIVO HEAD | Merge PR #48 final | 42 commits, piloto vivo, alembic lineal |
| feat/eval-benchmark-v1 | MIXTO | Cherry-pick `layer2_benchmark` + archive | PR #15, benchmark 74.1% |
| backup/pre-opcion-d-eval-v1 | SUPERADO | Archive | Gemelo eval-v1 |
| feat/scrapling-v2 (LOCAL) | SUPERADO | Push + archive | Subset eval-v1 12/15 |
| feat/crece-v2-full-implementation | SUPERADO | Archive sin merge | Scaffold abr-03, 25 migs faltan |
| feat/agentation-widget | MIXTO | Cherry-pick provider.tsx | PR #35 MCP fix Joy |
| hotfix/pre-piloto-v2 | MIXTO | Verificar superseded | Probable redundante phase-b |
| fix/remove-lenis-v2 | LOW | Merge solo este | Final trio Lenis |
| fix/remove-lenis-smooth-scroll, revert/lenis-removal | LOW | Archive | Duplicado / anti-fix |
| feat/joy-scraper-demoscopia | SUPERADO | Archive | Absorbido `dccd7aa` |
| feat/brightdata-{browser,yt}-joy (LOCAL) | SUPERADO | Push + archive | Stack descontinuado |
| feat/scraperapi-tiktok-joy (LOCAL) | SUPERADO | Archive | Restaurado `0611313` |
| docs/joy-gap, joy-seed, prompt-plan-v1.1, close-session, cherry-pick-gate, post-mortem-3d6fe3f | LOW | PR consolidado docs | Mayoría DECISIONS/STATUS |
| docs/decisions-append-2026-04-21 | MEDIUM | PR consolidado docs | DECISIONS+PILOTO conflict |
| fix/eval-v1-cherry-pick-preconditions | LOW | Merge directo | Docs cherry-pick fallido |

---

## Fase 1.B — riesgos técnicos

### Tabla riesgo

| Rama | Alembic | Conflict | Env | API | Total |
|---|---|---|---|---|---|
| backup/pre-opcion-d-eval-v1 | split | ~10 | secret | 7 | HIGH |
| feat/eval-benchmark-v1 | split + ds03/3d6fe3f | ~10 | secret | 7 | HIGH |
| feat/crece-v2-full | split (5 vs 30) | 7 add/add | - | - | HIGH |
| feat/phase-b (HEAD) | lineal | - | 6 | 14 | MEDIUM |
| feat/agentation-widget | OK | 4 | 1 | - | MEDIUM |
| hotfix/pre-piloto-v2 | OK | 2 | - | - | MEDIUM |
| docs/decisions-append | OK | 2 docs | - | - | MEDIUM |
| 10 ramas restantes | mixto | clean | - | - | LOW |

**Conteos:** HIGH=3 · MEDIUM=5 · LOW=10 · CI: 17/18 nunca corrió.

### Top 5 hallazgos críticos
1. Secret literal `pgmI0aOa8bSj9dUoh1Ja0OLwXTC2` (`SCRAPECREATORS_API_KEY`) en eval-v1+backup → rotar antes de tocar.
2. Alembic split-head en eval-v1/backup/crece-v2-full: faltan `s1m1/s3m1/s5m1/d23g1` → merge ciego rompe upgrade head.
3. `backend/eval/layer2_benchmark/` ausente de phase-b/main → cherry-pick `0681153` (74.1% / Claude 95.5% / Gemma 79.5%).
4. CI ciego: `e2e-smoke.yml` 2 runs failure → activar push+PR auto antes T3.
5. 11 env vars sin documentar: OLLAMA_*×5, CHROME_BIN, INSTAGRAM_*, SCRAPECREATORS, ANTHROPIC, CLAUDE_MODEL, LIMIT, NEXT_PUBLIC_AGENTATION.

### Blob conflicts (alembic)
- `ds03_social_comments_data_source.py`: main `06d21ab` vs phase-b `357eb13` (PEP 604) → aceptar phase-b.
- `3d6fe3f1660d_add_resultados_electorales`: main `d12bb672` vs phase-b `84cdb2e7` → diff no inspeccionado → revisar pre-merge.

### Pre-requisitos T3 (no negociables)
- (a) Rotar `SCRAPECREATORS_API_KEY` (vault + Coolify) pre eval-v1
- (b) Activar CI `e2e-smoke.yml` push+PR a main
- (c) Documentar 11 env vars en `*.env.example`
- (d) Diff manual blob `3d6fe3f1660d`

---

## Recomendaciones consolidadas

### Orden T1→T4
- **T1 LOW (~2h):** 6 docs/* + joy-scraper-demoscopia + fix/eval-v1-precond + fix/remove-lenis-v2
- **T2 MEDIUM (~3h):** agentation (PR #35), decisions-append, hotfix/pre-piloto-v2
- **T3 HIGH (~6-8h):** cherry-pick `0681153` + secret rotation, archive backup, archive crece-v2-full
- **T4 ARCHIVE (~2h):** scrapling-v2 + 3 LOCAL (push+tag), tags `archive/*` residuales
- **Final:** merge phase-b a main PR #48

### Pendientes CEO (binarias)
- [ ] Aprobar orden T1→T4 con phase-b al final
- [ ] Rotar `SCRAPECREATORS_API_KEY` en Coolify+Vercel pre eval-v1
- [ ] Resolución blob `ds03`: phase-b gana (PEP 604)
- [ ] Archive sin merge `feat/crece-v2-full-implementation`
- [ ] Cherry-pick selectivo `0681153` vs merge completo eval-v1
- [ ] PR único consolidado para 4 docs/*
