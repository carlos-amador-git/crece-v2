# HANDOFF · CRECE v2 · 2026-05-19 noche (pre-compact sesión maratón)

**Sesión:** Linda · 2026-05-19 · maratón ~10h · branch base main · post-piloto §9.8 día 30.
**Cliente Saymi:** aún NO ha visto la app (CEO confirmó · cliente entra "cuando se ocupe").
**URL prod:** https://frontend-zeta-sepia-46.vercel.app · deploy `frontend-prb2qni9a` aliased.

---

## Lo que se entregó hoy (5 PRs merged a main)

| PR | Commit | Scope |
|---|---|---|
| #51 | `be519aed` | P0 fixes pre-piloto (Neutral fallback + @@handle + caveat Monitoreo) |
| #52 | `0c523cf1` | P1+P2 fixes (split-view cliente_seed + 9 fixes más) |
| #53 | `4b6e6acb` | #1 tono_discurso + F1 UnifiedPostCard + F2 parcial + Bloque B+C tests |
| #54 | `b2f9ba67` | F4 Content Hub Posts Workspace (/dashboard/hub + BFF /posts/unified + sidebar consolidado + redirects 308) |
| direct | docs | STATUS + AUDIT-FULL reporte |

**16 fallos del plan deuda + Content Hub F1-F4 completos + audit-full ejecutado.**

---

## Estado real post-sesión

### Deploy prod actual

- Backend: nuevos endpoints `/api/v1/social/tono-discurso-{timeline,coverage}` + `/api/v1/posts/unified?view=feed|comentarios|top|fans`
- Frontend nueva ruta `/dashboard/hub` con tabs internos + sidebar single ítem "Contenido"
- 4 redirects 308 activos desde rutas viejas
- Misael ⭐ Fan #1 mockup intacto (D-MISAEL-VIP-40 · 40 reactions / 12 comments en split-view)

### audit-full score 73.25/100 (sobre-estimado per Gemini)

| Audit | Score | Estado |
|---|---|---|
| Smoke | 100 | ✅ |
| Funcional | 86 | 🟡 regresión sin filtros /hub |
| Seguridad | 44 | 🔴 .env.scraping-keys tracked |
| Calidad código | 79 | 🟡 |
| Diseño UX/UI | 74 | 🟡 |
| Responsive | 76 | 🟡 mobile débil |
| Hardening IA | 70 | 🟡 |
| Accessibility | 68 | 🟡 |

Reporte canónico: `.context/AUDIT-FULL-2026-05-19.md`.

---

## Pendientes con prioridad post-compact

### CEO asumió responsabilidad / sin urgencia

