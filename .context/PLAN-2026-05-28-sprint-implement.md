# PLAN — Sprint Implement 2026-05-28 noche
**Origen:** `~/.claude/plans/structured-greeting-clarke.md` (aprobado por CEO).
**Modo:** autónomo con loop verificación. Skip sprint bloqueado, defer sprint con dependencia CEO.

## Sprints

### Sprint A — Fix bug `n_ins` adapter comments (30-45 min) · INDEPENDIENTE
**Objetivo:** Defensa en profundidad contador real de INSERTs en `ingest_radar_comments_payload.py`.
**Archivos:**
- `backend/scripts/ingest_radar_comments_payload.py` (EDIT línea 95)
**Cambios:**
- Mover `n_ins += 1` DENTRO del `if commit and cid:` (línea 82)
- Agregar `n_skipped_no_cid = 0` + incrementarlo cuando `cid` es falsy
- Actualizar print final: incluir `n_skipped_no_cid`
**Criterio aceptación:**
- Dry-run con JSON sintético (cid=None) reporta `n_ins=0, n_skipped_no_cid>0`
- Dry-run con JSON válido reporta `n_ins=N` correcto
- Commit conventional + Co-Authored-By
**Dependencias:** ninguna.
**Tests:** test ad-hoc con JSON sintético en `/tmp/`.

---

### Sprint B — Gobernanza Etapa 1 (2-3h) · INDEPENDIENTE
**Objetivo:** Adoptar Etapa 1 del doc gobernanza nuevo: AGENTS.md raíz + docs/adr/ con 5 ADRs canónicos + SESSION_HANDOFF template.

#### B.1 — AGENTS.md raíz (45 min)
**Archivos:**
- `AGENTS.md` (CREATE)
**Contenido (escrito a mano, ≤500 líneas según ETH Zürich):**
- Stack + comandos exactos desde `Makefile` real
- Límites declarados: `migrations/` solo alembic, `.context/governance/*` solo PR humano, `.env*` nunca commit, `frontend/src/lib/api/utils/vip-overrides.ts` mockup intencional
- Definition of Done: `make test` exit 0, `pnpm tsc --noEmit` exit 0, conventional commit, ADR si arquitectónico
- Política humano-vs-agente: agentes abren ADR para decisiones arquitectónicas con frontmatter `author: AGENT <tool/model>`
- Cierre sesión → `.context/templates/SESSION_HANDOFF.md`
- Perfiles de prueba (Piña, Solano, Saymi, Pepe, Felipe) con sus dirigente_id
- Anti-patrones (no Inter/Roboto, no púrpura genérico, no datos mock, etc.)

#### B.2 — docs/adr/ + 5 ADRs canónicos (1h)
**Archivos:**
- `docs/adr/README.md` (CREATE — índice)
- `docs/adr/0001-ollama-off-plan-ia-timeout.md` (CREATE)
- `docs/adr/0002-misael-vip-mockup-frontend.md` (CREATE)
- `docs/adr/0003-fans-perfiles-sidebar-invariante.md` (CREATE)
- `docs/adr/0004-anti-fallback-data-ui.md` (CREATE)
- `docs/adr/0005-misael-vip-40-12.md` (CREATE)
**Plantilla Nygard:** Title / Status / Context / Decision / Consequences. Frontmatter con `author` (HUMAN ceo o AGENT linda).
**Fuente:** extraer de `DECISIONS.md` solo las secciones vigentes y arquitectónicas. NO migrar todo el 158KB.

#### B.3 — SESSION_HANDOFF template + Co-Author verify (30 min)
**Archivos:**
- `.context/templates/SESSION_HANDOFF.md` (CREATE)
**Contenido:** fusión del doc §"Archivo de handoff" + disciplina email-handoff SRE + memoria 3-capas Anthropic.

**Criterio aceptación Sprint B:**
- AGENTS.md ≤500 líneas, comandos copy-paste, sin auto-generar
- 5 ADRs creados, frontmatter author correcto, status `Accepted`
- README docs/adr/ lista los 5 con links
- SESSION_HANDOFF.md plantilla con secciones del doc

---

