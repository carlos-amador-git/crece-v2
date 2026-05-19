# Propuesta — App de Posicionamiento Digital para PyMEs MX

**Fecha:** 2026-05-07
**Origen:** Idea exploratoria del CEO. Producto **standalone** que reusa CRECE v2 como base de dominio y CFDI-Platform como **referencia arquitectónica** (patrones agentic, stack moderno). NO integra facturación ni se bundlea con CFDI-Suite.
**Estado:** Investigación pre-decisión. NO implementar nada hasta cerrar análisis.

---

## 1. Tesis inicial

CRECE v2 tiene ~60-70% del andamiaje reusable para un producto de **posicionamiento digital para PyMEs mexicanas** (restaurantes, lavaautos, tintorerías, dentistas, talleres, refaccionarias, etc.).

Lo que cambia respecto a CRECE:
- IPD (Índice de Penetración Digital electoral) → **IRD (Índice de Reputación Digital comercial)**
- Dirigentes políticos → **negocios locales** (con sucursales, horarios, GMB)
- Crisis política/veda INE → **gestión de reseñas negativas + respuesta automatizada**
- Plan de campaña electoral → **calendario de contenido + respuestas a reviews**
- Benchmarking vs partidos → **benchmarking vs competencia local en radio de N km**

Lo que se mantiene casi tal cual:
- Scrapers (X, IG, FB, TikTok, YT) — mismo stack Apify+Scrapling+Brightdata
- NLP / matriz polaridad — adaptar vocabulario electoral → vocabulario hospitality/servicio
- Multi-tenant + RLS — un negocio = un tenant
- Dashboards (treemap, stream, sunburst) — mismos componentes
- Plan-IA generator (Claude+Gemini+Gemma) — adaptar prompt templates

Lo que es **nuevo y crítico**:
- **Google Business Profile API** (antes GMB) — corazón del producto, no existe en CRECE
- **Aggregadores de reviews:** Google Maps, Yelp, TripAdvisor, Uber Eats, DiDi Food, Rappi, OpenTable, Booking, Foursquare
- **Local SEO citations:** NAP consistency (Name/Address/Phone)
- **Respuesta automática a reviews** con tono ajustable (agentic — aquí entra CFDI-Platform stack)
- **Geolocalización por sucursal** (PostGIS ya está)

---

## 2. Herencia arquitectónica — qué se toma de cada proyecto

### De CRECE v2 (lógica de dominio)
- Scrapers multi-plataforma (X, IG, FB, TikTok, YT) — Apify+Scrapling+Brightdata
- NLP de sentimiento + matriz de polaridad de 53 reglas (adaptar vocabulario)
- Dashboards multi-tenant con PostGIS (treemap, stream, sunburst)
- Plan-IA generator (Claude+Gemini+Gemma local) — adaptar prompts
- Sistema de alertas / war room
- Patrón de auditoría y NLP layer 2 (triangulación 3 LLMs)

### De CFDI-Platform (patrones arquitectónicos, NO funcionalidad)
- **Estructura agentic:** orquestación de agentes con responsabilidades claras
- **Stack moderno** que ya validaron en producción (revisar qué usa CFDI-Platform exactamente: ¿FastAPI agentes? ¿LangGraph? ¿Pydantic AI? ¿custom?)
- **Loop human-in-the-loop** para aprobaciones críticas
- **Patrones de observabilidad** del agente (trazas, costos por llamada LLM, retries)
- **Manejo de credenciales y secrets** entre agentes
- **Estructura de proyecto / monorepo** si aplica

### Resultado: app nueva con
- Dominio: el de CRECE adaptado a posicionamiento comercial
- Arquitectura: la base agentic de CFDI-Platform aplicada a respuesta automática a reseñas, generación de contenido, alertas inteligentes
- Stack: lo mejor de ambos, sin deuda técnica heredada

**No comparte:** base de datos, autenticación, dominio, ni facturación. Es un proyecto desde cero que **toma prestado** módulos de CRECE y **estudia** patrones de CFDI-Platform.

---

## 3. Mercado objetivo (hipótesis a validar)

