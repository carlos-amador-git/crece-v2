# AUDIT-FULL · CRECE v2 · 2026-05-19 noche

**Origen:** /audit-full ejecutado tras sesión maratón cierre Content Hub F4 + 16 fixes UI + #1 tono_discurso. 8 agents paralelos + cross-audit Gemini.

**URL prod auditada:** https://frontend-zeta-sepia-46.vercel.app
**Deploy:** `frontend-prb2qni9a` aliased (commit main `b2f9ba67`).
**Estado piloto:** cliente Saymi aún NO ha visto la app.

## Score global

**73.25 / 100** (promedio ponderado) — Gemini cross-audit lo califica como **"sobre-estimado"** dado que el score promedia el 100/10 de smoke con el 44% crítico de seguridad. El score numérico oculta la tríada crítica que sigue.

## Tabla consolidada · 8 dimensiones

| Auditoría | Score | Peso | Resultado | Top finding |
|---|---|---|---|---|
| Smoke Test | 100/100 | 10% | ✅ excelente | Chatwoot widget 429 externo (no bloquea) |
| Funcional | 86/100 | 20% | 🟡 OK con regresión | Sin filtros en /hub (regresión vs /social viejo) |
| Seguridad | 44/100 | 20% | 🔴 crítico | `.env.scraping-keys` tracked en git |
| Calidad código | 79/100 | 15% | 🟡 OK | 0 tests para `/posts/unified` (370 LOC) |
| Diseño UX/UI | 74/100 | 10% | 🟡 OK | Sin skeletons en Hub · sin badge data_source visible |
| Responsive | 76/100 | 10% | 🟡 mobile débil | UnifiedPostCard no apila vertical en mobile (5.5/10) |
| Hardening IA | 70/100 | 10% | 🟡 OK | Prompt injection vía contenido scrapeado |
| Accessibility | 68/100 | 5% | 🟡 OK | Sidebar contraste 2.01:1 (esperado ≥4.5:1 WCAG AA) |
| **GLOBAL** | **73.25/100** | 100% | 🟡 **NO listo para cliente** | Tríada crítica activa |

## Top 10 issues priorizados por impacto (Gemini)

| # | Severity | Issue | Por qué urgente |
|---|---|---|---|
| 1 | 🔴 CRÍTICO | `.env.scraping-keys` tracked en git | Exposición credenciales · riesgo financiero APIs scraping · purga + rotación inmediata |
| 2 | 🟡 ALTO | Prompt injection vía contenido scrapeado | `dirigente_context_builder.py:334-379` · posts/comments crudos al LLM con solo `.strip()[:N]` |
| 3 | 🟡 ALTO | Rate limit ausente `/posts/unified` | API pesada · puede tumbar BD o generar costos masivos |
| 4 | 🟡 ALTO | Sin filtros en `/hub` | Regresión funcional vs `/social` viejo · cliente B2B necesita filtros para usar workspace |
| 5 | 🟡 MEDIO | UnifiedPostCard no apila vertical mobile | App inusable en móvil · mala primera impresión letal |
| 6 | 🟡 MEDIO | Sin badge data_source visible | Cliente no distingue Apify vs RADAR vs Mixed · falta contexto B2B |
| 7 | 🟡 MEDIO | Sin skeletons en Hub | UX percibida lenta · inaceptable producto Premium |
| 8 | 🟡 MEDIO | Sin tests `/posts/unified` BFF (370 LOC) | Deuda técnica · invisible al cliente corto plazo |
| 9 | 🟢 BAJO | Sidebar contraste 2.01:1 WCAG fail | Accesibilidad · no rompe flujo crítico |
| 10 | 🟢 BAJO | Colisión label "Contenido" sidebar | Fricción menor · explicable en onboarding |

## Gaps no cubiertos por los 8 audits (Gemini)

| Gap | Severity | Acción |
|---|---|---|
| Performance / N+1 queries BFF sin tests de carga | HIGH | Sprint post-cliente: stress test con dataset realista |
| Resiliencia frontend · Error Boundaries específicos | MEDIUM | Si BFF cae 500, ¿app crashea o fallback graceful? · validar |
| Privacy / PII filtering en pipeline scraping → IA | HIGH | Validar que perfiles sociales no se persisten/procesan con PII identificable |

## Veredicto Gemini sobre score

> "Un score de 73.25% es un espejismo: la presencia de credenciales trackeadas y vulnerabilidades de inyección de prompts significa que el producto es inseguro para un entorno productivo B2B."

## Recomendación Gemini

> "**Frenar la demo hasta resolver la tríada crítica** (Credenciales expuestas, Rate Limits y Filtros del Hub). Rotar las llaves comprometidas hoy mismo, aplicar rate-limiting básico en FastAPI, restaurar los filtros mínimos viables en el Hub y añadir las clases flex-col para móvil. Lo visual y la deuda técnica (tests/skeletons) pueden esperar al próximo sprint post-demo."

## Plan de acción recomendado (orden ejecución)

### Pre-cliente · obligatorio (~2-4h)
1. **Credentials** (PENDIENTE CEO · task #47): rotar 7 keys + `git rm --cached` + `git filter-repo` para purgar historia
2. **Filtros en /hub** (regresión funcional): agregar selectors platform + date_from + date_to + sentiment al frontend `/dashboard/hub/page.tsx` (~45 min)
3. **Rate limit `/posts/unified`**: agregar `@limiter.limit("60/minute")` en `posts_unified.py` (~10 min)
4. **Responsive mobile fix**: cambiar grid `grid-cols-1 md:grid-cols-2 xl:grid-cols-3` en Hub (~20 min)

### Sprint post-cliente · alta prioridad (~3-5h)
5. **Prompt injection mitigation**: delimitar contexto LLM con `<context></context>` + sanitize patterns jailbreak en `dirigente_context_builder.py` (~1h)
6. **Skeletons en Hub**: UnifiedPostCardSkeleton ya existe · solo aplicarlo en ContenidoGrid mientras isLoading (~20 min)
7. **Badge data_source visible**: agregar inline en UnifiedPostCard (Apify/RADAR/Mixed) (~30 min)
8. **Tests `/posts/unified`**: 4 vistas × auth × paginación · ~10-12 tests pytest (~2h)
9. **Accessibility fixes**: sidebar contraste · listitem inválido · link-name fantasmas (~1h)

### Backlog · medio plazo
- Performance N+1 stress tests + Error Boundaries frontend + PII compliance review
- Colisión label "Contenido" (renombrar /dashboard/contenido a /dashboard/content-factory o similar)
- Limpieza código muerto rutas viejas (frontend/src/app/dashboard/social/ etc tras 1 mes estables)

## Comparación vs auditorías anteriores

No hay audit-full previo en `.context/`. Este es baseline. Referencias parciales:
- `AUDIT-FULL-2026-04-25.md` (pre piloto previo)
- `AUDIT-SECURITY-RBAC-2026-05-15.md` (audit security previo)

## Artefactos generados

- Screenshots diseño: `/tmp/audit_design_*.png` (6 archivos)
- Screenshots responsive: `/tmp/audit_responsive_*.png` (15 archivos)
- Scripts auditoría reutilizables: `/tmp/crece-audit-smoke.mjs`, `/tmp/a11y-audit.mjs`, `/tmp/playwright-audit/audit.js`

## Pendiente CEO

- **Task #47** rotar credentials `.env.scraping-keys` + git filter-repo (requiere CEO presente · acción destructiva)
- Decisión: ¿frenar cliente hasta cerrar tríada o liberar con caveats documentados?
