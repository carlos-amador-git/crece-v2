# Investigación · SaaS de Posicionamiento Digital para PyMEs (MX)
**Fecha:** 2026-05-07 · **Autor:** Deep Research Agent (Claude Opus 4.7) · **Cliente:** MD Consultoría TI / CEO
**Objetivo:** Apoyar decisión build/buy/partner para una app SaaS standalone que reuse lógica de CRECE v2 y patrones agentic de CFDI-Platform.

---

## 0. Hallazgos no obvios (TL;DR)

1. **Birdeye/Podium NO publican precios y arrancan en USD $299/mes por sucursal** — eso es ~$5,300 MXN/mes por sucursal, prohibitivo para 99% de PyMEs MX (presupuesto típico de marketing digital total: $3-15K MXN/mes). Hay un hueco enorme entre ese tier y "agencia local que cobra $5K MXN/mes pero hace todo a mano". Ese hueco es el oportunidad.
2. **Yelp es prácticamente irrelevante en MX**. TripAdvisor sí tiene tracción en restaurantes turísticos. El 95% de la "reseña que importa" para PyME mexicana = **Google Business Profile (GBP) + Facebook + (cada vez más) Uber Eats/DiDi/Rappi**. Cualquier producto MX puede empezar **mono-plataforma con GBP** y cubrir 70-80% del pain real.
3. **Google Business Profile API es gratis** (rate limited a 300 QPM, 10 edits/min/perfil). El costo marginal por negocio monitoreado es ~$0 en GBP. El costo real son los LLMs y la infra, no las APIs de plataformas.
4. **Uber Eats / DiDi Food / Rappi NO tienen API pública para terceros**. Solo Telnet/Deliverect tienen integración POS oficial. Cualquier scraping = TOS violation con riesgo legal real (no solo técnico). Recomendación: ignorar en MVP, integrar solo si el restaurante da export CSV manual.
5. **La LFPDPPP fue actualizada en 2025** — más estricta que la versión 2010. Republicar reseñas existentes en GBP/Facebook bajo su URL original = bajo riesgo. **Crear un sitio agregador que muestre reseñas con nombre/foto del autor sin consentimiento = alto riesgo** (PROFECO + IFT + INAI tienen jurisdicción cruzada).
6. **PROFECO subió multas en 2025**: hasta $2.34M MXN o 10% de ingresos brutos por publicidad engañosa. **Generar reseñas falsas con IA o incentivar al dueño a hacerlo = exposición seria**. Diseñar el producto desde el día 1 con guardrails que impidan esto.
7. **Patrón ganador en MX para SaaS PyME (Konfío, Bind, Clip)**: NO se vende por SEO/Google Ads, se vende por **canal humano** — agencias locales, asesores fiscales, cámaras (Coparmex, Canacintra), franquicias. El SaaS que paga comisión al asesor fiscal es el que escala.
8. **El stack de CRECE v2 (FastAPI async + Next.js 14 + PostGIS + Celery + scrapers + NLP triple capa) es ~70% reusable**. Lo que cambia: dominio de datos (negocios vs dirigentes), prompts del generador IA, dashboards. Lo que se mantiene: arquitectura multi-tenant, scrapers IG/FB, NLP de sentimiento, infra Docker, generador de planes.
9. **CrewAI tiene 44.6K stars pero no tiene checkpointing**. Para un agente 24/7 que responde reseñas y debe sobrevivir crashes, **LangGraph + interrupt() + Postgres checkpointer es lo único maduro hoy**. Pydantic AI gana en code quality pero todavía no tiene la madurez operacional de LangGraph para HITL.
10. **El "voice cloning textual" (RAG sobre conversaciones previas del negocio) es lo que separa una respuesta automatizada de una buena**. Es el verdadero moat técnico, no los scrapers.

---

## A) Competencia internacional + búsqueda específica MX/LATAM

### Tabla comparativa — players globales

| Producto | Precio entrada (USD/mes/sucursal) | País/idioma | Features clave | Integraciones | Hueco |
|---|---|---|---|---|---|
| **Birdeye** | $299 (Starter) → $599 (Professional) | EN, ES limitado | Reviews 200+ sites, listings 50+ sites, AI replies, surveys, social sharing automático | GBP, Facebook, Yelp, TripAdvisor, 3000+ integraciones | Caro para multi-loc, UX overloaded |
| **Podium** | Custom (≈$289-$449/mes) | EN principal | SMS-first review collection, webchat, payments, AI 24/7 | GBP, Facebook, CRMs | Single-location bias, no multi-idioma maduro |
| **Reputation.com** | Enterprise only ($500+/mes) | EN, multi | Reputation score, listings, surveys, social, business intel | 100+ | No PyME, vendor enterprise |
| **Yext** | $149/mes (5 locs mín) | EN | Knowledge graph, listings 100+ directorios, AI search | Schema.org, Apple, Bing | Caro <5 locs, fuerte en listings débil en reviews |
| **NiceJob** | $75 (Reviews) / $125 (Pro) flat | EN | Review requests automatizados, social proof widgets, referrals | GBP, Facebook | Single-loc, sin español maduro |
| **Grade.us** | ~$110-180/loc | EN | Drip campaigns review requests, white-label para agencias | GBP, Facebook, Yelp | UX old, sin AI |
| **Trustpilot** | Free tier + paid desde $259/mes | Multi (ES sí) | Marketplace de reviews, mostly e-commerce | Shopify, etc. | No es GBP-first, B2C ecom focus |
| **Buffer** | $6-$120/mes flat | Multi | Social scheduling 9 plataformas | Todas redes sociales | No tiene reviews ni listings |
| **Hootsuite** | $99-$249/mes flat | Multi | Social scheduling + monitoring + analytics | 30+ redes | Solo social, no reviews/GBP edits |
| **Sprout Social** | $249-$499/usuario/mes | Multi | Enterprise social + listening + analytics | Todas redes + helpdesk | Por usuario (caro), enterprise focus |
| **ReviewGrower** | $9.95/loc | EN (ES?) | Review collection básico | GBP, Facebook | Producto delgado, no AI |