### Sprint C — MAPA §2 Diagnóstico Tier 1 B01-B18 (2-3h) · INDEPENDIENTE
**Objetivo:** Cerrar §2 del MAPA-FUNCIONAL con checklist 7 pasos + auditoría Gemini.

#### C.1 — Grep + lectura (45 min)
- Grep `B0[1-9]|B1[0-8]` en `backend/`
- Leer `app/services/diagnostico/{er,breakout,matrix_2x2,benchmark,sentiment_plutchik,crisis_spike,growth_attribution,sov,share_like_ratio,humanizacion}_service.py`
- Leer endpoint `/diagnostico/{dirigente_id}`
- Leer hook `useDiagnosticoTier1` (si existe — sub-regla #6 CRUD simétrico)
- Leer página `/dashboard/diagnostico/[dirigenteId]/`
- Queries SQL cobertura por bloque (sub-regla #5)

#### C.2 — Redacción §2 (1-1.5h)
**Archivos:**
- `.context/MAPA-FUNCIONAL.md` (EDIT — reemplazar esqueleto §2 con sección sólida)
**Contenido:** 6 sub-secciones del template MODELO + tablas endpoints/hooks/páginas con citas `file:line`.

#### C.3 — Auditoría Gemini (30 min background)
- Generar prompt desde `PROMPT-AUDITOR-GEMINI.md` ajustado a ruta+§2
- `nohup gemini --yolo -p "$(cat <prompt>)" > .context/audits/2026-05-28-mapa-funcional-seccion-2.md 2>&1 &`

#### C.4 — Correcciones post-audit (30 min)
- Aplicar hallazgos sustantivos
- Si defensa razonada con datos: aclarar redacción (sub-regla §5.4 nueva)
- Commit

**Criterio aceptación Sprint C:**
- §2 cubre los 10 servicios + endpoint + hook + página + cobertura DB
- Auditoría Gemini con ≤2 hallazgos sustantivos
- Correcciones aplicadas
- Status §2 en README governance: 🟡 → ✅

---

### Sprint D — Ingest Felipe E2E · BLOQUEADO (espera Marx)
SKIP esta sesión. Marx envía paquete completo cuando termine comments. Cuando llegue:
- Tasks #1 y #2 del TaskList se activan
- Verificar dedup por URL antes INSERT (9 cross-scheme pfbid/base64 en manifest)
- Confirmar counts a Marx con SQL

---

### Sprint E — Docs governance faltantes · PARCIAL
- ORGANIZACION.md: ejecutable sin CEO (fork GitLab Handbook + sección agentes)
- REGLAS.md: ejecutable sin CEO (consolidar LFPDPPP + D-* + error notebook)
- PRODUCTO.md: REQUIERE CEO (Cagan Vision FAQ + Amazon Working Backwards)

DEFER esta sesión si no alcanza tiempo. Si alcanza: ORGANIZACION + REGLAS.

---

## Asignación recursos (Fase 3)

| Sprint | Skills carga | Herramientas |
|---|---|---|
| A | python-expert, systematic-debugging | Bash (dry-run JSON sintético) |
| B | technical-writer (para AGENTS.md), obsidian-markdown | Read Makefile, DECISIONS.md (slices), CLAUDE.md |
| C | claude-obsidian:wiki-query, sequential-thinking | Grep, Read services, psql via container, Gemini --yolo background |

## Loop verificación post-sprint

Tras cada sprint:
1. ¿Archivos creados/editados son los planeados? (no scope creep)
2. ¿Conventional commit + Co-Authored-By? `git log -1 --format=%B`
3. ¿No tocaron archivos fuera del plan? `git diff --name-only main...HEAD`
4. ¿Tests / dry-runs pasan donde aplica?
5. Si falla → fix antes del siguiente sprint

## Reporte final

Tras Sprint C (o el último ejecutado):
- Actualizar `.context/STATUS.md` (append nueva sección con resumen)
- Append `.context/DECISIONS.md` con decisiones nuevas (si las hubo)
- Actualizar `.context/governance/README.md` status: §2 MAPA ✅, AGENTS.md ✅, ADRs ✅
- TaskUpdate: marcar completados, dejar pendientes con status real
- Mensaje a CEO con tabla "completado vs planificado vs pendiente vs bloqueado"
