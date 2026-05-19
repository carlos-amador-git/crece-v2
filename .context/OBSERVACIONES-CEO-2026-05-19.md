# Observaciones CEO · 2026-05-19 · post-merge piloto Saymi

Documento canónico de observaciones del CEO durante validación visual de la URL prod `frontend-zeta-sepia-46.vercel.app` tras merge PR #48 a main (commit `125d2ec`). **Sin explicaciones, sin propuestas — solo registro fiel.**

---

## OBS-1 · Discrepancia card "Ganadores" vs gráfica Engagement

**CEO escribió textual:**
> "Tenemos 2.8 mil likes en parte inferior para el post del 8 de mayo y en la gráfica solo tenemos casi 1.3K?"

**Datos verificados en BD (2026-05-19 13:30 local):**

| Fuente | Valor | Tabla / Campo |
|---|---|---|
| Card "Ganadores · 08-may" | **2,834** likes | `social_posts.likes` (post_id=5221 · Panini · "fiebre mundialista") |
| Tooltip gráfica 08/05 "Reactions" | **1,279** | `SUM(watched_like_events)` agregado por `published_at::date` |
| Reactors capturados específicamente del post Panini (5221) | **0** | `watched_like_events WHERE post_id=5221` |
| Otros posts del 08-may con reactors capturados | 6 posts · 1,279 total | mismo agregado del chart |

**Hecho observable:** los dos números provienen de fuentes distintas (snapshot público FB vía Apify vs reactors individuales RADAR Hugo). El post Panini específico no tiene reactors individuales capturados.

---

## OBS-2 · Cero reactions abril 2026 en la gráfica

**CEO escribió textual:**
> "Porque no hay reacciones para abril? de ningún tipo. Se supone que Hugo te mando en su momento el time stamp y que las publicaciones provienen desde esa fecha, abril 2026."

**Datos verificados en BD (2026-05-19 13:30 local):**

| Período | Posts FB en BD | Likes públicos sum | Reactors individuales capturados |
|---|---|---|---|
| Abril 14-30 (13 días con posts) | 155 | ~36,475 | **0** |
| Mayo 06-16 (11 días con reactors) | 42 posts con reactors | — | 8,247 |

Primer día con reactions capturadas: **2026-05-06**.

**Pregunta abierta (NO asumir respuesta sin verificar con Hugo):**
- ¿Hugo recibió instrucción de cubrir abril y su engine descartó esos posts, o se interpretó otra ventana?
- ¿Es técnicamente viable re-correr RADAR sobre posts de abril ahora, o esa visibilidad ya expiró del lado FB?

---

## OBS-3 · Posts aparecen en múltiples secciones · sugerencia de reacomodo

**CEO escribió textual:**
> "Los posts los tenemos en varias secciones en el menu. Comentarios, top Post, Fantasmas. Tal vez se me escapa otro. Los perfiles observados debe subir de categoria. Ya sería un cuarto. ¿No sería mejor un reacomodo de esta información?"

**Inventario verificado del sidebar (`frontend/src/components/layout/sidebar.tsx`):**

### Lugares donde aparecen posts actualmente

| # | Ruta | Etiqueta sidebar | Grupo en sidebar | Naturaleza |
|---|---|---|---|---|
| 1 | `/dashboard/social` | Monitoreo | Social | Feed general de posts (`PostCard` × `useSocialPosts`) |
| 2 | `/dashboard/social/comentarios` | Comentarios | Social | Lista de comments con su post padre (`useSocialComments`) |
| 3 | `/dashboard/content/top` | Top Posts | Social | Ranking de posts top (`useTopPosts` con filtros plataforma/métrica) |
| 4 | `/dashboard/aceptacion/fantasmas` (tab "Perfiles Observados") | Fantasmas | Índice Aceptación | TopPostsCards (ganadores + negativos) **+ TopFansRanking** |

**Aclaración geográfica solicitada por CEO:**
- "Perfiles Observados" hoy es un **tab dentro de Fantasmas** (3er tab), no es entrada propia del sidebar.
- CEO propone subir "Perfiles Observados" a entrada de menú de nivel 1 (mismo rank que Monitoreo, Comentarios, Top Posts, Fantasmas).
- Total quedaría con **5 entradas que muestran posts** (las 4 actuales + Perfiles Observados independizado).

