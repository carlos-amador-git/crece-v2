# Inventario del Dashboard CRECE — Estado real

> Generado con walkthrough automatizado (Playwright) el **2026-04-10** contra el deploy en Vercel con datos reales.
> Base: `frontend-zeta-sepia-46.vercel.app` conectado a backend local vía Cloudflare tunnel.

## Resumen ejecutivo

- **15 páginas** revisadas, **todas cargan** sin errores fatales
- **Estructura del sidebar ya está organizada** en 4 grupos (Principal / Análisis / Fase 2 / Sistema) — no necesita rediseño de navegación
- **8 páginas tienen datos reales y funcionan** plenamente
- **4 páginas tienen empty states intencionales** (esperan input del usuario o están bloqueadas por datos externos)
- **3 bugs transversales** presentes en todas las páginas (detallados al final)

## Componentes reutilizables ya construidos

Estos componentes **ya existen y están en uso**. Cualquier mejora debe reusarlos o extenderlos antes de crear nuevos:

### Charts (`components/charts/`)
| Componente | Usado en | Descripción |
|---|---|---|
| `IpdRadarChart` | `/dirigentes/[id]`, `/benchmark` | Radar 0-10 de presencia digital por plataforma |
| `SentimentLineChart` | `/dashboard`, `/dirigentes/[id]`, `/benchmark` | Líneas positivo/neutral/negativo |
| `SentimentPieChart` | `/social` | Donut de distribución de sentimiento |
| `EngagementBarChart` | `/dirigentes/[id]`, `/benchmark` | Barras de engagement por plataforma |

### Dashboard (`components/dashboard/`)
| Componente | Usado en | Descripción |
|---|---|---|
| `KpiCard` | transversal | Card de métrica con icono y delta |
| `FilterSelect` | `/contenido`, `/participacion` | Select genérico con opción "Todos" |
| `FunnelBar` | `/campanas` | **Barras horizontales de conversión (funnel) YA EXISTE** |
| `ContentCard` | `/contenido` | Card de pieza de contenido |
| `ProgressBar` | `/canvassing` | Barra de progreso genérica |

### Social / Dirigentes (`components/social/`, `components/dirigentes/`)
| Componente | Usado en | Descripción |
|---|---|---|
| `PostCard` | `/dashboard`, `/dirigentes/[id]`, `/social` | Card de publicación social |
| `SentimentBadge` | `/dirigentes/[id]`, `/social` | Badge con color según sentimiento |
| `PlatformIcon` | `/dirigentes` | Ícono por red social |
| `IpdScoreBadge` | `/dirigentes`, `/benchmark` | Badge con IPD coloreado |
| `ProfileHeader` | `/dirigentes/[id]` | Header con avatar, cargo, plataformas |

### Alerts / Compliance
| Componente | Descripción |
|---|---|
| `CrisisAlertList` | Lista de alertas activas |
| `CrisisAlertBanner` | Banner superior cuando hay crisis |
| `ImportGastosDialog` | Dialog para importar gastos electorales |

---

## Páginas — estado detallado

### 1. `/dashboard` — Overview · **FUNCIONA**

**Titulo:** Dashboard
**Componentes:** `Card`, `Skeleton`, `SentimentLineChart`, `PostCard`, `CrisisAlertList`
**Endpoints:** `/auth/me`, `/dashboard/overview`, `/dashboard/status`, `/alerts`, `/social/posts`, `/social/sentiment-timeline`, `/dirigentes/`

**Lo que muestra (datos reales):**
- KPIs: Total Dirigentes 2, Avg IPD 3.9, Posts 24h 0, Alertas 0
- Gráfico "Tendencia de Sentimiento" últimos 30 días
- "Seguidores por Plataforma": Twitter 9.6K, Facebook 8.3K, Instagram 3.9K, TikTok 0 — Total 21.8K
- Quick status bar: Workers 2/2, Scrapers 0 ejecutando
- Publicaciones recientes con sentiment badges

**Problemas detectados:**
- 🐛 **Filtros de tiempo (Hoy / 7d / 30d / 90d) no funcionan** — `activeFilter` se guarda en state pero nunca se pasa a los hooks
- 🐛 **"Avg IPD Score 3.9" sin contexto de /10** — el usuario no sabe si 3.9 es bueno o malo
- ⚠️ **"Posts (24h): 0"** — scrapers no han corrido recientemente o no hay data fresh
- ⚠️ **"+0%" en todos los deltas** — cuando no hay histórico, el `change` siempre es 0, se ve raro
- ⚠️ **Sentiment chart con dense zig-zag** — sin suavizado ni agregación, parece ruidoso visualmente
- ⚠️ **Mapa electoral comentado en el código** (no visible) — hidden hasta que lleguen shapefiles INE

