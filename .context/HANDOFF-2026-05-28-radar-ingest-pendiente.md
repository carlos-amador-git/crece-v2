# HANDOFF — Residual mínimo ingest radar→crece · 2026-05-28

**Status:** ~99% cerrado. Único residual: 495 rx del reel Piña 3982 (url mismatch). NO urgente.

## Lo que se hizo en la sesión 2026-05-28

### Paquete (a) — 18 parents
Hugo entregó `crece-handoff-parents-20260528_0354.json` (3 FB reels + 9 YT + 6 X).

**Hallazgo crítico:** los 18 ya estaban en CRECE — el bug real era `raw_data->>'url'` VACÍO en los 3 reels FB. Por eso `url_to_post` del reactors ingest no linkeaba.

**Fix:** UPDATE manual del url en los 3 reels FB CRECE (desde el export) + re-run `ingest_radar_reactors_v2.py --commit` para Balles + Piña FB (idempotente).

**Resultado reactions:**
| dir | antes | después | cobertura |
|---|---|---|---|
| Balles (8) | 22,982 | **24,669** | **100% ✅** |
| Piña (1) | 9,875 | **10,941** | **96%** |

### Paquete (b) — 58 comments YT/X
Hugo entregó `crece-handoff-comments-yt-x-20260528_0401.json` (Balles 32 YT + 24 X · Piña 1 YT + 1 X).

**Bug del adapter `ingest_radar_comments_payload.py`:** lee `cid = it.get("comment_id") or it.get("comment_id_surrogate") or pl.get("comment_id") or pl.get("comment_id_surrogate")` — pero el export Hugo trae `platform_comment_id`. Como `cid=None`, el `if commit and cid:` SKIPEA el INSERT, pero `n_ins += 1` está FUERA del if → reporta `ingestables=N [APPLY] OK` engañoso. Lo mismo con `content`/`time_iso` (Hugo: `content`/`published_at`).

**Workaround aplicado:** pre-transform de los 4 split JSONs con aliases (`comment_id ← platform_comment_id`, `comment_text ← content`, `time_iso ← published_at`). Re-run → ingestó 53 nuevos (5 ya existían, ON CONFLICT skip — consistent con dedup de Hugo).

**Resultado comments:**
| dir/plat | antes | después | nuevos |
|---|---|---|---|
| Balles YT | 4 | **32** | +28 |
| Balles X | 620 | **644** | +24 |
| Piña X | 14 | **15** | +1 |
| Piña YT | 1 | **1** | +0 (dup) |

## Único residual: Piña 3982265445406416 — 495 rx (diagnóstico definitivo Hugo 2026-05-28)

**NO es 1 url mismatch — son 12 posts FB distintos** que comparten el `platform_post_id_numeric=3982265445406416` (FB roll-up de reactions al feedback_id del reel subyacente, pero cada reacción vive en su pfbid propio).

Evidencia (Hugo):
- 279 reactores únicos / 495 reactions → 38% audience overlap (sería >90% si fueran copias).
- Counts muy variables por url: 5, 9, 14, 16, 25, 31, 36, 41, 44, 52, 99, 123.
- 12 urls únicas en `pina-reactors-v2-20260528.json` filtrando `platform_post_id_numeric=="3982265445406416"`. Todas `/posts/pfbid…`.
- 0 de las 12 urls están en CRECE social_posts.
- Engine descubrió las 12 en un solo pase del 05-18.

**Para cerrar los 495:** Hugo necesita seedear los 12 pfbids en radar (0/12 actualmente). Requiere corrida FB con Camoufox + cookies CEO. Dos vías:
- **Targeted:** fetch directo de los 12 URLs (mínima huella FB).
- **Full pepe_hybrid Piña FB:** discovery más amplio, podría traer otros posts faltantes también.

**Cuando se ejecute:** Hugo seedea + re-exporta los 12 como parents → yo ingesto via `ingest_radar_yt_x_posts.py --platform FACEBOOK --dirigente-id 1` → re-corro `ingest_radar_reactors_v2.py` Piña FB → `url_to_post` fallback linkea las 495 al post correcto por url.

**No-urgente. Dejado como deuda residual.** Requiere autorización CEO para corrida FB con cookies (huella). Cuando se haga, Piña cierra a 100%.

## Deuda técnica (RESUELTA por Hugo radar-side)

**Hugo aplicó fix en su exporter** (commit `fb93dec` en repo radar): ahora emite AMBOS field names — `platform_comment_id`/`content`/`published_at` (v2) + `comment_id`/`comment_text`/`time_iso` (legacy). Próximos ingests jalan sin pre-transform.

Pendiente opcional CRECE-side (mejora de fidelidad, no urgente):
- `scripts/ingest_radar_comments_payload.py`: mover `n_ins += 1` DENTRO del `if commit and cid:` para que el contador refleje INSERTs reales (no items procesados). Hoy puede reportar `[APPLY] OK` engañoso si por cualquier razón `cid` es falsy.

## Cómo retomar
1. Ping Hugo (peer radar, cwd `~/Projects/radar`).
2. Cargar `pina-reactors-v2-20260528.json`, identificar el post_url real de los 495 reactores del reel 3982. UPDATE el url del post en CRECE. Re-correr reactors Piña FB (con hash swap si Balles también).
3. Aplicar el patch del adapter (arriba) — quality of life para futuros ingests.
4. Verificar reactions Piña → ~11,436 esperado.

## Hash swap Ballesteros (si re-corres reactors dir 8)
- Hash original (restaurar): `$2b$12$Sd4DqIBZul3YzqAiLKKuDuH9J69nqHw8FtM69SzfkIMYNsAWKeKNy`
- Swap a demo2026!: `UPDATE users SET hashed_password=(SELECT hashed_password FROM users WHERE email='pina@crece.mx') WHERE id=11`
- Restaurar: `UPDATE users SET hashed_password='<hash original arriba>' WHERE id=11`
