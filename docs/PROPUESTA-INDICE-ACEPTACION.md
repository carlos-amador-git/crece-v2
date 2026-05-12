# Propuesta — Índice de Aceptación (IA) por publicación

**Fecha:** 2026-04-13
**Autor de la conversación:** Joy (sesión CRECE v2) con CEO
**Estado:** Análisis de viabilidad — NO aprobado para implementación todavía
**Origen:** Idea del CEO: "ver cuántos seguidores emitieron comentario, dieron like, cuántos rechazaron; cuántos externos manifestaron algo; incluso quiénes de los seguidores no hicieron caso de la publicación"

---

## Pregunta original del CEO

> "El político hace una publicación o un reel y recibe muchos likes, u otros comentarios. Lo interesante, por ejemplo, sería ver cuántos seguidores emitieron comentario, dieron like, cuántos rechazaron, etc. Y adicional, cuántos externos manifestaron algo, o incluso comentaron. Esto incluso podría llevarse a ver exactamente qué seguidores no hicieron caso de la publicación."

## Reformulación en tres preguntas distintas (no mezclar)

1. **Activación interna** — ¿qué fracción de mi base ya conquistada reaccionó?
2. **Expansión externa** — ¿el mensaje cruzó la burbuja y llegó a no-seguidores?
3. **Aceptación / rechazo** — de los que reaccionaron, ¿cuántos aprobaron vs rechazaron?

Y una pregunta bonus:
4. **Mapa de fantasmas** — ¿qué seguidores ignoran sistemáticamente al dirigente?

---

## Viabilidad técnica hoy, por plataforma

| Plataforma | Lista followers | Lista likers | Comentaristas | Reactions breakdown | Reach/impresiones |
|---|---|---|---|---|---|
| Twitter/X | Sí (rate limit severo) | NO (X ocultó likes públicos en 2024) | Sí (replies/quotes/RT) | N/A | Solo owner |
| Instagram | Solo con Business API (token del dirigente) | Parcial (primeros N) | Sí (scrape) | Solo likes | Solo con Business API |
| Facebook | NO desde 2018 (Cambridge Analytica) | No | Sí | Sí (like/love/angry/sad/wow/haha) | Solo con Page token |
| TikTok | NO | No | Sí (público) | Solo agregados | Solo Creator API |
| YouTube | NO (privacidad) | No (solo count) | Sí | No | Solo Analytics API |

**Conclusión dura:** el cruce follower-por-follower (quién interactuó vs quién me ignoró) **solo es viable en Twitter y en Instagram si el dirigente nos da acceso Business**. En Facebook/TikTok/YouTube las APIs cerraron esa puerta por privacidad post-2018.

---

## Diseño propuesto del IA — 4 capas

### Capa 1 — Activación (solo donde se pueda cruzar)
```
activación = engagers_internos / total_followers
```
- Twitter: viable con snapshot de followers + set de repliers/quoters/retweeters.
- IG business: viable si el dirigente conecta Meta Business Suite.
- FB/TikTok/YT: N/A honesto — no se inventa.

### Capa 2 — Expansión externa
```
expansión = engagers_externos / engagers_totales
```
- Alto (>60%) = mensaje escaló, encontró audiencia nueva.
- Bajo (<20%) = solo eco de la base, contenido no viraliza.
- Viable en Twitter (replies + quotes públicos con autor) y FB/IG/TikTok/YT vía comments scrapeables.

### Capa 3 — Aprobación vs Rechazo
- Facebook: nativo (reactions breakdown — Love/Like = aprobación, Angry/Sad = rechazo).
- Resto: NLP político v1 sobre comments → polaridad.
- Advertencia: **comments de rechazo ≠ comments de rechazo de seguidor**. Mezclar troll externo con disidente interno deforma la señal. Etiquetar origen.

### Capa 4 — Mapa de fantasmas (seguidores dormidos)
- Solo Twitter/IG business.
- `followers_sin_engagement_en_últimos_N_posts / total_followers`
- Ventanas sugeridas: 30d, 90d.
- Cohortes: nuevos vs viejos, bots detectados vs humanos.

---

## Fórmula compuesta — por plataforma, no única

No se usa un IA único. Se construye un IA por red, con pesos calibrados a lo que esa red permite medir. Luego un IA global como promedio ponderado por audiencia, análogo al IPD 0-10 actual.

