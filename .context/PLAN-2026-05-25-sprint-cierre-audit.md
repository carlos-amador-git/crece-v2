# PLAN · Cierre tríada + audit-full + matriz polaridad · 2026-05-25 tarde

**Origen:** post-cierre PLAN-2026-05-25-sprint-multi (F1-F3+F5 verdes) · CEO pide terminar tríada audit-full + items menores del audit · verificar matriz polaridad.

**Branch:** `feat/post-ingest-hugo-2026-05-20` (55 commits ahead de main).

**Operador:** Linda (Claude Opus 4.7).

**Premisas CEO (vigentes):**
- Calidad > Tiempo
- Eficiencia y operación de la app > Tiempo
- Autonomía total, sin pedir confirmación por fase salvo gate fallido
- Política RAM dura: un subprocess Claude `--print` a la vez

**No-re-audit:** CEO dijo "Auditorías ya hicimos antes" · este plan cierra items abiertos del audit-full `.context/AUDIT-FULL-2026-05-19.md` · NO ejecuta nuevo audit.

---

## Estado verificado primary source (read-only)

### Matriz polaridad Saymi · estado real

Distribución `tono_discurso` sobre 2,173 posts clasificados Saymi:

| Vocab | Tono | Posts |
|---|---|---:|
| **v1 legacy** | neutral | 1,070 |
| v2 | celebratorio | 422 |
| v2 | personal | 274 |
| v2 | informativo | 237 |
| **v1 legacy** | positivo | 103 |
| v2 | propositivo | 52 |
| v2 | solidario | 15 |
| **TOTAL v1 legacy** | (52%) | **1,173** |
| **TOTAL v2** | (44%) | **1,000** |

NO es 100% legacy como decía el plan-20. Hay mezcla parcial. Decisión CEO: ¿homogenizar a v2? (~1h LLM secuencial sobre 1,173 posts vocab v1).

### Audit-full 2026-05-19 · 10 items abiertos

| # | Severity | Item | ETA | Bloqueo |
|---|---|---|---|---|
| 1 | 🔴 CRÍT | `.env.scraping-keys` tracked git | 1-2h | requiere CEO presente · alto blast |
| 2 | 🟡 ALTO | Prompt injection `dirigente_context_builder.py:334-379` | 1h | autopiloto OK |
| 3 | 🟡 ALTO | Rate limit ausente `/posts/unified` | 10 min | autopiloto OK |
| 4 | 🟡 ALTO | Sin filtros en `/hub` (regresión vs /social) | 45 min | autopiloto OK |
| 5 | 🟡 MED | UnifiedPostCard no apila vertical mobile | 20 min | autopiloto OK |
| 6 | 🟡 MED | Sin badge data_source visible | 30 min | autopiloto OK |
| 7 | 🟡 MED | Sin skeletons en Hub | 20 min | autopiloto OK |
| 8 | 🟡 MED | 0 tests `/posts/unified` BFF (370 LOC) | 2h | autopiloto OK |
| 9 | 🟢 BAJO | Sidebar contraste 2.01:1 WCAG fail | 30 min | autopiloto OK |
| 10 | 🟢 BAJO | Colisión label "Contenido" sidebar | 15 min | autopiloto OK |

ETA total autopiloto: ~6h · CEO-blocked: ~1-2h adicional.

---

## FASES

### F1 · Tríada + items HIGH backend (~2.5h · autopiloto · sin LLM masivo)

#### F1.1 · Rate limit `/posts/unified` (#3 · 10 min)
Archivo: `backend/app/api/v1/endpoints/posts_unified.py`
- Replicar patrón `slowapi` de otros endpoints (grep `@limiter.limit` ya en codebase)
- Decorador `@limiter.limit("60/minute")` (recomendación Gemini)
- Smoke: curl ráfaga, verificar 429 al sobrepasar

#### F1.2 · Prompt injection mitigation (#2 · 1h)
Archivo: `backend/app/services/dirigente_context_builder.py:334-379`
- Delimitar contexto LLM con `<context></context>` tags
- Patrones jailbreak comunes a sanitizar: "ignore previous", "system:", "</context>", backticks delimitadores, prompt inversion
- Helper `sanitize_for_llm(text)` reutilizable
- Tests: 3-5 casos de inyección conocidos retornan texto sanitizado

#### F1.3 · `.env.scraping-keys` interim mitigation (#1 part A · 30 min · autopiloto)
**NO rotación de keys ni filter-repo en este sprint** · esos requieren CEO presente.
Acción interim:
- `git rm --cached backend/.env.scraping-keys` (saca del index futuro)
- Confirmar `.gitignore` ya cubre el archivo (verificar línea 137)
- Commit: `chore(secrets): untrack .env.scraping-keys · historia previa diferida a sesión CEO`
- Crear task explícita pendiente: rotación + filter-repo en sesión propia
- Documentar en BLOCKERS.md