### Otras vistas que tocan posts (no son entrada de menú pero los referencian)

- `/dashboard/dirigentes/[id]` · perfil dirigente incluye posts del mismo
- `/dashboard/recomendaciones` · cita posts para evidencia
- `/dashboard/planes/[id]` · plan IA cita posts (vía recomendaciones)

**Status decisión:** CEO pidió **documentar nada más**. Pregunta abierta:
> "¿No sería mejor un reacomodo de esta información?"

Sin respuesta proporcionada. Pendiente para conversación siguiente.

---

## Pendiente conversación

CEO indicó:
> "Documenta y regresamos al tema de los post y su confiabilidad."

→ próximo tema: **confiabilidad de la información de posts** (continuación de OBS-1 y OBS-2). Sin acción hasta que CEO lo retome.

---

## OBS-4 · Overview · chart Tono Discursivo + tags fantasma (2026-05-19 tarde)

**Captura:** `/dashboard` con chart "Tono Discursivo" + "Publicaciones Recientes". CEO pidió ordenar por impacto.

### P1 · HIGH · Desinformación "0 de 315 clasificados"

Header chart: "Muestra: 0 de 315 posts del periodo (0% clasificados) · 315 pendientes de clasificación".

**Realidad BD (Saymi 30d, todas plataformas):** 315 posts ✓ pero:
- 0 con `sentiment_label` (campo legacy)
- **82 con `tono_discurso` + `target_politico`** (framework nuevo · matriz polaridad v2 cerrada 2026-04-13)

**Causa raíz:** componente Overview lee del campo legacy deprecado en favor de `tono_discurso`. 26% de posts SÍ están clasificados pero chart usa el campo equivocado.

### P2 · HIGH · Tags "Neutral" hardcoded en cards

Cards "Publicaciones Recientes" muestran `Neutral` tag en CADA post. Pero header dice "0 clasificados". Probable: fallback hardcoded cuando `sentiment_label IS NULL` → asigna `"Neutral"`. **Viola "NUNCA inventar datos" visiblemente al cliente.**

### P3 · MEDIUM · Chart empty disfrazado

Eje X muestra solo `14/4` con 1 bar al 100% pese a subtítulo "últimos 30 días". Empty state oculto detrás de un bar.

### P4 · LOW · Filtros irrelevantes

Subtítulo "sin RTs · >20 chars" cuando filtro plataforma = Facebook. RTs no aplican a Facebook.

---

## OBS-5 · Top Posts · /dashboard/content/top (2026-05-19 tarde)

**Captura:** Top Posts ordenados por Engagement % · ventana 90 días · todas plataformas · 20 de 228 elegibles.

### P1 · HIGH · Doble @ en handle visible al cliente

UI muestra `@@saymipineda` en cada card. **BD tiene `@saymipineda` con un solo @** (verificado en `social_profiles.handle` para TikTok). Bug cosmético frontend que duplica el `@`. **Cliente lo va a notar inmediatamente en demo.**

### P2 · HIGH · Sesgo del ranking Engagement %

Post #5 "La Procesión de Estandartes y Relicarios" tiene **2.2K likes / 30K views** (post viral verdadero) pero queda en posición #5 detrás de:
- #1: Tecamac (154 likes / 2K views · 7.92%)
- #2: Día Maestra Mezcalero (30 likes / 410 views · 7.80%)
- #3: Semana Santa (86 likes / 1.1K views · 7.50%)

