# HANDOVER-AI — Decisiones extraídas por Sonnet

## Sesión 2026-05-19 (post-apagón) — Cierre Sprint D + F plan fans-dashboard

**Closed:**
- Sprint D backfill NLP Saymi (commit `177f768`) — 274 comments procesados con `--effort high` tras audit empírico que probó que `effort=low` subestimaba críticas (42% clasificaciones distintas en muestra n=50). Estado final: 96%+ de comments Saymi clasificados, 0 fails.
- Sprint F `regen_plan_dirigente.py` standalone — script offline para generar planes Saymi sin tocar Ollama legacy (D-1). Stack: CC subprocess `claude --print --effort high` + fallback `gemini-clean --mode plan`. Persiste a `planes_ia` + `recomendaciones_plan_ia`. Verificado con dry-run Saymi: contexto 5521 chars, 3 winners + 3 losers + quotes.

**Decisiones nuevas:**
- D-1 ratificada operativamente: endpoint `/plan-ia/generate` sigue 503. Generación 100% offline vía script.
- Diferencia con pipeline original async: el script standalone NO replica los 18 bloques B01-B18; usa contexto curado de `dirigente_context_builder` (que Sprint E enriqueció con `performance_posts`). Si en el futuro se necesitan los 18 bloques cuantitativos, se compone con el pipeline original cuando se desbloquee.

**Pendiente próxima sesión:**
- Lanzar Sprint F contra Saymi en producción (estima 3-7 min CC subprocess).
- Tests Sprint F (script con LLM externos, mock no trivial).
- Cleanup BD S-8.1 (154 auto_suggested + 320 events) — esperando orden CEO.
- Decisiones BLOQUE 1 plan consolidado: D-1.1 endpoint Juan · D-1.2 Groq · D-1.3 Meta · D-1.4 competidores.

---

## Sesión: 11703 | Compactación: 2026-05-17_21:23:24

Based on this Claude Code session transcript, here is the structured extraction:

---

## 1. ARCHITECTURAL DECISIONS

**D-PLAN-IA-CC-GEMINI-CLI-1 (CONFIRMED):** Subprocess CC + Gemini CLI stays as the runtime architecture for Plan IA feature, despite Gemini's recommendation to use direct APIs (Groq + Claude). CEO explicitly overrode Gemini's recommendation.
- *Why:* CEO's direction. The "CC + Gemini CLI generates specific data, NLP, detailed plans" instruction was reaffirmed as runtime, not offline batch.

**D-038 (PROPOSED by Hugo):** ADR with hard rules for scraping architecture to prevent architectural drift.
- *Why:* Mitigate inconsistency discovered in session (Yesenia Nolasco scraping error).

