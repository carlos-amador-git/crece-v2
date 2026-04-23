# Sprint 23-B · Investigación scraper fields (F-23-05 datos)

**Fecha:** 2026-04-23.
**Scope:** investigar estado real de `comment_count`, `share_count`, `source_url` antes de proponer migration en piloto activo (alerta Gemini cross-audit).

## Hallazgos del modelo

Archivo `backend/app/models/social.py:155-196`:

| Campo | Presencia en modelo | Default | Nota |
|---|---|---|---|
| `likes` | ✅ `Integer, default=0, nullable=False` | 0 | Existe |
| `comments` | ✅ `Integer, default=0, nullable=False` | 0 | Existe — valores 0 en UI = "no recolectado" o "sin comments reales", ambiguo |
| `shares` | ✅ `Integer, default=0, nullable=False` | 0 | Existe — misma ambigüedad |
| `views` | ✅ `Integer, default=0, nullable=False` | 0 | Existe |
| `url` / `source_url` | ❌ **NO existe columna dedicada** | — | Solo hay `platform_post_id` (raw id scrapeado) |

## Hallazgo del schema/API

Archivo `backend/app/schemas/social.py:39` `SocialPostResponse`:

- **No expone `url` en la respuesta.** El frontend (`frontend/src/lib/api/types.ts:86`) define `url: string` como required pero el backend nunca lo envía → en runtime llega como `undefined`.
- Mi fix de Sprint 23-A (`hasUrl = Boolean(post.url && post.url.trim().length > 0)`) hace graceful degradation correcto. Tarjetas NO son clickeables porque `post.url` es undefined.

## Hallazgo crítico para F-23-03/F-23-04

Archivo `backend/app/api/v1/endpoints/social.py:113-121` `sentiment_timeline`:

```python
async def sentiment_timeline(
    ...,
    platform: Platform | None = None,      # ✅ ya soportado
    date_from: date | None = None,
    date_to: date | None = None,
    include_rts: bool = False,              # ✅ ya soportado
) -> list[SentimentTimelinePoint]:
```

**Revelación:** el backend ya acepta `platform` e `include_rts`. El frontend hook `useSentimentTrend` NO los propaga. **F-23-03 + F-23-04 NO requieren cambios de backend.** Se resuelven con frontend puro — calificación **🟡 CALIB sin bloqueante.**

Bonus: el hook frontend acepta `days: number` pero el backend no tiene param `days` (usa `date_from`/`date_to`). El valor no se está enviando. No bloqueante pero anotar como deuda.

## Propuestas de fix

### Propuesta P1 — URL computada en schema (F-23-05 datos) · NO requiere migration

Extender `SocialPostResponse` con campo `url: str | None = None` computado a partir de `platform + platform_post_id + handle` en el endpoint `list_posts`. Patrón:

| Platform | Template |
|---|---|
| TWITTER / X | `https://x.com/{handle}/status/{platform_post_id}` |
| INSTAGRAM | `https://www.instagram.com/p/{platform_post_id}/` (requiere que `platform_post_id` sea shortcode, no id numérico) |
| FACEBOOK | `https://www.facebook.com/{handle}/posts/{platform_post_id}` (aproximado) |
| YOUTUBE | `https://www.youtube.com/watch?v={platform_post_id}` |
| TIKTOK | `https://www.tiktok.com/@{handle}/video/{platform_post_id}` |

**Riesgo:** si algún scraper guarda `platform_post_id` con formato distinto al esperado, la URL queda mal. Mitigación: unit test por plataforma + dejarlo `None` si no hay handle disponible. Graceful degradation ya cubre `None`.

**Esfuerzo estimado:** 1-2h backend + 30min validation. **No toca BD.** No hay migration. Puede cerrarse dentro del piloto sin §9.8.

### Propuesta P2 — `url` como columna persistida · §9.8 REQUERIDO

Alternativa robusta: añadir `url: str | None` como columna en `social_posts` y poblarla desde el scraper cuando esté disponible en el raw HTML/JSON.

- Migration alembic + backfill ~1.2K comments actuales + update de 5 scrapers activos.
- Toca BD en prod del piloto → ventana de mantenimiento + plan de rollback (Gemini riesgo #1).
- Propuesta para §9.8 del 2026-05-20.

### Propuesta P3 — Diferenciar 0 real vs no-recolectado (F-23-05 contadores) · §9.8 REQUERIDO

Campos `comments`, `shares` como `Integer | None` (nullable=True). Scrapers escriben `None` si no lograron leer, `0` si leyeron y era 0. Frontend pinta "—" para None, "0" para 0.

- Migration alembic que cambia nullability → bloquea tabla → mantenimiento.
- Refactor de 5+ scrapers para distinguir los dos casos.
- Propuesta para §9.8 del 2026-05-20.

## Decisión recomendada

1. **Hoy (Sprint 23-B cerrado):** ejecutar **Propuesta P1** — URL computada en schema/API, graceful degradation ya en frontend.
2. **Hoy (bonus):** wirear frontend `useSentimentTrend` con `platform` e `include_rts` → cierra F-23-03 + F-23-04 como CALIB sin tocar backend.
3. **Propuesta para §9.8 del 2026-05-20:** Propuestas P2 (url column) + P3 (nullable counters) agrupadas como "schema hardening social_posts".

## Estado

- ✅ Investigación completa
- ⏸ Ejecución P1 + F-23-03/04 pendiente (ver Sprint 23-B.2 en PLAN)
- 📋 P2 + P3 documentadas para §9.8
