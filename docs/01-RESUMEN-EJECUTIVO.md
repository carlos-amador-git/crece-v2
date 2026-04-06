# CRECE v2.0 -- Resumen Ejecutivo

**Plataforma de Inteligencia Electoral y Social**
Movimiento Ciudadano CDMX

Preparado por: MD Consultoria TI
Fecha: Abril 2026
Version del documento: 1.0

---

## 1. Vision General

CRECE v2.0 es una plataforma integral de inteligencia politica que sustituye al sistema anterior basado en Oracle APEX. Disenada especificamente para Movimiento Ciudadano CDMX, la plataforma centraliza el monitoreo digital, el analisis de sentimiento, la generacion de contenido con inteligencia artificial, la gestion de campanias y el seguimiento electoral en una sola interfaz moderna y escalable.

El sistema transforma la operacion politica de un modelo reactivo y manual a uno proactivo y basado en datos, permitiendo que los equipos de comunicacion y estrategia tomen decisiones informadas en tiempo real.

### Problema que resuelve

Los equipos de comunicacion politica enfrentan tres desafios criticos:

1. **Monitoreo fragmentado.** Las redes sociales de cada dirigente se revisan manualmente, sin consolidar metricas ni detectar crisis a tiempo.
2. **Decisiones sin datos.** Las estrategias de contenido y campania se definen por intuicion, sin indicadores objetivos de penetracion digital ni comparativos contra competidores.
3. **Cumplimiento normativo.** La legislacion electoral del INE exige trazabilidad de gastos, etiquetado de contenido generado por IA y restricciones en periodo de veda, requisitos dificiles de cumplir sin automatizacion.

CRECE v2.0 resuelve estos tres frentes con 16 modulos funcionales integrados.

---

## 2. Modulos de la Plataforma

### Fase 1 -- Inteligencia Digital (8 modulos)

| No. | Modulo | Descripcion |
|-----|--------|-------------|
| 1 | **Dashboard con KPIs en Tiempo Real** | Panel central con indicadores clave: numero de dirigentes activos, puntaje IPD promedio, publicaciones monitoreadas y alertas activas. Actualizacion automatica. |
| 2 | **Gestion de Dirigentes** | Perfil completo de cada dirigente con su Indice de Penetracion Digital (IPD) en escala 0-10, presencia por plataforma y evolucion historica. |
| 3 | **Monitoreo de Redes Sociales** | Seis scrapers activos que recolectan datos de Twitter/X, Instagram, Facebook, TikTok, YouTube y Bluesky. Ejecucion automatizada diaria via n8n. |
| 4 | **NLP y Analisis de Sentimiento** | Ocho modelos de procesamiento de lenguaje natural (pysentimiento): sentimiento, emociones, discurso de odio, toxicidad, contenido ofensivo, reconocimiento de entidades (NER) y extraccion de topicos. |
| 5 | **Benchmarking** | Comparacion competitiva por seguidores, presencia en plataformas e IPD. Permite contrastar a cada dirigente contra competidores directos y contra el promedio nacional de MC. |
| 6 | **Planes IA (Estrategia Digital a 90 Dias)** | Generacion automatica de planes de accion digital utilizando Ollama con el modelo Gemma 3 12B ejecutado localmente, sin costo por consulta. |
| 7 | **Content Factory** | Generacion de contenido asistida por IA con etiquetado automatico de cumplimiento INE. Cada pieza generada incluye metadatos del modelo utilizado. |
| 8 | **Bot Detection / Salud Digital** | Auditoria de salud del engagement: deteccion de anomalias, identificacion de seguidores falsos y evaluacion de la calidad de la audiencia. |

### Fase 2 -- Operacion Electoral (8 modulos)

