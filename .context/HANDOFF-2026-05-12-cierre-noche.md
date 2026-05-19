# HANDOFF · Cierre 2026-05-12 noche · próxima sesión 2026-05-13

## TL;DR para la sesión siguiente

CEO pidió arrancar nueva sesión para:
1. **Feature seguidores**: dirigentes quieren ver nombres de followers + si comentaron
2. **OAuth real**: doctrina = dirigentes dan accesos → scraper privilegiado
3. **Pipeline auditoría**: dejar de descubrir huecos de población usando la app manualmente

Plan completo en `.context/PLAN-2026-05-13-followers-oauth-pipeline.md` · `PLAN-current.md` redirige ahí.

## Lo que se hizo HOY (2026-05-12 tarde+noche)

### Sprint A · UX Perfil Dirigente (commit `07f5f57`)
7 fixes Gemini ronda 2 + nueva opción "Área Apilada" en sentiment chart:
- S1 Sentimiento Timeline 3 chart types (línea/barras/área apilada) + localStorage
- S2 Engagement bar chart `formatNumber` en ejes
- S3 Badges sentimiento contrastantes
- S4 ProfileHeader balanceado (60% izq · IPD der · redes en box)
- S5 ActividadAlineada empty state shimmer + pulsing dot "IA procesando"
- S6 Semáforo badge stale más vibrante + ping
- S7 Sidebar Recomendaciones → Wand2

Gemini cross-audit: ✅ Resuelto en los 7. "Ready for demo".

### Sprint B · Thumbnails (commit antes del último)
- Migration `spm_media1` agrega `social_posts.media_urls jsonb`
- Backfill desde `raw_data` (26 posts YouTube)
- Scrapers IG (ensta + instaloader) + FB capturan `media_urls` al persistir
- PostCard rediseñado: miniatura 60×60 con fallback a PlatformIcon

### Sprint C · Bug endpoint comentarios (commit último)
**Diagnóstico**: `/dashboard/social/comentarios` mostraba "Sin comentarios" pese a
**2,830 comments** en BD. El endpoint `GET /api/v1/social/comments` **no existía**
en backend (solo había PATCH/POST en HITL).

**Fix**: nuevo endpoint paginado scoped por org_id en `social.py`:
- Filtros: dirigente_id, platform, tono, polaridad
- JOIN comment → post → profile → dirigente
- Schema 1:1 con type `SocialComment` del hook frontend

## Estado del repo

- Branch: `feat/phase-b-pesos-editables`
- Último commit: `feat(social): endpoint GET /social/comments paginado scoped`
- Pushed a origin ✅
- Vercel deploy live: `frontend-zeta-sepia-46.vercel.app` (con sprint UX)
- Backend Mac Mini :8002 healthy con endpoint comments registrado
- Tunnel cloudflared `added-causing-obituaries-newsletters` vivo (PID 61084)
- Docker compose: 8 containers up (backend + db + celery worker/beat/flower + frontend + minio + redis)

## Auditoría que reveló estado real (NO rehacer)

| Pendiente del backlog inicial | Estado | Evidencia |
|---|---|---|
| G-1 cron snapshots followers | ✅ Ejecutado HOY 19:04 UTC | 31 rows en `social_profile_snapshots` |
| G-3 Neutro vs Institucional | ✅ Backend + Frontend hechos | `humanizacion_service.py` línea 175-186 + `cards.tsx` línea 680-681 |
| Pepe Monroy onboarding | ✅ Completo | Dirigente id=57 + user `pmonroy@paz.mx` VIEWER + perfiles IG/FB |
| Efemérides módulo | ✅ Completo | 70 fechas seedeadas + endpoint `/calendario/proximas` + hook + card |
| S3b thumbnails | ✅ Hoy 2026-05-12 | Sprint B arriba |
| Bug comments | ✅ Hoy 2026-05-12 | Sprint C arriba |

## Pendientes que VAN a la próxima sesión (PLAN-2026-05-13)

| Sprint | Tema | Esfuerzo |
|---|---|---|
| S1 | Modelos `social_followers` + `follower_engagement` + migration | 45 min |
| S2 | OAuth real YouTube (Google Console · sin App Review) | 1.5h |
| S3 | Scraper privilegiado YouTube usando OAuth token | 45 min |
| S4 | Vista frontend "Mis seguidores" | 1h |
| S5 | Pipeline auditoría de campos (corre nightly + pre-commit) | 1h |
| S6 | OAuth IG/FB DIFERIDO · documentar Meta App Review gate | 0h |

## Memoria persistente actualizada (2026-05-12 noche)

Ver auto-memory en:
- `~/.claude/projects/-Users-marxchavez-Projects-crece-v2/memory/MEMORY.md`
- Nuevas memorias: `project_session_close_2026_05_12_noche.md`,
  `feedback_audit_before_rebuild.md`, `project_followers_oauth_pending.md`

## Reglas que la próxima sesión DEBE respetar

1. **AUDITAR antes de implementar.** Hoy 2 veces fallé en esto:
   - Propuse rehacer efemérides cuando ya estaba 100% completo
   - Propuse rehacer Pepe Monroy cuando user+dirigente+plataformas ya existían
   - El user llamó la atención · disculpa formal · re-corregido

2. **NO correr scrapers como parte de onboarding.** Crear org+dirigente+user
   es suficiente. Los scrapers son async y corren en su ciclo.

3. **NO inventar mocks/fallbacks con números.** Si endpoint no listo → Skeleton
   o estado vacío explícito (regla D-ANTI-MOCK-1).

4. **Karpathy reglas #1-4 son obligatorias.** Especialmente Surgical Changes:
   tocar solo lo necesario, no "mejorar" código adyacente.

## Cosas que descubrimos por accidente (worth documentar)

- El `humanizacion_service.py` separa Neutro/Sin marcador desde
  D-HUMANIZ-NEUTRO-1 (mismo día). Frontend ya lo renderiza. Reportar como bug
  estaba obsoleto.
- 70 efemérides ya seedeadas con seed_efemerides.py. La card está fusionada
  dentro de `/dashboard/recomendaciones` (no en `/calendario` que redirige).
- El scraper IG (instaloader/ensta) NO guardaba media_urls hasta hoy.
  IG retroactivo queda sin thumbnails hasta el próximo ciclo.

## Comando para arrancar mañana

```bash
cd ~/Projects/crece-v2
# Verificar branch correcto
git status

# Leer plan
cat .context/PLAN-2026-05-13-followers-oauth-pipeline.md

# Arrancar dev
docker compose up -d
docker compose ps
```

## Riesgo conocido

- **HANDOVER-AI.md** se modificó automáticamente durante esta sesión (hook
  de compactación). Cambios incluidos en commit ux pero el contenido es de
  sesiones previas, no de hoy. Si la próxima sesión se confunde con eso,
  ignorarlo y partir de este HANDOFF.

---

Cierre 2026-05-12 23:30. Sesión Linda.