---

### 2. `/dashboard/dirigentes` — Lista · **FUNCIONA**

**Titulo:** Dirigentes
**Componentes:** `Card`, `Input`, `Badge`, `IpdScoreBadge`, `PlatformIcon`
**Endpoints:** `/dirigentes/`

**Lo que muestra:**
- 2 dirigentes registrados (Piña, Solano) ambos con IPD 3.9
- Tabla con: Nombre, Cargo, Partido (MC), IPD, Plataformas (iconos), Última actividad (hace 5d)
- Filtros "Todos los partidos" / "Todos los estados" (funcionan visualmente)
- Búsqueda por nombre / cargo
- Botón "Agregar Dirigente"

**Oportunidades:**
- El IPD es el mismo para ambos (3.9) — o hay un bug de cálculo o ambos están coincidentemente iguales. **A verificar**.

---

### 3. `/dashboard/dirigentes/1` — Detalle · **FUNCIONA EXCELENTE**

**Titulo:** Alejandro Piña Medina
**Componentes:** `ProfileHeader`, **`IpdRadarChart`**, `SentimentLineChart`, `EngagementBarChart`, `PostCard`, `SentimentBadge`, `Tabs`
**Endpoints:** `/dirigentes/1`, `/social/sentiment-timeline`, `/planes/`

**Lo que muestra (rica):**
- ProfileHeader con avatar, cargo, ubicación, 0 secciones, plataformas
- 4 KPIs: Posts (7d) 2, Engagement (7d) 5.586, Sentimiento Positivo 70%, Crecimiento +0%
- **IPD Radar con 6 ejes** (Twitter, Instagram, Facebook, TikTok, YouTube, Engagement)
- Sentimiento (30 días) — mismo chart que overview
- **Tabs funcionales:** Overview, Social, Electoral, Planes

**Esta es la página más rica del dashboard.** Ya tiene casi todo lo que se pidió en los comentarios (radar, tabs, sentiment).

---

### 4. `/dashboard/social` — Monitoreo · **FUNCIONA**

**Titulo:** Monitoreo Social
**Componentes:** `PostCard`, **`SentimentPieChart`**, `SentimentBadge`, `Input`
**Endpoints:** `/social/posts`

**Lo que muestra:**
- 3 KPIs: Total Posts 19, Originales 5, Retweets 14
- Feed con post cards reales
- Filtros dropdown "Todas" / "Todos" + toggle "Solo originales"
- **SentimentPieChart** visible (donut amarillo, 100% neutral — sospechoso)
- Sección "Top por Engagement"

**Problema:** El sentiment pie chart dice "100% neutral" — probablemente los posts no tienen `sentiment_label` asignado aún (el NLP no corrió).

---

### 5. `/dashboard/benchmark` — **EMPTY STATE INTENCIONAL**

**Titulo:** Benchmarking Competitivo
**Componentes:** `IpdRadarChart`, `EngagementBarChart`, `SentimentLineChart`, `IpdScoreBadge`
**Endpoints:** `/dirigentes/`

**Estado:** La página carga un empty state: *"Selecciona un dirigente y un competidor para comparar"*. Dos dropdowns vacíos.

**Esto NO es un bug** — espera input. Pero los 3 componentes de chart están listos para renderizar cuando el usuario seleccione.

**Oportunidad:** Preseleccionar el primer dirigente + primer competidor para que haya algo visible de entrada (principio de UX: "evitar empty state cuando hay data default razonable").

---

### 6. `/dashboard/electoral` — **BLOQUEADO POR DATOS**

**Titulo:** Mapa Electoral
**Componentes:** `Card`
**Endpoints:** ninguno (solo carga la página)

**Estado:** Empty state explícito: *"Mapa en desarrollo — estará disponible cuando se carguen los shapefiles de secciones electorales del INE"*.

**Está correctamente comunicado al usuario.** No es un bug, es una transparencia. Bloqueado por #7 en STATUS.md.

---

### 7. `/dashboard/participacion` — **FUNCIONA MUY BIEN**

