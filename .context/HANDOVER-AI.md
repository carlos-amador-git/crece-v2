# HANDOVER-AI — Decisiones extraídas por Sonnet
## Sesión: 18658 | Compactación: 2026-05-21_05:59:58

The HANDOVER-AI.md already contains the exact 6 sections requested. Here it is formatted cleanly:

---

## 1. ARCHITECTURAL DECISIONS

| Decision | What | Why |
|---|---|---|
| **D-BFF-ENDPOINT** | `GET /api/v1/posts/unified` as single BFF with `?view=` discriminator (feed/top/comentarios/fans) | Consolidate data access; rejected one-endpoint-per-view |
| **D-HUB-ROUTE** | Route set to `/dashboard/hub` (not `/dashboard/contenido`) | `/dashboard/contenido` already occupied by Content Factory (148 lines) |
| **D-SIDEBAR-CONSOLIDATION** | 4 sidebar items → 1 "Content Hub" via 308 redirects | D13.5=A — absorbed F0 group |
| **D-F4-TIMING** | Executed F4 immediately despite Gemini deferral recommendation | Gemini's premise (client had seen the app) was false — no mental model to protect |
| **D-IG-SESSION-SHARING** | Did NOT share CRECE instagrapi session with Hugo/RADAR | CRECE does fresh login each run; no persistent session exists |
| **D-NO-FRONTEND-TESTS** | No Vitest/Jest for `applyVipOverrides` | Playwright smoke sufficient; framework install = scope creep (~45 min) |

---

## 2. REJECTED ALTERNATIVES

- **F0 sidebar group "Contenido"** — absorbed into F4's single-entry consolidation
- **Separate `/dashboard/contenido` route** — file collision with existing Content Factory
- **Gemini "defer F4"** — premise verified false; overridden by CEO
- **Sharing session file with Hugo** — no persistent session on CRECE side
- **Multiple BFF endpoints (one per view)** — replaced by single `/posts/unified?view=`

---

## 3. ASSUMPTIONS TO VERIFY

- `backend/.env.scraping-keys` repo still **private** — verified at audit time but should re-confirm
- **F2 Top Posts** 🟡 PARTIAL (P0–P2 only) — acceptable for client demo? Not confirmed
- **Smoke counts** (feed=1681, top=1532, comentarios=1222, fans=42) assumed to reflect real data — not quality-audited
- **`total_all`** flagged as dead code — not verified before audit ran

---

## 4. BLOCKERS / OPEN QUESTIONS

| ID | Severity | Issue |
|---|---|---|
| **SEC-ENV-01** | 🔴 | `backend/.env.scraping-keys` tracked in git with API keys/proxy creds. CEO accepted rotation responsibility. Task #47 created. |
| **SIDEBAR-LABEL-COLLISION** | 🟡 | Two items labeled "Contenido" — hub vs Content Factory |
| **FILTROS-REGRESION** | 🟡 | `/dashboard/hub` has no filters (regression vs old `/social`) |
| **0 TESTS /posts/unified** | 🟡 | New BFF endpoint has zero pytest coverage |
| **10 RUFF ERRORS** | 🟡 | Backend code quality, unresolved |
| **MOBILE-WEAK** | 🟡 | UnifiedPostCard no vertical stack, touch targets <44px, fonts <12px (7.6/10) |
| **ACCESSIBILITY-CONTRAST** | 🟡 | Sidebar contrast 2.01:1 (WCAG AA requires 4.5:1) — 6.8/10 |
| **B-26-01** | 🔴 | Plan IA timeout Coolify — demo Ballesteros still blocked (carried over) |

---

## 5. KEY PEER MESSAGES

- **→ Hugo (RADAR):** CRECE has no persistent instagrapi session; passed `INSTAGRAM_USERNAME/PASSWORD`; proposed Hugo build own session with `dump_settings`
- **← Hugo:** Confirmed D3 IG closed — login OK, session dumped, Saymi smoke: 12K followers / 4K posts
- **← Gemini cross-audit:** `approve_with_changes` — blocking concern on F4 timing; CEO overrode (false premise)
- **← Gemini audit-full:** Score 73.25/100 flagged as over-estimated (security dimension masked by average)

---

## 6. NEXT STEPS (PLANNED, NOT EXECUTED)

1. **Credentials rotation** (CEO responsibility) — rotate `SCRAPERAPI_KEY`, `CRAWLBASE_JS_TOKEN`, `WEBSHARE_*`; then BFG/filter-branch to purge from history
2. **Tríada técnica (~75 min):**
   - Fix "Contenido × 2" label collision
   - Add skeletons/loading states to `/dashboard/hub`
   - Restore filters (regression)
   - Add pytest for `/posts/unified`
3. **Sprint post-cliente** — scope TBD after client sees platform
4. **Mobile/accessibility hardening** — vertical stacking, touch targets ≥44px, sidebar contrast fix
5. **F3 Refactor Fans TopPost** — not executed in F4, still pending
6. **§9.8 day-30 review** (≈2026-05-20) — formal gate checkpoint
