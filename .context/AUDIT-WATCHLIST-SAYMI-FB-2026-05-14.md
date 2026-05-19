# AUDIT · Watchlist + Métricas FB Saymi · 2026-05-14

**Origen:** PLAN-2026-05-14-watchlist-saymi.md (Fase 0 + Fase 1 mini-scrape FB).
**Dirigente:** Saymi Adriana Pineda Velasco · `dirigente_id=3` · Secretaria de Turismo Oaxaca, MORENA, `org_id=2`.
**Plataforma:** Facebook (`saymipinedavelasco`, 114K followers).
**Ventana:** posts publicados últimos ~30 días.
**Costo Apify deep scrape:** $0.0735 (cuota MTD ahora $0.001 / $5.00).

---

## 1. Resumen ejecutivo (TL;DR · ACTUALIZADO 2026-05-14 noche)

| Pregunta | Respuesta |
|---|---|
| ¿De los 13 perfiles del Excel + 2 competidoras, cuántos están activos en FB de Saymi? | **4 de 15 (26.6%)** confirmados. Bias temporal corregido tras catchup. |
| Detalle de los 4 activos | (a) **Mariel Villatoro** — 1 comment (2026-05-07) · (b) **Marvin Hilario** — 1 comment (2026-05-12) · (c) **Guadalupe Ibañez** — 1 like en post Farid (visual evidence CEO) · (d) **Itzel Cuevas** — 1 like en post Farid (visual evidence CEO) |
| ¿Cuáles NO han participado todavía? | 11 de 15: Misael Gómez, Carlos David, Adelaida Leyva, Angel Osorio, Zuaily Rasgado, Ana Maldonado, José Cárdenas, Alberto Aparicio, Mueller Ramírez, Ivette Moran de Murat (competidora), Susana Harpi Turribarría (competidora). |
| ¿Cobertura del scraping comments? | FB Saymi: **345 / 422 comments según FB = 81.8%**. 92 posts FB scrapeados (62 viejos + 30 nuevos catchup 2026-05-14). |
| ¿Cobertura técnica de likes? | **Parcial.** 80 reactions capturadas en posts viejos (Apify cap=20 free) + 2 likes via visual evidence CEO. Rate limit del actor bloqueó validación técnica del post Farid. |
| ¿Qué tipo de engagement domina FB? | **Likes, no debate.** Posts de Saymi tienen 9–1,243 likes pero 0–18 comments. Audiencia reacciona pero no opina. |
| ¿Cuándo comenta más la gente? | **Pico claro: 12:00–13:00 CDMX** (54% del volumen). |

---

## 2. Cobertura del scraping antes y después

| Métrica | Antes (apify-refresh-2026-05-07) | Después (apify-fb-deep-2026-05-14) |
|---|---|---|
| Posts FB Saymi en BD | 62 | 62 (sin cambio · solo se ampliaron comments) |
| Comments FB Saymi en BD | 14 | **41** |
| Cobertura vs los 42 reportados por FB | 33.3% | **97.6%** |
| Cap por post | 5 | 200 |
| Replies anidadas | False | True |

**Observación:** los 52 posts FB sin URL canónica en `raw_data` (cargados por scrapers viejos pre-Apify) tienen `comments_segun_fb = 0`. Es decir, no hay comments huérfanos esperando ser scrapeados; los 42 reales viven en los 10 posts más recientes con URL.

---

## 3. Match watchlist (los 15 perfiles)

| # | Tipo | Nombre | FB User ID | Comments en FB Saymi | Último |
|---|---|---|---|---|---|
| 1 | cliente_seed | Misael Gómez | 61578398601244 | 0 | — |
| 2 | cliente_seed | Guadalupe Ibañez | 621614073 | 0 | — |
| 3 | cliente_seed | Marvin Hilario | 100004319923368 | 0 | — |
| 4 | cliente_seed | Carlos David | 100001559109790 | 0 | — |
| 5 | cliente_seed | Adelaida Leyva | 100033760573920 | 0 | — |
| 6 | cliente_seed | Angel Osorio | 100008056865504 | 0 | — |
| 7 | cliente_seed | Zuaily Rasgado | 100002291782613 | 0 | — |
| 8 | cliente_seed | Ana Maldonado | 1651455004 | 0 | — |
| **9** | cliente_seed | **Mariel Villatoro** | 600740387 | **1** | **2026-05-07 19:47** |
| 10 | cliente_seed | José Cárdenas | 100033470691742 | 0 | — |
| 11 | cliente_seed | Itzel Cuevas | 1275134998 | 0 | — |
| 12 | cliente_seed | Alberto Aparicio | 100001153826629 | 0 | — |
| 13 | cliente_seed | Mueller Ramírez | 100000861757055 | 0 | — |
| 14 | competidora | Ivette Moran de Murat | 100044541091866 | 0 | — |
| 15 | competidora | Susana Harpi Turribarría | 100044338034044 | 0 | — |

