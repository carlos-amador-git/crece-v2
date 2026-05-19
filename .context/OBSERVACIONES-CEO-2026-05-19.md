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
