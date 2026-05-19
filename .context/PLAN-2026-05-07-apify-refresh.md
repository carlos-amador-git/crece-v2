# PLAN: Apify Refresh 7 dirigentes — 2026-05-07

**Branch:** `feat/phase-b-pesos-editables` · **Status budget:** $4.94 disponible Apify free tier

---

## Objetivo

Refrescar **posts + comments** de los 7 dirigentes piloto en una sola pasada
controlada, con UPSERT idempotente, validación post-insert, y hard-stop si
costo Apify excede umbral.

**No-objetivo:** back-fill histórico de comments. Solo posts/comments con
fecha ≥ 2026-04-07 (ventana 30d).

---

## Entradas validadas (snapshot 2026-05-07)

### Roster + handles (verificado contra `social_profiles`)

| ID | Dirigente | TW | IG | FB | TT | YT |
|----|-----------|-----|-----|-----|-----|-----|
| 1 | Piña | `alejandro_pinha` | `alejandro.pinha` | `alejandropinamedina` | `@alejandro.pinha` | `alejandropinamedina` |
| 2 | Solano | `@rafasolanoperez` | `@rafasolanoperez` | **`RafaSolanoPerez`** ⚠️ corregido hoy | `@rafasolanoperez` | — |
| 3 | Pineda | `@saymipinedav` | `@saymipinedavelasco` | `saymipinedavelasco` | `@saymipineda` | `saymipinedavelasco` |
| 4 | Nolasco | `@Yes_Nolasco` | `@yes_nolasco` | `YesNolasco` | `@yes_nolasco` | — |
| 5 | Jiménez | `@GabyJimenezMX` | `@gabyjimenezgo` | `GabyJimenezGo` | `@gabyjimenezmx` | — |
| 6 | Cravioto | `@craviotocesar` | `@cesarcravioto` | `craviotocesar` | `@cesar_craviotor` | `CesarCraviotoR` |
| 8 | Ballesteros | `@LBallesterosM` | `@lauraballesterosm` | `LauraBallesterosMX` | — | `LauraBallesterosMX` |

**Sin perfil → saltar:**
- YT: 3 dirigentes (Solano, Nolasco, Jiménez)
- TT: 1 dirigente (Ballesteros)

### Constraints BD verificados

- `social_posts.platform_post_id` → UNIQUE (UPSERT seguro)
- `social_comments.platform_comment_id` → UNIQUE (UPSERT seguro)
- `social_comments.parent_post_id` → FK a `social_posts.id` (orden importa: posts ANTES de comments)
- `social_comments.author_hash` → SHA256(`COMMENT_AUTHOR_SALT` + author_id) — LFPDPPP

### Apify cuenta verificada

- Token `apify_api_eG89F2BGegEPSHrnBOTlbwwILRswuF3obKC9` → user `vocational_nail` (mdsamca2025@gmail.com)
- Plan: Free $5/mes · ciclo 2026-04-24 → 2026-05-23
- Usado: $0.056 / $5
- **Disponible: $4.94** ← presupuesto duro

---

## Actores + costo proyectado

| Plataforma | Actor (verificado, ya usado por CEO en abril) | Costo unitario FREE | Items 7 dirigentes | Costo proy. |
|---|---|---|---|---|
| TT (posts+comments en 1 run) | `clockworks/tiktok-scraper` con `commentsPerPost=20` | $0.0037/result + $0.00125/comment + $0.001 start | 6 perfiles × 30 vids × 20c = ~3600 unit | **~$1.10** |
| IG posts | `apify/instagram-scraper` `resultsType=posts` | $0.0027/result | 7 × 30 = 210 | $0.57 |
| IG comments | `apify/instagram-scraper` `resultsType=comments` | $0.0026/comment | 7 × 30 × 10 = 2100 | $5.46 ⚠️ |
| FB posts | `apify/facebook-posts-scraper` | $0.005/post + $0.001 start | 7 × 10 = 70 | $0.36 |
| FB comments | `apify/facebook-comments-scraper` | $0.0025/comment + $0.001 start | 7 × 10 × 10 = 700 | $1.76 |
| YT posts | `streamers/youtube-scraper` | $0.004/result + $0.0013 date filter | 4 × 30 = 120 | $0.49 |
| YT comments | yt-dlp local (verificado funciona) | $0 | — | $0 |
| TW posts | `delicious_zebu/advanced-x-twitter-profile-scraper` | $0.0008/item | 7 × 30 = 210 | $0.17 |
| TW replies | `scraper_one/x-post-replies-scraper` | $0.025 init + $0.0025/result | 7 × 30 × 5 = 1050 | $2.65 ⚠️ |

### ⚠️ Problema de presupuesto

**Suma cruda:** $12.56 — rebasa $4.94 disponible.

**Dos campos pesan: IG comments ($5.46) + TW replies ($2.65) + FB comments ($1.76).**

### Mitigación: límites estrictos por dirigente

- IG comments: `resultsLimit=5` por post (en vez de 10) → $2.73
- TW replies: limit=2 por post (en vez de 5) → $1.06 + $0.18 init = $1.24
- FB comments: cap 5 c/post → $0.88

**Total con límites: ~$5.51** — todavía rebasa marginalmente.

### Decisión de presupuesto requerida CEO (UNA de tres)

**A. Hard-cap $4.50** — ejecutar TT+IG posts+FB+YT+TW posts SIN comments completos. Solo TT trae comments incluidos (1 run all-in-one). El resto: solo posts. **Comments quedan parciales.**

**B. Hard-cap $4.50 + IG/FB comments completos, TW replies skip** — sin replies de Twitter. Replies TW siguen siendo gap pero TT/IG/FB sí cubren.
- Estimado: $4.40