| Segmento | Volumen MX aprox | Pain point |
|----------|------------------|-----------|
| Restaurantes | ~600K | Reviews negativas mata reservas; competencia agresiva en Google Maps |
| Lavaautos | ~30K | NAP inconsistente, sin GMB, dependen de boca a boca |
| Tintorerías | ~20K | Reseñas raras pero críticas, sin presencia digital |
| Dentistas/clínicas | ~250K | Compliance + reputación = cierra/abre consulta |
| Refaccionarias | ~80K | Catálogo + ubicación + confianza |
| Estéticas/barberías | ~150K | IG-driven, agendamiento + reviews |

Disposición a pagar techo realista: **$300-800 MXN/mes** SaaS directo para PyME individual; **$1,500-3,000/mes** para cadenas/franquicias con 3+ sucursales.

---

## 4. Preguntas abiertas (cerrar antes de cualquier código)

1. ¿Qué framework agentic usa CFDI-Platform exactamente? (LangGraph, Pydantic AI, OpenAI Agents SDK, custom — definir antes de elegir)
2. ¿Reusar módulos de CRECE como **librerías importables** o copiar y adaptar?
3. ¿APIs oficiales (Google, Yelp, TripAdvisor) o scraping? Mix probable.
4. ¿Modelo de pricing: por sucursal, por número de plataformas, flat?
5. ¿Quién compite ya en MX? (¿hay alguien hispanizado seriamente?)
6. ¿Qué tanto del NLP electoral de CRECE es transferible vs reentrenamiento total?
7. ¿Equivalente comercial de "veda" / compliance? (PROFECO, COFEPRIS, NOM-051, LFPDPPP sobre datos de reseñas)
8. ¿Monorepo (una carpeta con backend+frontend+agents) o multi-repo? (CFDI-Platform debe servir de referencia)
9. ¿Nombre tentativo del producto? (CRECE-Negocios, CRECE-PyME, otro)

---

## 5. Prompt de investigación para Claude Desktop / Gemini

> **Copia y pega esto en Claude Desktop o Gemini Pro 2.5 con búsqueda web activa:**