**Causa:** Engagement % = `(likes+comments+shares)/views`. Posts nicho con bajas views inflan %. **Para "insumo de plan semanal IA" esto es contraproducente** — el IA va a creer que el post Tecamac (#1 actual) es mejor contenido que el viral #5.

**Recomendación:** dual sort (Engagement % + threshold mínimo de views/likes) o segundo orden por engagement absoluto.

### P3 · MEDIUM · Card sin indicador de plataforma

Post #1 Tecamac aparece sin indicar que es de **TikTok** (BD verificada). Cliente con filter "Todas" no sabe qué red social. Falta badge/icon de plataforma por card.

### P4 · MEDIUM · Post #3 "0 comments / 0 shares" en top

86 likes / 0 coments / 0 shares / 1.1K views. Engagement % = 7.50% pero **engagement social = 0 interacciones humanas**. Para insumo IA debería filtrar posts con cero interacciones sociales (no replicar ese patrón).

### P5 · LOW · Sort sin secundario por fecha

Fechas mezcladas (mar, abr, feb) sin sub-orden cronológico. OK por diseño actual; sería útil opcion sort secundario.

### P6 · LOW · "228 elegibles" sin explicación

228 elegibles vs 315 totales sin tooltip de qué define "elegibilidad" (probable: filtro content length + sin RTs + ventana).

---

## OBS-6 · Fantasmas / Perfiles Observados (2026-05-19 tarde · captura adicional)

**Captura:** mismo dashboard ya validado, pero con foco en card "Negativos" que CEO está revisando.

### P1 · HIGH · Inconsistencia card Negativos vs chart Engagement

**Card Negativos #1 "22-abr"** muestra:
- 235 likes ← viene de `social_posts.likes` (snapshot público Apify)
- 4 comments
- Polaridad -1.00 ← viene de `nlp_polaridad` agregado de comments

**Chart Engagement diario el mismo 22-abr:**
- Cero reactions (barra invisible)

**Misma raíz que OBS-1:** dos fuentes de datos (snapshot público vs reactors capturados RADAR). La card USA likes_publicos + polaridad_comments (datos válidos en BD), mientras que el chart solo agrega `watched_like_events` (ausentes en abril). **Tres conceptos sin glosario unificado en la misma página: reactions, likes públicos, polaridad.**

### P2 · MEDIUM · Banda explicada solo del lado derecho

Header chart: "banda gris = posts aún acumulando reactions". Explica la zona derecha (últimos 3d). **NO explica que la zona izquierda (abril 14-30) también está vacía** — pero por motivo distinto (sin scrape RADAR, no por "acumulando"). Usuario asume "todo OK" cuando en realidad falta cobertura.

### P3 · YA documentado (OBS-3) · No es nuevo

Tab "Perfiles Observados" + sidebar "Fans y Perfiles" entrega el mismo contenido (decisión D-2 · espejo intencional para no romper mental model pre-piloto).

---

## OBS-7 · Lista cliente_seed Saymi NO visible por default + Gemini opinion (2026-05-19 tarde)

**CEO propuso:** poner la lista cliente_seed completa al costado del Top Fans (split view two-column).

**Realidad BD verificada (13 cliente_seed Saymi · `dirigente_observador_id=3 source='cliente_seed'`):**

| # | Display Name | Handle | Reactions capturadas |
|---|---|---|---|
| 1 | Mueller Ramírez | mueller.ramirezlopez | 34 |
| 2 | Carlos David | carlosdavid.nvo | 27 |
| 3 | **Misael Gómez** | misael.gomez.981351 | **10** ← Fan #1 vía mockup D-MISAEL-VIP-40 |
| 4 | Angel Osorio | norberto.morales.3760 | 9 |
| 5 | Mariel Villatoro | mariel.lopezvillatoro | 8 |
| 6 | Guadalupe Ibañez | sagitario.ram.5 | 5 |
| 7 | Ana Maldonado | anaa.malsa | 4 |
| 8 | Itzel Cuevas | itzi.cuevas | 4 |
| 9 | Zuaily Rasgado | zuaiily | 4 |
| 10 | Adelaida Leyva | adelaida.leyvasanchez | 3 |
| 11 | Marvin Hilario | MarvinCruzV | 2 |
| 12 | Alberto Aparicio | alberto.apariscio | 1 |
| 13 | José Cárdenas | PepeHernandezOax | 1 |

**Actualización importante:** los 13 cliente_seed AHORA tienen reactions capturadas (1 a 34) tras el ingest reactors completado. El postmortem S-8.1 había reportado "0/13 matches" en el primer dump (176 reactors) pero la corrida posterior con 8,247 reactions sí cubrió a los 13. **Misael real solo tiene 10 reactions** (no 40 como muestra el mockup VIP).

### Gemini opinion · `approve_split_view`

**Propuesta concreta:**
- Layout: `grid grid-cols-1 xl:grid-cols-2 gap-6` (responsive · apila en mobile/tablet, split solo en xl)
- Izquierda: **Top Fans Generales** (ranking dinámico actual · MixedTopFansList)
- Derecha: **Audiencia Objetivo Curada** (lista estática 13 cliente_seed · CuratedTargetList)
- 2 componentes nuevos derivados del WatchedProfilesTab.tsx existente
- Derivar `targetList` y `activeList` en tiempo de render (NO modificar hooks fetching)

**Alternativa si split view tarda:**
- Insight Card automatizada arriba del ranking: "Hallazgo: X de 13 perfiles objetivo interactuaron en los últimos 44 días" → comunica valor de negocio sin alterar layout estructural.

**Mejoras UX adicionales (Gemini):**
- HIGH: zero-state visual intencional (texto muted, badge "Inactivo") para métricas en 0 — evita que usuario asuma error.
- MEDIUM: badges "Sugerido" vs "Objetivo" en avatars del Top Fans para reconocer cliente_seed en lista mixta.

**Riesgos pre-piloto identificados (Gemini):**
- Romper responsive en tablets/1080p escalado · usar `xl` o `2xl` como breakpoint para 2 cols, apilar abajo.
- Regresiones por separar data en componente de 28KB · derivación en render, no modificar hooks.

**Anti-patrón a evitar:** scroll-trapping (`overflow-y-auto` por columna). Ambas listas deben empujar altura natural del documento.

---

## OBS-8 · Monitoreo Social muestra solo 19 posts (2026-05-19 tarde)

**CEO observó:** "solo 19 posts... super bajo".

**Realidad BD Saymi por ventana:**

| Ventana | Posts BD |
|---|---|
| 24h | 0 |
| 48h | 0 |
| 72h | 3 |
| **7d** | **37** |
| 30d | 315 |
| histórico | 1,681 |

**Causa raíz del "19":**
- Hook `useSocialPosts` con `per_page: 50` sin filtro window explícito.
- Frontend hace dedup por `content.slice(0,100) + platform` → 37 posts/7d → 19 únicos por contenido.
- Probable: endpoint backend default retorna ventana ~7d implícita.
- "19 originales" es artefacto del dedup, no de cobertura real BD.

### Problemas detectados Monitoreo Social

**P1 · HIGH · Bajada de 315 a 19 sin caveat al usuario:** ventana implícita y dedup invisibles. Usuario cree que "solo hay 19" — verdad parcial.

**P2 · HIGH · Distribución de Sentimiento "100% Neutral":** dona pura amarilla. Misma raíz que OBS-4 P2: si `sentiment_label IS NULL`, frontend asigna `Neutral` fallback → inventa dato. Cliente piloto verá "100% Neutral" como si todo estuviera clasificado.

**P3 · MEDIUM · Top por Engagement: solo 2 cards visibles, ambas "Neutral":** mismo problema sentiment_label.

**P4 · LOW · Trending CDMX empty state legítimo:** "Sin trends en este periodo. El worker corre cada hora y necesita posts recientes con mención de alcaldía o coordenadas". OK · honesto.

---

## OBS-9 · ¿Por qué Monitoreo Social y Comentarios están separados? (2026-05-19 tarde)

**Pregunta CEO:** "Recuerdame por qué tenemos Monitoreo Social y Comentarios separados? Por qué no todo en un solo submenu?"

### Razón histórica/técnica (BD)

| Vista | Entidad BD | Hook | Filtros principales |
|---|---|---|---|
| Monitoreo Social | `social_posts` (publicaciones del dirigente · lo que él escribe) | `useSocialPosts` | platform, search, dirigente_id |
| Comentarios | `social_comments` (audiencia · lo que otros dicen sobre el dirigente) | `useSocialComments` | post_id, sentiment, dirigente_id, paginación |

Son entidades distintas en BD con relación FK (`social_comments.parent_post_id → social_posts.id`). Cada una tiene su propio scraper, NLP pipeline, filtros y workflow de clasificación.

### Por qué la separación NO se justifica para el usuario final

- Conceptualmente el usuario piensa "qué pasa con mi presencia en redes" — no "voy a ver primero MIS posts y luego LO QUE DICEN de mí".
- Distinción autor/audiencia es interna del modelo de datos, NO un mental model natural.
- "Monitoreo Social" como label no comunica "mis posts" (etiqueta ambigua).
- El cliente piloto (Saymi/Misael) tiene que aprender 2 vistas para responder UNA pregunta: "¿cómo va mi presencia?".

### Conexión con el Plan Content Hub v2 (ya aprobado)

Esta pregunta VALIDA la dirección del Content Hub. El plan ya prevé:

| Fase Content Hub | Item relacionado |
|---|---|
| F1 · UnifiedPostCard | Componente que representa post + sus comments + polaridad agregada |
| F2 · refactor /social + /content/top | Consolida vistas de posts |
| **F4 · Posts Workspace `/dashboard/contenido`** | **Consolida TODO: Monitoreo + Comentarios + Top + Fans en una sola ruta con vistas conmutables. Las 4 rutas viejas redirigen 308 a esta.** |

**En el modelo Workspace F4:**
- Vista `feed` = posts del dirigente (lo que Monitoreo hace hoy)
- Vista `comentarios` = comments con su post padre embebido (lo que Comentarios hace hoy)
- Vista `top` = ranking (lo que Top Posts hace hoy)
- Vista `fans` = audiencia que reacciona (lo que Fans y Perfiles hace hoy)

Todo con un solo set de filtros globales (rango fecha, plataforma, dirigente, sentiment) en un solo endpoint backend `/api/v1/posts/unified`.

### Recomendación operativa

**Corto plazo (post-piloto):** mantener Monitoreo y Comentarios separados HOY. Cliente Saymi/Misael ya van a ver la versión actual mañana.

**Mediano plazo (F4 Content Hub · backlog 4-6 sem):** consolidar en `/dashboard/contenido`. La distinción `social_posts` vs `social_comments` se mantiene en BD pero se UI se unifica con un toggle "Posts ⇄ Comentarios" o sub-tabs.

**No es decisión de hoy, ya está agendada en el plan Content Hub aprobado.**

---

## Resumen problemas detectados ordenados por impacto (2026-05-19 tarde · v2)

| Vista | # | Severity | Problema | Status |
|---|---|---|---|---|
| Overview | 1 | HIGH | Chart lee `sentiment_label` legacy en lugar de `tono_discurso` nuevo · muestra "0% clasificados" cuando es 26% | Pendiente fix |
| Overview / Monitoreo / Top Posts / Publicaciones Recientes | 2 | HIGH | Cards con tag `Neutral` hardcoded fallback (inventa dato · viola "NUNCA inventar") | Pendiente fix |
| Top Posts | 3 | HIGH | Doble `@@saymipineda` en handles · visible cliente | Pendiente fix cosmético |
| Top Posts | 4 | HIGH | Engagement % sin threshold mínimo · post nicho 154 likes gana a viral 2.2K · sesgo para insumo IA | Pendiente decisión producto |
| Fantasmas | 5 | HIGH | Card Negativos usa likes_publicos vs chart usa reactors · disonancia semántica | Mitigación Hugo re-scrape + glosario |
| Monitoreo | 6 | HIGH | "19 posts" cuando BD tiene 315 · dedup + ventana implícita sin caveat al usuario | Pendiente fix UX + label |
| Monitoreo | 7 | HIGH | Distribución Sentimiento "100% Neutral" cuando 0 clasificados reales (donut amarillo entero) | Pendiente fix (mismo que #2) |
| Fans y Perfiles | 8 | HIGH | Lista cliente_seed Saymi NO visible por default · escondida tras filter "Cliente" | Gemini sugiere split-view |
| Top Posts | 9 | MEDIUM | Sin indicador plataforma por card | Pendiente fix UX |
| Top Posts | 10 | MEDIUM | Posts con 0/0/0 interacción social en top | Pendiente decisión producto |
| Overview | 11 | MEDIUM | Chart empty disfrazado de bar al 100% | Pendiente fix |
| Fantasmas | 12 | MEDIUM | Banda gris solo explica derecha · abril sin explicación | Pendiente fix UX |
| Sidebar | 13 | MEDIUM | Monitoreo Social + Comentarios separados sin razón funcional para usuario | YA en plan Content Hub F4 (backlog) |
| Overview | 14 | LOW | Filtros "sin RTs" en Facebook | Pendiente fix UX |
| Top Posts | 15-16 | LOW | Sort secundario · explicación "228 elegibles" | Pendiente fix UX |