**C. Aceptar exceder free tier** — $5-7 cargados a tarjeta del CEO. Cobertura completa.

→ **Mi recomendación: B** (pierde solo TW replies, todo lo demás cubierto, $0 cargo).

---

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| **R1.** Apify run timeout (>10 min) en TT con 6 perfiles + comments | Timeout 15 min, retry 1x. Si segundo timeout: marcar plataforma fallida, seguir con otras |
| **R2.** Output JSON keys distintas vs schema BD | Función `_normalize_<plataforma>(raw)` por actor. Test con 1 item antes de batch |
| **R3.** Date parsing rompe (ISO vs UNIX vs custom) | Helper `_parse_date()` con 4 formatos + fallback `None` |
| **R4.** Author IDs ausentes en algún comment → hash colisión | `author_hash = SHA256(salt + comment_id)` si `author_id is None` (degrada gracefully) |
| **R5.** Solano FB todavía falla con `RafaSolanoPerez` | Pre-check: `curl HEAD https://www.facebook.com/RafaSolanoPerez` antes del run. Si 404, skip y log |
| **R6.** Apify rate limit (free tier ~3 concurrent) | Runs SECUENCIALES (no paralelo). +30 min total pero 0 errores de rate limit |
| **R7.** Comments referencian `parent_post_id` que aún no insertamos | Orden estricto: posts primero, COMMIT, luego comments. Cada plataforma como transacción |
| **R8.** Costo real >$4.50 a mitad del run | Hard-stop: pre-cada-actor consultar `/users/me/limits`, si `monthlyUsageUsd > 4.50` PARAR y reportar |
| **R9.** `crece-backend` recibe restart durante el run y pierde progreso | Script `apify_refresh_all.py` ejecuta DIRECTO desde host con psycopg2 (no requiere container) |
| **R10.** Comments duplicados de runs históricos | UPSERT con ON CONFLICT (platform_comment_id) DO NOTHING. Re-run idempotente |
| **R11.** Plan IA Ballesteros se invalida con datos nuevos | NO regenerar planes IA en este sprint. Solo data refresh |
| **R12.** NLP no procesa los nuevos comments | Worker `nlp_comments_batch_v2.py` ya procesa donde `nlp_model_version IS NULL` — pickup automático posterior, fuera de scope |

---

## Plan de ejecución

### Fase 0 — Pre-flight (15 min, $0)

- [x] Handle Solano FB corregido (BD UPDATE aplicado)
- [x] APIFY_TOKEN actualizado en `.env.scraping-keys`
- [x] Bugs scraper local committeados (1b713b5)
- [ ] **CEO autoriza presupuesto A/B/C**
- [ ] Construir `scripts/apify_refresh_all.py` con:
  - Inputs por plataforma (handles normalizados)
  - 7 funciones `_normalize_<plat>(raw)` con tests inline
  - UPSERT logic
  - Cost-cap pre-check (consulta `/users/me/limits`)
  - Logging estructurado
- [ ] **Test mini con 1 dirigente, 1 plataforma**: Ballesteros TW (más barato $0.02). Validar end-to-end antes del batch.

### Fase 1 — Sprint 1 Ballesteros completo (10 min, ~$0.50)

- [ ] Apify TT (skip — Ballesteros no tiene TT)
- [ ] Apify IG posts → comments
- [ ] Apify FB posts → comments
- [ ] Apify YT posts (yt-dlp comments local)
- [ ] Apify TW posts → (skip replies si plan B)
- [ ] **Checkpoint costo:** consulta `/users/me/limits`. Si Δusd ≤ $0.70 → OK. Si > $0.70 → STOP, reportar.

### Fase 2 — Sprint 2 roster (30-45 min, ~$3.00)

- [ ] Loop 6 dirigentes (Piña, Solano, Pineda, Nolasco, Jiménez, Cravioto)
- [ ] Por cada (dirigente, plataforma): llamar actor, normalizar, UPSERT
- [ ] **Checkpoint costo cada 2 dirigentes**

### Fase 3 — Validación (10 min, $0)

- [ ] Re-correr query inventario inicial. Compara:
  - `n_posts` aumentó por dirigente×plataforma
  - `n_comments` aumentó (si plan B: TT/IG/FB/YT, no TW)
  - `MAX(published_at)` post-2026-04-25 (data fresca)
- [ ] HTTP smoke a `/api/v1/social/aceptacion/overview` — debe responder 200 con números actualizados
- [ ] HTTP smoke a `/api/v1/social/aceptacion/fantasmas-por-plataforma` con token Piña

### Fase 4 — Commit + STATUS (5 min)

- [ ] Commit `scripts/apify_refresh_all.py` + reporte de ejecución
- [ ] STATUS.md update: posts/comments nuevos × dirigente × plataforma + costo real
- [ ] Push branch

---

## Criterios de éxito

- ✅ Cada (dirigente con perfil, plataforma) tiene posts con `published_at` ≥ 2026-04-07
- ✅ TT/IG/FB tienen comments nuevos por dirigente (≥1 si el post tenía comments públicos)
- ✅ Costo Apify total ≤ $4.50
- ✅ Cero errores de FK / duplicate key
- ✅ `/aceptacion/fantasmas-por-plataforma` muestra `unique_commenters > 0` en plataformas que antes eran 0

## Criterio de fallo (rollback)

Si Fase 1 (Ballesteros) consume >$0.70 o falla en >1 plataforma → ABORT Sprint 2, reportar al CEO con datos reales antes de seguir.

UPSERT es idempotente: cualquier dirigente parcialmente cubierto puede re-correrse sin duplicar. No hay rollback de filas a hacer.

---

## Pendiente decisión CEO

**1. Presupuesto: A, B, o C?**

**2. ¿Apruebas el plan tal cual o ajusto algo antes?**