### Gate F1
- `posts_unified.py` con `@limiter.limit` aplicado · curl 429 al sobrepasar
- `dirigente_context_builder.py` con `<context>` wrap + sanitize_for_llm + 3 tests verdes
- `.env.scraping-keys` ya no aparece en `git status` y `git ls-files` no lo lista
- pytest backend suite no rompe

---

### F2 · UX + frontend cleanups (~2h · autopiloto · sin LLM)

#### F2.1 · Filtros `/hub` (#4 · 45 min)
Archivo: `frontend/src/app/dashboard/hub/page.tsx`
- Agregar selectors: platform (multi-checkbox), date_from/date_to (range), sentiment (radio: all/positive/neutral/negative)
- State via `searchParams` (mantiene deep-linking actual con `?tab=`)
- Hook `useUnifiedPosts` ya acepta filtros · solo conectar UI

#### F2.2 · Mobile vertical UnifiedPostCard (#5 · 20 min)
Archivo: `frontend/src/components/posts/unified-post-card.tsx`
- Cambiar grid `grid-cols-1 md:grid-cols-2 xl:grid-cols-3` para apilar en mobile
- Verificar avatar+text wrap sin overflow en viewport 360px

#### F2.3 · Skeletons en Hub (#7 · 20 min)
- `UnifiedPostCardSkeleton` ya existe · solo aplicarlo en ContenidoGrid mientras `isLoading`
- Reemplazar Spinner genérico actual

#### F2.4 · Badge data_source visible (#6 · 30 min)
- Agregar `<Badge>` inline en UnifiedPostCard con `post.data_source` (Apify/RADAR/Mixed)
- Color sutil (muted-foreground) para no competir con métricas

### Gate F2
- `/dashboard/hub` con filtros funcionales (smoke: cambiar platform reduce resultados)
- Vista mobile 360px: cards apiladas verticalmente sin overflow
- ContenidoGrid muestra skeletons mientras isLoading
- Cards muestran data_source visible
- `npx tsc --noEmit` verde · `check-no-mocks` verde

---

### F3 · Accessibility + tests + cleanup (~3h · autopiloto · puede correr en paralelo lógico con F2)

#### F3.1 · Tests `/posts/unified` BFF (#8 · 2h)
Archivo nuevo: `backend/tests/api/v1/test_posts_unified.py` (si existe extender)
- 4 vistas (feed/top/comentarios/fans) × auth (Saymi/Pepe/admin) × paginación (límite 10/50/100)
- Mínimo 10-12 tests · cubrir el 370 LOC del endpoint
- Verificar RBAC: usuario Saymi no ve posts Pepe

#### F3.2 · Accessibility fixes (#9 · 30 min)
- Sidebar contraste · cambiar `text-muted-foreground` → `text-foreground/70` o similar para llegar a 4.5:1
- Validar listitem inválido (encontrar HTML semántico roto)
- Link-name fantasmas: agregar `aria-label` a links sin texto

#### F3.3 · Colisión label "Contenido" (#10 · 15 min)
Sidebar tiene 2 ítems "Contenido": Content Factory + Hub.
- Renombrar `/dashboard/contenido` (Content Factory) a label "Generador de contenido" o similar
- Mantener `/dashboard/hub` como "Contenido" (workspace unificado)

### Gate F3
- 10+ tests `/posts/unified` verdes
- Sidebar contraste ≥ 4.5:1 (Chrome DevTools Lighthouse check manual)
- Sidebar sin colisión "Contenido" duplicada

---

### F4 · Matriz polaridad Saymi · decisión CEO (~1h LLM secuencial · OPCIONAL)

**CONDICIONAL:** si CEO decide homogenizar vocab v1 → v2.

Acción:
- Crear `backend/scripts/migrate_tono_v1_to_v2.py`
- Mapping LLM por post: input `(content, tono_v1)` → output `tono_v2` desde lista [celebratorio/informativo/propositivo/personal/solidario/critico/defensivo]
- 1,173 posts en batches de 10 · effort=medium · ETA ~1h
- UPDATE social_posts SET tono_discurso = nuevo · agregar `migration_origin='v1→v2-2026-05-25'` a `nlp_model_version`

**Si CEO dice no:** SKIP. La mezcla v1+v2 es aceptable porque frontend ya maneja ambos vocabularios (D-EKMAN-1 hizo defensivo el mapping).

### Gate F4
- 1,173 posts con `tono_discurso` en vocab v2 después del batch
- 0 fails en el batch
- Frontend B05/B10 muestra distribución uniforme sin "Sin clasificar" extras

---

### F5 · Commit incremental + push + deploy + reporte (~30 min)

#### F5.1 · Commits por fase
- `feat(api): rate-limit /posts/unified 60/min`
- `fix(security): sanitize prompt injection en dirigente_context_builder + tests`
- `chore(secrets): untrack .env.scraping-keys interim · rotación en sesión CEO`
- `feat(hub): filtros platform+date+sentiment + skeletons + badge data_source`
- `fix(ui): mobile vertical UnifiedPostCard + sidebar contrast + colisión label`
- `test(api): suite /posts/unified 12 cases · 4 vistas × auth × paginación`
- (si F4) `chore(nlp): migrate tono v1→v2 Saymi 1173 posts`