### Players hispano/MX
La búsqueda fue clara: **no existe un player mexicano serio en el bundle "presencia digital + reseñas + redes" para PyME**. Lo que existe:
- **Agencias** (Posiciona.Digital, Seology, ORM Agencia) — venden servicio profesional con SaaS subyacente de terceros (típicamente Birdeye o Hootsuite white-label) por $5-25K MXN/mes.
- **SaaS verticales** que tocan partes: Bind ERP (facturación/contabilidad), Konfío (fintech + ERP), Clip (POS), Heru (fiscal autónomos). Ninguno hace reputación.
- **Reputación pura**: empresas tipo gestionreputaciononline.com, mejorimagen.mx — son agencias de PR + monitoreo manual, no SaaS self-serve.

**Conclusión A:** El vertical "SaaS de presencia digital self-serve para PyME mexicana en español" está vacío. Birdeye no traduce bien y cobra en USD; las agencias no escalan.

Fuentes: [Birdeye pricing](https://birdeye.com/pricing/), [Birdeye real cost RepliFast](https://www.replifast.com/blog/birdeye-pricing-2026), [Yext pricing GetApp](https://www.getapp.com/marketing-software/a/yext/), [NiceJob G2](https://www.g2.com/products/nicejob/pricing), [Sortlist MX reputation](https://www.sortlist.com/s/reputation-management/mexico-mx), [Inquirer top 12](https://usa.inquirer.net/191823/best-reputation-management-software).

---

## B) Repos open-source clonables o como base

### Multi-tenant SaaS boilerplates

| Repo | Stars (aprox) | Licencia | Stack | Fit | Reusar |
|---|---|---|---|---|---|
| [ixartz/SaaS-Boilerplate](https://github.com/ixartz/SaaS-Boilerplate) | 7K+ | MIT | Next.js 14 + Tailwind + Shadcn + Clerk + Drizzle | Alto (frontend) | Auth, billing Stripe, multi-tenant routing, i18n, landing |
| [benavlabs/FastAPI-boilerplate](https://github.com/benavlabs/FastAPI-boilerplate) | 2K+ | MIT | FastAPI async + Pydantic v2 + SQLAlchemy 2.0 + Postgres + Redis | Alto (backend) | Auth, rate limiting, caching, queue, RBAC |
| [Madeeha-Anjum/multi-tenancy-system](https://github.com/Madeeha-Anjum/multi-tenancy-system) | <1K | MIT | FastAPI + Postgres schema-per-tenant | Medio | Patrón schema-per-tenant si se prefiere sobre RLS |
| [sudharsangs/nextjs-multitenant-saas-boilerplate](https://github.com/sudharsangs/nextjs-multitenant-saas-boilerplate) | <1K | MIT | Next 15 + TS + Postgres + Drizzle | Medio | Tenant isolation patterns |

### Agentic templates

| Repo | Stars | Licencia | Stack | Reusar |
|---|---|---|---|---|
| [wassim249/fastapi-langgraph-agent-production-ready-template](https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template) | ~1K | MIT | FastAPI + LangGraph + Langfuse + Prometheus + JWT + Alembic + mem0 + pgvector | **Top fit** — incluye HITL, checkpointing, fallback de modelos, observabilidad |
| [NicholasGoh/fastapi-mcp-langgraph-template](https://github.com/NicholasGoh/fastapi-mcp-langgraph-template) | ~500 | MIT | FastAPI + MCP + LangGraph | Medio — útil si planeas exponer tools como MCP |
| [von-development/awesome-LangGraph](https://github.com/von-development/awesome-LangGraph) | índice | n/a | Catálogo curado | Para descubrir piezas específicas |

### Social schedulers (alternativa headless a Buffer/Hootsuite)

| Repo | Stars | Licencia | Plataformas | Reusar |
|---|---|---|---|---|
| [gitroomhq/postiz-app](https://github.com/gitroomhq/postiz-app) | ~25K | AGPL-3.0 ⚠️ | 17+ (X, IG, FB, LinkedIn, GBP) | **Estudiar pero NO clonar** — AGPL viral. Útil como referencia de cómo manejar OAuth multi-plataforma |
| [TechSquidTV/Shoutify](https://github.com/TechSquidTV/Shoutify) | ~3K | MIT | 10+ | **Clonable** — más simple, MIT, self-hosted |
| [brightbeanxyz/brightbean-studio](https://github.com/brightbeanxyz/brightbean-studio) | ~1K | MIT | 10+ incluye GBP | **Clonable** — incluye GBP nativamente |
| [Mixpost](https://mixpost.app/) | comercial | Closed/license | 10+ | One-time license, no clonable directo |

### Review aggregators / GBP wrappers
- [google/google-my-business-samples](https://github.com/google/google-my-business-samples) — Apache 2.0, samples oficiales en JS/Java/Python/.NET/PHP. **Punto de partida obligado.**
- [dresenhista/google_my_business](https://github.com/dresenhista/google_my_business) — Python wrapper para reviews. Pequeño, MIT, útil como ejemplo concreto.
- **NO existe** un "review aggregation engine" maduro multi-fuente open source que valga la pena clonar. Esto es BUILD propio (3-5 días con LLM como acelerador).

### Reputation scoring algorithms
- No hay librería estándar. Los algoritmos publicados (Birdeye, Reputation.com) son secret sauce.
- **Reusar de CRECE v2:** matriz de polaridad de 53 reglas + pysentimiento + spaCy. Adaptar diccionario electoral → diccionario PyME (servicio, calidad, precio, atención, limpieza, sabor para restaurantes, espera, etc.).

### Local SEO / NAP consistency
- No hay open source serio. Yext domina con Knowledge Graph propietario. Clonar = reinventar 50 directorios MX (Sección Amarilla, Doctoralia, Dentistas.mx, OpenTable MX, Foursquare, Apple Maps...). **Recomendación: NO en MVP.** Empezar solo con GBP.

Fuentes: [SaaS-Boilerplate ixartz](https://github.com/ixartz/SaaS-Boilerplate), [FastAPI-boilerplate benavlabs](https://github.com/benavlabs/FastAPI-boilerplate), [wassim249 LangGraph template](https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template), [Postiz](https://github.com/gitroomhq/postiz-app), [Shoutify](https://github.com/TechSquidTV/Shoutify), [google-my-business-samples](https://github.com/google/google-my-business-samples).

---

## C) APIs y costos

### Google Business Profile API

- **Costo:** Gratis. No hay tier de pago.
- **Cuotas default:** 300 QPM (queries por minuto), **10 ediciones/min/perfil (no incrementable)**, ~1000 lecturas/día/proyecto inicial.
- **OAuth scope:** `https://www.googleapis.com/auth/business.manage`. Es scope sensible — Google puede pedir security review si tu app tiene >100 usuarios.
- **Lo que se puede leer:** Reviews (texto, rating, autor, fecha), Insights (views, calls, directions), Posts, Q&A, fotos, info del negocio.
- **Lo que se puede escribir:** Responder reviews, crear/editar Posts, actualizar info NAP, subir fotos, manejar Q&A.
- **Aprobación:** Para producción debes pasar **OAuth verification + GBP API approval** (formulario aparte, 2-6 semanas). Empezar **AHORA** este trámite si decides ir.
- **Costo mensual estimado:**
  - 100 negocios × 24 chequeos/día × 5 endpoints = ~12K calls/día → cabe en cuota gratis.
  - 1,000 negocios × misma frecuencia = 120K calls/día → necesitas quota increase, sigue gratis.
  - 10,000 negocios → necesitas quota increase grande + arquitectura de batching. Probablemente Google te limita a refresh cada 6h. Sigue $0 directo, pero el costo es el infra de scheduling y el riesgo de throttling.

### Yelp Fusion API
- **Costo:** Pagado, no hay free tier comercial. Pricing por volumen no público.
- **Restricciones brutales:** Solo retorna **3 reviews por negocio** (no full reviews), sin bulk download, **TOS prohíbe construir directorios competidores**. No retorna negocios sin reviews.
- **Veredicto MX:** Yelp tiene poca tracción en MX comparado con GBP. **Skip en MVP.**

### TripAdvisor Content API
- **Acceso:** Gratis con primeros 5,000 calls/mes; pay-as-you-go después.
- **Restricción dura:** **Solo B2C** — apps consumer-facing. Un dashboard B2B para dueños no califica directamente. Necesitas wrapper consumer si quieres usarlo.
- **Aprobación:** Requiere submission y review, key provisional caduca en 6 meses si no vas a producción.
- **Veredicto MX:** Solo tiene sentido para restaurantes turísticos y hoteles. No para tintorerías o talleres.

### Uber Eats / DiDi Food / Rappi
- **API pública:** **NO** para developers terceros. Solo POS partners certificados (Deliverect, Otter, Telnet, Olo) tienen API directa al negocio.
- **Ruta legal:** Pedir al dueño que conecte su cuenta vía OAuth-like flow del partner POS — si Deliverect lo tiene, se puede integrar. Costo: $50-150 USD/mes/restaurante por Deliverect.
- **Ruta scraping:** **Alto riesgo legal** + TOS violation explícito. No recomendable.
- **Recomendación MX:** Empezar con upload manual de CSV (Uber Eats Manager exporta reportes), automatizar luego solo para restaurantes que justifiquen Deliverect.

### Costos mensuales totales estimados (sin LLM)
| Negocios | GBP API | Yelp | TripAdvisor | Total APIs |
|---|---|---|---|---|
| 100 | $0 | skip | $0 (cabe en free) | **$0** |
| 1,000 | $0 (con quota request) | skip | ~$50 | **~$50** |
| 10,000 | $0 (con architecture) | skip | ~$500 | **~$500** |

**El costo real está en LLMs**, no en APIs. Ver sección H.

Fuentes: [GBP API limits](https://developers.google.com/my-business/content/limits), [Yelp Fusion docs](https://docs.developer.yelp.com/), [Yelp Places API](https://business.yelp.com/data/products/places-api/), [TripAdvisor Content API](https://developer-tripadvisor.com/content-api/), [TripAdvisor FAQ](https://developer-tripadvisor.com/content-api/FAQ/).

---

## D) Mercado mexicano PyME — datos duros

### Penetración digital
- **INEGI Censos Económicos 2024 (preliminar):** Pequeña empresa: 86.2% usa computadora, 82.1% internet. **Microempresa: solo 22.3% computadora, 23.5% internet**. Esto es CRÍTICO — el "PyME" de los censos es muy distinto del "lavaautos de la esquina". Diseñar UX para mobile-only.
- **AMVO 2025:** E-commerce MX = $789.7B MXN, +20% YoY, 14.8% de retail total. Mobile = 69% del tráfico.
- **80% de PyMEs MX aumentaron uso de herramientas digitales desde 2020.** PyMEs digitalizadas reportan +20% productividad y -15% costos operativos.

### Disposición a pagar — rangos típicos
- Marketing digital total mensual recomendado: **$10,000-15,000 MXN para PyME visible, $3,000-8,000 MXN si presupuesto limitado.**
- Herramientas SaaS individuales que ya usan: SendPulse $180-360 MXN/mes, Elementor $180 MXN/mes equivalente.
- **Sweet spot razonable para un SaaS de presencia digital MX: $499-1,499 MXN/mes/sucursal** (USD $25-75). Birdeye en USD $299/mes (~$5,300 MXN) está fuera de rango.

### SaaS B2B PyME MX exitosos — patrones
- **Konfío** (fintech + ERP, 2.5BUSD AUM): pivot de "préstamo" a "suite" — ERP gratis para retener cliente del crédito. Lección: el primer producto subsidia el segundo.
- **Bind ERP** (>13 años, líder ERP cloud PyME MX): canal de asesores fiscales + contadores con comisión recurrente. Onboarding incluye captura asistida de catálogo.
- **Clip** (POS): hardware como gancho, SaaS por arriba. Onboarding presencial inicial.
- **Heru** (fiscal autónomos): mobile-first puro, viral entre freelancers, $99-299 MXN/mes, growth por referidos en redes.
- **Kueski**: BNPL con onboarding instantáneo, no SaaS pero modelo de fricción cero.

### Canales de adquisición MX que funcionan
1. **Asesores fiscales y contadores** — comisión recurrente 15-25% de MRR. Konfío y Bind lo demuestran.
2. **Cámaras y asociaciones**: Canacintra, Coparmex, CANIRAC (restaurantes), AMITI, Concamin. Acuerdos institucionales.
3. **Franquicias** (Toks, El Globo, lavaderos Galaz) — un solo deal son 50+ sucursales.
4. **Agencias de marketing locales** — white-label o reseller con 30-40% margen.
5. **WhatsApp + referidos** — Heru lo demostró con autónomos.
6. **NO funciona bien:** Google Ads en frío para PyME no-tech. SEO sí, pero tarda 6-12 meses.

### Fricción típica de onboarding PyME no-tech
- No saben qué es "OAuth", no recuerdan contraseña de GBP (o nunca lo reclamaron).
- 60% de PyMEs MX **no han reclamado su perfil de GBP** — el primer valor del producto puede ser literalmente eso.
- Necesitan onboarding asistido vía WhatsApp o videollamada los primeros 30 min.
- No leen email — el canal de soporte tiene que ser WhatsApp.

Fuentes: [AMVO 2025 estudio](https://amvo.org.mx/amvo-estudios), [INEGI ICT PyMEs](https://www.ift.org.mx/transformacion-digital/blog/impulsando-el-futuro-de-mexico-como-la-transformacion-digital-en-pymes-esta-cambiando-la-economia-y), [Konfío blog crecimiento](https://konfio.mx/blog/crecimiento-empresarial/comercio-electronico-en-mexico-2025-tendencias-y-estrategias-para-aumentar-ventas/), [Bind ERP](https://bind.com.mx/), [SendPulse PyMEs](https://sendpulse.com/latam/blog/cuanto-necesitan-invertir-las-pymes-en-marketing-digital), [Shortway costos](https://shortway.com.mx/cuanto-cuesta/marketing-para-pymes).

---

## E) Compliance MX

### LFPDPPP (actualizada 2025)
- Toda recolección de datos personales requiere consentimiento (expreso o tácito vía aviso de privacidad).
- **Republicar reseñas existentes públicamente bajo URL de origen (linkear a GBP)**: bajo riesgo, considera fair use de información ya pública.
- **Mostrar nombre + foto + texto de la reseña dentro de tu producto sin link al origen**: zona gris, podría considerarse tratamiento de datos personales del autor sin base legal. Mitigación: anonimizar (mostrar solo iniciales) o citar con link y disclaimer "Reseña pública en Google".
- **Almacenar la reseña en tu DB**: OK si es para procesamiento del cliente que es dueño del negocio; el cliente debe tener su propio aviso de privacidad. Tú eres "encargado", no "responsable".
- **Privacy notice obligatorio** en el SaaS desde día 1. INAI (ahora absorbido por Secretaría Anticorrupción tras reforma 2025) puede sancionar.

### PROFECO
- Multas 2025: hasta **$2,345,728 MXN o 10% de ingresos brutos** por publicidad engañosa.
- La generación de **reseñas falsas con IA** o el incentivar reviews positivas a cambio de descuentos sin disclosure = publicidad engañosa.
- PROFECO mencionó explícitamente IA e influencers en sus comunicados 2025.
- **Diseño defensivo:** El producto NUNCA debe permitir crear/falsificar reseñas. Solo solicitar reseñas legítimas a clientes reales (vía email/WhatsApp post-servicio). Auditoría interna de prompts para que el asistente jamás escriba "review desde el lado del cliente".

### TOS de plataformas
- **Google GBP:** prohíbe scraping, pero permite uso completo de la API con OAuth. El producto debe ser cliente API, no scraper.
- **Yelp:** prohíbe específicamente "build a competing directory". Skip de todos modos.
- **TripAdvisor Content API:** uso B2C only, redistribución limitada por display requirements.
- **Facebook Pages API:** OAuth obligatorio, app review estricto desde 2018, scope `pages_read_engagement` + `pages_manage_posts`.
- **Instagram Graph API (no Basic Display):** solo cuentas Business o Creator, vía Facebook Login, también requiere app review.

### Riesgos legales conocidos para agregadores
- US case: hiQ Labs v. LinkedIn (scraping público OK pero con caveats). En MX no hay precedente equivalente; el riesgo es contractual (TOS) más que civil.
- **Recomendación dura:** ir 100% por API oficial en MVP. Scraping solo para fuentes secundarias (sin TOS firmado individual) y con riesgo asumido.

Fuentes: [LFPDPPP DOF](https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf), [Hogan Lovells nueva ley datos MX](https://www.hoganlovells.com/es/publications/mexicos-new-federal-data-protection-law-what-it-means-for-companies), [PROFECO multas 2025 KPMG](https://kpmg.com/mx/es/tendencias/2025/01/flash-monto-de-multas-de-profeco-en-2025.html), [PROFECO publicidad engañosa Independiente](https://elindependiente.mx/nacional/2025/09/20/publicidad-enganosa-profeco-multas-buen-fin/).

---

## F) Arquitectura técnica

### Scraping vs API oficial — matriz por plataforma

| Plataforma | API oficial | Scraping viable | Recomendación MX MVP |
|---|---|---|---|
| Google Business Profile | ✅ Gratis, completo | ❌ Innecesario | **API oficial** |
| Facebook Pages | ✅ Graph API, OAuth | ⚠️ Posible pero TOS | **API oficial** |
| Instagram Business | ✅ Graph API (cuentas business) | ⚠️ instaloader (CRECE ya tiene) | **API oficial** para business; instaloader para descubrimiento |
| TripAdvisor | ✅ Content API (B2C) | ⚠️ TOS prohíbe | **Solo si aplica al vertical (turismo)** |
| Yelp | ⚠️ Limitado y caro | ⚠️ Posible | **Skip** |
| Uber Eats / DiDi / Rappi | ❌ Solo via Deliverect/Telnet | ❌ Alto riesgo | **Manual upload CSV en MVP** |
| Doctoralia (dentistas) | ✅ Pública | ✅ posible | **API oficial si existe partnership** |
| Sección Amarilla | ❌ | ✅ Scrapling lo resuelve | **Scraping autorizado por dueño** |
| TikTok / YT | ✅ APIs (caras/limitadas) | ⚠️ CRECE usa TikTok-Api/scrapetube | **Reusar stack CRECE** |
| X / Twitter | ⚠️ API muy cara | ⚠️ CRECE usa twscrape/Apify | **Solo para crisis monitoring, no core** |

### Respuesta automática a reseñas — sin caer en spam/bot detection
1. **Nunca responder en <30 min**: parece bot. Buffer aleatorio 1-6h.
2. **Variabilidad léxica**: temperature alta + diccionario de aperturas y cierres por sucursal. Embeddings de respuestas previas para evitar repetición.
3. **Personalización mínima**: nombre del autor (si está), referencia a algo específico de la reseña (extraer entidades con NLP).
4. **Voice cloning textual via RAG**: el dueño hace 5-10 respuestas manuales al iniciar; se indexan en pgvector; futuras respuestas son in-context con esos ejemplos. Esto es lo que hace que suene "humano del negocio" y no "ChatGPT genérico".
5. **Tono ajustado a rating**: 1-2 estrellas → empatía + invitación a contactar offline; 3 estrellas → agradecimiento + pregunta cómo mejorar; 4-5 → agradecimiento natural sin formulismo.
6. **HITL obligatorio para 1-2 estrellas**: no se publica sin aprobación humana. Para 4-5 puede auto-publicar con flag de "deshacer" 30 min.

### Patrón HITL maduro — LangGraph

```
review_received → 
  classify (rating, sentiment, entidades) →
  generate_draft (RAG sobre voice del negocio) →
  IF rating ≤ 2 OR contains_complaint: interrupt() → 
    human reviews via dashboard / WhatsApp →
    approve | edit | reject_with_feedback →
  ELSE: auto-queue (with 30-min undo window) →
  publish_to_GBP →
  log + analytics
```

LangGraph `interrupt()` + Postgres checkpointer permite que el agente sobreviva reinicios y que el humano apruebe desde dashboard horas después.

Fuentes: [LangGraph HITL docs](https://docs.langchain.com/oss/python/langchain/human-in-the-loop), [HITL LangGraph 2026 GrowwStacks](https://growwstacks.com/blog/human-in-the-loop-ai-agents-langgraph), [LangGraph HITL Elastic](https://www.elastic.co/search-labs/blog/human-in-the-loop-hitllanggraph-elasticsearch).

---

## G) Modelo de negocio

### Pricing — qué usan los líderes
| Modelo | Quién | Pros | Contras |
|---|---|---|---|
| Per-location tiered | Birdeye, Reputation.com | Escala con cliente | Dolor para multi-loc pequeños |
| Flat plan | NiceJob, Buffer | Predecible | Mala monetización del cliente grande |
| Per-feature add-ons | Yext, Podium | Upsell natural | UX confusa |
| Per-user/seat | Sprout Social | B2B clásico | Mata adopción en PyME (1 dueño = 1 seat) |
| Hybrid (base + per-loc) | Birdeye Premium | Flexible | Negociación enterprise lenta |

### Pricing recomendado MX (basado en disposición real)
- **Free / Starter:** 1 sucursal, 1 plataforma (GBP), 50 respuestas IA/mes, branding de la app. **$0 MXN.**
- **Pro:** 1 sucursal, 3 plataformas (GBP+FB+IG), 500 respuestas/mes, voice cloning, sin branding. **$799-999 MXN/mes** (~$40-50 USD).
- **Business:** hasta 3 sucursales, todas las plataformas, AI ilimitada (con fair use), reportes mensuales generados. **$1,999-2,499 MXN/mes** (~$100-125 USD).
- **Multi-sucursal:** custom desde 4 locs, $499-799 MXN/loc adicional.
- **Anual:** 2 meses gratis (16-17% descuento) — estándar.
- **Setup fee:** $0 self-serve, $1,500-3,000 MXN onboarding asistido (opcional).

### Onboarding flow recomendado
1. **Sign-up con WhatsApp + email** (no solo email).
2. **Conectar GBP en 2 clics** (OAuth) — si el dueño no recuerda, ofrecer flujo de "reclamar tu perfil" guiado paso a paso.
3. **Análisis automático del estado actual** (IPD adaptado: completitud GBP, fotos, posts, reviews, respuestas pendientes, sentiment promedio). Mostrar score 0-10 en 60 segundos.
4. **Generar 5 acciones recomendadas** con la IA (responder N reseñas pendientes, completar campos faltantes, postear oferta, pedir reseñas a últimos 10 clientes).
5. **Aprobar y disparar** la primera acción (responder 1 reseña) en la propia onboarding — el "aha moment" debe ser <5 minutos desde sign-up.
6. **WhatsApp opt-in** para alertas de reseñas nuevas y aprobaciones.

### Canales B2B PyME MX — orden de prioridad
1. **Asesores fiscales / contadores** (programa de partners con comisión 20% MRR recurrente). Top canal probado por Konfío y Bind.
2. **CANIRAC** (restaurantes, 50K asociados) — pilot vertical restaurante.
3. **Concanaco-Servytur** (cámaras de comercio).
4. **Franquicias** (Toks, Vips, lavaderos, dentistas tipo Dental Brackets) — un deal, muchas sucursales.
5. **Agencias de marketing locales** white-label o reseller.
6. **Referidos PyME a PyME** con mes gratis (Heru playbook).
7. **Contenido SEO** en español sobre "cómo responder reseñas Google" — long tail tarda 6-9 meses pero compone.

Fuentes: [Birdeye pricing](https://birdeye.com/pricing/), [Konfío](https://konfio.mx/), [Bind ERP](https://bind.com.mx/), [Shortway costos PyME](https://shortway.com.mx/cuanto-cuesta/marketing-para-pymes).

---

## H) Patrones agentic — referencia para arquitectura

### Comparativa frameworks (caso: respuesta a reseñas + content + crisis monitoring)

| Framework | Stars | Madurez prod | HITL | Checkpointing | Multi-LLM | Verdict para este caso |
|---|---|---|---|---|---|---|
| **LangGraph** | ~14K | Alta — LangSmith, mem0, Postgres checkpointer | ✅ `interrupt()` | ✅ nativo | ✅ via LangChain | **Top pick.** Único con HITL + recovery maduros |
| **Pydantic AI** | ~8K | Media-alta — type safety fuerte | ⚠️ manual | ⚠️ manual | ✅ excelente | Buena 2da opción si prioridad es código limpio sobre features ops |
| **OpenAI Agents SDK** | ~10K | Media — handoffs explícitos, tracing | ⚠️ limitado | ⚠️ limitado | ❌ solo OpenAI/compat | Skip — vendor lock-in al modelo |
| **CrewAI** | ~44K | Media — gran adopción, abstracción simple | ❌ no nativo | ❌ no nativo | ✅ via LiteLLM | Skip para 24/7 prod, OK para prototype |
| **AutoGen** | ~38K | Media — Microsoft, multi-agent conversations | ⚠️ manual | ⚠️ limitado | ✅ | Skip — overhead alto, mejor para research |

**Recomendación:** **LangGraph** para el agente principal (review responder + content generator + crisis monitor). Pydantic AI para tools internas tipo extract entities, classify intent — donde el code quality importa más que el state machine.

### Patrones de orquestación
- **Supervisor + workers** (recomendado para este caso): un agente "Director" recibe eventos (nueva reseña, alerta de crisis, request de contenido) y dispatcha a workers especializados (Reviewer, Content Creator, Crisis Manager). Workers no se hablan entre sí. Estado central. Reusa el patrón de CFDI-Platform.
- **Swarm** (no recomendado): cada agente decide. Útil para creative tasks, peligroso para producción facturada.
- **Hierarchical**: capas de decisión. Útil si añades enterprise tier.
- **Blackboard**: agentes leen/escriben a estado compartido. Útil para colaboración asíncrona, complica debugging.

### Costos LLM en agentes 24/7 — playbook
1. **Model tiering (60-90% ahorro):** GPT-4o-mini / Haiku / Gemma local para clasificar; Claude Sonnet / GPT-4o solo para draft de respuesta delicada (1-2 estrellas).
2. **Prompt caching (Anthropic/OpenAI):** cachear el system prompt + voice clone examples → 50-90% off en tokens cacheados. Crítico cuando RAG context es estable por negocio.
3. **Batch API:** para tareas no time-sensitive (resúmenes mensuales, análisis de competencia) → 50% off, latencia hasta 24h. OK para reportes.
4. **Token budgets:** `max_tokens` en cada call, límite por task, cap mensual por tenant.
5. **Embeddings locales:** sentence-transformers o nomic-embed para RAG → $0/embedding.
6. **Gemma local (CRECE ya lo tiene en infra):** clasificación, extracción de entidades, NLP simple = $0. Reservar Claude/GPT para generación de respuesta.

Combinado: 70-85% reducción vs uso naive (Mavik Labs, Anthropic, Morph confirman cifras consistentes).

### Persistencia de estado del agente
- LangGraph Postgres checkpointer → estado serializable cada step.
- mem0 + pgvector para memoria de largo plazo por tenant (preferencias del dueño, voice samples, casos resueltos).
- Reusar la PostGIS de CRECE — solo añadir extensión vector y tablas de checkpoints.

### Boilerplates production a estudiar
- [wassim249/fastapi-langgraph-agent-production-ready-template](https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template) — el más completo encontrado (mem0, pgvector, Langfuse, Prometheus, JWT, fallback de modelos, HITL).
- [assada/agent_template](https://github.com/assada/agent_template) — más minimalista, útil si quieres entender el core sin overhead.
- [NicholasGoh/fastapi-mcp-langgraph-template](https://github.com/NicholasGoh/fastapi-mcp-langgraph-template) — si quieres exponer tus tools como MCP servers (para integrar con Claude Code / Cursor de los partners).

Fuentes: [LangGraph vs CrewAI vs Pydantic AI 2026 dev.to](https://dev.to/linou518/the-2026-ai-agent-framework-decision-guide-langgraph-vs-crewai-vs-pydantic-ai-b2h), [Speakeasy framework comparison](https://www.speakeasy.com/blog/ai-agent-framework-comparison), [Paxrel cost optimization](https://paxrel.com/blog-ai-agent-cost-optimization), [Mavik Labs LLM cost 2026](https://www.maviklabs.com/blog/llm-cost-optimization-2026), [Morph LLM cost](https://www.morphllm.com/llm-cost-optimization), [AWS caching](https://aws.amazon.com/blogs/database/optimize-llm-response-costs-and-latency-with-effective-caching/).

---

## I) Recomendación final

### Build vs Buy vs Partner — por componente

| Componente | Decisión | Justificación |
|---|---|---|
| Multi-tenant SaaS skeleton (auth, billing, RBAC, i18n) | **Buy/clone** ixartz/SaaS-Boilerplate (frontend) + benavlabs/FastAPI-boilerplate (backend) | MIT, maduros, ahorras 4-6 semanas |
| Agentic core (review responder + content) | **Buy/clone** wassim249/fastapi-langgraph-agent-production-ready-template | MIT, incluye HITL, mem0, observability — diff vs CRECE: CRECE no es agentic todavía |
| Scrapers IG/FB/TT/YT | **Reuse CRECE v2** | Ya construidos y probados con perfiles reales |
| NLP sentimiento + matriz polaridad | **Reuse CRECE v2** + adaptar diccionarios PyME | El framework de 53 reglas + pysentimiento + spaCy aplica directo, cambia el léxico |
| GBP integration | **Build** sobre google-api-python-client | No hay wrapper open-source maduro que valga; build directo en 3-5 días |
| Social scheduling (FB/IG/GBP posts) | **Buy/study** Shoutify (MIT) o brightbean-studio (MIT). Evitar Postiz (AGPL) | OAuth multi-plataforma es dolor, vale la pena copiar patrones |
| Voice cloning RAG | **Build** sobre pgvector (ya en stack) | Es el moat técnico, custom obligado |
| Frontend dashboard | **Reuse CRECE v2 patterns** + md-design-system | Ya hay 70% de alineación reportada |
| WhatsApp notifications | **Buy** WhatsApp Cloud API directo | API oficial, $0 fixed + costo por conversación |
| Listings management 50+ directorios | **Skip MVP, partner luego** (Yext reseller o Synup) | No vale construir; fase 2 |
| Uber Eats / DiDi data | **Skip MVP, manual upload v2** (Deliverect partner) | API solo via partners pagos, no en MVP |
| Crisis monitoring (X/news/menciones) | **Reuse CRECE v2 stack** (Apify+Scrapling+twscrape) | Ya está construido, solo cambia léxico de alertas |
| Generador de planes IA | **Reuse CRECE v2 triple capa** (Claude + Gemini + Gemma) | Adaptar prompts a contexto comercial vs político |
| Pago / billing | **Buy** Stripe (MX soportado) + integración con CFDI-Platform | Stripe MX maduro; CFDI-Platform genera factura |

### Top 3 repos a clonar
1. **[wassim249/fastapi-langgraph-agent-production-ready-template](https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template)** — El esqueleto agentic completo. Cambia ~30% (modelos de dominio, prompts, tools). MIT.
2. **[ixartz/SaaS-Boilerplate](https://github.com/ixartz/SaaS-Boilerplate)** — Frontend multi-tenant con Clerk auth, i18n, landing, billing. Ahorra ~4 semanas. MIT.
3. **[brightbeanxyz/brightbean-studio](https://github.com/brightbeanxyz/brightbean-studio)** — Social scheduling con GBP nativo. Estudiar y portar el OAuth manager. MIT.

### Top 3 riesgos a mitigar antes de escribir código

1. **Aprobación OAuth de Google Business Profile API.** Trámite real (formulario + security review), tarda 2-6 semanas en buen caso. **Acción:** iniciar el formulario de approval YA, antes de empezar a codear. Sin esto, el producto no funciona en producción multi-cliente.
2. **Compliance LFPDPPP + PROFECO.** Una multa de $2.3M MXN te apaga el proyecto. **Acción:** redactar privacy notice + terms of service con abogado especializado en datos personales MX antes del primer cliente; diseñar el agente con guardrails que impidan reseñas falsas, falsas atribuciones, o publicación sin aprobación humana en casos sensibles.
3. **Riesgo de voice cloning sonando genérico (= competidor barato).** Si el moat técnico es la voz del negocio, debes invertir en RAG fino y pruebas A/B con dueños reales desde sprint 1, no como afterthought. **Acción:** sprint 0 dedicado a ingeniería de prompts + pgvector + 5 negocios reales que aporten 10-20 respuestas históricas cada uno.

### Estimación de tiempo a MVP — 1 vertical (restaurantes), 1 plataforma (GBP)

Asumiendo equipo: 1 backend (CRECE veterano), 1 frontend, 1 IA/prompts, CEO/PM. Stack ya conocido (FastAPI+Next.js+PostGIS+Celery).

| Sprint | Duración | Entregable |
|---|---|---|
| Sprint 0 — Setup | 1 semana | Repo bootstrap, OAuth GBP request enviado, multi-tenant base de boilerplates clonados, infra Docker en Coolify |
| Sprint 1 — Onboarding & GBP | 2 semanas | Sign-up, OAuth GBP funcional, sync inicial reviews+posts+info, dashboard básico read-only |
| Sprint 2 — Análisis & scoring | 1.5 semanas | IPD-PyME score 0-10, sentiment de reviews (NLP CRECE adaptado), top 5 acciones recomendadas |
| Sprint 3 — Agente respuestas | 2 semanas | LangGraph + interrupt() + voice cloning RAG, dashboard de aprobación, publicación a GBP |
| Sprint 4 — Solicitud de reseñas | 1 semana | WhatsApp Cloud API + email, templates, link tracking, drip |
| Sprint 5 — Polish & piloto | 1.5 semanas | Onboarding asistido, billing Stripe, privacy notice, 5 restaurantes piloto reales |
| **TOTAL MVP** | **~9 semanas** | **Producto vendible a restaurante mexicano single-loc, GBP-only, en español, $799-999 MXN/mes** |

Riesgos al timeline:
- Si OAuth GBP tarda >6 semanas en approval, sprint 5 se mueve. **Mitigar:** usar OAuth en modo testing con 100 usuarios cap durante el piloto.
- Si voice cloning no rinde en sprint 3 → +1 semana adicional de iteración.
- Si compliance review dispara cambios → +1 semana.

**Estimación realista: 9 semanas optimista, 12 semanas razonable, 15 semanas conservador.**

---

## Apéndice — sources consultadas

- [Birdeye pricing 2026 RepliFast](https://www.replifast.com/blog/birdeye-pricing-2026)
- [Birdeye pricing oficial](https://birdeye.com/pricing/)
- [Podium vs Birdeye SocialPilot](https://www.socialpilot.co/reviews/comparison/birdeye-vs-podium)
- [Reputation management top 12 Inquirer](https://usa.inquirer.net/191823/best-reputation-management-software)
- [Yext pricing GetApp](https://www.getapp.com/marketing-software/a/yext/)
- [NiceJob G2 pricing](https://www.g2.com/products/nicejob/pricing)
- [Sortlist Mexico reputation](https://www.sortlist.com/s/reputation-management/mexico-mx)
- [GBP API limits oficial](https://developers.google.com/my-business/content/limits)
- [GBP OAuth implementation](https://developers.google.com/my-business/content/implement-oauth)
- [Yelp Fusion docs](https://docs.developer.yelp.com/)
- [Yelp Places API biz](https://business.yelp.com/data/products/places-api/)
- [TripAdvisor Content API](https://developer-tripadvisor.com/content-api/)
- [TripAdvisor FAQ](https://developer-tripadvisor.com/content-api/FAQ/)
- [AMVO estudio venta online 2025](https://blog.amvo.org.mx/publicaciones/estudio-sobre-venta-online-en-mexico-2025)
- [INEGI ICT PyMEs IFT](https://www.ift.org.mx/transformacion-digital/blog/impulsando-el-futuro-de-mexico-como-la-transformacion-digital-en-pymes-esta-cambiando-la-economia-y)
- [Konfio crecimiento](https://konfio.mx/blog/crecimiento-empresarial/comercio-electronico-en-mexico-2025-tendencias-y-estrategias-para-aumentar-ventas/)
- [Bind ERP](https://bind.com.mx/)
- [SendPulse PyMEs presupuesto](https://sendpulse.com/latam/blog/cuanto-necesitan-invertir-las-pymes-en-marketing-digital)
- [Shortway costos marketing PyME](https://shortway.com.mx/cuanto-cuesta/marketing-para-pymes)
- [LFPDPPP DOF](https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf)
- [Hogan Lovells nueva ley datos MX](https://www.hoganlovells.com/es/publications/mexicos-new-federal-data-protection-law-what-it-means-for-companies)
- [Lawwwing LFPDPPP guide](https://lawwwing.com/en/does-your-website-comply-with-mexicos-lfpdppp-a-practical-guide-for-digital-businesses/)
- [PROFECO multas 2025 KPMG](https://kpmg.com/mx/es/tendencias/2025/01/flash-monto-de-multas-de-profeco-en-2025.html)
- [PROFECO publicidad engañosa Independiente](https://elindependiente.mx/nacional/2025/09/20/publicidad-enganosa-profeco-multas-buen-fin/)
- [LangGraph HITL docs](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)
- [HITL LangGraph 2026 GrowwStacks](https://growwstacks.com/blog/human-in-the-loop-ai-agents-langgraph)
- [LangGraph CrewAI Pydantic AI 2026 dev.to](https://dev.to/linou518/the-2026-ai-agent-framework-decision-guide-langgraph-vs-crewai-vs-pydantic-ai-b2h)
- [Speakeasy framework comparison](https://www.speakeasy.com/blog/ai-agent-framework-comparison)
- [Paxrel agent cost optimization](https://paxrel.com/blog-ai-agent-cost-optimization)
- [Mavik Labs LLM cost 2026](https://www.maviklabs.com/blog/llm-cost-optimization-2026)
- [AWS LLM caching blog](https://aws.amazon.com/blogs/database/optimize-llm-response-costs-and-latency-with-effective-caching/)
- [Morph LLM cost optimization](https://www.morphllm.com/llm-cost-optimization)
- [ixartz SaaS-Boilerplate](https://github.com/ixartz/SaaS-Boilerplate)
- [benavlabs FastAPI-boilerplate](https://github.com/benavlabs/FastAPI-boilerplate)
- [wassim249 FastAPI LangGraph template](https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template)
- [NicholasGoh FastAPI MCP LangGraph](https://github.com/NicholasGoh/fastapi-mcp-langgraph-template)
- [von-development awesome-LangGraph](https://github.com/von-development/awesome-LangGraph)
- [gitroomhq postiz-app](https://github.com/gitroomhq/postiz-app)
- [TechSquidTV Shoutify](https://github.com/TechSquidTV/Shoutify)
- [brightbeanxyz brightbean-studio](https://github.com/brightbeanxyz/brightbean-studio)
- [google google-my-business-samples](https://github.com/google/google-my-business-samples)
- [dresenhista google_my_business](https://github.com/dresenhista/google_my_business)
- [Madeeha-Anjum multi-tenancy-system](https://github.com/Madeeha-Anjum/multi-tenancy-system)
- [Deliverect Telnet integration Uber Eats Rappi DiDi](https://www.deliverect.com/en/integrations/telnet)
- [Expansión Mexico delivery 2025](https://expansion.mx/tecnologia/2025/05/30/mexico-segundo-mercado-delivery-latinoamerica)
