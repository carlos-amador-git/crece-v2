# HANDOFF · sesión 2026-05-14 · cierre por contexto al 3%

## Lo que se hizo hoy

1. **Watchlist Saymi FB** completa: 13 watched · 8 activos (17 reactions: 8 like + 4 love + 3 care + 2 like-visual) · sistema backend+frontend funcional
2. **Pool Apify 3 cuentas** con rotación · $11+ usado · $3.89 restante · helper `backend/app/services/apify_pool.py`
3. **Modelo `competitor_profile`** ligero (mensual) + migraciones cp1+cp2 + endpoint
4. **Exploratorio stack gratuito likers** completo · `.context/EXPLORATORIO-LIKERS-STACK-GRATUITO-2026-05-14.md`
5. **`backend/scripts/ig_likers_instagrapi.py`** smoke-tested OK · 155 likers IG capturados a $0
6. **Prompt scraper propio** para investigación paralela CEO · `.context/PROMPT-INVESTIGACION-SCRAPER-PROPIO-2026-05-14.md`

## Aclaración para el CEO

"X/TT/YT plataforma no expone" se refería **solo a lista nominal de quién dio like a un post específico**. Posts/followers/comments/stats ya cubiertos en stack gratuito. Solo la lista nominal de reactors es inaccesible (X removió 2023, TT/YT nunca expusieron).

## Pendientes próxima sesión (orden de prioridad)

### Críticos
1. **Migración `cp3`**: ampliar `ck_watched_like_source` para incluir `instagrapi_auth`. Workaround actual: `ig_likers_instagrapi.py` usa `'other_scraper'` (ver nota línea ~159 del script)
2. **Cargar handles IG** para los 13 watched de Saymi (hoy watchlist es FB-only, por eso 0 matches IG)
3. **Refinar scroll Playwright FB** `/tmp/fb_extract_reactors.py`: subir iter 8→20 + scroll del scrollable interno · script no committeado

### Medios
4. Auto-relogin headless FB (storage_state expira ~30 días)
5. Cooldown reactions Apify Saymi $0.43 — opcional, ya hay validación suficiente
6. Confirmar partido Ivette Morán (provisional: Independiente)

### Bajos
7. Revisar respuesta claude.ai del prompt (cuando CEO la traiga) sobre Nivel 2/3 scraper propio
8. Onboarding Pepe Monroy (id=57) cuando cliente PAZ entregue watchlist

## Archivos sin commitear

```
.context/AUDIT-WATCHLIST-SAYMI-FB-2026-05-14.md
.context/EXPLORATORIO-LIKERS-STACK-GRATUITO-2026-05-14.md
.context/PLAN-2026-05-14-stack-gratuito-likers.md
.context/PLAN-2026-05-14-watchlist-saymi.md
.context/PROMPT-INVESTIGACION-SCRAPER-PROPIO-2026-05-14.md
.context/HANDOFF-2026-05-14-stack-gratuito-likers.md

backend/app/api/v1/endpoints/competitors.py
backend/app/api/v1/endpoints/watched_profiles.py
backend/app/models/competitor_profile.py
backend/app/models/watched_profile.py
backend/app/services/apify_pool.py
backend/migrations/versions/cp1_competitor_profiles.py
backend/migrations/versions/cp2_competitor_monthly.py
backend/migrations/versions/wp1_watched_profiles.py
backend/scripts/apify_fb_catchup_posts_saymi.py
backend/scripts/apify_fb_deep_saymi.py
backend/scripts/apify_fb_likes_watchlist_v2.py
backend/scripts/apify_fb_reactions_saymi.py
backend/scripts/apify_fb_reactions_scraper_one.py
backend/scripts/ig_likers_instagrapi.py  ← NUEVO HOY

frontend/src/lib/api/hooks/use-competitors.ts
frontend/src/lib/api/hooks/use-watched-profiles.ts
frontend/src/components/aceptacion/watched-profiles-tab.tsx
[+ modificados: __init__.py, fantasmas/page.tsx, models/__init__.py]
```

**Migraciones BD aplicadas**: wp1 (watched_profiles+watched_like_events) · cp1 (competitor_profiles+posts+weekly) · cp2 (rename weekly→monthly)

## Pool Apify final

```
SOPORTE: $4.00 used · $1.00 disp
ANGEL:   $4.99 used · $0.01 disp
RAFA:    $4.69 used · $0.31 disp
Total disponible cross-cuentas: $1.32
```

## Estado UI

`/dashboard/aceptacion/fantasmas` → tab "Perfiles Observados":
- 13 observados · 8 activos (62%) · 2 comments · 17 reactions detectadas (label corregido de "Likes")
- Sección "Competidores monitoreados" con 2 (Ivette + Susana) y badges verified
- Drawer con timeline al click row
- 8 sugerencias de comentaristas frecuentes sin observar

Memoria persistente actualizada con todos los hallazgos clave (3 archivos nuevos en `~/.claude/projects/.../memory/`).