#### F5.2 · Push + Vercel deploy
```bash
git push origin feat/post-ingest-hugo-2026-05-20
docker restart crece-backend  # rate-limit + sanitize changes
cd frontend && vercel --prod --yes
vercel alias <deploy-url> frontend-zeta-sepia-46.vercel.app
```

#### F5.3 · Smoke prod
- Curl ráfaga `/api/posts/unified` retorna 429 al sobrepasar (rate limit verde)
- `/dashboard/hub` muestra filtros funcionales
- Mobile 360px: cards apiladas
- Sidebar 1 ítem "Contenido" (no 2)

### Gate F5
- Push exitoso · Vercel alias responde 200 (307 a /login esperado)
- Backend container responde 200 en `/api/health`

---

## Criterios G1-G10 sprint

| # | Criterio | Cómo se mide |
|---|---|---|
| G1 | Rate limit /posts/unified activo | curl ráfaga > 60/min retorna 429 |
| G2 | Prompt injection sanitized | tests pytest 3+ casos jailbreak retornan texto limpio |
| G3 | .env.scraping-keys untrackeado | `git ls-files | grep scraping-keys` retorna vacío |
| G4 | Filtros /hub funcionales | clic platform=Twitter reduce resultados |
| G5 | Mobile vertical | viewport 360px Chrome DevTools sin overflow horizontal |
| G6 | Skeletons + badge data_source | inspección visual primer render |
| G7 | Tests /posts/unified | 10+ tests pasan · cobertura >80% del BFF |
| G8 | Sidebar contraste AA | Lighthouse contrast check ≥ 4.5:1 |
| G9 | Sin colisión "Contenido" | sidebar muestra labels distintos |
| G10 | F4 si ejecuta · vocab uniforme v2 | psql distribución 0 posts "neutral"/"positivo" Saymi |

---

## Política RAM (vigente)

- F1+F2+F3 NO usan subprocess Claude · cero RAM risk
- F4 (si ejecuta) usa CC subprocess secuencial uno a la vez · verificar `memory_pressure` ≤70% pre-batch
- F5 deploy local · sin LLM

---

## Rollback por fase

| Fase | Rollback |
|---|---|
| F1 | `git revert` commits · SQL: no hay UPDATE BD en F1 (solo código) |
| F2 | `git revert` commits frontend |
| F3 | `git revert` commits tests + sidebar |
| F4 | per-batch `UPDATE social_posts SET tono_discurso = (nlp_model_version backup)` desde log batch |
| F5 | `vercel rollback` al deploy anterior · alias preservado |

---

## Pendientes diferidos explícitos (NO en este sprint)

- **F1.3 part B:** rotación 7 keys + `git filter-repo` + force-push · sesión propia con CEO (alto blast)
- **PII compliance review** (gap audit Gemini high) · sprint propio post-cliente
- **Performance N+1 stress test BFF** · sprint propio
- **Error Boundaries frontend específicos** · medium gap audit · sprint propio
- **55+ commits sin merge a `main`** · decisión operativa CEO
- **Backlog "Contenido con más impacto" REAL** (endpoint dedicado ORDER BY engagement_rate)
- **B-COMPETIDORES-MODELO-1** modelo huérfano · diferido del 14-may
- **Mobile audit completo** (más allá de #5 de este sprint) · sprint propio

---

## Decisiones registradas

- **D-AUDIT-CLOSURE-2026-05-25** · cerrar 9 de 10 items audit-full en este sprint · item #1 parte B (rotación + filter-repo) diferido sesión CEO
- **D-MATRIZ-POLARIDAD-MIXTA-2026-05-25** · estado mixto v1+v2 verificado primary source (1173/1000 split) · NO 100% legacy como decía plan-20. F4 condicional decisión CEO.
- **D-SECRETS-INTERIM-2026-05-25** · `git rm --cached` como mitigación interim · rotación real en sesión propia con presencia CEO porque requiere actualizar Coolify+Vercel+local+coordinar Hugo

---

## ETA total

| Fase | ETA |
|---|---|
| F1 tríada backend | 2.5h |
| F2 frontend UX | 2h |
| F3 a11y + tests + sidebar | 3h |
| F4 matriz polaridad (condicional) | 1h |
| F5 deploy + smoke | 30 min |
| **TOTAL autopiloto sin F4** | **~8h** |
| **TOTAL con F4** | **~9h** |

Es sprint largo. Si tiempo es restricción, priorizar F1+F2+F5 (~5h) y F3+F4 a sesión siguiente.

---

## Cómo lanzar

```
/sprint-implement
```

Linda ejecuta autónoma con gates de verificación. Plan extenso · pausar si gate falla.
