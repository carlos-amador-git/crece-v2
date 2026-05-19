# PLAN · Deuda Tests + Smoke pre-piloto + Bug fix · 2026-05-19 · v2 (post cross-audit Gemini)

**Origen:** CEO 2026-05-19 post aprobación Content Hub v2. Petición: /plan formal para los 6 items diferidos.
**Clasificación Loki Mode:** OPERATIVA (testing + bug fix · sin arquitectura nueva).
**Nivel proyecto:** CRECE v2 = Nivel 2 (gobierno electoral).
**Modo ejecución:** **Multi-sesión** (Gemini concern · NO Single Session de 8h) · cross-audit Gemini integrado.

## Cambios v1 → v2 (post cross-audit Gemini)

Gemini emitió `approve_with_changes` con 2 blocking concerns + 2 non-blocking. Cambios absorbidos:

| Concern Gemini | Cambio v2 |
|---|---|
| Bug #3 control chars **puede romper UI plan individual durante demo** (HIGH) | **#3 promovido al bloque A** · verificación HOY en demo flow real (`/dashboard/planes/52`). Si UI rompe con jq strict-equivalent del axios → fix HOY pre-piloto. Si UI tolera (axios lenient) → mover a B post-piloto. |
| 6.5-8h en Single Session colapso contexto IA (HIGH) | **Reagrupar en 3 sesiones IA separadas** (no Single Session). Cada bloque = 1 sesión con handoff documentado. Loki "Single Session" se refería a coordinación (NO Agent Teams), Gemini lo malinterpretó como una sola sesión IA · aclaración explícita aquí. |
| Mock asyncpg con SQLite in-memory es anti-patrón (Postgres dialect SQL difiere) | **Estrategia mockeo v2: BD test Docker en puerto 5439** (`crece-db-test` separado de `crece-db:5438`). Mismo asyncpg dialect, RLS desactivable, teardown limpio. Fallback secundario: monkeypatch a nivel de SQLAlchemy query (no DB). |
| Missing: smoke E2E debe ser strictly read-only | **#1 spec explícita:** Playwright headless · NO crea data · NO edita · NO usa POST/PUT/DELETE excepto login. Logout al final. |
| Missing: fragmentación sesión IA | **Sección nueva al final:** handoff entre sesiones · qué se commitea entre sesiones · qué leer al arrancar siguiente. |

## Alcance · 6 items