**Titulo:** Participación Ciudadana
**Componentes:** `FilterSelect`, `Input`, `Badge`
**Endpoints:** ninguno visible (datos inline o mockeados)

**Lo que muestra:**
- 4 KPIs: Propuestas Activas 6, En Deliberación 3, Votaciones Abiertas 3, Total Votos 13,586
- Tabs: Propuestas Activas, Votaciones, Resultados
- Filter chips temáticos: Todas, Movilidad, Seguridad, Agua, Empleo, Servicios
- Cards de propuestas con categoría, estado, descripción, autor, likes, comentarios

**Observación importante:** Esta página parece **no hacer llamadas al backend** (solo `/auth/me` y `/alerts`). Los datos podrían estar hardcodeados en el frontend — **a verificar**. Si es así, hay que conectarla al servicio Decidim o marcarla claramente como demo.

---

### 8. `/dashboard/scoring` — **FUNCIONA CON BUG MENOR**

**Titulo:** Voter Scoring
**Componentes:** `Button`, `Skeleton`, `Badge`, donut chart inline
**Endpoints:** `/voter-scoring/segments`, `/voter-scoring/by-seccion` (**422 error**)

**Lo que muestra:**
- Badge superior "Datos sintéticos — INEGI Censo 2020 CDMX" (transparencia ✅)
- 4 KPIs: Total Scored 606, Avg Score 21.8, Opositor 495 (81.7%), Promotable 90 (14.8%)
- Distribución por Segmento — donut con Opositor 81.7%, Promotable 14.8%, Persuadible 2.5%
- Scoring por Sección — **EMPTY** con mensaje "Sin datos por sección"
- Botón "Run Scoring"

**Problema:** `/voter-scoring/by-seccion` devuelve 422 (Unprocessable Entity) — probablemente se llama sin pasar el `seccion_id` requerido. La sección termina vacía cuando debería mostrar algo.

**Fix:** La página debe pasar un `seccion_id` por defecto (1) o mostrar un selector. Actualmente el endpoint requiere el parámetro en la ruta y el frontend lo está llamando sin él.

---

### 9. `/dashboard/planes` — Lista · **FUNCIONA**

**Titulo:** Planes IA
**Componentes:** `Card`, `Badge`, `Button`
**Endpoints:** `/planes/`, `/dirigentes/`

**Lo que muestra:**
- Tabs: Todos, Borrador, Aprobado, Ejecutado, Rechazado
- **Múltiples planes listados** (al menos 6 visibles), todos diagnósticos de Piña/Solano con fechas
- Badge "DIAGNOSTICO" en cada uno
- Estado "Borrador" en la derecha
- Fecha y conteo de palabras visible

**Observación:** Todos son diagnósticos, no hay planes estratégicos generados. El botón "Generar Plan" está presente.

---

### 10. `/dashboard/contenido` — **FUNCIONA**

**Titulo:** Content Factory
**Componentes:** `FilterSelect`, `ContentCard`
**Endpoints:** `/contenido/`, `/dirigentes/`

**Lo que muestra:**
- 2 filtros: "Todos los formatos", "Todos los estados"
- **2 piezas de contenido reales** generadas:
  - "Mejora del transporte público en CDMX" (post_twitter, publicado)
  - "Movilidad en CDMX" (post_twitter, borrador)
- Timestamp, identificador, hashtags

**Firma en cada card:** "Contenido generado con asistencia de Inteligencia Artificial" ✅ (cumplimiento INE)

---

### 11. `/dashboard/canvassing` — **EMPTY STATE + MAPA PENDIENTE**

**Titulo:** Smart Canvassing
**Componentes:** `Card`, `Badge`, `ProgressBar`
**Endpoints:** `/canvassing/routes`

**Lo que muestra:**
- Empty state: "No hay rutas. Optimiza la primera"
- Sección "Mapa de Ruta" con placeholder "Mapa disponible próximamente"
- Sección "Puntos de Visita" vacía
- Botón "Optimize Route"

**Estado:** Correctamente construida pero sin data. Igual que electoral, espera el mapa.

---

### 12. `/dashboard/ciudadanos` — **FUNCIONA CON DATOS REALES**

**Titulo:** CRM Ciudadanos
**Componentes:** `Card`, `Input`, `Badge`
**Endpoints:** `/ciudadanos/`