**Competidor data cleanup:**
- Saymi (id=3): `competidor_directo_ids = {}` (Yesenia removed — she's a cabinet colleague, not political rival)
- Piña (id=1): `competidor_directo_ids = {5}` (only Gabriela Jiménez CDMX kept; Saymi + Yesenia removed)

**B-VIOLENCIA-TAGS-1 → DESCARTADO:** Sub-classifying violence by type (insults/threats/gender) rejected. Current LOW/MEDIUM/HIGH severity + top comments in CardB18 already covers 80% of the value.

**B-23-04 → Deuda post-piloto:** Structural card rewrite deferred to post-pilot (Sprint 8-16).

**Reactor import strategy:** Null `reaction_type` from Hugo's data mapped to `'like'` as placeholder (~85% of FB reactions are likes; low bias). Will be overwritten when Hugo fixes the bug in Sprint 9 re-import.

---

## 2. REJECTED ALTERNATIVES

**Gemini's recommendation:** Use direct APIs (Groq + Claude API) for Plan IA runtime instead of subprocess CC + Gemini CLI. *Rejected by CEO* — maintained current architecture.

**Cap-reduced reactions scraping (TOP 100 × cap 10):** Proposed by assistant to fit $2.05 remaining budget. *Rejected by CEO* — contradicts "get all reactions" instruction.

**Option A (partial import, ~3K reactors):** Proposed as lower-risk import for FB reactor data. *Rejected* — CEO correctly noted that having the full 10K corpus enables future queries without re-scraping; partial data defeats the purpose.

---

## 3. ASSUMPTIONS MADE (TO VERIFY)

- `reaction_type=None` → mapped to `'like'` as placeholder. **Assumption:** ~85% of FB reactions are likes. Should be verified against a sample with known reaction breakdown.
- `story_fbid` from Hugo's data can be matched against `raw_data->>'url'` path in existing posts. **Needs verification:** the 5-line fix proposed at session end was not confirmed to work yet.
- Yesenia Nolasco's entry into `competidor_directo_ids` was assumed to originate from a prior session misidentifying "Oaxaca + Secretary = rival." **Not confirmed** — no audit log found for who added id=4.
- Gabriela Jiménez Godoy (id=5, CDMX Diputada Federal MORENA) is a valid competitor for Piña. **Assumed correct** but not explicitly validated by CEO in this session.

---

## 4. BLOCKERS / OPEN QUESTIONS

**B-26-01 (DEMO BLOCKER — HIGH PRIORITY):** Plan IA timeout on Coolify — Ollama doesn't finish in 9 min. Feature is inoperative for Ballesteros pilot demo. Fix: refactor `_call_ollama` → CC subprocess + Gemini CLI + Groq fallback. Research from Juan available (`md-research/analysis/2026-05-17-llm-apis-cross-product.md`). Estimated ~3-4h work. **Not yet executed.**

**Reactor import match failure:** Only 1/48 posts matched (0/13 `cliente_seed`) when trying to link Hugo's `story_fbid` to existing BD posts. Fix proposed (match via `raw_data->>'url'` path), but **not yet confirmed working.**

**Hugo's `reaction_type=None` bug:** All 10,011 reactions imported as null. Hugo confirmed fix in Sprint 9, but current import has placeholder bias.

**Pepe Monroy scraping:** CEO has not confirmed whether to proceed. Requires `cliente_seed` + `storage_state` (not available to assistant — needs CEO direct).

**Saymi competitor data (Hugo's 10K corpus):** Import to BD attempted but match logic failing. Blocking full reactor intelligence for Saymi.

**April 1-13 gap:** Backfill only reached April 14 (not April 1 as instructed). Gap exists.

---

## 5. KEY PEER MESSAGES (Hugo ↔ Jess)

- **Hugo → Jess:** Confirmed he does NOT have Saymi's `cliente_seed` or `storage_state`; CEO must provide directly.
- **Hugo → Jess:** Shared 10K reactor dataset (65 posts, 10,011 reactors, 13/13 Misael matches, Mueller Ramírez "silent fan" discovered with 38 reactions, Ivette Morán 2.3× Saymi engagement).
- **Hugo → Jess:** Discovered "engagement-article-links discovery" pattern — using FB comments as an index to find posts from non-followed accounts. Noted as reusable pattern.
- **Hugo → Jess:** `reaction_type=None` bug in his export confirmed; fix coming Sprint 9.
- **Jess → Hugo:** Flagged Yesenia Nolasco as NOT a competitor (cabinet colleague) — Hugo should NOT scrape her. Hugo's RADAR filter bug (YesNolasco appearing) may be explained by follower status false-positive, not scraping error.
- **Hugo → Jess:** ADR D-038 with hard rules proposed to prevent architectural drift.
- **Jess → Hugo:** Shared 3 Saymi competitors with FB handles + Pepe Monroy data (what exists vs what's missing).

---

## 6. NEXT STEPS (PLANNED, NOT YET EXECUTED)

1. **Fix reactor import match logic** — use `raw_data->>'url'` path to match `story_fbid` instead of `platform_post_id`. 5-line fix in endpoint. Verify against 48 envelopes.
2. **B-26-01 Plan IA fix** — refactor `_call_ollama` using Groq + Gemini CLI + CC subprocess chain. Use Juan's research from `md-research/analysis/2026-05-17-llm-apis-cross-product.md`. ~3-4h.
3. **Fill April 1-13 gap** for Saymi posts — requires additional Apify budget or alternative approach.
4. **Pepe Monroy scraping** — pending CEO decision + credentials.
5. **Hugo Sprint 9** — re-import reactor data with `reaction_type` fixed (will overwrite placeholders via ON CONFLICT).
6. **Draft ADR D-038** — hard rules for scraping architecture (Hugo proposed, not yet written).
7. **Ivette Morán benchmark integration** — if CEO wants Ivette's aggregate totals (2.3× Saymi) visible in Saymi's benchmarking view, add to dashboard. No decision made.