| # | Item | Tipo | Tamaño |
|---|---|---|---|
| 1 | Smoke pre-piloto §9.8 | Validación E2E | ~20 min |
| 2 | Tests Sprint F (`regen_plan_dirigente.py` + fix `plan_tareas`) | Tests backend | ~2-3h |
| 3 | Bug `/planes/{id}` control chars JSON | Backend fix | ~30-45 min |
| 4 | Tests Sprint A (3 endpoints stats) | Tests backend | ~1.5h |
| 5 | Tests Sprint D (`backfill_nlp_saymi.py` + `audit_cc_effort_high.py`) | Tests backend | ~1.5h |
| 6 | Test `applyVipOverrides` (Misael Fan #1) | Test frontend | ~30 min |

**Total esfuerzo:** 6.5-9h.

## Secuenciación v2

Tres bloques · cada uno en su propia sesión IA:

```
BLOQUE A (HOY · pre-piloto · sesión IA actual)
  ├── #1 Smoke pre-piloto §9.8 (Playwright READ-ONLY)
  └── #3 Verificación bug /planes/{id} control chars
        ├── ¿UI rompe en /dashboard/planes/52? (concern Gemini HIGH)
        ├── Si rompe → fix HOY pre-piloto
        └── Si no rompe → mover #3 a Bloque B

BLOQUE B (Post-piloto · día 1-2 · sesión IA nueva)
  ├── #3 Bug /planes/{id} fix (si no se hizo en A)
  └── #6 Test applyVipOverrides
        └── Paralelizables

BLOQUE C (Post-piloto · día 3-5 · sesión IA nueva)
  ├── #2 Tests Sprint F (parser → adapters → INSERT con BD test :5439)
  ├── #4 Tests Sprint A (3 endpoints stats)
  └── #5 Tests Sprint D (backfill NLP + audit)
        └── Fixtures compartidas en tests/fixtures/
```

**Gating crítico:**
- Si Bloque A encuentra regresión HIGH en demo flow O bug control chars rompe UI → fix HOY · Bloque B/C se reagendan.
- Si todo verde → Bloques B y C continúan según calendario.

## Detalle por ítem

### #1 · Smoke pre-piloto §9.8 (HOY · ~20 min) · **READ-ONLY estricto (Gemini)**

**Scope:**
- Playwright headless contra `frontend-zeta-sepia-46.vercel.app`.
- **Strictly read-only:** solo POST `/auth/login` (login) y `/auth/logout` al final. CERO mutaciones en /dirigentes, /planes, /watched-profiles, /recomendaciones. Solo GET para todas las páginas.
- Login Saymi (`pineda@crece.mx` / `demo2026!`).
- Recorrido completo flujo demo:
  1. Overview
  2. Dirigentes (lista)
  3. Diagnóstico (B01-B18 visibles)
  4. Diferenciadores (Tier 2)
  5. FODA
  6. Social → Monitoreo · Comentarios · Clima · Top Posts (4 vistas)
  7. Indice Aceptación → Overview · Por dirigente · Fantasmas · **Fans y Perfiles (Misael ⭐ Fan #1)**
  8. Planes IA → plan_id=52 (5 tareas TODO)
  9. Reels (guiones)
  10. Recomendaciones
  11. Mi Evaluación
- Capturar screenshot por vista (15 screenshots).
- Detectar: 5xx, console errors, `Dirigente no encontrado`, mockup leak, layout broken.

**Criterio aceptación:**
- [ ] 11 vistas cargan sin 5xx.
- [ ] Misael Fan #1 visible en `/aceptacion/fans` con 40 reactions / 12 comments.
- [ ] Plan ID=52 visible en `/planes/52/tareas` con 5 TODO.
- [ ] Cero "Dirigente no encontrado" en ningún screenshot.
- [ ] Reporte resumen al CEO con screenshots + findings.

**Si encuentro regresión visible HOY:**
- Severity HIGH → fix HOY antes del piloto. Resto del plan se reagenda.
- Severity MEDIUM → documentar como blocker, decisión CEO si fix HOY o pre-demo mañana.
- Severity LOW → documentar para post-piloto.

### #6 · Test `applyVipOverrides` (Post-piloto día 1 · ~30 min)

**Scope:**
- `frontend/src/lib/api/utils/__tests__/vip-overrides.test.ts`.
- Casos:
  - dirigenteId=3 + raw incluye misael.gomez.981351 → Misael en posición 1 con 40/12, badge ⭐ Fan #1.
  - dirigenteId=3 + raw NO incluye misael → Misael se inyecta en posición 1.
  - dirigenteId=otro (sin override config) → ranking sin tocar.
  - Otros profiles desplazados a posiciones 2-N preservando orden relativo.

**Criterio:** 4/4 tests verdes · `npm test -- vip-overrides` pasa.

### #3 · Bug `/planes/{id}` control chars (Bloque A verificación HOY · Bloque B fix si confirma) · ~30-45 min fix

**Verificación HOY (Bloque A · 5-10 min):** durante el smoke pre-piloto, Playwright entra a `/dashboard/planes/52` (página individual del plan). Si:
- UI renderiza OK las 5 tareas + título plan → **bug NO afecta demo · #3 se queda en Bloque B post-piloto**.
- UI muestra error de parsing JSON, blank screen, "Error loading" → **bug rompe demo · fix HOY antes del piloto**.

**Lógica del fix (cuando se aplique · HOY o post-piloto):**

**Scope:**
- Identificar el campo que emite `\n` raw (probable `prompt_usado` o `contenido` con LLM output).
- Fix: sanitize strings antes de serialize, usar `json.dumps(..., ensure_ascii=False)` o equivalente FastAPI.
- O alternativa: response model con `Field(..., examples=[...])` y custom serializer.

**Test acompañante:**
- `backend/tests/api/v1/test_planes_endpoint.py::test_get_plan_id_emits_valid_json_with_control_chars`
- Sanity: jq y python `json.loads` strict ambos parsean el response.

**Criterio:** curl + `python3 -c "json.loads(...)"` sobre `/planes/52` no falla con `Invalid control character`.

### #2 · Tests Sprint F (Post-piloto día 3-4 · ~2-3h)

**Scope dividido:**
- `tests/scripts/test_regen_plan_dirigente.py`:
  - `test_parse_llm_json` — fence, JSON balanceado, control chars, malformed input
  - `test_validate_shape` — 3-8 recs, tipo enum, accion_texto required, ventana parseable
  - `test_call_claude_code_mock` — subprocess mockeado, retorna JSON válido / inválido / timeout
  - `test_call_gemini_cli_fallback` — CC falla → Gemini se llama
  - `test_plataforma_enum_mapping` — IG/FB/X/TikTok/YouTube/all → INSTAGRAM/FACEBOOK/...
  - `test_insert_plan_and_recomendaciones_mock_db` — verifica SQL queries construidas (in-memory SQLite o asyncpg mock)
  - `test_insert_paralelo_plan_tareas` — verifica plan_tareas row paralela (commit bc53ae5 cobertura)

**Estrategia mockeo v2 (anti-patrón SQLite corregido · concern Gemini):**
- `subprocess.run` con `monkeypatch` → retorna `CompletedProcess(returncode=0, stdout=fixture_json)`.
- **BD test Docker `crece-db-test` puerto 5439** (NO SQLite in-memory). Razón: asyncpg + Postgres dialect SQL difiere de SQLite, ya pasó con queries `raw_data->>'url'` y similar. Mismo motor que prod, lockeo predecible, teardown via DROP/CREATE schema.
  - Setup: nuevo servicio en `docker-compose.test.yml` apuntando a `crece-db-test:5439` con mismo schema (alembic apply) pero data vacía.
  - Fixture pytest `db_session_test` rollback-per-test para aislamiento.
- Fallback secundario si BD test no disponible: monkeypatch a nivel de SQLAlchemy query (mock del `session.execute`), no del backend DB.
- Fixtures con 5 recomendaciones reales del plan_id=52 como ground truth (JSON estático en `tests/fixtures/`).

**Criterio:** ≥10 tests · 100% verdes · coverage del script ≥80%.

### #4 · Tests Sprint A (Post-piloto día 4 · ~1.5h)

**Scope:**
- `backend/tests/api/v1/test_watched_profiles_dashboard.py`:
  - `test_interactions_summary_window_44d` → KPIs correctos
  - `test_timeline_30_buckets_44d`
  - `test_top_posts_winners_polaridad_positiva` (`kind=winners`)
  - `test_top_posts_losers_polaridad_negativa` (`kind=losers`)
  - `test_top_posts_sample_quotes_present`
  - `test_dirigente_id_access_control` — viewer NO ve dirigentes de otra org
  - `test_empty_data_dirigente_sin_posts`

**Estrategia datos:**
- Fixture pytest con dirigente_id=3 + posts mock + comments mock + watched_like_events mock.
- Cleanup post-test.

**Criterio:** ≥7 tests · 100% verdes · cobertura endpoints ≥85%.

### #5 · Tests Sprint D (Post-piloto día 5 · ~1.5h)

**Scope:**
- `tests/scripts/test_backfill_nlp_saymi.py`:
  - `test_filtro_length_gt_3` — emojis (3 chars) se excluyen
  - `test_retry_exponencial_3_intentos` — CC falla 2 veces → 3er intento OK
  - `test_effort_high_default` — variable `CC_EFFORT` lee de env
  - `test_tono_polaridad_mapping` — celebratorio→+1, critico→-1, etc
  - `test_upsert_no_dup` — re-correr no duplica filas
  - `test_dry_run_no_writes`

- `tests/scripts/test_audit_cc_effort_high.py`:
  - `test_sample_seed_42_reproducible`
  - `test_diff_count_categories` — clasificación distinta vs polaridad signo distinta

**Criterio:** ≥8 tests · 100% verdes.

## Riesgos · plan general

| ID | Riesgo | Mitigación |
|---|---|---|
| R-A | Smoke pre-piloto encuentra regresión HIGH en demo flow | Fix HOY antes del piloto · bloque B y C se reagendan |
| R-B | Mock asyncpg complicado para tests Sprint F | Plan B: usar BD de test separada en docker-compose (existe `crece-db` puerto 5438, levantar `crece-db-test` puerto 5439) |
| R-C | Tests Sprint A requieren scrapear datos de Apify para fixtures realistas | Plan B: usar dump JSON estático guardado en `tests/fixtures/saymi_44d_snapshot.json` |
| R-D | Bug `/planes/{id}` puede tener causa raíz más profunda que escapar `\n` | Si fix simple falla, downgrade a issue documentado · prioridad sigue baja por axios tolerance |

## Plan de validación

- **Backend tests (#2, #3, #4, #5):** `pytest backend/tests/...` con coverage report. CI corre en cada PR.
- **Frontend test (#6):** `cd frontend && npm test -- vip-overrides`.
- **Smoke (#1):** Playwright headless · screenshots a `/tmp/crece_smoke_*.png` para review CEO.

## Plan de deploy

- **Smoke (#1):** ya hay deploy actual · NO requiere deploy nuevo · solo validación.
- **Bug fix #3:** PR formal con CI + Gemini review (siguiendo patrón hoy) → `cd frontend && vercel --prod --yes` si tocó frontend (no aplica aquí, solo backend). Backend cambios entran via Coolify auto-deploy o el flujo que el equipo use.
- **Tests #2-#6:** NO requieren deploy productivo. Son parte del CI.

## Gating entre bloques

```
A (HOY) ─gate_smoke─→ piloto §9.8 ─gate_demo_ok─→ B (día 1-2) ─gate_B_verde─→ C (día 3-5)
                                          │
                                          └─ Si demo encuentra bugs nuevos → B se reordena
```

## Total esfuerzo

| Bloque | Items | Horas | Cuándo |
|---|---|---|---|
| A | #1 | 0.5h | HOY |
| B | #3, #6 | 1-1.5h | Día 1-2 post-piloto |
| C | #2, #4, #5 | 5-6h | Día 3-5 post-piloto |
| **Total** | 6 items | **6.5-8h** | ~1 semana calendario |

## Fragmentación sesiones IA (concern Gemini)

**NO se ejecutan 8h en una sola sesión IA.** Cada bloque arranca en sesión IA independiente con handoff documentado:

### Handoff entre sesiones

Al final de cada bloque:
- Commit + push de todos los cambios.
- Update `.context/STATUS.md` con bloque cerrado, lo que falta, próximos pasos.
- Update `.context/HANDOVER-AI.md` con decisiones nuevas + assumptions a verificar.
- Si hay blockers descubiertos durante el bloque, agregar a `.context/BLOCKERS.md`.

Al arrancar siguiente bloque (sesión nueva):
- Leer CONTEXT ANCHOR completo (`STATUS.md`, `HANDOFF`, `DECISIONS.md`, `BLOCKERS.md`, `PLAN-current.md`).
- Leer este plan v2.
- Confirmar al CEO el bloque que arranca + leer estado del anterior antes de tocar código.

### Tamaño esperado de cada sesión IA
- Bloque A (HOY): ~30-45 min · 1 sesión actual.
- Bloque B: ~1-1.5h · 1 sesión separada post-piloto.
- Bloque C: dividible en 3 sub-sesiones (#2 Sprint F, #4 Sprint A, #5 Sprint D) por separación cognitiva o 1 sola sesión de 5-6h con compactaciones intermedias.

## Pendiente CEO antes de ejecutar

1. Aprobar plan v2 o pedir ajustes.
2. Luz verde para arrancar **bloque A (smoke + verificación bug control chars) HOY**.
3. Si bloque A encuentra regresión HIGH o bug rompe demo, decisión inmediata: fix HOY o aceptar como caveat documentado.

## Trazabilidad

- v1: plan original (smoke A · bug en B · tests en C · single session).
- v2: post cross-audit Gemini (`approve_with_changes` · 2 blocking + 2 non-blocking absorbidos).
- Cross-audit raw: `/tmp/gemini_plan_b_response.txt` (no committeado).
