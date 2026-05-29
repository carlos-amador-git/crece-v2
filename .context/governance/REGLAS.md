# REGLAS — CRECE v2

**Última actualización:** 2026-05-28
**Propósito:** consolidar el código de conducta, las reglas duras, los compliance obligatorios, y los ADRs canónicos vigentes. Antes de proponer cualquier feature/cambio: leer este doc, leer `AGENTS.md` raíz, leer `MAPA-FUNCIONAL.md` de la sección afectada.

> **Doble capa:**
> - **Nivel A (humano · valores de ingeniería):** secciones §1-3. Inspirado en handbooks abiertos GitLab/PostHog (CC BY-SA).
> - **Nivel B (agente · contratos ejecutables):** secciones §4-9 + referencia obligatoria a `AGENTS.md` raíz.

---

## 1. Valores de ingeniería (Nivel A)

### 1.1 Honestidad técnica
- **Reportar honestamente.** Si tests fallan, decirlo con el output. Si un paso fue skipped, decirlo. Cuando algo funciona y está verificado, decirlo plano sin hedging.
- **No "está casi listo".** O está hecho con criterio de aceptación verificable o no está hecho.
- **No "se ve bien en mocks".** Si no se probó contra datos reales, no es funcional.

### 1.2 Datos reales > datos sintéticos
- **Cero inventos.** Si falta un dato → reportar el vacío. NUNCA llenarlo con sintético.
- **Cero fallback hardcoded en UI con números visibles.** Skeleton + estado vacío explícito (ADR D-ANTI-MOCK-1).
- **Validado por:** `frontend/scripts/check-no-mocks.sh` corre antes de commit y en CI.

### 1.3 Calidad > tiempo
- Si una tarea requiere 2 sesiones para hacerse bien, se hace en 2 sesiones.
- NO aceptar compromisos parciales tipo "30% mejor que 0%" (regla CEO 2026-05-28).
- Auditoría obligatoria antes de cerrar sección de doc de gobernanza.

### 1.4 Cero scope creep
- "Surgical Changes" (CLAUDE.md global §Karpathy 3): tocar solo lo que el ticket pide.
- Si notas dead code adyacente → mencionarlo, no borrarlo (salvo orphans dejados por tu propio cambio).
- Match el estilo existente aunque lo harías distinto.

---

## 2. Reglas de comunicación

### 2.1 Caveman default (regla `~/.claude/CLAUDE.md`)
- Lite siempre activo: cero filler, cero pleasantries, oraciones completas con artículos.
- Patrón: dato → acción → razón. Sin "Great question", sin cierre "avísame si…".
- Auto-clarity: cae a prosa normal SIN pedirlo cuando hay riesgo de ambigüedad técnica, acción irreversible, mensaje a cliente.

### 2.2 Reporte de progreso
- Final del turno: tabla "completado / pendiente / bloqueado" si la sesión tuvo >3 sub-tareas.
- Mensaje al CEO empieza por bloqueador crítico si existe, NO al final.

---

## 3. Reglas de cambio organizacional

- Cambios a este doc requieren PR humano del CEO (`AGENTS.md` §5 límite duro).
- Cambios a `MODELO-TRABAJO-AUDIT.md`, `PROMPT-AUDITOR-GEMINI.md`, `README.md` (governance) también PR humano.
- ADRs `Accepted` son inmutables. Para cambiar la decisión: ADR nuevo + flip del viejo a `Superseded by ADR-NNNN`.

---

## 4. Compliance legal (Nivel B · obligatorio)

### 4.1 LFPDPPP (Ley Federal de Protección de Datos Personales en Posesión de Particulares)
- **Pseudonimización obligatoria:** todos los `author_username` / `commenter_handle` de redes sociales se hashean vía `app.services.author_hash.ensure_author_hash()` con salt env `COMMENT_AUTHOR_SALT` antes de persistir.
- **NO exponer al cliente** los `author_hash` raw — solo via UI con display name.
- **Datos `_radar_engine`, `_source_engine`** son metadatos técnicos, no PII.
- **Reactor display names** entran en BD pero quedan asociados al hash (no al username crudo).

### 4.2 INE compliance
- **Modo veda:** parámetro `?en_veda=true` en B17 (`hitl_evaluation.py` y `diagnostico_tier2.py`) activa reglas estrictas.
- **Trazabilidad de gastos generados por IA:** todo contenido generado debe tener `modelo_ia` poblado (en `planes_ia.modelo_ia` y `social_posts.nlp_model_version`).
- **Etiquetado IA:** UI debe mostrar "Generado por IA" en planes y diagnósticos. Validar en cada release.

