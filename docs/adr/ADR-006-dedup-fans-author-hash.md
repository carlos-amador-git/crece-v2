# ADR 006: Dedup de fans por author_hash en presentación (ranking + conteo)

**Estado:** Accepted
**Fecha:** 2026-06-13
**Autor:** AGENT Linda (claude-opus-4-8) · **Deciders:** ceo, linda
**Cross-audit:** Gemini CLI (2026-06-13, aprobado con 3 ajustes integrados)

## Contexto
RADAR asigna un `profile_external_id` DISTINTO al mismo fan entre capturas (esquema dual /
fix de reels). La constraint de `watched_profiles` es `(dirigente, platform, profile_external_id)`
→ el mismo fan en la misma plataforma entra como **N watched_profiles** (distinto ext, MISMO
`author_hash` canónico = sha256(platform:nombre:salt)).

**Impacto medido (Saymi, 2026-06-13):** 95,624 perfiles vs 73,528 (nombre,platform) únicos (~23%
duplicados, 5,358 creados en el re-ingest de hoy). El ranking de fans **inflaba ~2x**: Pedro Carlock
mostraba 988 reactions (suma de 4 perfiles del mismo fan) cuando el real es 514. Causa doble:
(a) el endpoint hacía `LIMIT` sobre perfiles individuales + `n_likes` por `wp.id`; (b) el frontend
dedupeaba por `display_name` **sumando** todos los perfiles.

**NO afectaba:** diagnósticos D's/IPD/bot-detection (no usan `watched_profiles`), gate de cobertura
(usa eventos). Solo presentación: ranking de fans + conteo total.

## Decisión
**Layer-of-fix en presentación (NO toca BD — coherente con la decisión 2026-05-20/06-05 "dedup en
presentación, BD intacta", tras abortar el re-hash total que orfanaba comments):**

1. **Ranking** (`watched_profiles.py` list): agrupar por `author_hash` (`ROW_NUMBER` PARTITION BY,
   1 representativo por hash). `n_likes = COUNT(DISTINCT post_id)` sobre TODOS los perfiles del hash
   (ajuste Gemini: `post_id`, no la tupla con `reaction_type` — un Like+Love del mismo fan/post por
   duplicación seguiría inflando).
2. **Conteo total** (`watched_summary`): `COUNT(DISTINCT author_hash)` en vez de `COUNT(*)`.
3. **Frontend** (`top-fans-ranking`): el dedup por `display_name` se mantiene para sumar FB+IG del
   mismo nombre (engagement cross-plataforma); ya no encuentra duplicados intra-plataforma.

## Consecuencias
- El ranking ya no infla por duplicación de ext (Pedro 988→514). Verificado: los perfiles del mismo
  fan+plataforma comparten `author_hash` → se agrupan.
- Conteo total Saymi 95,624→92,235. **NO baja a 73,528** porque ~18,335 (nombre,platform) tienen
  varios `author_hash` por **variación del nombre** (espacios/emojis/case) → deuda de normalización
  SEPARADA y pre-existente (ver Pendientes).
- Performance OK: índices `ix_watched_author_hash` + `ix_watched_like_post` ya existen.

## Pendientes derivados (escalados, NO en este ADR)
- **Causa raíz (lado RADAR):** UPSERT de `watched_profiles` por `author_hash` en la ingesta — que
  una nueva captura actualice el `profile_external_id` del registro existente en vez de crear uno
  nuevo. Sin esto, `watched_profiles` crece con basura (~23% hoy → ~50%/mes, Gemini). Coordinar D-050.
- **Normalización de nombres:** los 18k (nombre,platform) con múltiples hash (variantes de nombre).
  Requiere normalizar el input de `ensure_author_hash` (trim/lower/strip-emoji) + posible backfill.
- **VIP Misael:** su override (400 reactions) quedó por debajo del top real dedupeado (Pedro 514).
  Recalibrar a >514 — requiere PR humano del CEO (regla 12, no editar `vip-overrides.ts` sin OK).

## More Information
- Diagnóstico con datos: sesión 2026-06-13 (handoff). Cross-audit: `/tmp/gemini-fans-verdict.md`.
- Relacionado: D-AUTHOR-HASH-PII (2026-05-26), bug fans 06-05, ADR-005.
