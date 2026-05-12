# CRECE v2.0 -- Documento Tecnico

**Version:** 2.0.0
**Fecha:** Abril 2026
**Audiencia:** Desarrolladores, DevOps, integradores
**Clasificacion:** Interno -- MD Consultoria TI

---

## Tabla de Contenidos

1. [Vision General](#1-vision-general)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Servicios Docker](#3-servicios-docker)
4. [Base de Datos](#4-base-de-datos)
5. [API REST](#5-api-rest)
6. [Autenticacion y Autorizacion](#6-autenticacion-y-autorizacion)
7. [Pipeline de IA y NLP](#7-pipeline-de-ia-y-nlp)
8. [Scrapers de Redes Sociales](#8-scrapers-de-redes-sociales)
9. [Workers y Tareas Asincronas](#9-workers-y-tareas-asincronas)
10. [Despliegue en Produccion](#10-despliegue-en-produccion)
11. [Configuracion de Variables de Entorno](#11-configuracion-de-variables-de-entorno)
12. [Comandos de Operacion](#12-comandos-de-operacion)
13. [Problemas Conocidos](#13-problemas-conocidos)

---

## 1. Vision General

CRECE v2.0 es una plataforma de inteligencia electoral y social construida para Movimiento Ciudadano CDMX. Reemplaza el sistema anterior basado en Oracle APEX, migrando a una arquitectura moderna de contenedores con separacion clara entre backend (FastAPI), frontend (Next.js) y workers (Celery).

El sistema cubre cuatro modulos principales en Fase 1:

- **Diagnostico Digital** -- Calculo del Indice de Penetracion Digital (IPD) por dirigente.
- **Monitoreo Social** -- Scrapers multiplataforma + analisis NLP de sentimiento y entidades.
- **Benchmarking** -- Comparacion de metricas contra competidores y promedios nacionales.
- **Planes IA** -- Generacion de planes estrategicos con Ollama (Gemma 3 12B), Claude API o Gemini.

---

## 2. Arquitectura del Sistema

### 2.1 Diagrama General

```
                           +-----------+
                           |  Traefik  |
                           | (Coolify) |
                           +-----+-----+
                                 |
                    TLS (Let's Encrypt)
                                 |
              +------------------+------------------+
              |                                     |
       +------+------+                     +--------+--------+
       |   Nginx     |                     |   Next.js 15    |
       | (rate limit,|                     |   (standalone)  |
       |  SSE, WS)   |                     |   puerto 3000   |
       +------+------+                     +-----------------+
              |
       +------+------+
       |  FastAPI     |
       |  (uvicorn)   |
       |  4 workers   |
       |  puerto 8000 |
       +------+------+
              |
   +----------+----------+----------+
   |          |          |          |
+--+---+ +---+----+ +---+----+ +---+----+
| Post | | Redis  | | MinIO  | | Ollama |
| GIS  | |   7    | |  (S3)  | | Gemma3 |
| 16   | |        | |        | | 12B    |
+------+ +--------+ +--------+ +--------+

       +-------------+-------------+
       |             |             |
  +----+----+  +-----+-----+  +---+---+
  | Celery  |  | Celery    |  | n8n   |
  | Worker  |  | Beat      |  | (6 WF)|
  | 4 conc. |  | scheduler |  +-------+
  +---------+  +-----------+
```

### 2.2 Flujo de Datos

```
Dirigente registrado
       |
       v
Scraper (Celery) --> Redes Sociales (IG, X, FB, TikTok, YT, Bluesky)
       |
       v
NLP Pipeline --> pysentimiento (8 modelos) + spaCy NER
       |
       v
PostgreSQL (metricas, sentimiento, posts)
       |
       v
Diagnostico (IPD 0-10) + Benchmarking + Alertas
       |
       v
Plan IA (Ollama/Claude/Gemini) --> Streaming SSE al frontend
       |
       v
Dashboard Next.js (MapLibre + Recharts + Zustand)
```

### 2.3 Stack Tecnologico

| Capa | Tecnologia | Version |
|------|-----------|---------|
| Backend | FastAPI, SQLAlchemy 2.0 async, Pydantic v2 | Python 3.12 |
| Frontend | Next.js (App Router), TypeScript, Tailwind CSS, shadcn/ui | Next.js 15 |
| Estado frontend | Zustand | -- |
| Graficas | Recharts | -- |
| Mapas | MapLibre GL JS | -- |
| Base de datos | PostgreSQL + PostGIS + pgvector | 16 + 3.4 |
| Cache/broker | Redis | 7 |
| Workers | Celery (3 colas) | -- |
| Storage | MinIO (S3-compatible) | latest |
| IA local | Ollama (Gemma 3 12B) | -- |
| IA remota | Claude API (opcional), Gemini CLI (planificacion) | -- |
| Proxy | Nginx | -- |
| Automatizacion | n8n (6 workflows, 30+ nodos) | -- |
| Deploy | Docker Compose via Coolify (Traefik + Let's Encrypt) | -- |
| Migraciones | Alembic | -- |

---

## 3. Servicios Docker

El archivo `docker-compose.coolify.yml` define 7 servicios para produccion. En desarrollo se usa `docker-compose.yml` con 8 servicios (incluye Flower para monitoreo de Celery).

### 3.1 Tabla de Servicios

| # | Servicio | Imagen | Configuracion clave | Puerto (dev) |
|---|----------|--------|---------------------|-------------|
| 1 | db | postgis/postgis:16-3.4 | shared_buffers=256MB, max_connections=100 | 5438:5432 |
| 2 | redis | redis:7-alpine | maxmemory 256mb, allkeys-lru, appendonly yes | 6383:6379 |
| 3 | minio | minio/minio:latest | console en :9001 | 9006:9000, 9007:9001 |
| 4 | backend | Build desde ./backend | 4 workers uvicorn, uvloop, httptools | 8002:8000 |
| 5 | celery-worker | Build desde ./backend | concurrency=4, colas: default,scrapers,nlp | -- |
| 6 | celery-beat | Build desde ./backend | schedule en /tmp/celerybeat-schedule | -- |
| 7 | frontend | Build desde ./frontend | Next.js standalone (node server.js) | 3001:3000 |
| 8* | flower | mher/flower:2.0 | Solo desarrollo | 5555:5555 |

### 3.2 Red y Volumenes

- **Red:** `crece-net` (bridge). Todos los servicios se comunican por nombre de contenedor.
- **Volumenes persistentes:**
  - `crece-postgres-data` -- Datos de PostgreSQL
  - `crece-redis-data` -- AOF de Redis
  - `crece-minio-data` -- Objetos S3

### 3.3 Dependencias entre Servicios

```
db (healthcheck: pg_isready)
  |
  +---> backend (espera db + redis)
  |       |
  |       +---> frontend (espera backend)
  |
  +---> celery-worker (espera db + redis)
  +---> celery-beat (espera db + redis)

redis (healthcheck: redis-cli ping)
  |
  +---> backend
  +---> celery-worker
  +---> celery-beat
  +---> flower
```

---

## 4. Base de Datos

### 4.1 Resumen

- **Motor:** PostgreSQL 16 con extensiones PostGIS 3.4 y pgvector
- **Migraciones:** Alembic (excluye esquemas tiger de PostGIS)
- **Aislamiento:** Politicas RLS (Row-Level Security) por `dirigente_id`
- **Total de tablas:** 37

### 4.2 Diagrama ER (Modelos Principales)

```
+------------------+       +--------------------+       +------------------+
|      User        |       |    Dirigente       |       |  SocialProfile   |
+------------------+       +--------------------+       +------------------+
| id (PK)          |       | id (PK)            |<------| id (PK)          |
| email            |       | full_name          |       | dirigente_id (FK)|
| hashed_password  |       | partido            |       | platform         |
| role             |------>| distrito           |       | username         |
| dirigente_id(FK) |       | cargo              |       | followers        |
| is_active        |       | created_at         |       | engagement_rate  |
+------------------+       +--------------------+       +------------------+
                                   |                            |
                    +--------------+----------+                 |
                    |              |          |                  |
             +------+---+  +------+---+ +----+------+   +------+------+
             | PlanIA   |  |Benchmark |  |Electoral  |   | SocialPost  |
             +----------+  +----------+ +-----------+   +-------------+
             | id (PK)  |  |Competidor|  |SeccionEl. |   | id (PK)     |
             | dirig_id |  |Comp.Prof.|  |Intencion  |   | profile_id  |
             | modelo_ia|  +----------+ |Voto       |   | content     |
             | status   |               +-----------+   | sentiment   |
             +----------+                               | posted_at   |
                                                        +-------------+
                                                               |
                                                        +------+------+
                                                        | Sentiment   |
                                                        | Analysis    |
                                                        +-------------+
```

### 4.3 Catalogo de Modelos (26 modelos SQLAlchemy)

| Modulo | Modelos | Descripcion |
|--------|---------|-------------|
| Usuarios | `User`, `ApiKey` | Autenticacion, roles, API keys para integraciones |
| Dirigentes | `Dirigente` | Entidad central, vincula todo el grafo politico |
| Social | `SocialProfile`, `SocialPost`, `SentimentAnalysis`, `MetricaSocial` | Perfiles, publicaciones, sentimiento, metricas agregadas |
| Electoral | `SeccionElectoral`, `IntencionVoto`, `GastoElectoral`, `AlertaCompliance` | Secciones electorales, encuestas, control de gastos INE |
| Benchmark | `Competidor`, `CompetidorSocialProfile` | Competidores politicos y sus perfiles sociales |
| Planes IA | `PlanIA`, `ContenidoGenerado`, `ContenidoPieza`, `IaContentRegistry` | Planes generados por IA, piezas de contenido, registro |
| CRM | `Ciudadano`, `CrmInteraccion`, `VoterScore`, `VoterScoreIntegration` | Ciudadanos, interacciones, puntuacion de votante |
| Campanas | `Campana`, `CampanaMensaje`, `CampanaSegmento`, `Campaign` | Campanas de difusion, segmentacion, mensajes |
| Territorio | `Encuesta`, `Evento`, `EventoAsistente`, `RutaCanvassing`, `PuntoRuta` | Encuestas de campo, eventos, rutas de recorrido |
| Gobierno | `ProgramaSocial`, `ProgramaBeneficiario`, `Organizacion` | Programas sociales, beneficiarios |
| Solicitudes | `SolicitudCiudadana`, `SeguimientoSolicitud` | Atencion ciudadana |
| Alertas | `AlertaCrisis` | Alertas de crisis en redes sociales |

### 4.4 Extensiones PostgreSQL

| Extension | Uso |
|-----------|-----|
| PostGIS 3.4 | Columnas geometry (SRID 4326), consultas espaciales ST_* |
| pgvector | Tabla de embeddings con indice HNSW (384 dimensiones) |

---

## 5. API REST

### 5.1 Estructura General

Todos los endpoints viven bajo el prefijo `/api/v1/`. La documentacion interactiva Swagger esta disponible en `/docs` (deshabilitada en produccion).

### 5.2 Tabla de Routers (29 routers)

| Prefijo | Tag | Descripcion |
|---------|-----|-------------|
| `/health` | health | Health check, readiness |
| `/auth` | auth | Login, registro, forgot-password, refresh token |
| `/dirigentes` | dirigentes | CRUD dirigentes, diagnostico IPD |
| `/social` | social | Perfiles sociales, publicaciones, sentimiento |
| `/electoral` | electoral | Secciones electorales, intencion de voto |
| `/benchmark` | benchmark | Competidores, comparacion de metricas |
| `/planes` | planes | Generacion de planes IA (SSE streaming) |
| `/ciudadanos` | ciudadanos | CRUD ciudadanos, busqueda |
| `/eventos` | eventos | Eventos, asistentes, geolocalizacion |
| `/programas` | programas | Programas sociales, beneficiarios |
| `/organizaciones` | organizaciones | Organizaciones aliadas |
| `/encuestas` | encuestas | Encuestas de campo |
| `/metricas-sociales` | metricas-sociales | Metricas agregadas por plataforma |
| `/geo` | geo | Consultas geoespaciales, mapas |
| `/voter-scoring` | voter-scoring | Puntuacion de votantes |
| `/contenido` | contenido | Contenido generado por IA |
| `/blindaje` | blindaje | Blindaje legal, compliance INE |
| `/campanas` | campanas | Campanas de difusion |
| `/canvassing` | canvassing | Rutas de canvassing, puntos |
| `/participacion` | participacion | Participacion ciudadana |
| `/campaigns` | campaigns | Integracion de campanas (n8n) |
| `/content` | content-factory | Fabrica de contenido IA |
| `/alerts` | alerts | Alertas de crisis |
| `/crm` | crm | Integraciones CRM |
| `/webhooks` | webhooks | Webhooks para n8n y externos |
| `/api-keys` | api-keys | Gestion de API keys |
| `/dashboard` | dashboard | Overview, KPIs, metricas del dashboard |
| `/osint` | osint | Investigacion OSINT (Sherlock) |
| `/bot-detection` | bot-detection | Deteccion de bots en redes |

### 5.3 Conteo

Aproximadamente **80+ endpoints REST** distribuidos en 29 routers.

---

## 6. Autenticacion y Autorizacion

### 6.1 Mecanismo

- **JWT (JSON Web Tokens)** con claim `role` y `dirigente_id`.
- **Algoritmo:** Configurable via `JWT_ALGORITHM` (por defecto HS256).
- **Expiracion:** Configurable via `JWT_EXPIRE_MINUTES`.
- **Endpoint de login:** `POST /api/v1/auth/login` (OAuth2PasswordBearer).

### 6.2 Roles del Sistema

| Rol | Permisos |
|-----|----------|
| `admin` | Acceso total. Gestion de usuarios, configuracion global. |
| `analyst` | Lectura de todos los datos. Generacion de planes IA. Benchmark. |
| `field_operator` | CRUD ciudadanos, eventos, canvassing, encuestas. Datos territoriales. |
| `viewer` | Solo lectura. Dashboards y reportes. |

### 6.3 Filtrado Automatico

El claim `dirigente_id` en el JWT permite filtrado automatico de datos. Un usuario con `dirigente_id=5` solo ve datos asociados a ese dirigente (reforzado por RLS en PostgreSQL).

### 6.4 API Keys

Para integraciones externas (n8n, webhooks), el sistema soporta API keys gestionadas desde `/api/v1/api-keys`. Las keys se validan en un middleware independiente del flujo JWT.

---

## 7. Pipeline de IA y NLP

### 7.1 Proveedores de IA

El sistema soporta tres proveedores configurables via `AI_PROVIDER`:

| Proveedor | Modelo | Uso | Costo |
|-----------|--------|-----|-------|
| Ollama (local) | Gemma 3 12B | Generacion de planes, contenido, datos sensibles | $0 |
| Claude API | claude-sonnet/opus | Estrategia, analisis complejos (opcional) | Por token |
| Gemini CLI | gemini-2.5-pro | Planificacion, revision cruzada | Por token |

La variable `AI_PROVIDER` acepta: `ollama`, `claude`, `gemini`. El backend selecciona automaticamente el servicio correspondiente en `plan_generator.py` y `content_factory.py`.

### 7.2 Indice de Penetracion Digital (IPD)

El IPD es el indicador principal del sistema. Se calcula en tiempo real (no se almacena) a partir de cuatro componentes:

```
IPD (0-10) = Seguidores(30%) + Engagement(30%) + Frecuencia(20%) + Cobertura(20%)
```

**Pesos por plataforma:**

| Plataforma | Peso | Benchmark Seguidores | Benchmark Engagement |
|------------|------|---------------------|---------------------|
| Twitter/X | 30% | 50,000 | 2.0% |
| Facebook | 25% | 100,000 | 3.0% |
| Instagram | 20% | 50,000 | 4.0% |
| TikTok | 10% | 30,000 | 6.0% |
| YouTube | 10% | 20,000 | 3.0% |
| Bluesky | 5% | 5,000 | 3.0% |

Los benchmarks representan figuras politicas mexicanas de nivel medio. Un IPD de 10 equivale a presencia optima en todas las plataformas.

### 7.3 Pipeline NLP

```
Post de red social
       |
       v
pysentimiento (8 modelos robertuito, entrenados en espanol)
       |
       +---> Sentimiento (positivo/negativo/neutro)
       +---> Emocion (alegria, enojo, miedo, etc.)
       +---> Hate speech detection
       +---> Ironia detection
       |
       v
spaCy es_core_news_lg
       |
       +---> NER (personas, organizaciones, lugares)
       +---> Clasificacion tematica zero-shot
       |
       v
Normalizacion por plataforma
       |  (Twitter tiende negativo, Instagram positivo)
       v
Almacenamiento en SentimentAnalysis + alertas de crisis
```

---

## 8. Scrapers de Redes Sociales

### 8.1 Tabla de Scrapers

| Plataforma | Libreria | Autenticacion | Notas |
|------------|----------|---------------|-------|
| Instagram | ensta (Guest) | No | Perfiles publicos. Rate limit agresivo. |
| Twitter/X | Scweet v5.2 | Cookie `auth_token` | Requiere cuenta activa. |
| Facebook | curl-cffi | No (TLS fingerprint Chrome) | Paginas publicas unicamente. |
| TikTok | yt-dlp | No | `--flat-playlist` para metadatos. |
| YouTube | scrapetube | No | Canal + videos recientes. |
| Bluesky | httpx (AT Protocol) | No | API publica AT Protocol. |

### 8.2 Patron de Resiliencia

Cada scraper sigue un patron de fallback de tres niveles:

```
Nivel 1: Libreria principal (tabla anterior)
    |  si falla (rate limit, API change)
    v
Nivel 2: Fallback custom (httpx/playwright)
    |  si falla
    v
Nivel 3: Apify/API de pago (ultimo recurso)
```

### 8.3 Colas Celery

Los scrapers se ejecutan en la cola `scrapers` con concurrencia controlada para evitar rate limiting. Las tareas de NLP se procesan en la cola `nlp`. Tareas generales usan la cola `default`.

---

## 9. Workers y Tareas Asincronas

### 9.1 Configuracion Celery

| Parametro | Valor |
|-----------|-------|
| Broker | Redis (db 1) |
| Result backend | Redis (db 2) |
| Concurrencia (worker) | 4 en produccion, 2 en desarrollo |
| Colas | `default`, `scrapers`, `nlp` |
| Scheduler | celery-beat con archivo en `/tmp/celerybeat-schedule` |

### 9.2 Tareas Programadas

Celery Beat ejecuta tareas periodicas definidas en la configuracion del worker:

- Scraping de perfiles registrados (frecuencia configurable por dirigente)
- Analisis NLP de publicaciones pendientes
- Calculo de metricas agregadas
- Verificacion de alertas de crisis

### 9.3 Automatizacion con n8n

El sistema incluye 6 workflows de n8n con mas de 30 nodos, conectados via webhooks al backend:

- Notificaciones de alertas de crisis
- Sincronizacion de metricas
- Triggers de generacion de contenido
- Reportes automaticos

La autenticacion entre n8n y el backend se realiza con `N8N_WEBHOOK_SECRET`.

---

## 10. Despliegue en Produccion

### 10.1 Diagrama de Despliegue

```
+-------------------------------------------------------+
|                     VPS (Coolify)                      |
|                                                        |
|  +----------+    +----------------------------------+  |
|  | Traefik  |--->| Docker Compose (7 servicios)     |  |
|  | (auto    |    |                                  |  |
|  |  TLS)    |    |  backend  frontend  celery-*     |  |
|  +----------+    |  db  redis  minio                |  |
|                  +----------------------------------+  |
|                                                        |
|  +----------+                                          |
|  | Ollama   |  <--- Gemma 3 12B (GPU si disponible)    |
|  | :11434   |                                          |
|  +----------+                                          |
|                                                        |
|  +----------+                                          |
|  | n8n      |  <--- 6 workflows de automatizacion      |
|  +----------+                                          |
+-------------------------------------------------------+
```

### 10.2 Procedimiento de Despliegue

1. **Configurar variables de entorno** en Coolify (ver seccion 11).
2. **Push a rama `main`** -- Coolify detecta el push y ejecuta build automatico.
3. **Coolify ejecuta:**
   ```
   docker compose -f docker-compose.coolify.yml build
   docker compose -f docker-compose.coolify.yml up -d
   ```
4. **Traefik** asigna certificado TLS via Let's Encrypt y configura el reverse proxy.
5. **Post-deploy:** verificar health en `/api/v1/health`.

### 10.3 Nginx (Produccion)

Nginx actua como reverse proxy entre Traefik y el backend FastAPI:

- **Rate limiting:** Proteccion contra abuso en endpoints publicos.
- **SSE streaming:** Configuracion especial de buffering para endpoints de generacion IA (`/planes/generate`).
- **WebSocket:** Soporte para conexiones persistentes.
- **Timeouts:** Ajustados para operaciones de IA (Ollama puede tardar hasta 480s en CPU).

### 10.4 Checklist de Produccion

- [ ] Variables de entorno configuradas (ver seccion 11)
- [ ] `JWT_SECRET` generado con al menos 32 caracteres aleatorios
- [ ] `POSTGRES_PASSWORD` seguro (no usar el default de desarrollo)
- [ ] `CORS_ORIGINS` restringido al dominio de produccion
- [ ] Swagger UI deshabilitado (`/docs` retorna 404 en produccion)
- [ ] Volumenes de PostgreSQL y MinIO respaldados
- [ ] Ollama corriendo en el VPS con modelo Gemma 3 12B descargado
- [ ] Health check responde 200 en `/api/v1/health`

---

## 11. Configuracion de Variables de Entorno

Referencia completa basada en `.env.coolify.example`. Copiar a `.env` y ajustar valores.

### 11.1 Base de Datos

| Variable | Descripcion | Ejemplo |
|----------|-------------|---------|
| `POSTGRES_USER` | Usuario PostgreSQL | `crece` |
| `POSTGRES_PASSWORD` | Contrasena PostgreSQL | `<secreto>` |
| `POSTGRES_DB` | Nombre de la base de datos | `crece` |
| `DATABASE_URL` | URL asyncpg (construida automaticamente en Docker) | `postgresql+asyncpg://crece:<pw>@db:5432/crece` |
| `DATABASE_URL_SYNC` | URL sincrona (para Alembic y Celery) | `postgresql://crece:<pw>@db:5432/crece` |

### 11.2 Redis

| Variable | Descripcion | Ejemplo |
|----------|-------------|---------|
| `REDIS_URL` | Cache de aplicacion (db 0) | `redis://redis:6379/0` |
| `CELERY_BROKER_URL` | Broker Celery (db 1) | `redis://redis:6379/1` |
| `CELERY_RESULT_BACKEND` | Results Celery (db 2) | `redis://redis:6379/2` |

### 11.3 Seguridad

| Variable | Descripcion | Ejemplo |
|----------|-------------|---------|
| `JWT_SECRET` | Secreto para firmar tokens JWT | `<cadena-aleatoria-32+>` |
| `JWT_ALGORITHM` | Algoritmo JWT | `HS256` |
| `JWT_EXPIRE_MINUTES` | Minutos de validez del token | `1440` |
| `CORS_ORIGINS` | Origenes permitidos (JSON array) | `["https://crece.mdconsultoria-ti.org"]` |

### 11.4 IA

| Variable | Descripcion | Ejemplo |
|----------|-------------|---------|
| `AI_PROVIDER` | Proveedor activo: `ollama`, `claude`, `gemini` | `ollama` |
| `OLLAMA_BASE_URL` | URL de Ollama | `http://host.docker.internal:11434` |
| `OLLAMA_MODEL` | Modelo Ollama | `gemma3:12b` |
| `CLAUDE_API_KEY` | API key de Anthropic (opcional) | `sk-ant-...` |

### 11.5 Storage

| Variable | Descripcion | Ejemplo |
|----------|-------------|---------|
| `MINIO_ENDPOINT` | Endpoint MinIO (interno) | `minio:9000` |
| `MINIO_ROOT_USER` | Usuario admin MinIO | `minioadmin` |
| `MINIO_ROOT_PASSWORD` | Contrasena admin MinIO | `<secreto>` |

### 11.6 Integraciones

| Variable | Descripcion | Ejemplo |
|----------|-------------|---------|
| `N8N_WEBHOOK_SECRET` | Secreto para validar webhooks de n8n | `<secreto>` |

### 11.7 Frontend

| Variable | Descripcion | Ejemplo |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | URL del backend para el navegador | `http://localhost:8002/api/v1` |
| `NEXT_PUBLIC_MAPLIBRE_STYLE` | URL del estilo MapLibre | `https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json` |

---

## 12. Comandos de Operacion

### 12.1 Desarrollo Local

| Comando | Descripcion |
|---------|-------------|
| `make dev` | Levantar todos los servicios en modo desarrollo |
| `make dev-build` | Build + levantar servicios |
| `make build` | Build de imagenes Docker |
| `make down` | Detener todos los servicios |
| `make restart` | Reiniciar todos los servicios |
| `make logs` | Seguir logs de todos los servicios |
| `make logs-backend` | Solo logs del backend |
| `make logs-worker` | Solo logs del worker Celery |
| `make logs-frontend` | Solo logs del frontend |
| `make ps` | Ver estado de contenedores |

### 12.2 Base de Datos

| Comando | Descripcion |
|---------|-------------|
| `make migrate` | Ejecutar migraciones Alembic (upgrade head) |
| `make migrate-create MSG="descripcion"` | Crear nueva migracion autogenerada |
| `make migrate-down` | Revertir ultima migracion |
| `make seed` | Poblar datos iniciales |
| `make reset-db` | Destruir BD, recrear y migrar (DESTRUCTIVO) |
| `make shell-db` | Abrir consola psql |

### 12.3 Testing

| Comando | Descripcion |
|---------|-------------|
| `make test` | Ejecutar 148 tests con pytest |
| `make test-cov` | Tests con reporte de cobertura |
| `make lint` | Ejecutar ruff + mypy |
| `make format` | Formatear codigo con ruff |

### 12.4 Shell

| Comando | Descripcion |
|---------|-------------|
| `make shell` | Bash en contenedor backend |
| `make shell-redis` | redis-cli |
| `make shell-frontend` | Shell en contenedor frontend |

### 12.5 Produccion

| Comando | Descripcion |
|---------|-------------|
| `make prod` | Levantar stack de produccion |
| `make prod-build` | Build de imagenes de produccion |
| `make prod-down` | Detener stack de produccion |
| `make prod-logs` | Seguir logs de produccion |

### 12.6 Limpieza

| Comando | Descripcion |
|---------|-------------|
| `make clean` | Eliminar contenedores, volumenes e imagenes (DESTRUCTIVO) |
| `make prune` | Limpiar recursos Docker no utilizados |

---

## 13. Problemas Conocidos

| ID | Problema | Impacto | Workaround |
|----|----------|---------|------------|
| K-001 | `CrmInteraccion` usa `registrado_por_id` pero el modelo tiene `promotor_id` | Errores en endpoints CRM | Alinear nombre de campo en schemas o modelo |
| K-002 | Ollama tarda ~480s en CPU-only para generacion de contenido | Timeouts en frontend | Configurar timeout de Nginx a 600s. Preferir GPU en produccion. |
| K-003 | Imagen PostGIS muestra warning `amd64` en Mac ARM (M1/M2/M3/M4) | Solo cosmetic. Funciona via emulacion Rosetta. | Ignorar warning. |
| K-004 | Filtros de periodo (7d/30d/90d) son solo UI hasta acumular datos | Graficas vacias en instalaciones nuevas | Ejecutar scrapers manualmente para generar datos historicos. |

---

## Apendice A: Puertos de Desarrollo

Puertos asignados para desarrollo local (no colisionan con otros proyectos del ecosistema MD Consultoria):

| Servicio | Puerto Host | Puerto Contenedor |
|----------|------------|-------------------|
| PostgreSQL | 5438 | 5432 |
| Redis | 6383 | 6379 |
| FastAPI Backend | 8002 | 8000 |
| Next.js Frontend | 3001 | 3000 |
| MinIO API | 9006 | 9000 |
| MinIO Console | 9007 | 9001 |
| Flower (dev) | 5555 | 5555 |

Estos puertos estan registrados en `~/Projects/claude-agents/PORT-REGISTRY.md`. Consultar ese archivo antes de modificar puertos para evitar conflictos con otros proyectos.

---

## Apendice B: Estructura de Directorios

```
crece-v2/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # 29 archivos de router
│   │   ├── core/               # config.py, database.py, security.py
│   │   ├── models/             # 26 modelos SQLAlchemy
│   │   ├── schemas/            # Schemas Pydantic v2
│   │   ├── services/           # 14 servicios de negocio
│   │   ├── scrapers/           # 8 scrapers (+ base.py)
│   │   ├── nlp/                # analyzer.py (pysentimiento + spaCy)
│   │   └── workers/            # Celery tasks
│   ├── migrations/             # Alembic
│   ├── scripts/                # seed.py
│   └── tests/                  # 148 tests
├── frontend/
│   └── src/
│       ├── app/                # Next.js App Router pages
│       ├── components/         # Componentes UI (shadcn/ui)
│       └── lib/                # API client, hooks, stores (Zustand)
├── docker/                     # Nginx config, Postgres init, Coolify config
├── docs/                       # Documentacion tecnica
├── docker-compose.yml          # Desarrollo
├── docker-compose.prod.yml     # Override de produccion
├── docker-compose.coolify.yml  # Configuracion Coolify
├── Makefile                    # Comandos de operacion
└── .env.coolify.example        # Plantilla de variables
```
