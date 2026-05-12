# CRECE v2.0 — Plataforma de Inteligencia Electoral y Social

## Qué es
Plataforma de inteligencia política para Movimiento Ciudadano CDMX. Reemplaza sistema Oracle APEX anterior.
Cliente: ConsultoríaMD (relación de 4+ años con MC).

## Stack
- **Backend**: FastAPI (Python 3.12+), SQLAlchemy 2.0 async, PostgreSQL 16 + PostGIS 3.4
- **Frontend**: Next.js 14+ (App Router), TypeScript, Tailwind CSS, shadcn/ui, MapLibre GL JS, Recharts
- **Workers**: Celery + Redis (scrapers, NLP, IA)
- **Storage**: MinIO (S3-compatible)
- **Deploy**: Docker Compose → Coolify sobre VPS

## Estructura
```
crece-v2/
├── backend/           # FastAPI app
│   ├── app/
│   │   ├── api/v1/    # Endpoints REST
│   │   ├── core/      # Config, auth, DB
│   │   ├── models/    # SQLAlchemy (user, dirigente, social, electoral, benchmark, plan_ia)
│   │   ├── schemas/   # Pydantic v2
│   │   ├── services/  # Lógica de negocio (diagnostico, sentiment, plan_generator)
│   │   ├── scrapers/  # Scrapers por plataforma (twitter, ig, fb, tiktok, yt)
│   │   ├── nlp/       # pysentimiento + spaCy
│   │   └── workers/   # Celery tasks
│   ├── migrations/    # Alembic
│   ├── scripts/       # seed.py
│   └── tests/
├── frontend/          # Next.js dashboard
│   └── src/
│       ├── app/       # App Router pages
│       ├── components/ # UI components
│       └── lib/       # API client, hooks, utils
├── docker/            # Nginx, Postgres init, Coolify config
├── docker-compose.yml
├── docker-compose.prod.yml
└── Makefile
```

## Comandos
```bash
make dev          # Levantar entorno desarrollo
make build        # Build containers
make migrate      # Alembic upgrade head
make seed         # Poblar datos iniciales
make test         # Pytest
make logs         # Ver logs
make down         # Detener todo
make reset-db     # Reset completo
```

## Módulos Fase 1
1. **Diagnóstico Digital**: Índice de Penetración Digital (IPD) 0-10 por dirigente
2. **Monitoreo Social**: Scrapers + NLP (pysentimiento, spaCy) + alertas de crisis
3. **Benchmarking**: Comparación vs competidores y MC nacional
4. **Planes IA**: Generación con Claude API (streaming SSE) + Ollama local

## Módulos Fase 2 (futuro)
- WhatsApp Campaign Manager
- Smart Canvassing (rutas optimizadas)
- Content Factory con IA
- CRM Político + Voter Scoring
- Participación Ciudadana (Decidim)
- Blindaje Legal

## Reglas importantes
- Coordenadas México: lat 14.5-32.7, lon -118.4 a -86.7. SRID 4326.
- NUNCA inventar datos electorales. Solo datos reales del INE.
- Sentimiento normalizado por plataforma (Twitter skews negative, Instagram positive).
- Todo contenido generado con IA debe tener campo `modelo_ia` poblado.
- Cumplimiento INE: modo veda, trazabilidad de gastos, etiquetado IA.

## Plan de referencia
`/Users/marxchavez/Downloads/Reporte_Consolidado_CRECE_v2_Final.md`

## Perfiles de prueba
- **Alejandro Piña** (IPD ~4/10): Twitter 3.1K, Instagram 2.2K, Facebook 1.8K, sin TikTok/YT
- **Rafael Solano** (IPD ~2/10): Instagram personal, LinkedIn 170, sin presencia política digital


---

## REGLAS DE CALIDAD (LEER ANTES DE ESCRIBIR CÓDIGO)

### Filosofía: Probar primero, decidir después
1. NUNCA escribir código custom cuando existe una librería activa que hace lo mismo.
2. NUNCA crear mocks, stubs, o datos inventados. Si algo no funciona, reportarlo como blocker.
3. NUNCA reimplementar lo que una librería ya resuelve. Usar la librería, wrapear si es necesario.
4. Cada pieza de código debe probarse contra datos reales antes de hacer commit.

### Antes de escribir código, SIEMPRE preguntarse:
- ¿Existe una librería pip/npm que ya haga esto? → USARLA.
- ¿El plan de investigación especificó una herramienta? → USAR ESA, no inventar alternativa.
- ¿Puedo probar esto contra datos reales de Piña/Solano? → SI NO, no sirve.
- ¿Estoy escribiendo más de 50 líneas para algo que una librería hace en 5? → PARAR.

