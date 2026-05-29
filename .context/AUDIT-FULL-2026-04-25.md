# AUDIT-FULL · CRECE v2 · 2026-04-25

**Modo:** /audit-full · 8 auditorías paralelas · 7 completadas + 1 fallida (smoke).
**Branch:** `hotfix/23a-ui-puros` · **CWD:** `/Users/marxchavez/Projects/crece-v2`
**Sesión:** Joy (Opus 4.7).

---

## Score global

| Auditoría | Score | Peso | Aporte |
|---|---:|---:|---:|
| Smoke Test | **N/A** | 10% | (audit stalled · backend bajo carga) |
| Funcional módulos | 63/100 | 20% | 14.0 |
| Seguridad LFPDPPP/INE | 50/100 | 20% | 11.1 |
| Calidad código (estático) | 59/100 | 15% | 9.9 |
| Diseño UX/UI | 66/100 | 10% | 7.3 |
| Responsive 3 BPs | 84/100 | 10% | 9.3 |
| Hardening IA | 52/100 | 10% | 5.8 |
| Accessibility WCAG AA | 80/100 | 5% | 4.5 |
| **Total ponderado (sin smoke)** | **62/100** | 90% | **62** |

**Lectura:** producto operativo con base sólida (responsive, a11y, tipografía), deuda concentrada en seguridad de aplicación + calidad de código + IA hardening. Score se inserta entre el "60% reescritura" pesimista y el "80% funcional" del audit funcional · refleja que la app **funciona para 2 de 3 pilotos** pero acumula deuda explotable.

---

## Lo que ya se corrigió HOY (commits pendientes)

Backend (`hotfix/23a-ui-puros` · sin commitear):
- ✅ H-01 IDOR `/planes` · `org_id` scoping en todos los endpoints + helper `_get_dirigente_with_org_check`
- ✅ H-02 `prompt_usado` / `datos_entrada` redacted del response público · clase `PlanIAAdminResponse` separada
- ✅ H-06 rate limit `5/hour` en `POST /planes/generar` y `/generar/stream`
- ✅ C-01 `VedaElectoralMiddleware` montado en `main.py`
- ✅ C-02 Sentry `before_send` scrubbing + `send_default_pii=False`
- ✅ Smoke H-02 verificado (PASS · keys públicas no incluyen `prompt_usado`)

Frontend (`hotfix/23a-ui-puros` · sin commitear):
- ✅ Next.js `14.2.21` → `14.2.35` (CVSS 9.1 Authorization Bypass) · `tsc --noEmit` PASS

**Falta:** commits + push + redeploy Vercel + restart backend con compose (consciente del costo de logs).

---

## Top 10 P0 abiertos (orden de impacto)

| # | ID | Audit | Hallazgo | Estado |
|---|---|---|---|---|
| 1 | A-02 | Seguridad | `POST /arco/exercise` sin auth ni rate-limit · DELETE masivo de comments posible vía falso ARCO | abierto |
| 2 | A-01 | Seguridad | `ProxyHeadersMiddleware(trusted_hosts=["*"])` rompe rate-limit /login (IP spoof) | abierto |
| 3 | C-03 | Seguridad | RLS migration aplicada pero endpoints usan `get_db` no `get_db_rls` · sin defensa en profundidad | abierto · cambio invasivo |
| 4 | H-07 | IA | Puerto 11434 Coolify Ollama expuesto sin auth · inferencia gratuita externa posible | requiere CEO/Carlos firewall |
| 5 | F-MAYNEZ | Funcional | Máynez (id=7) 0 posts BD · scrapers chromedriver crash · NO MOSTRAR en demo | B-23-06 |
| 6 | F-IPD | Funcional | IPD divergencia API (2.44) vs DB (2.69) · drift no documentado | abierto |
| 7 | F-7D | Funcional | Hero "Actividad alineada" siempre vacío en ventana 7d · last_post hace 7-12 días según dirigente | B-23-07 |
| 8 | H-04 | IA | Texto raw scrapers entra al prompt LLM con `replace('"',"'")` solo · prompt injection viable | abierto |
| 9 | A-03 | Seguridad | Discord webhook envía `str(exc)[:500]` sin sanitizar · filtración a tercero (LFPDPPP) | abierto |
| 10 | A-04 | Seguridad | JWT 24h sin refresh · token robado vivo 24h sin revocación | abierto |