```
Estoy diseñando una app SaaS **standalone** de "posicionamiento digital" para
PyMEs mexicanas (restaurantes, lavaautos, tintorerías, dentistas, talleres).
El producto agrega reseñas de Google Maps, Yelp, TripAdvisor, Uber Eats,
DiDi Food, Rappi, redes sociales (IG, FB, TikTok), genera un Índice de
Reputación Digital, y responde reseñas con IA (con aprobación humana opcional).

Tengo dos proyectos previos cuya **arquitectura** quiero combinar (NO
integrar funcionalmente — son proyectos separados que sirven de cantera):

1. **CRECE v2** (plataforma electoral) — me da la **lógica de dominio**:
   - Scrapers multi-plataforma (X, IG, FB, TikTok, YT) con stack
     Apify+Scrapling+Brightdata
   - NLP de sentimiento (pysentimiento + spaCy + matriz polaridad 53 reglas)
   - Dashboards multi-tenant con PostGIS
   - Generador de planes con triangulación Claude+Gemini+Gemma local
   - Stack: FastAPI async + Next.js 14 App Router + PostgreSQL 16 + PostGIS +
     Celery + Redis + MinIO

2. **CFDI-Platform** (facturación electrónica agentic mexicana) — me da los
   **patrones arquitectónicos**:
   - Estructura de agentes orquestados
   - Loop human-in-the-loop
   - Observabilidad de agentes (trazas, costos LLM, retries)
   - Manejo de credenciales entre agentes
   - Patrón monorepo / estructura de proyecto

   NOTA: NO quiero integrar la facturación. Solo replicar los patrones
   agentic de cómo construyeron la app.

Investiga y entrégame:

A) **Competencia global y MX:**
   - Birdeye, Podium, Reputation.com, Yext, NiceJob, Grade.us, Trustpilot
   - Buffer, Hootsuite, Sprout Social, Later (social-only)
   - Players hispanos/MX: ¿existen? ¿qué cobran? ¿qué les falta?
   - Pricing tiers, features matrix, posicionamiento.

B) **Repos open-source clonables o como base** (preferir MIT/Apache, evitar AGPL/GPL):
   - Review aggregation / sentiment dashboards
   - Google Business Profile API wrappers (Python preferido)
   - Local SEO / NAP consistency checkers
   - Social media schedulers headless (alternativa a Buffer)
   - Reputation scoring algorithms publicados
   - Multi-tenant SaaS boilerplates en FastAPI+Next.js
   Por cada repo: stars, licencia, último commit, fit con stack FastAPI+Next.js+PostGIS, qué piezas reusar.

C) **APIs y costos:**
   - Google Business Profile API (cuotas, costos, OAuth scopes requeridos)
   - Yelp Fusion API (¿sigue activa para reviews? últimas restricciones)
   - TripAdvisor Content API
   - Uber Eats / DiDi Food / Rappi: ¿hay API o solo scraping?
   - Costos mensuales típicos para 100, 1000, 10000 negocios monitoreados.

D) **Mercado mexicano PyME:**
   - Estudios de penetración digital PyME MX recientes (INEGI, AMIPCI, AMVO)
   - Disposición a pagar SaaS por ticket promedio
   - Casos de éxito de SaaS B2B PyME MX (Konfio, Bind ERP, Clip, Kueski)
   - Canales de adquisición típicos (cámaras, asociaciones, franquicias)

E) **Compliance MX:**
   - LFPDPPP aplicado a datos de reseñas (¿requiere consentimiento del autor?)
   - PROFECO sobre publicidad y reseñas falsas
   - COFEPRIS si hay clientes salud/clínicas
   - Términos de servicio de Google Maps, Yelp, etc. respecto a scraping y republicación

F) **Arquitectura técnica - decisiones críticas:**
   - ¿Scraping vs API oficial? Matriz por plataforma con costo/riesgo/cobertura.
   - ¿Cómo hacer respuesta automática sin caer en spam o detección como bot?
   - Patrones de "human-in-the-loop" para aprobación de respuestas con IA
   - Embeddings/RAG para responder en tono del negocio (cada cliente con su voz)

G) **Modelo de negocio:**
   - Pricing por sucursal vs flat vs per-feature
   - Comparable: ¿qué cobra Birdeye en US vs lo que un restaurante MX puede pagar?
   - Onboarding: ¿qué fricción es aceptable para un dueño de tintorería de 60 años?
   - Canales de adquisición B2B PyME MX (cámaras, asociaciones, franquicias, agencias)

H) **Patrones agentic de referencia:**
   - LangGraph vs Pydantic AI vs OpenAI Agents SDK vs CrewAI vs Autogen — comparar para este caso de uso
   - Patrones de orquestación: supervisor + workers, swarm, hierarchical
   - Cómo manejar costos LLM en agentes que corren 24/7 (cache, modelos por nivel)
   - Persistencia de estado del agente (Redis, Postgres, file)
   - Boilerplates open-source de apps agentic en producción que pueda estudiar

Entrégame un reporte con secciones A-G, con fuentes citadas (URLs), tabla
comparativa de competidores, lista priorizada de repos a clonar, y una
recomendación final de "build vs buy vs partner" para cada componente.

Formato de salida: markdown con tablas. Profundidad: ~3000-5000 palabras.
```

---

## 6. Próximos pasos sugeridos (NO ejecutar sin luz verde)

1. Correr el prompt de §5 en Claude Desktop **y** Gemini, comparar resultados.
2. Disparar `deep-research` agent en paralelo con prompt similar (background).
3. Auditar el repo de CFDI-Platform para extraer el patrón agentic exacto (qué framework, qué estructura, qué orquestación).
4. Auditar CRECE v2 para listar módulos extraíbles como librerías reusables.
5. Cerrar preguntas abiertas de §4 con datos.
6. Definir nombre + repo nuevo (sugerencia: `crece-negocios` o `mdc-posicionamiento`).
7. Si va, escribir PRD formal con `/sc:brainstorm` + `/requirements`.
8. Si va, hacer un MVP de 1 plataforma (Google Business Profile + 1 vertical, ej. restaurantes) antes de generalizar.

---

## 7. Riesgos identificados

- **Scope creep:** CRECE no terminó piloto Piña (gate cerrado pero F-06..F-16 abiertos). Abrir nuevo producto sin terminar el actual = receta para incendio.
- **Scraping legal:** Google Maps TOS prohíben scraping comercial. APIs oficiales tienen cuotas que escalan caro.
- **Comoditización:** Birdeye+Podium ya valen $1B+ cada uno. ¿Ventana real en MX o llegamos tarde?
- **Distracción CFDI-Platform:** ese sí está generando ingreso. Posicionamiento es bet, no caja.

---

**Decisión pendiente del CEO:** ¿avanzamos a investigación profunda (paso 1-2) o pausamos hasta cerrar gate piloto CRECE?