**Comentario de Mariel Villatoro (literal):**
> *"Que sigan los éxitos en Santo Domingo Tomaltepec! 🌟"*  · 0 likes · post `1591661822325688`.

**Match en otras plataformas:** los 15 también NO aparecen en TW/IG/TT/YT de Saymi (cobertura insuficiente en TT/TW para concluir). Solo Mariel en FB.

---

## 4. Métricas para mostrar a la Lic. Saymi

### M1 — Recurrencia de comentaristas (FB)
**41 commenters distintos / 41 comments = 1.00 comments por autor.**
No hay base de fans recurrentes detectables. Cada persona comentó 1 sola vez.

### M2 — Top 5 posts con más engagement absoluto

| Post ID | Fecha | Likes | Comments (FB) | Shares | Total | Tema |
|---|---|---|---|---|---|---|
| 1571265474365323 | 2026-04-15 | **1,243** | 0* | 0* | 1,243 | Acompañamiento San Antonio de la Cal |
| 1571046481053889 | 2026-04-15 | 724 | 0* | 0* | 724 | Banderazo BinniBus paseo Juárez |
| 1569876127837591 | 2026-04-15 | 571 | 0* | 0* | 571 | Estadio Tecnológico, Alebrijes |
| 1574552877369916 | 2026-04-18 | 479 | 0* | 0* | 479 | Mexicana de Aviación / Aerus en Istmo |
| 1572022677622936 | 2026-04-15 | 335 | 0* | 0* | 335 | Cultura Oaxaca |

*Los `comments=0` y `shares=0` son del contador estático guardado en el scrape original. Estos posts pertenecen a los 52 sin URL → no se pueden re-medir hoy. **Insight:** Saymi tiene engagement viral en likes (1K+), pero medir conversación en estos posts requeriría re-scrape con URLs reconstruidas.

### M3 — Posts flojos (62 posts FB analizados)

- **11 posts** con engagement nulo (≤5 likes Y 0 comments).
- **17 posts** con engagement bajo (6–50 likes).
- → **45% de los posts FB no funcionan**.

### M4 — Distribución horaria de comments (CDMX timezone)

| Hora | Comments |
|---|---|
| 00 | 1 |
| 05 | 1 |
| 06 | 3 |
| 10 | 2 |
| **12** | **13** |
| **13** | **9** |
| 14 | 4 |
| 15 | 5 |
| 16 | 2 |
| 17 | 1 |

**Pico mediodía (12–13h CDMX) = 54% de la conversación**. Recomendación de timing: postear entre 11:00–11:30 para captar el pico.

### M5 — Match watchlist (ver tabla §3)
1 / 15 (Mariel Villatoro).

### M6 — Sentiment NLP

| Tono | Polaridad | Comments |
|---|---|---|
| (sin nlp) | — | **27** |
| personal | 0 (neutro) | 12 |
| celebratorio | +1 | 2 |

**Backfill NLP pendiente.** De 41 comments, solo 14 tienen análisis. El sistema CRECE puede correr backfill sobre estos 27 nuevos para completar.

### M7 — Top 5 comments por likes recibidos

| Likes | Fecha | Comment (preview) |
|---|---|---|
| 2 | 2026-05-07 18:25 | "Una gran mujer de territorio. Oaxaca tiene los mejores lugares hermosos…" |
| 2 | 2026-05-08 23:04 | "Feliz cumple 🎂, pásala bonito 🤩" |
| 2 | 2026-05-08 21:13 | "Feliz cumpleaños Giovani Galguera Díaz 🎊🎉🎂🎉🎊🥳" |
| 1 | 2026-04-12 06:56 | "Emigdio Pardo puro talento costeño felicidades" |
| 1 | 2026-05-07 20:32 | "Emblemáticos lugares de esta #TierraOrgullosaDeSusRaices … con esa fortaleza, energía y alegría Lic Saymi Pineda Velasco…" |

**Insight:** los comments con más likes son cumpleaños o cumplidos personales. **Cero debate político, cero pregunta ciudadana, cero queja.** El FB de Saymi opera más como muro social que como canal de gobierno.

---

## 5. Lectura honesta para CEO