### Patrón de resiliencia para scrapers/integraciones externas
```
Intento 1: Librería probada (ej: instaloader para Instagram)
    ↓ si falla (rate limit, cambio de API, etc.)
Intento 2: Fallback custom (código httpx/playwright propio)
    ↓ si falla
Intento 3: Apify/API de pago como último recurso
```

### Librerías OBLIGATORIAS (no reinventar)
| Plataforma | Librería primaria | Fallback | NO hacer |
|---|---|---|---|
| Twitter/X | twscrape (con cuentas auth) | httpx syndication | Código custom de parsing HTML |
| Instagram | instaloader v4.15 | httpx público | Reimplementar login flow |
| Facebook | facebook_page_scraper | httpx + beautifulsoup | Código custom con cookies |
| TikTok | TikTok-Api v7.3.2 (Playwright) | yt-dlp --flat-playlist | httpx sin Playwright |
| YouTube | scrapetube v2.6 | YouTube Data API v3 | Solo API sin fallback |
| Bluesky | AT Protocol (atproto SDK) | — | Ignorar esta plataforma |

### Lo que NO es aceptable
- Código que "compila pero nunca se probó contra datos reales"
- Funciones que retornan listas vacías o ceros como placeholder
- Tests que pasan porque mockean todo y no validan nada real
- Reimplementar parseo de HTML/JSON que una librería ya hace
- Ignorar librerías del plan para "ir más rápido" con código custom

### Cuando algo no funcione
NO inventar un workaround silencioso. En vez de eso:
1. Documentar QUÉ falló y POR QUÉ en un comentario `# BLOCKER: ...`
2. Proponer la siguiente alternativa del stack de resiliencia
3. Preguntar antes de implementar algo que no estaba en el plan


## REGLAS DE CALIDAD (OBLIGATORIAS — LEER ANTES DE CADA TAREA)

### Filosofía: Calidad > Velocidad
Este proyecto prioriza código que FUNCIONE CON DATOS REALES sobre código que compile rápido.
NO se acepta trabajo que "se ve bien en tests mock" pero nunca se probó contra APIs reales.

### Regla 1: NUNCA escribir código custom cuando existe una librería probada
Si el plan dice "usar librería X", USAR librería X. No escribir un wrapper custom que
reimplemente lo que la librería ya hace. Si la librería no sirve, DECIRLO y pedir
autorización para cambiar de approach — no inventar una solución alternativa silenciosamente.

### Regla 2: NUNCA usar datos mock como sustituto de verificación real
- Los tests unitarios pueden usar mocks para no depender de APIs externas en CI.
- ANTES de dar algo por terminado, probar con datos reales (perfiles de Piña/Solano).
- Si no se puede probar (falta API key, falta cuenta), DECIRLO como blocker.
- NUNCA reportar algo como "implementado" si solo funciona con datos inventados.

### Regla 3: Pedir autorización antes de desviarse del plan
Si durante la implementación descubres que el plan no funciona (librería rota, API cambiada,
enfoque incorrecto), PARAR y reportar:
- Qué dice el plan
- Qué encontraste que no funciona
- Qué alternativas propones
- Esperar autorización antes de continuar
NO tomar decisiones de arquitectura por tu cuenta.

### Regla 4: Reportar estado honestamente
Al terminar cada tarea, reportar con esta tabla:

| Componente | Estado real | Probado con datos reales | Blocker |
|---|---|---|---|
| Scraper X | Funcional | Sí, @alejandro.pinha | - |
| Scraper Y | Stub | No, falta API key | B-001 |

"Funcional" = ejecuté el código y obtuve datos reales de una cuenta real.
"Stub" = compila pero no se ha probado contra una API real.
NO usar "Implementado" si realmente es un stub.

### Regla 5: Un commit por funcionalidad verificada
No hacer commits masivos de 10 features a la vez.
Un commit = una funcionalidad que funciona y fue verificada.
Correcto: "feat: Instagram scraper con instaloader — probado @alejandro.pinha"
Incorrecto: "feat: 5 scrapers + 3 modelos + NLP upgrade + 22 E2E tests"

### Regla 6: Leer el plan completo ANTES de empezar
Antes de escribir la primera línea de código:
1. Leer CLAUDE.md completo
2. Leer el archivo de sprint/tarea asignado
3. Leer docs/ARQUITECTURA-INTEGRADA.md si es relevante
4. Si algo del plan no tiene sentido, PREGUNTAR antes de implementar

### Perfiles de prueba obligatorios para scrapers
- Instagram: @alejandro.pinha (público, ~2,231 seguidores)
- Twitter: @Alejandro_Pinha (~3,100 seguidores)
- Instagram: @rafasolanoperez (público, contenido personal)
- Toda funcionalidad de scraping DEBE probarse contra estos perfiles.

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current