| No. | Modulo | Descripcion |
|-----|--------|-------------|
| 9 | **Voter Scoring** | Modelo de Machine Learning (RandomForest) que asigna una puntuacion de propension electoral a cada ciudadano, alimentado con datos sinteticos del Censo INEGI 2020. |
| 10 | **Campanias WhatsApp** | Integracion con Chatwoot para envio segmentado de mensajes, seguimiento de entregas y apertura, y gestion de listas de difusion. |
| 11 | **Blindaje Legal / Compliance** | Auditor automatizado de gasto electoral con alertas de violacion a topes de campania. Incluye modo veda electoral que restringe automaticamente funciones sensibles. |
| 12 | **Canvassing (Recorridos de Campo)** | Optimizacion de rutas para operadores de campo mediante PostGIS. Asigna zonas, calcula recorridos y registra avance geografico. |
| 13 | **CRM Politico** | Base de datos ciudadana con historial de interacciones, seguimiento de promotores y clasificacion por nivel de afinidad. |
| 14 | **Participacion Ciudadana** | Modulo de recepcion y gestion de solicitudes y retroalimentacion ciudadana. |
| 15 | **Automatizacion n8n** | Seis flujos de trabajo automatizados con 30 nodos personalizados. Ejecuta scraping diario, procesamiento NLP y alertas sin intervencion manual. |
| 16 | **Busqueda Semantica (pgvector)** | Embeddings vectoriales de 384 dimensiones para busqueda por similitud de contenido. Permite encontrar publicaciones relacionadas sin depender de palabras clave exactas. |

---

## 3. Arquitectura de Inteligencia Artificial

CRECE v2.0 implementa un ecosistema de IA en tres capas, disenado para equilibrar capacidad, costo y privacidad de datos:

| Capa | Proveedor | Modelo | Funcion | Costo |
|------|-----------|--------|---------|-------|
| Estrategia | Claude (Anthropic) | Claude 3.5+ | Analisis estrategico de alto nivel, redaccion ejecutiva | Suscripcion mensual |
| Analisis masivo | Gemini (Google) | Gemini Pro | Analisis de codebase y documentacion extensa (ventana de 1M tokens) | Gratuito |
| Generacion local | Ollama | Gemma 3 12B | Generacion de contenido, planes a 90 dias, analisis de sentimiento | $0 (ejecucion local) |

La capa local con Ollama/Gemma 3 es especialmente relevante: permite generar contenido de campania y planes estrategicos sin enviar datos sensibles a servidores externos y sin incurrir en costos por token. El modelo se ejecuta en el mismo servidor de produccion.

---

## 4. Metricas Clave

### Cobertura funcional

| Metrica | Valor |
|---------|-------|
| Modulos implementados | 16 de 16 planificados |
| Tests automatizados | 148 (todos en verde) |
| Plataformas monitoreadas | 6 (Twitter, Instagram, Facebook, TikTok, YouTube, Bluesky) |
| Modelos NLP activos | 8 (sentimiento, emociones, odio, toxicidad, ofensivo, NER, topicos, engagement) |
| Flujos n8n automatizados | 6 flujos, 30 nodos personalizados |
| Dimensiones vectoriales (pgvector) | 384 |

### Datos reales en el sistema

| Dirigente | Seguidores totales | Plataformas activas | IPD estimado |
|-----------|--------------------|---------------------|--------------|
| Alejandro Pina | 8,800 | 3 (Twitter, Instagram, Facebook) | ~4/10 |
| Rafael Solano | 12,900 | 4 (Instagram, LinkedIn, Facebook, YouTube) | ~2/10 |

### Indicadores tecnicos

| Indicador | Estado |
|-----------|--------|
| Aislamiento multi-tenant | Activo (datos por dirigente) |
| Cumplimiento INE | Modo veda, etiquetado IA, topes de gasto |
| Tipo de base de datos | PostgreSQL 16 + PostGIS 3.4 |
| Framework backend | FastAPI (Python 3.12, async) |
| Framework frontend | Next.js 14 (App Router, TypeScript) |
| Orquestacion | Docker Compose |

---

## 5. Infraestructura y Despliegue

| Componente | Entorno | Detalle |
|------------|---------|---------|
| Frontend | Vercel | Preview en vivo, despliegue continuo por rama |
| Backend + Workers | Coolify (VPS) | Servidor 163.245.208.96, mismo que ChatMX |
| Base de datos | PostgreSQL 16 | PostGIS 3.4, pgvector, alojado en VPS |
| Automatizacion | n8n | Ya operativo en el mismo servidor |
| IA Local | Ollama | Gemma 3 12B, ejecutado en el VPS |
| Almacenamiento | MinIO | Compatible con S3, para archivos y medios |

