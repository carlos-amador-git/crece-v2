# HANDOFF — Ingest 3 dirigentes + fix fans + deploy Carlos · 2026-06-05

**Status:** cierre. Saymi+Pepe+Felipe completos. Deploy Carlos listo. Bug de fans (mío) cerrado.
**Sesión:** Linda · Claude Opus 4.8 · 2026-06-05 (larga, atendida de cerca por el CEO).
**Próxima sesión arranca con:** el PENDIENTE #1 (automatizar updates RADAR→CRECE) o los 3 dirigentes restantes.

---

## ⚠️ LEER PRIMERO
1. **Deploy Carlos listo:** código `origin/main @ 1d070c9` (sync 0/0) + Release **`data-snapshot-2026-06-05`** (re-cortado final, ~38.6MB, Saymi+Pepe+Felipe). Mensaje listo en `.context/MENSAJE-CARLOS-REDEPLOY-2026-06-05.md` (el CEO se lo pasa a Carlos). Runbook restore: `DEPLOY-COOLIFY-CARLOS.md` PASO 8.1. **Borrar el Release tras restore (PII).**
2. **Vercel** (`frontend-zeta-sepia-46.vercel.app`) ya muestra todo en vivo (vía túnel persistente → backend local). Coolify = cuando Carlos restaure.
3. **Smoke test:** 13 dirigentes · 8,118 posts · **11,218 comments** · 344,644 reactor-events.

## Qué se hizo (medido por fecha en cada paso)
- **Ingest Saymi · Pepe · Felipe** completo: comments 4 redes (FB+IG+TT+X) + reactors FB/IG + followers.
- **Huecos cazados con la regla de cobertura** (gap real = `comments_count>0` sin captura, NO "posts sin comments"):
  - Saymi reactor gap 20/05–02/06 → backfill RADAR (FB+IG).
  - Pepe IG gap (causa: 2 targets IG `pepe.monroy`+`pepemonroyma`, los 6 posts en el 2º) → cerrado.
  - Pepe FB 01/06 cutoff (+10 comments) cerrado · Pepe FB 31/05 = cero REAL (`fb_comments_section_not_found`).
- **Cards (temprano en la sesión):** dedup posts misma-red + badge plataforma · B04 etiqueta cobertura parcial · Misael override 400 (ADR-0007).

## BUG GRAVE QUE GENERÉ YO (cerrado, documentado)
Mi backfill de reactors guardó `author_hash` NUMÉRICO crudo (bypaseó `ensure_author_hash`) → rompió el join watched_profiles↔social_comments + violó pseudonimización LFPDPPP + creó duplicados de fans.
- **Causa:** no leí `D-AUTHOR-HASH-PII` (DECISIONS.md:3) ANTES de cargar. La identidad canónica es **sha256(display_name)**, no el ID numérico.
- **Fix aplicado:** (a) `scripts/fix_fans_author_hash.py` re-hash 182k fans numéricos al canónico + consolidación set-based (commit a2212df); (b) adapter `ingest_radar_reactors_v2.py` ahora usa `ensure_author_hash(display_name)` (previene recurrencia); (c) **dedup de fans en FRONTEND** (`top-fans-ranking.tsx`, commit cbc88ab) — BD INTACTA.
- **Gemini frenó una catástrofe:** mi 2ª propuesta (re-hash TOTAL de la BD) habría orfanado los comments históricos (hash por `commenter_id`). ABORTADO. La solución correcta (dedup en presentación) ya estaba en el feedback del CEO del 2026-05-20.
- **Misael Fan #1 intacto** (override por `profile_external_id`, no afectado).

## PENDIENTES (orden de prioridad)
1. **🔴 AUTOMATIZAR updates RADAR→CRECE (CEO 2026-06-05, prioridad).** Las actualizaciones NO deben depender de pasar info manual entre peers (claude-peers). RADAR debe entregar/CRECE jalar en automático (scheduled job / contrato de handoff automatizado / watch dir). Hoy todo el ingest fue manual peer-a-peer — insostenible. Diseñar el pipeline automático.
2. **Gaby / Ballesteros / Piña** — ingest de comments pendiente (pedir handoff a Hugo). Marcado en STATUS.
3. **Carlos** ejecuta el redeploy en Coolify (su cancha) cuando el CEO coordine.
4. **NLP eficiente en tokens** (ADR-0008 `Proposed`): rutear textual→`analyze_full()` local + político→LLM batcheado. Aplicar en próxima actualización de dirigentes. + **área de investigación futura** (duda CEO: ¿polaridad política derivable local?).
5. **TT_BURNER_AUTH_MODE** — gate TikTok comments, el CEO lo activa ~mid-jun (Hugo bloqueado hasta entonces).
6. **SOP-INGEST-RADAR-HANDOFF.md** pendiente de auditoría Gemini formal (sigue 🟡).
7. **Deuda menor:** dups sha256 históricos pre-existentes (el frontend dedup los maneja en display; constraint UNIQUE diferido requiere dedup global). NO tocar BD (Gemini).

## LECCIÓN DE LA SESIÓN (para el error notebook)
Patrón recurrente, caro: **ejecutar ANTES de leer la gobernanza del dominio.** El CEO me mandó 3 veces a `/gemini` + a leer docs, y las 3 la respuesta YA estaba escrita (D-AUTHOR-HASH-PII, FEEDBACK-CEO-2026-05-20, AVISO-PRIVACIDAD). Costó horas + casi una catástrofe de datos. **Gatillo mecánico:** antes de cualquier carga/migración que toque identidad/hash/PII/schema → leer el ADR/decisión del dominio PRIMERO, no después de la corrección.

## Commits de la sesión (todos en origin/main)
Cards: `ed1face` `4ea9de2` · ADR-0008: `0a0aa23` · adapter IG: `0ae995e` · fans fix: `a2212df` · frontend dedup: `cbc88ab` · deploy docs: `450dca0` `a6baaaa` `1d070c9`.

## Cómo retomar
- Si el CEO retoma **automatización RADAR** → ese es el pendiente #1 (diseño de pipeline).
- Si retoma los **3 dirigentes** → pedir handoff a Hugo, ingerir con el SOP, medir por fecha, re-cortar Release.
- Reactivar freeze de ingest si hay multi-sesión.