### 4.3 ToS de redes sociales
- Scrapers operan en el lado **autorizado**: solo perfiles públicos del propio dirigente cliente.
- NO scraping de competidores sin autorización explícita CEO.
- NO masiva recolección de PII para reventa.

---

## 5. Reglas operativas duras

### 5.1 Reglas que no admiten excepción
| # | Regla | Citación |
|---|---|---|
| 1 | **NO acciones destructivas Docker sin confirmación textual CEO en sesión actual** | `~/.claude/CLAUDE.md` §"Regla de Acciones Destructivas Docker" · postmortem `cfdi-motor/.context/POSTMORTEM-20260413-docker-raw-wipe.md` |
| 2 | **NO rotar `.env*`** | Feedback CEO 2026-05-25 (`memory/feedback_no_rotar_scraping_keys.md`) |
| 3 | **NO modificar archivos del bloque ESTABLE mid-task** (incluye ADRs `Accepted`, `AGENTS.md`, `CLAUDE.md`, `MODELO-TRABAJO-AUDIT.md`) | `~/.claude/CLAUDE.md` §"Cache Hygiene" + `AGENTS.md` §5 límites duros |
| 4 | **NO multi-sesión sobre mismo cwd sin git worktrees** | `~/.claude/CLAUDE.md` §"Regla de Git Worktrees para Multi-Sesión" |
| 5 | **NO commit sin Co-Authored-By cuando es agente** | `AGENTS.md` §6.4 |
| 6 | **NO ADR `Accepted` editado.** Si la decisión cambia → ADR nuevo + flip del viejo a `Superseded by ADR-NNNN`. | `AGENTS.md` §7 + `docs/adr/README.md` §"Reglas de mantenimiento" |
| 7 | **NO datos sintéticos / mock data en UI con números** | ADR-0003 (D-ANTI-MOCK-1) + `check-no-mocks.sh` |
| 8 | **HARD RULE: grep antes de proponer** | `memory/feedback_buscar_codigo_antes_proponer.md` (2026-05-28) |
| 9 | **NO sugerir reescritura masiva cuando hay layer-of-fix más barato** | `memory/feedback_layer_of_fix_before_refactor.md` |
| 10 | **NO inventar problemas sobre tools validadas por CEO** | `~/.claude/skills/learned/writing-review-list.md` regla #7 |
| 11 | **PSEUDONIMIZACIÓN OBLIGATORIA `author_hash` LFPDPPP**: todo `author_username` / `commenter_handle` de redes pasa por `app.services.author_hash.ensure_author_hash()` antes de INSERT. NO persistir usernames crudos. | LFPDPPP + `AGENTS.md` §11 + `REGLAS.md` §4.1 |
| 12 | **NO editar `frontend/src/lib/api/utils/vip-overrides.ts` sin PR humano explícito CEO**. Mockup intencional ADR-0002. | `AGENTS.md` §5 límites duros + ADR-0002 |

### 5.2 Reglas que aplican con criterio
- **Test cost ratio:** test contra API de pago debe ser ≤ 15-20% del costo de la extracción real (`memory/feedback_test_cost_ratio.md`).
- **Auditar antes de proponer rebuild:** ejecutar audit BD/grep ANTES de proponer sprint de rebuild (`memory/feedback_audit_before_rebuild.md`).
- **env_file root-only:** docker-compose lee solo root `.env`. `backend/.env` no llega al container (`memory/feedback_env_file_root_only.md`).
- **Persistir decisiones de peers en DECISIONS.md INMEDIATAMENTE** (`memory/feedback_persist_peer_decisions.md`).
- **Sentry middleware vs auto-instrumentación:** preferir `SentryTraceMiddleware` explícito sobre `StarletteIntegration` cuando hay tests con ASGITransport (`memory/feedback_sentry_middleware_vs_autoinstrument.md`).

---

## 6. ADRs canónicos vigentes

5 ADRs canónicos migrados al formato Nygard+MADR en `docs/adr/` (2026-05-28):
- [ADR-0001 Ollama OFF · Plan IA pausado](../../docs/adr/0001-ollama-off-plan-ia-pausado.md)
- [ADR-0002 VIP overrides como mockup frontend-only](../../docs/adr/0002-vip-overrides-mockup-frontend.md)
- [ADR-0003 Anti-fallback data UI](../../docs/adr/0003-anti-fallback-data-ui.md)
- [ADR-0004 Fans y Perfiles sidebar invariante](../../docs/adr/0004-fans-perfiles-sidebar-invariante.md)
- [ADR-0005 Misael VIP override 250/12](../../docs/adr/0005-misael-vip-override-250-12.md)

El resto vive en `DECISIONS.md` formato narrativo histórico. Aplican como contratos arquitectónicos hasta que sean `Superseded`.

