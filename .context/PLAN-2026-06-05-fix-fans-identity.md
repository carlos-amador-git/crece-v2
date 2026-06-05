# PLAN 2026-06-05 — Fix identidad fans (mi error: 18,337 dups) + join comments

**Causa:** mi backfill reactors guardó author_hash NUMÉRICO crudo en vez de
`ensure_author_hash(display_name)` como hacen los comments → rompió join + 18,337 dups.
**Identidad canónica (documentada + convergida):** sha256 del display_name vía
`ensure_author_hash`. Salt `crece-v2-lfpdppp-salt-2026`. IG recipe VERIFICADO (INSTAGRAM).

## Gates (backup + verificación cada uno, NADA destructivo sin preview)
- **G0** Backup pre-fix. ✅ obligatorio.
- **G1** Preview read-only: cuántos fans se consolidan por (dirigente,platform,display_name),
  cuántos eventos se mueven. Mostrar números ANTES de tocar.
- **G2** Consolidar dups: mover watched_like_events del row redundante al canónico
  (menor id por display_name), borrar redundantes. NO se pierde ninguna reacción.
  Verificar: count eventos antes==después; fans baja ~18k.
- **G3** Fix adapter `ingest_radar_reactors_v2.py`: usar `ensure_author_hash(display_name,
  platform)` — previene recurrencia futura.
- **G4** Set author_hash canónico = ensure_author_hash(display_name) para que matchee comments;
  verificar fans muestran n_comments>0 (IG seguro; FB depende de string adapter "RADAR").
- **G5** Constraint UNIQUE (dirigente, platform, author_hash). Commit.

## Regla: SQL verificable en cada gate. Backup como red. Si algo no cuadra, parar y reportar.