**Lo que muestra:**
- 4 KPIs: Total 606, Con Teléfono 15, Con Email 5, Simpatizantes MC 6
- Tabla paginada con: Nombre, Teléfono, Email, Edad, Escolaridad, Sección, MC (Sí/No), Fuente
- **Múltiples filas visibles** (Adriana Aguilar, Elizabeth Aguilar, Fernando López, Guadalupe Díaz...)
- Datos reales de los 200 sintéticos generados

**Observación:** Con Teléfono = 15 de 606 y Con Email = 5 es muy bajo. Es esperado porque son sintéticos, pero la tarjeta no transparenta que son datos sintéticos (otras páginas sí lo hacen con un badge).

---

### 13. `/dashboard/campanas` — **EMPTY STATE**

**Titulo:** Campaign Manager
**Componentes:** `Card`, `Badge`, `Input`, **`FunnelBar`**, `Textarea`
**Endpoints:** `/campanas/`, `/ciudadanos/`, `/dirigentes/`

**Lo que muestra:**
- Empty state: "No hay campañas. Crea la primera"
- Analytics con empty state: "Selecciona una campaña para ver analytics"
- Botón "Nueva Campaña"

**Observación crítica:** **Ya importa `FunnelBar`** — esto confirma que el componente existe y está listo. Cuando se cree una campaña, el funnel ya funcionará (enviados → entregados → leídos → respondidos).

---

### 14. `/dashboard/compliance` — **FUNCIONA COMPLETA**

**Titulo:** Blindaje Legal
**Componentes:** `Button`, `Badge`, `Skeleton`, `ImportGastosDialog`
**Endpoints:** `/blindaje/alertas`, `/blindaje/gastos`, `/blindaje/reporte/1`

**Lo que muestra:**
- 4 KPIs: Total Gastos $0, % Tope 0.0%, Alertas 0, Tope Campaña RIE $500K
- Secciones: Gastos Registrados (empty), Alertas (empty)
- **"Referencia Electoral CDMX 2024"** con datos reales del INE:
  - Tope Gastos Campaña $500,000 MXN
  - Tope Precampaña $100,000 MXN
  - Financiamiento Privado $50,000 MXN
  - Lista Nominal CDMX 7,459,827
  - Participación 2024 62.3%
  - MC Votación CDMX 8.7%
- Botones "Importar Gastos", "Run Audit"

**Esta página está completa funcionalmente**, solo falta que alguien suba gastos reales.

---

### 15. `/dashboard/bot-detection` (Salud Digital) — **FUNCIONA EXCELENTE**

**Titulo:** Salud Digital
**Componentes:** `Button`, `Badge`, `Skeleton`
**Endpoints:** `/bot-detection/analyze/1`, `/dirigentes/`

**Lo que muestra (rica):**
- Selector de dirigente arriba (Alejandro Piña Medina)
- Badge "Saludable"
- **Score global 83** — Piña, 3 perfiles analizados, 0 anomalías
- Leyenda de semáforo: verde=orgánico, amarillo=audiencia inactiva, rojo=manipulación
- **Breakdown por plataforma:**
  - **Twitter @Alejandro_Pinha** — Score 70 Saludable · Engagement 0.06% · 3.7K seguidores · Avg Eng 2.3 · 50 posts
  - **Instagram @alejandro.pinha** — Score 100 Saludable · Engagement 1.97% · 3.3K · Avg Eng 64.8 · 50 posts
  - **Facebook @alejandropinamedina** — Score 80 Saludable · Engagement 0.49% · 1.8K · Avg Eng 9.6 · 19 posts
- Hints: "Engagement muy bajo (0.06%) para 3.7K" / "Variación alta (CV=3.2) — posible amplificación puntual"

**Esta página es oro.** Ya usa semaforización, números absolutos, hints accionables. **Es el modelo de cómo deberían verse las otras páginas.**

---

## Bugs transversales (afectan todas las páginas)

| # | Bug | Impacto | Fix estimado |
|---|-----|---------|--------------|
| B1 | **404 error en todas las páginas** — probablemente favicon.ico o algún asset faltante | Cosmético en consola, no afecta UX | 5 min |
| B2 | **Filtros de tiempo Hoy/7d/30d/90d no funcionan** en overview — `activeFilter` no se propaga a hooks | Usuario cree que filtra pero no hace nada | 30 min |
| B3 | **Scoring por Sección devuelve 422** — llamada sin `seccion_id` requerido | Card vacío sin razón aparente | 20 min |

