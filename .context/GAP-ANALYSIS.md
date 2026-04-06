# CRECE v2.0 — Gap Analysis: Plan vs Realidad
## Fecha: 2026-04-05

## Fuentes: CLAUDE.md (plan), PLAN-current.md (batches), func-audit (pruebas en vivo)

---

## FASE 1 — Prometida vs Implementada

| Feature | Plan | Código existe? | Funciona en vivo? | Score func-audit |
|---------|------|---------------|-------------------|-----------------|
| Diagnóstico Digital (IPD) | Índice 0-10 por dirigente | SI | SI (con seed data) | 37/50 |
| Monitoreo Social — Scrapers | 5 scrapers (TW, IG, FB, TT, YT) | SI (código) | NO ejecutados — 0 datos reales scrapeados | 29/50 |
| Monitoreo Social — NLP | pysentimiento + spaCy | SI (código + tests mock) | NO probado con datos reales | ~20/50 |
| Monitoreo Social — Alertas crisis | Detección automática negatividad | SI (modelo + endpoint) | NO — sin datos para triggear | ~15/50 |
| Benchmarking | Comparación vs competidores + MC | SI (modelo + endpoint) | **NO — endpoint crashea 500** | 5/50 |
| Planes IA — Claude | Generación streaming SSE | SI | **NO — API key placeholder** | 13/50 |
| Planes IA — Ollama | Generación local Gemma 4 | SI (código) | **NO PROBADO — nunca ejecutado** | ??/50 |

### Veredicto Fase 1: Código completo, pero solo Diagnóstico IPD funciona end-to-end.

---

## FASE 2 — Prometida vs Implementada

| Feature | Plan | Código existe? | Funciona en vivo? | Score func-audit |
|---------|------|---------------|-------------------|-----------------|
| WhatsApp Campaign Manager | Chatwoot-MX webhooks | SI (modelo + endpoint) | VACÍO — sin datos, sin Chatwoot conectado | ~10/50 |
| Smart Canvassing | PostGIS rutas optimizadas | SI (modelo + endpoint) | **ROTO — frontend llama /rutas, backend tiene /routes** | ~8/50 |
| Content Factory | Claude API multi-formato | SI | **NO — hardcoded Claude, sin Ollama, API 401** | 10/50 |
| CRM Político | Interacciones ciudadano | SI (modelo + endpoint) | Endpoint fijo (promotor_id), sin datos | ~15/50 |
| Voter Scoring | scikit-learn + fallback | SI (modelo + servicio) | **VACÍO — ML pipeline nunca ejecutado** | 12/50 |
| Participación Ciudadana | Solicitudes + seguimiento | SI (modelo + endpoint) | VACÍO — sin datos | ~15/50 |
| Blindaje Legal | Gastos INE + compliance | SI (modelo + endpoint) | VACÍO — sin datos | ~15/50 |

### Veredicto Fase 2: Todo en código, nada funciona end-to-end. Módulos son cascarones.

---

## TRANSVERSAL — Prometido vs Implementado

| Feature | Plan | Estado |
|---------|------|--------|
| Multi-tenant RLS | PostgreSQL row-level security | SI — policies aplicadas |
| Modo Veda Electoral | Middleware que bloquea operaciones | SI — código existe, no probado |
| Vector Tiles (MVT) | Mapas electorales ST_AsMVT | SI — endpoint existe, sin geometries |
| Design System MD | Instrument Sans + DM Sans + tokens | SI — implementado |
| n8n Custom Nodes | 5 nodos (segmentar, sentimiento, contenido, canvassing, voter) | SI código — NO integrados con n8n real |
| Mobile Expo | 4 screens (login, encuestas, rutas, perfil) | SI scaffold — NO conectado a API |
| Coolify Deploy | docker-compose.coolify.yml | SI config — NO desplegado |

---

## HERRAMIENTAS DEL ECOSISTEMA — Usadas vs Disponibles

| Herramienta | Disponible en skills/MCPs | Usada en CRECE? |
|------------|--------------------------|-----------------|
| Ollama/Gemma 4 | SI (`/ollama` command) | Código existe, NUNCA ejecutado |
| Gemini CLI | SI (`/gemini` command) | Solo como dev tool, NO integrado en producto |
| Remotion (video) | SI (`/video` skill) | NO integrado |
| Playwright (testing) | SI (MCP + skill) | Tests E2E escritos, no ejecutados recientemente |
| Chrome DevTools | SI (MCP) | Usado para verificación visual |
| NotebookLM | SI (`/notebooklm` skill) | NO integrado |
| Magic UI (21st.dev) | SI (MCP) | MCP con errores, no usable |
| shadcn | SI (MCP + skill) | SI — componentes instalados |
| CFDI Facturación | SI (skill) | NO — no aplica a CRECE |
| WhatsApp Cloud API | SI (skill) | NO — usa Chatwoot como intermediario |
| pgvector | SI (skill) | NO — no hay búsqueda semántica implementada |
| PostGIS | SI (skill) | SI — canvassing, electoral, geo |

---

## RESUMEN DE GAPS

### P0 — Sin esto no hay demo
1. **Ollama como provider default** — cambiar AI_PROVIDER, verificar que corre, probar plan generation
2. **Content Factory con Ollama** — refactor para soportar provider switching
3. **Benchmark 500** — fix serialización modelo Competidor
4. **Canvassing ruta mismatch** — alinear frontend/backend

### P1 — Demo funciona pero no impresiona
5. **Scrapers deben correr al menos 1 vez** — datos reales de Piña/Solano
6. **Voter Scoring** — ejecutar pipeline con datos existentes
7. **Landing → datos vivos** — endpoint público showcase
8. **NLP debe procesar los posts scrapeados** — sentiment real, no seed

### P2 — Para producción
9. **Geometries electorales** — cargar shapefiles CDMX del INE
10. **WhatsApp/Chatwoot** — conexión real
11. **Mobile app** — conectar a API
12. **n8n nodes** — integrar con instancia real
13. **Monitoring** — Sentry/Prometheus
14. **Video generation** — evaluar Remotion
15. **Forgot-password email** — Celery task real

### P3 — Del plan original, sin implementar
16. **Decidim** (participación ciudadana estilo Decidim) — solo hay solicitudes básicas
17. **pgvector búsqueda semántica** — no implementada
18. **Content Factory video** — solo genera texto, no video
19. **Voter Scoring ML real** — solo existe el fallback rule-based
