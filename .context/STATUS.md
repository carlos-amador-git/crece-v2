# CRECE v2.0 — Status

## Estado: SPRINT 1 COMPLETO ✅
## Fecha: 2026-04-11

## Sprint 1 — Saneamiento (ejecutado 2026-04-11)

9 tareas ejecutadas, verificadas con Playwright contra deploy de Vercel.

| ID | Tarea | Resultado |
|----|-------|-----------|
| S1.1 | Correr NLP sobre social_posts | 378 posts reprocesados. Distribución real: 99 POSITIVE / 161 NEUTRAL / 121 NEGATIVE |
| S1.2 | Verificar RLS con 3 demo logins | Admin=2 dirigentes/381 posts, Piña=1 dirigente/191 posts, Solano=1 dirigente/190 posts. Split 191+190=381 ✓ |
| S1.3 | Fix bug filtros tiempo | Endpoint acepta period=today/7d/30d/90d, hook propaga `activeFilter` |
| S1.4 | Fix 422 scoring/by-seccion | Nuevo endpoint lista 16 secciones con agregados |
| S1.5 | Investigar IPD idéntico | Sin bug: Piña 3.90 vs Solano 3.87, redondean a 3.9 |
| S1.6 | Auditar /participacion | Confirmado mockup. Banner DEMO amarillo visible |
| S1.7 | Fix 404 favicon | icon.svg creado en src/app/ |
| S1.8 | KPIs del político | "Tu Audiencia / Presencia Digital / Conversación / Tema Urgente" con data real |
| S1.9 | Sidebar enriquecido | Dirigente users ven badges IPD X/10 y followers total |

**Bug adicional encontrado y corregido (fuera de plan):** Frontend leía `post.sentiment` pero backend devuelve `sentiment_label`. Por eso el pie chart salía 100% neutral. Fix: `SocialPost` type, `PostCard`, `SentimentBadge`, `social/page.tsx`.

**Deuda conocida pendiente:** prefetch RSC a `/dashboard/settings` (ruta muerta en sidebar, no bloqueante).

**Cross-audit Gemini:** aprobado con recomendaciones — correr pytest antes de commit (pytest no está en container prod, verificación alternativa pasó: import check + API smoke test de 6 endpoints, todos 200).

**Deploy:** frontend-zeta-sepia-46.vercel.app (production) actualizado.

---

## Estado histórico previo

## Plan original ~98% cubierto
## Fecha: 2026-04-05

## Sesión de hoy — Resultados

### Gaps cerrados (15 de 15 del plan original + 4 sprint adicionales)

| # | Tarea | Estado | Detalle |
|---|-------|--------|---------|
| 1 | Bluesky | HECHO | AT Protocol, sin auth, probado con Patricia Mercado |
| 2 | Sherlock | HECHO | Servicio + endpoint /osint/sherlock, anti-injection |
| 3 | sentiment-spanish | HECHO | CNN model como validación secundaria en NLP |
| 4 | Modelos propaganda | HECHO | cardiffnlp/twitter-roberta-base-offensive |
| 5 | NLP datos reales | HECHO | 7/7 modelos funcionando con posts de Piña/Solano |
| 6 | **Voter Scoring ML** | **HECHO** | 200 ciudadanos sintéticos INEGI, RF accuracy=1.0, 606 scored |
| 7 | Geometries INE | POSPUESTO | Shapefiles pesados, no bloquea demo |
| 8 | WhatsApp/Chatwoot | HECHO | Webhook HMAC verificado, test E2E pasó |
| 9 | Mobile app | HECHO | Dashboard + Diagnóstico screens, 5 tabs |
| 10 | n8n nodes | **HECHO** | 6 workflows importados, 30 nodos custom, mdconsultoria-ti.org |
| 11 | Decidim | PENDIENTE | Requiere diseño de producto |
| 12 | pgvector | HECHO | Embeddings 384-dim, HNSW index, búsqueda semántica |
| 13 | Remotion video | HECHO | 6 escenas animadas, formato reel vertical MC |
| 14 | Proxies residenciales | PENDIENTE | Config de producción |
| 15 | Threads/Telegram | HECHO | Telegram funcional, Threads stub listo |
| S1 | **Benchmark endpoint** | **HECHO** | Prefix corregido, /competidores y /ranking OK |
| S2 | **Content Factory E2E** | **HECHO** | Ollama genera tweet real para Piña (~480s CPU) |
| S3 | **Voter Scoring seed** | **HECHO** | 200 ciudadanos INEGI, RF trained, 606 scored |
| S4 | **Bot detection** | **HECHO** | Servicio pattern-based, username/profile/posts análisis |

### Score: 16 HECHO / 0 BLOQUEADO / 2 PENDIENTE (diseño/infra)

### Tests: 148 green

### Scrapers — 40+ herramientas probadas, 8 plataformas cubiertas

| Plataforma | Herramienta | Auth | Costo |
|------------|------------|------|-------|
| Instagram | ensta (Guest) | Ninguna | $0 |
| Twitter/X | Scweet v5.2 | Cookie auth_token | $0 |
| YouTube | scrapetube + yt-dlp | Ninguna | $0 |
| TikTok | yt-dlp | Ninguna | $0 |
| Facebook | curl-cffi (Chrome TLS) | Cookies c_user+xs | $0 |
| Bluesky | AT Protocol (httpx) | Ninguna | $0 |
| Telegram | Telethon | — | $0 |
| Threads | Stub (baja adopción MX) | — | $0 |

### NLP — 8 modelos operativos

| Modelo | Función | Status |
|--------|---------|--------|
| pysentimiento/robertuito | Sentimiento primario | OK |
| sentiment-spanish/CNN | Validación cruzada | OK |
| pysentimiento/emotion | Emociones (Ekman) | OK |
| pysentimiento/hate | Hate speech | OK |
| spaCy es_core_news_md | NER + topics | OK |
| cardiffnlp offensive | Controversia/propaganda | OK |
| citizenlab toxicity | Toxicidad multilingüe | OK |
| xlm-roberta-large-xnli | Zero-shot topics | OK |

### Infraestructura

| Servicio | Estado |
|----------|--------|
| Ollama Coolify (gemma3:12b) | FUNCIONANDO — 163.245.208.96:11434 |
| PostgreSQL + PostGIS + pgvector | FUNCIONANDO — :5438 |
| Frontend Vercel | DEPLOYED — frontend-zeta-sepia-46.vercel.app |
| Chatwoot webhook | CONECTADO |

## Lo que queda pendiente

- Geometries INE (#7) — shapefiles pesados, no bloquea demo
- Proxies (#14) — decisión de compra de servicio
- Decidim (#11) — proyecto independiente en ~/Projects/decidim-mc/