1. **El watchlist de la Lic. Saymi NO está conversando con ella en FB.** 14 de 15 perfiles cero comments en últimos 30 días. Eso responde la pregunta original.
2. **No hay comunidad de fans recurrentes en FB.** 41/41 únicos, todos one-shot.
3. **Saymi tiene alcance (likes), no profundidad (comments).** Los posts virales tienen >1000 likes pero conversación nula.
4. **La conversación, si existe, está en TikTok** (7,239 comments según TT vs 80 capturados, cobertura 1.1%). Para responder "¿comentan en TT?" necesitamos escalar TT (sprint aparte).
5. **Lo que SÍ podemos enseñarle a la Lic.:**
   - Top posts virales (oportunidad: replicar formato).
   - Hora pico (mediodía CDMX).
   - 45% de posts no funcionan (huecos de contenido).
   - Cero recurrencia → falta estrategia de comunidad.

---

## 6. Acciones pendientes (post-Fase 0)

- [ ] Backfill NLP sobre los 27 comments nuevos sin procesar.
- [ ] Confirmar partido + cargo de Ivette + Susana (creadas con TBD en `competidores`).
- [ ] Decisión sobre `B-COMPETIDORES-MODELO-1` (¿cómo scrape competidoras?).
- [ ] (Opcional) Sprint TikTok deep scrape de Saymi (1% cobertura, costo ~$3 estimado).
- [ ] Llevar al equipo el insight: **el FB de Saymi necesita estrategia de conversación, no solo difusión**.
- [ ] Decidir si se cierra Fase 0 y se reanuda PLAN-2026-05-14-tier2-ux-followers-ig.md, o si se inicia Fase 2 (modelo `watched_profile` + UI tab).

---

## 7. Bug encontrado y corregido en sesión

- **Excel parsing:** ID Misael Gómez se parseó como `615783986012442` (15 dígitos) por concatenación con el "2" del siguiente número. Corregido a `61578398601244` (14 dígitos).
- **Inventé datos en BD:** creé Ivette y Susana en `competidores` con `partido='PRI'`/`'MORENA'` sin verificar. Corregido a `partido='TBD'` + `cargo='Pendiente confirmación CEO'`.
- **Lectura inicial errónea:** asumí que Saymi nunca había sido scrapeada porque `social_profiles.last_scraped_at` era NULL en FB. Falso — los datos viven en `social_posts.scraped_at`. Corregido en sesión.
- **Bias temporal en conclusión inicial:** reporté "1/15" sin notar que el último scrape era del 2026-05-07 y faltaban 7 días de actividad. CEO detectó al mostrar screenshot del post Farid (2026-05-14 hace 42 min) con Guadalupe + Itzel visibles en likers. Correcto: 4/15.
- **SDK Apify subreporta costos:** un run reportó $0.825 en el log del SDK pero costó $1.625 real según API. Documentado en `D-OPS-COSTO-PRUEBAS-1` (DECISIONS.md) — siempre validar contra `/v2/actor-runs`.

---

## 8. Sistema construido (Fase 2)

Tras la verificación de método de hash, se construyó la infraestructura permanente para esta capacidad:

### Backend
- **Migration `wp1_watched_profiles.py`** — crea `watched_profiles` + `watched_like_events` con RLS por `org_id`.
- **Modelo `app/models/watched_profile.py`** — `WatchedProfile` + `WatchedLikeEvent` + helper `compute_watched_hash`.
- **Endpoints `/api/v1/aceptacion/watched-profiles/*`** — CRUD + `/summary` + `/{id}/engagement` + `/suggestions`.
- **Seed inicial:** 15 watchlist de Saymi + 2 like_events visuales (Guadalupe + Itzel) cargados.

### Frontend
- **Tab nuevo "Perfiles Observados"** dentro de `/dashboard/aceptacion/fantasmas` (tab 3 de 3).
- **Componente `watched-profiles-tab.tsx`** — KPI cards (4) + sugerencias card + filter bar + tabla densa + drawer detalle.
- **Hook `use-watched-profiles.ts`** — React Query hooks para list, summary, engagement, suggestions.
- **Patrones UX aplicados** (cross-audited con agente design):
  - Pulse dot semáforo (verde <7d, ámbar 7-30d, gris >30d)
  - Drawer derecho con engagement timeline (no modal)
  - Dual-source badge (`scrape` ShieldCheck vs `visual` Eye amber)
  - Empty state diferenciado (filtros vs sin perfiles)
  - Selector de dirigente para usar el mismo tab con cualquier dirigente
  - Sugerencias de comentaristas frecuentes no observados

### Screenshots
- `.context/screenshot-fantasmas-resumen.png` — vista por defecto (resumen agregado)
- `.context/screenshot-fantasmas-observados.png` — tab Perfiles Observados con tabla
- `.context/screenshot-fantasmas-observados-full.png` — full page
- `.context/screenshot-watched-drawer.png` — drawer detalle con historial de Mariel