> **Cobertura:** este doc cataloga **35 ADRs representativos** del `DECISIONS.md`. La cuenta real es **73 ADRs únicos** (verificado `grep -cE "^### D-|^## D-" .context/DECISIONS.md` 2026-05-28). Los 38 restantes son ADRs históricos / superseded / contexto piloto específico.
>
> **⚠️ Drift de líneas declarado** (hallazgo audit Gemini 2026-05-28): los números de línea en las tablas §6.1-6.5 abajo pueden estar desfasados ±5 líneas por ediciones posteriores de `DECISIONS.md`. Los slugs de ADR (D-OPS-01, D-PILOTO-01, etc.) son la cita confiable; la línea es referencia rápida no autoritativa. Si la encuentras desfasada al verificar, abre PR con la línea actualizada.

### 6.1 Operativos (D-OPS)
| ADR | Decisión |
|---|---|
| D-OPS-01 | Cherry-pick selectivo sobre merge completo (línea 1179) |
| D-OPS-02 | Lenis remoción definitiva (línea 1191) |
| D-OPS-03 | Política release branch — PROPUESTA + mitigación interina activa (línea 1196) |
| D-OPS-04 | Deuda declarada: 11 commits restantes de `feat/eval-benchmark-v1` (línea 1203) |
| D-OPS-05 | Convención operativa: Fase 0 sprint verifica BD + código (línea 1223) |
| D-OPS-06 | Formato de instrucciones revisor §9.8 → Joy (línea 1229) |
| D-OPS-07 | Post-mortem incidente `3d6fe3f1660d` (línea 1077) |
| D-OPS-08 | Prohibición Alembic `autogenerate` sin revisión manual (línea 1116) |
| D-OPS-09 | Límite de scope por commit (migraciones atómicas) (línea 1134) |
| D-OPS-10 | Revisor §9.8 lee diff completo pre-autorización schema (línea 1150) |

### 6.2 Producto · Piloto comercial (D-PILOTO)
| ADR | Decisión |
|---|---|
| D-PILOTO-01 | Apertura piloto comercial con 3 dirigentes activos + 5 shadow (línea 1248) |
| D-PILOTO-02 | Login hardening: remover accesos demo de producción (línea 1269) |
| D-PILOTO-03 | Corrección documental: Ballesteros shadow → activo (no es promoción) (línea 1273) |

### 6.3 Gate (D-GATE)
| ADR | Decisión |
|---|---|
| D-GATE-01 | MATRIZ_ER_5x5 → Zenodo v1 empírico (F-01) (línea 1286) |
| D-GATE-02 | F-16 typeahead Harfuch DIFERIDO §6.4 (línea 1290) |
| D-GATE-03 | Prompt Plan IA v1.1 preparado NO ACTIVO (línea 1294) |
| D-GATE-05 | LaunchAgent cloudflared auto-update cierra D-INFRA-01 (línea 1299) |
| D-GATE-07 | Máquina de estados Plan IA es contrato canónico (línea 1304) |

### 6.4 Data Source (D-DS)
| ADR | Decisión |
|---|---|
| D-DS-01 | Snapshots diarios (no on-demand) (línea 1330) |
| D-DS-02 | Denormalización 3 columnas (línea 1333) |
| D-DS-03 | enum `data_source` (veto de Gemini al bool) (línea 1336) |
| D-DS-04 | Alerta deuda de frescura 48h (línea 1339) |
| D-DS-05 | Extender task existente, no crear nueva (línea 1342) |
| D-DS-06 | YouTube Docker IP block → opción 3 (línea 1345) |

### 6.5 Seguridad (D-SEC)
| ADR | Decisión |
|---|---|
| D-SEC-04 | IDOR parcial en `/dirigentes/{id}/crecimiento` (riesgo aceptado durante piloto) (línea 1233) |

### 6.6 Producto · Decisiones recientes
| ADR | Decisión | Cita |
|---|---|---|
| D-1 | Ollama OFF (Plan IA timeout Coolify) | `memory/MEMORY.md` |
| D-3 | Misael VIP mockup en `vip-overrides.ts`. BD jamás se toca. | `memory/MEMORY.md` |
| D-MISAEL-VIP-40 | Misael Fan #1 con 40/12 | `memory/MEMORY.md` |
| D-FANS-PERFILES-SIDEBAR-INVARIANTE | Sidebar Fans y Perfiles restaurada | Commit cd3e408e75 |
| D-ANTI-MOCK-1 | Anti-fallback-data UI 2026-05-11 | `frontend/scripts/check-no-mocks.sh` |
| D-PLANES-CONCEPTO-3 | Rediseño Planes IA 2026-05-21 (3 tabs visuales) | `dashboard/planes/page.tsx:3` |
| D-PLANES-DIAGNOSTICO-REMOVED | Tab Diagnóstico eliminado 2026-05-22 (2 tabs reales) | `dashboard/planes/page.tsx:57` |
| D-CTA-GENERATE-REMOVED | CTA "Generar Plan" eliminado del header 2026-05-21 | MAPA §4.1 |
| D-23-H Phase B | Mi Evaluación: solo Palanca 1 (pesos por categoría) | `dashboard/evaluacion/[id]/page.tsx:14` |
| D-ACEPTACION-DEDUPE | Multi-dirigente selector solo admin/analyst | MAPA §4.1 |