```
IA_red = α · activación + β · expansión + γ · (aprobación − rechazo)
```

Los pesos α/β/γ cambian por plataforma:
- Twitter: α alto (tenemos el cruce follower-level).
- Facebook: α = 0, γ alto (tenemos reactions breakdown nativas).
- TikTok/YouTube: β y γ dominan.

No forzar fórmula única — sería deshonesto.

---

## Riesgos y límites honestos

1. **Rate limits Twitter.** 3,673 followers de Piña tardan ~1h en scrapearse por sesión API v2. Multiplicar por 6 dirigentes × snapshot periódico = presupuesto API serio o cuenta enterprise ($$$).
2. **Términos de Servicio.** Instagram y TikTok prohíben scraping de listas de followers. Sin Business token del dirigente → ilegal + bloqueo. No se hace.
3. **Bots inflando denominador.** Un follower fake que nunca interactúa es indistinguible de un "fantasma real". Deprime la activación artificialmente. Requiere clasificador previo de bots o aceptar ruido de 15-30%.
4. **Unfollows silenciosos.** Follower que ya no sigue pero sí estaba cuando se publicó aparece como "ignoró". Solo un snapshot pre-post lo resuelve.
5. **Ironía / sarcasmo en español político.** NLP v1 (89% acc en posts) baja a ~70% en comments políticos. La métrica de rechazo es ruidosa — presentar con intervalos de confianza, no número seco.
6. **Ventana temporal.** Mapa de fantasmas requiere ≥90d de histórico. Hoy hay 0 snapshots de followers. Útil en 3 meses, no antes.

---

## Propuesta MVP (1-2 sprints, sin explotar APIs)

Construir el IA con lo que ya se puede cosechar:
- **Twitter:** activación + expansión + aceptación real. Esta es la red donde el IA "funciona completo".
- **FB/IG/TikTok/YT:** versión degradada — expansión (via comments) + aceptación (via NLP + reactions FB). Sin activación follower-level. Honesto: marcar como "IA-parcial".
- **Mapa de fantasmas:** diferir. Requiere infraestructura de snapshots mucho más pesada que `social_profile_snapshots` (esa es para agregados; fantasmas requiere `follower_snapshots` user-level).

## Versión completa (3-4 sprints, decisión estratégica)

Si el cliente pide el mapa de fantasmas:
- Conseguir Business API tokens de Meta (IG + FB) de cada dirigente — fricción política, no técnica.
- Subir plan Twitter API a tier con volumen suficiente (costo mensual notable).
- Tabla `follower_snapshots (user_id, profile_id, seen_at)` — ~3,673 followers × 4 redes × 6 dirigentes × snapshot semanal ≈ 500K filas/mes. Barato en Postgres con particionado.
- Tabla `post_engagers (post_id, user_id, type)` — volumen alto.
- Set difference calculada en vista materializada.

---

## Qué decir al cliente (honestidad)

> "Sí, se puede medir activación/expansión/aceptación en todas las redes. El mapa individual de quién ignora al dirigente solo es viable en Twitter de inmediato y en Instagram si nos das acceso Business. En Facebook es técnicamente imposible desde 2018 por políticas de privacidad de Meta — podemos medir agregados, no individuos."

---

## Decisión pendiente del CEO

Elegir entre:
- **(a) MVP agregado por post** — 1-2 sprints, todas las redes con limitaciones honestas, útil para dashboard de cada publicación.
- **(b) Mapa de fantasmas** — 3-4 sprints, solo Twitter + IG business, requiere tokens del dirigente y API Twitter paga, útil para estrategia de reactivación de base.
- **(c) Los dos en secuencia** (recomendación de Joy) — MVP ahora, fantasmas en Q siguiente cuando haya 90d de historia de snapshots. El snapshot diario del sprint actual (cirugía dirigente) ya empieza a acumular historial agregado; para fantasmas se requiere tabla adicional user-level, pero la decisión de construirla se difiere.

---

## Notas de contexto

- Esta conversación sucedió durante el sprint de cirugía al módulo dirigente (worktree `crece-v2-dirigente-surgery`, rama `feat/dirigente-surgery`).
- El snapshot diario que se construye en ese sprint (`social_profile_snapshots`) es agregado por perfil — NO captura engagement follower-level.
- La tabla `follower_snapshots` user-level NO se construye en este sprint.
- Mantener esta propuesta en backlog hasta que el CEO decida dirección.