La arquitectura comparte infraestructura con ChatMX (otro proyecto de MD Consultoria), lo que reduce costos operativos y simplifica el mantenimiento.

---

## 6. Estado del Proyecto

| Aspecto | Estado | Notas |
|---------|--------|-------|
| Modulos Fase 1 (Inteligencia Digital) | **Completo** | 8/8 modulos funcionales con datos reales |
| Modulos Fase 2 (Operacion Electoral) | **Completo** | 8/8 modulos funcionales |
| Suite de pruebas | **148/148 en verde** | Cobertura de endpoints, servicios y modelos |
| Frontend conectado al backend | **Operativo** | Dashboard, dirigentes, monitoreo, benchmarking |
| Despliegue frontend | **Activo** | Preview en Vercel |
| Despliegue backend | **Listo** | Configuracion Coolify preparada |
| Documentacion tecnica | **En progreso** | Arquitectura integrada, plan de sprints, este documento |

### Pendientes (ninguno bloquea la demostracion)

| Pendiente | Impacto | Prioridad |
|-----------|---------|-----------|
| Shapefiles INE para mapa electoral | Solo afecta visualizacion geografica de secciones electorales | Media |
| Proxies residenciales para scraping en produccion | Necesarios para operacion continua a escala; el scraping funciona en desarrollo | Media |
| Presupuesto participativo (Decidim) | Proyecto separado; no bloquea ningun modulo actual | Baja |

---

## 7. Propuesta de Valor

### Para el equipo de comunicacion

- **Deteccion de crisis en tiempo real.** El sistema analiza sentimiento y toxicidad de forma continua. Cuando se detecta una anomalia negativa, genera una alerta automatica antes de que la situacion escale.
- **Contenido generado sin costo.** La integracion con Ollama/Gemma 3 permite producir borradores de publicaciones, respuestas y planes de contenido sin pagar por cada generacion.
- **Comparativa objetiva.** El modulo de benchmarking cuantifica la brecha entre cada dirigente y sus competidores, eliminando percepciones subjetivas.

### Para la operacion electoral

- **Canvassing optimizado.** Los recorridos de campo se calculan con PostGIS, maximizando cobertura y minimizando traslados.
- **Voter Scoring predictivo.** El modelo ML prioriza ciudadanos con mayor propension a ser movilizados, concentrando recursos donde mas impactan.
- **CRM con historial completo.** Cada interaccion ciudadana queda registrada, evitando duplicidad y permitiendo seguimiento personalizado.

### Para el cumplimiento normativo

- **INE-compliant desde el dia uno.** El modo veda electoral se activa automaticamente en periodos de restriccion. Todo contenido generado por IA lleva etiquetado del modelo utilizado. Los gastos de campania se auditan contra los topes legales vigentes.

### Para la direccion

- **Cero dependencia de Oracle.** La migracion desde Oracle APEX elimina licenciamientos costosos y dependencia de un proveedor propietario.
- **Costo operativo minimo en IA.** La generacion de contenido con modelos locales reduce el costo marginal a cero, frente a alternativas que cobran por token.
- **Plataforma extensible.** La arquitectura modular permite agregar nuevas funcionalidades (nuevas redes sociales, nuevos tipos de analisis, integraciones con terceros) sin redisenar el sistema.

---

## 8. Proximos Pasos Recomendados

1. **Demostracion en vivo** con datos reales de Pina y Solano para validar flujo completo ante stakeholders.
2. **Activacion de proxies residenciales** para pasar de scraping en desarrollo a operacion continua en produccion.
3. **Carga de shapefiles INE** para habilitar la visualizacion geografica de secciones electorales en el mapa.
4. **Onboarding de dirigentes adicionales** para ampliar la cobertura del sistema mas alla de los dos perfiles de prueba.
5. **Capacitacion al equipo de comunicacion** sobre el uso del dashboard, la generacion de contenido y la interpretacion de alertas.

---

*Documento preparado por MD Consultoria TI para Movimiento Ciudadano CDMX.*
*Plataforma desarrollada con FastAPI, Next.js, PostgreSQL y un ecosistema de IA de tres capas.*
*Todos los datos de prueba corresponden a perfiles publicos reales.*