### 6.7 ADRs por proponer (deuda detectada en MAPA-FUNCIONAL)
| Tema | Razón | Detectado en |
|---|---|---|
| Adapters universales flat shape | Wrapper one-shot Felipe 2026-05-28 evidencia mismatch sistemático | MAPA §3, §4 |
| Contrato export radar↔crece | Marx propone D-041 en su lado | HANDOFF 2026-05-28 |
| `estructura_json` migrar legacy `riesgos` → `amenazas` | 14/35 DIAGNOSTICOs NULL en estructura_json (40%) | MAPA §3.4 |
| Estandarizar `modelo_ia` labels | 16 etiquetas distintas en BD | MAPA §4.4 |
| Persistir CIB flags (vs in-memory actual) | B12 → B13 sin audit trail | MAPA §8.5 |
| Tabla dedicada `reel_scripts` vs `contenido_piezas.variantes` jsonb | Decisión actual confusa | MAPA §6C.4 |
| Hooks centralizados `use-admin.ts` vs inline | Convención inconsistente vs cliente | MAPA §10E |
| HITL bilateral cliente+admin | Aclarar en ADR la decisión de scope RBAC compartido | MAPA §9 + §10 |

---

## 7. Error notebook (lecciones del CEO)

Las correcciones del CEO al agente quedan en `~/.claude/skills/learned/writing-review-list.md`. Las reglas activas se cargan en SessionStart hook.

**Promoción a CLAUDE.md global:** si una regla del notebook alcanza 3+ fails en el mismo patrón, se promueve. Las que ya están promovidas:
- "NO inventar problemas sobre tools validadas por CEO" (10 fails, promovida 2026-05-27)
- "Buscar código antes de proponer" (HARD RULE 2026-05-28)
- "Gobernanza docs: calidad > tiempo" (2026-05-28)

---

## 8. Tests y CI

- `make test` debe pasar antes de merge.
- `pnpm tsc --noEmit` debe pasar.
- `pnpm check:no-mocks` bloquea fallback data hardcoded.
- E2E con Playwright para flujos críticos.
- CI corre en GitHub Actions (verificar configuración actual).

---

## 9. Manejo de secretos

- `.env*` SIEMPRE gitignored. NO commit.
- `COMMENT_AUTHOR_SALT` env var crítico para LFPDPPP. NO compartir entre tenants.
- Tokens Apify, Brightdata, Crawlbase, Groq → solo en `.env*`. NO hardcoded.
- Credenciales OAuth (Google, Meta) → `~/.config/crece/` fuera del repo.

---

## 10. Versión y cambios

| Fecha | Cambio |
|---|---|
| 2026-05-28 | Versión inicial. Linda redactó tras `/sprint-implement` luz verde CEO. Consolida reglas de CLAUDE.md global + AGENTS.md proyecto + DECISIONS.md + error notebook. |
| 2026-05-28 (mismo día) | Audit Gemini intentado · timeout (300s, similar a §10 MAPA). Verificación lateral del redactor ejecutada: 35 ADRs citados confirmados existen en DECISIONS.md (rangos D-OPS-01 línea 1179, D-PILOTO-01 línea 1248, D-DS-01 línea 1330 muestreados). Hallazgo: el documento cubre 35 de los 73 ADRs únicos reales — corregido §6 nota de cobertura representativa. `check-no-mocks.sh` y `writing-review-list.md` confirmados existentes. |
| 2026-05-28 (re-audit) | Audit Gemini ⚠️ Pasa con ajustes (prompt acotado funcionó). 4 hallazgos aplicados §5.1: pseudonimización LFPDPPP como regla #11; inmutabilidad ADRs explícita en regla #6; bloque ESTABLE como parte de regla #3; vip-overrides.ts prohibido editar como regla #12. §6 ahora cita los 5 ADRs migrados a `docs/adr/` + declara drift de líneas en tablas §6.1-6.5. Reporte: `.context/audits/2026-05-28-reglas.md`. |