1. **Credentials rotation** (`.env.scraping-keys` tracked git · task #47): NO comprometidas según CEO · rotar cuando se ocupen los servicios externos · NO pánico · agenda flexible.

### Tríada técnica pre-cliente (CEO "no le ve problema" pero quedan abiertos)

2. **Filtros en `/hub`** (regresión funcional · ~45 min): agregar selectors platform + date_from + date_to + sentiment al frontend `/dashboard/hub/page.tsx`. Endpoint `/posts/unified` YA acepta esos params · solo expose en UI.
3. **Rate limit `/posts/unified`** (~10 min): agregar `@limiter.limit("60/minute")` en `backend/app/api/v1/endpoints/posts_unified.py:331`.
4. **Responsive mobile** (~20 min): UnifiedPostCard no apila vertical en mobile · cambiar grid a `grid-cols-1 md:grid-cols-2 xl:grid-cols-3` en hub/page.tsx.

### Sprint post-cliente (alta prioridad)

5. **Prompt injection mitigation**: `dirigente_context_builder.py:334-379` · delimitar contexto LLM con `<context></context>` + sanitizar patterns jailbreak. También `reels_generator.py:88` + `schemas/{reels,plan_ia}.py` (contexto_adicional user-controlled).
6. **Tests `/posts/unified`** (~2h): 4 views × auth × paginación · ~10-12 tests pytest siguiendo patrón `test_tono_discurso.py`.
7. **Skeletons en Hub** (~20 min): UnifiedPostCardSkeleton ya existe · aplicarlo en ContenidoGrid mientras `isLoading`.
8. **Badge data_source visible UnifiedPostCard** (~30 min): exponer Apify/RADAR/Mixed inline en card · diff visible para B2B.
9. **Accessibility fixes** (~1h): sidebar contraste 2.01:1 → ≥4.5:1, listitem inválido, link-name fantasmas, aria-prohibited-attr Overview.

### Sprint mediano plazo (backlog 4-6 sem)

10. **Performance**: N+1 queries en BFF · stress tests con dataset realista
11. **Resiliencia frontend**: Error Boundaries específicos si BFF falla
12. **PII compliance review**: pipeline scraping → IA
13. **Colisión label "Contenido"** sidebar: renombrar `/dashboard/contenido` Content Factory a `/dashboard/content-factory`
14. **Limpieza código muerto**: rutas viejas (`/social`, `/social/comentarios`, `/content/top`, `/aceptacion/fans`) tras 1 mes estable
15. **#1 tono_discurso granularidad 5**: requiere backfill NLP enriquecido sobre posts · sprint NLP dedicado
16. **Cleanup endpoint sentiment-timeline legacy** cuando todos consumers migrados
17. **Cleanup BD S-8.1** 154 auto_suggested + 320 events (esperando orden CEO post-postmortem)

### Cross-product (Hugo / RADAR)

18. **Threads activación** cuenta `soporte@consultoriamd.com.mx` / `chatmx_oficial` · Hugo pregunta si tiene opt-in Meta · pendiente CEO confirme empíricamente.
19. **D3 IG burner**: CERRADO ✓ por Hugo hoy (login OK · session dumped · Saymi smoke 12K followers).

---

## Decisiones tomadas durante la sesión

### Plan deuda 16 fallos (aprobado y ejecutado)

- P0 fixes pre-piloto: sentiment NULL no inventa Neutral · @@ handle fix · Monitoreo caveat dedup
- P1 fixes: split-view cliente_seed · indicador plataforma Top Posts · chart Overview empty state · banda gris Fantasmas dual
- P2 fixes: sin RTs condicional · Top Posts tooltip elegibles · warning low interactions · glosario disonancia Fantasmas
- #1 tono_discurso: endpoint nuevo paralelo (legacy sentiment-timeline NO tocado · cleanup posterior)

### Content Hub plan v3 (aprobado y ejecutado)

8 decisiones aprobadas convergencia Linda↔Gemini 7/8:
- D1.1=A migrar tono_discurso · paralelo legacy
- D1.2=A 5 valores literales · chart data-driven
- D1.3=A sprint dedicado post-piloto
- D13.1=C mixto F1-F3 escalonado + F4
- D13.2=A `/dashboard/hub` (ajuste por colisión `/contenido` Content Factory existente)
- D13.3=A endpoint unificado `/api/v1/posts/unified?view=`
- D13.4=C tabs internos `?tab=` deep-linking
- D13.5=A single ítem sidebar "Contenido"

F1 completo · F2 parcial (Monitoreo migrado · Top Posts mantiene fixes específicos) · F3 decisión scope (TopPostsCards mantiene quotes modal único · absorbido por F4) · F4 completo.

### Decisiones nuevas registradas en DECISIONS.md

- `D-MISAEL-VIP-40` (2026-05-19): Misael Fan #1 mockup frontend 40 reactions / 12 comments
- `D-BUG-CONTROL-CHARS-POST-PILOTO`: bug `/planes/{id}` JSON falso positivo · 3 endpoints serializan JSON strict OK
- `D-1` ratificada: Ollama OFF · endpoint `/plan-ia/generate` sigue 503
- `D-PLAN-IA-CC-GEMINI-CLI-1` ratificada: generación planes offline CC subprocess + fallback Gemini CLI

---

## Reglas aprendidas / errores cometidos hoy

### Regla "Verificar fuente primaria antes de scoring" fallé 5 veces

1. Asumí Storybook existía (no existía · Gemini me corrigió)
2. Asumí piloto significaba cliente vio la app (CEO me corrigió · cliente NO ha visto)
3. Asumí bug `/planes/{id}` control chars era real (verificación empírica refutó)
4. Asumí CRECE tenía session file IG para Hugo (script hace login fresh)
5. Asumí Misael 80 reactions era acuerdo previo (CEO me corrigió: acuerdo era 40)

**Sub-regla aprendida hoy:** cuando algo dependa de "qué hizo un peer/sistema externo" o "qué decidió el CEO antes", PREGUNTAR antes de inventar la causa. NO heredar suposiciones de Gemini sin verificar empíricamente.

### Patrones que funcionaron

- Branch desde main siempre (lección PR #49 → cherry-pick limpio en #50)
- Cross-audit Gemini antes de tocar código en decisiones estratégicas
- Multi-PR pequeños vs un PR gigante (5 PRs hoy sin conflicts)
- `vercel --prod --yes` manual obligatorio post-merge (proyecto `frontend` no auto-deploya)
- Playwright validación post-deploy antes de declarar listo

### Anti-patrones evitados

- "Big Bang UI rewrite" (Gemini · refactor progresivo F1-F4)
- "God Endpoint" `/posts/unified` (handlers separados internamente per view)
- Storybook desde cero (substituido por ruta dev oculta)
- SQLite mock para tests Postgres asyncpg (preferí BD test :5439)

---

## Próximo paso recomendado al re-entrar

1. **Leer CONTEXT ANCHOR estándar:** `STATUS.md` + este HANDOFF + `AUDIT-FULL-2026-05-19.md` + `DECISIONS.md` + `BLOCKERS.md` + `PLAN-current.md`
2. **Confirmar con CEO** cuáles pendientes técnicos atacar. Mi sugerencia operativa:
   - Si cliente entra esta semana: tríada técnica (~75 min) → score >85
   - Si cliente entra después: prompt injection mitigation primero (calidad > tiempo)
3. **NO tocar credentials git filter-repo** sin CEO presente y autorización explícita (acción destructiva · reescribe historia).
4. **Hugo cross-product**: ventana jueves · Threads activación pendiente confirmación CEO empírica.

---

## Información operativa rápida

| Item | Valor |
|---|---|
| URL prod cliente | https://frontend-zeta-sepia-46.vercel.app |
| Vercel proyecto que sirve cliente | `frontend` (NO `crece-v2`) |
| Deploy actual | `frontend-prb2qni9a` aliased |
| Branch main HEAD | `b2f9ba67` + docs posteriores |
| Login dirigente test | `pineda@crece.mx` / `demo2026!` (Saymi · dirigente_id=3) |
| Login admin test | `admin@consultoriamd.com` / `crece2026!` |
| BD prod CRECE | `crece-db:5438` host Mac Mini |
| Tunnel CF current | `/tmp/crece-tunnel.url` |
| Peer Hugo RADAR | `s2ryygne` · cwd `/Users/marxchavez/Projects/radar` |

## Archivos canónicos al re-entrar

- `.context/STATUS.md`
- `.context/HANDOFF-2026-05-19-cierre-maraton.md` (este archivo)
- `.context/AUDIT-FULL-2026-05-19.md`
- `.context/DECISIONS.md`
- `.context/BLOCKERS.md`
- `.context/PLAN-current.md`
- `~/.claude/plans/greedy-strolling-graham.md`

**Sesión maratón terminada · pre-compact.** Re-entrada limpia.
