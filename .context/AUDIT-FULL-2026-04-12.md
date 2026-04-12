# CRECE v2.0 — Auditoría Integral (2026-04-12)

## Score Global: 75.7 / 100

| Auditoría | Score | Peso | Ponderado |
|---|---|---|---|
| Smoke Test | 100 | 10% | 10.0 |
| Funcional | 71 | 20% | 14.2 |
| Seguridad | 69 | 20% | 13.8 |
| Calidad Código | 72 | 15% | 10.8 |
| Diseño UX/UI | 88 | 10% | 8.8 |
| Responsive | 73 | 10% | 7.3 |
| Hardening IA | 69 | 10% | 6.9 |
| Accessibility | 77 | 5% | 3.9 |
| **GLOBAL** | | **100%** | **75.7** |

## Top 10 Issues (validados por Gemini)

| # | Issue | Auditoría | Severidad | Fix estimado |
|---|---|---|---|---|
| 1 | Rate limiting inexistente en /auth/login | Security | P0 | 30min (slowapi) |
| 2 | Prompt injection via contexto_adicional | Hardening IA | P0 | 1h (sanitize + delimit) |
| 3 | SQL injection PostGIS geometry f-string | Security | P0 | 1h (parameterize) |
| 4 | Participación sin data | Funcional | P1 | 30min (seed) |
| 5 | Campañas sin data | Funcional | P1 | 30min (seed) |
| 6 | Touch targets <44px (h-9 = 36px) | Responsive | P1 | 30min (CSS) |
| 7 | Plan generator Claude sin try/except | Hardening IA | P1 | 30min |
| 8 | 11 tests failing (DB config) | Code Quality | P1 | 30min |
| 9 | ProxyHeadersMiddleware trusted_hosts=* | Security | P1 | 15min |
| 10 | No skip-to-content link | Accessibility | P2 | 15min |

## Gaps adicionales (Gemini cross-audit)

| Gap | Cubierto? | Nota |
|---|---|---|
| Rotación PII keys | SÍ (Sprint C, C.3) | Script funcional, dry-run verified |
| Re-indexación HNSW bajo carga | NO auditado | Pendiente para pre-prod |
| Kill Switch Veda Electoral | PARCIAL | Middleware existe pero no verificado E2E |

## Fortalezas

- **Smoke 100/100**: 19 endpoints, 22 pages, 0 errores
- **Dark mode 10/10**: sistema HSL completo con tokens semánticos
- **Embeddings 10/10**: 381/381 posts, HNSW funcional
- **Canvassing geo 9/10**: 9,631 ciudadanos con GeoJSON PostgreSQL-native
- **Social monitoring 9/10**: NLP real con pysentimiento sobre 381 posts
- **INE compliance 18/20**: etiqueta IA + modelo_ia en content factory
- **Mobile nav 9/10**: hamburger + drawer + collapse con tooltips

## Plan de acción recomendado

### Sprint E — Security Hardening (~3h)
1. slowapi rate limiting en /auth/login (5/min) y /forgot-password (3/min)
2. Sanitizar contexto_adicional en plan_generator + content_factory (delimited section)
3. Parametrizar PostGIS queries en canvassing service (ST_Collect via bind params)
4. ProxyHeadersMiddleware trusted_hosts restrictivo
5. Guard producción para JWT_SECRET/PII_KEY defaults

### Sprint F — Funcional + UX (~2h)
1. Seed data participación (10 solicitudes demo)
2. Seed data campañas (1 campaña demo con segmento)
3. Touch targets h-9→h-10 en button.tsx
4. Skip-to-content link en layout.tsx
5. Plan generator try/except + timeout

### Sprint G — Code Quality (~1h)
1. ruff --fix para 97 auto-fixable lint errors
2. Fix 11 tests failing (test DB migration sync)
3. INE disclaimer en plan_generator