## Hallazgos positivos (lo que NO hay que tocar)

1. **Sidebar organizado en 4 grupos** (Principal / Análisis / Fase 2 / Sistema) — estructura sólida, NO rediseñar
2. **15 de 15 páginas existen y cargan** — no hay placeholders 404
3. **Data de Piña/Solano se ve en todas las páginas relevantes** — la integración backend-frontend está viva
4. **Compliance tiene datos reales del INE** ya cargados
5. **Bot Detection / Salud Digital es el mejor ejemplo de diseño** con score numérico, semaforización, hints accionables, breakdown por plataforma
6. **FunnelBar ya existe** en `components/dashboard/` y está importado en campañas
7. **IpdRadarChart ya existe** en `components/charts/` y está usado en dirigente detail + benchmark
8. **FilterSelect ya existe** — reusable, no hay que crear `PlatformFilter` nuevo

## Sospechosos (a validar)

| # | Qué | Por qué sospechoso |
|---|-----|-------------------|
| S1 | **IPD = 3.9 idéntico para Piña y Solano** en la lista de dirigentes | Diferentes perfiles deberían dar diferentes IPDs |
| S2 | **Sentimiento 100% neutral en social pie chart** | Los posts no tienen `sentiment_label` asignado — el NLP no corrió sobre ellos |
| S3 | **Participación Ciudadana parece no llamar al backend** | No hay calls a `/participacion/*` — posible hardcoding |
| S4 | **Seguidores por Plataforma: TikTok 0** en overview | Correcto según perfil de Piña — pero no está claro que es intencional vs fallo de scraper |

## Oportunidades de mejora basadas en lo que existe

Todas las oportunidades se implementan **editando archivos existentes**, no creando nuevos (salvo los marcados con NUEVO).

### Overview (`dashboard/page.tsx`)
1. Fix bug B2 (filtros de tiempo)
2. Agregar `/10` al card de IPD + barra mini de contexto
3. Extender tooltip del `SentimentLineChart` con valor absoluto
4. Reemplazar "Seguidores por Plataforma" (barras de progreso) por sparklines inline
5. Humanizar etiquetas: "Avg IPD Score" → "Presencia Digital Promedio"

### Social (`dashboard/social/page.tsx`)
1. Correr NLP sobre los 19 posts existentes para que el `SentimentPieChart` muestre algo real (no 100% neutral)
2. Agregar filtro por plataforma (reusar `FilterSelect` que ya está importado en otras páginas)

### Scoring (`dashboard/scoring/page.tsx`)
1. Fix bug B3 (pasar `seccion_id=1` por default o agregar selector)
2. El donut ya existe y se ve bien — no tocar

### Benchmark (`dashboard/benchmark/page.tsx`)
1. Preseleccionar Piña como dirigente y el primer competidor como competitor
2. Los 3 componentes ya están importados — solo falta data inicial

### Ciudadanos (`dashboard/ciudadanos/page.tsx`)
1. Agregar badge "Datos sintéticos" arriba (como scoring ya hace)

### Dirigente detail (`dashboard/dirigentes/[id]/page.tsx`)
1. Esta página **ya tiene todo**: radar, tabs, sentiment, engagement, posts. **No tocar** salvo para enriquecer tooltips.

### Electoral y Canvassing
- **NO tocar** — empty states están correctamente comunicados. Esperar datos externos.

### Páginas sin cambios (funcionan bien)
- `/dashboard/planes` — múltiples planes visibles, tabs, generador
- `/dashboard/contenido` — piezas reales, firma de IA visible
- `/dashboard/compliance` — datos INE completos, estructura correcta
- `/dashboard/bot-detection` — **modelo a imitar en otras páginas**

## Conclusión

**La app NO necesita una reorganización.** Lo que necesita son:
1. **3 fixes de bugs** (5 + 30 + 20 = ~1h de trabajo)
2. **~10 mejoras contextuales** a páginas existentes, cada una editando 1-2 archivos
3. **Conectar participación al backend** si efectivamente está mockeado
4. **Correr NLP sobre los 19 posts existentes** para que el pie chart de social tenga contenido

**NO se necesitan:** componentes nuevos tipo `PlatformFilter`, `FunnelConversion`, páginas nuevas tipo `/war-room` o `/analisis`. El 80% del trabajo propuesto en comentarios 1/2/3 ya existe como primitiva y solo hay que **usarla mejor** en las páginas que ya están hechas.