---

## Top 10 P1 importantes

| # | Audit | Hallazgo |
|---|---|---|
| 1 | Calidad | `protobufjs` CVSS critical (RCE arbitrary code execution) · transitive |
| 2 | Calidad | `xlsx` HIGH prototype pollution · sin fix oficial · reemplazar por `exceljs` |
| 3 | Calidad | 0 tests unitarios frontend · `services/` 62 archivos solo 8 referenciados en tests |
| 4 | Calidad | 934 violaciones `ruff` (290 auto-fix con `--fix`) · ESLint NO configurado |
| 5 | Diseño | Dark mode roto · 140+ `dark:*` clases sin `ThemeProvider` ni `next-themes` |
| 6 | Diseño | KPI Card duplicado 4 veces (`KpiCard`, `StatCard`, `KPICard`, inline) · consolidar |
| 7 | Diseño | EmptyState fragmentado · 1 componente formal vs N inline ad hoc |
| 8 | Diseño | 3 fugas púrpura (anti-slop) · `participacion`, `landing/features`, `actividad-alineada-card:131` |
| 9 | A11y | `/dashboard/evaluacion/[id]` sin `<h1>` · tablas sin `scope=` ni `<caption>` |
| 10 | Responsive | Mobile 7.4/10 · `/login` overflow horizontal wordmark · touch targets shadcn 36-40px <44px |

---

## P2 backlog (no bloquea piloto)

- Seguridad: 5 medios + 4 bajos (M-01..M-05, B-01..B-04 documentados)
- A11y: SyntheticDataBanner sin `role="status"` · contraste amber chart no verificado empíricamente
- Funcional: onboarding wizard 9 pasos código vs 4 API · `/api/v1/health` 404 (path correcto fuera `/api/v1`)
- Diseño: 24 usos de Tailwind crudo (`text-blue-*`, `bg-emerald-*`) cuando ya existen `--chart-*` tokens
- Calidad: top 5 funciones >80 líneas (`_build_prompt` 170 LOC, `optimize_route_postgis` 159 LOC, `endpoints/dirigentes.py` 975 LOC archivo)

---

## Cosas reconocidas como NO verificadas (honestidad)

- Dependency CVEs Python (no se ejecutó `pip-audit` · no instalado en venv)
- Frontend uso de `localStorage` vs cookie HttpOnly para JWT
- Coverage cross-tenant en tests (no hay test que pruebe org A no ve org B)
- Vercel `NEXT_PUBLIC_*` actuales · no inspeccionados
- PII encryption en runtime · `core/pii_encryption.py` existe, no se validó uso real
- Logs lado VPS Coolify del Ollama · sin acceso

---

## Veredicto

**Demo viable HOY** con Piña (id=1) y Ballesteros (id=8) · **NO mostrar Máynez** (vacío end-to-end).

**Bloqueantes para "producción real con clientes":**
1. Cerrar A-02 (ARCO endpoint sin auth · vector legal real)
2. Cerrar C-03 (RLS runtime enforcement · defensa en profundidad)
3. Cerrar H-07 (Ollama Coolify firewall)
4. Migrar JWT a refresh + reducir TTL a 60 min

**No bloqueantes pero importantes:**
- Stack scrapers (chromedriver crash en FB · curl-cffi parcial) · agendar sprint dedicado
- Pipeline Plan IA via Coolify CPU genuinamente lento (>1h por plan) · necesita SSH al VPS para `ollama pull gemma3:4b` o auth/observabilidad

---

## Archivos fuente

- `.context/AUDIT-A11Y-2026-04-25.md`
- `.context/AUDIT-CALIDAD-2026-04-25.md`
- `.context/AUDIT-DISENO-2026-04-25.md`
- `.context/AUDIT-FUNCIONAL-2026-04-25.md`
- `.context/AUDIT-RESPONSIVE-2026-04-25.md`
- `.context/AUDIT-SEGURIDAD-2026-04-25.md`
- IA Hardening: agente lo entregó como texto inline en su task notification (no escribió archivo) · contenido en summary del task `a1b4117d72f9abed5`. Hallazgos H-01..H-13 documentados arriba en P0/P1.

Smoke test audit: stalled por backend bajo carga · no se completó · gap de cobertura reconocido. Cubierto parcialmente por audit Funcional (rutas frontend principales testeadas).
