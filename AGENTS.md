# AGENTS.md — CRECE v2

> **Para agentes (Claude Code, Codex, Cursor, Copilot, Gemini CLI, Windsurf, Devin).**
> Tu fuente única de verdad operativa. Si algo NO está aquí, NO lo inventes — pregunta al humano.
>
> **Para humanos:** este archivo se edita a mano. NO auto-generes (ETH Zürich 2026-02-12 encontró que archivos AGENTS.md auto-generados o inflados REDUCEN éxito de tareas ~3% y suben costo de inferencia +20%). Mantenerlo ≤500 líneas, alta señal.

---

## 1. Proyecto

**CRECE v2** — Plataforma de inteligencia electoral y social para Movimiento Ciudadano CDMX.
Reemplaza sistema Oracle APEX anterior. Cliente: ConsultoríaMD (relación de 4+ años con MC).

- **Cwd canónico:** `/Users/marxchavez/Projects/crece-v2`
- **Rama default:** `main`
- **Rama activa actual:** ver `git branch --show-current` (no asumir)
- **Doc de gobernanza:** `.context/governance/README.md` (orden de los 5 docs)

## 2. Stack (versiones congeladas)

| Capa | Tech | Versión |
|---|---|---|
| Backend | FastAPI (Python) | 3.12 |
| ORM | SQLAlchemy 2.0 async | — |
| DB | PostgreSQL + PostGIS | 16 + 3.4 |
| Workers | Celery + Redis | — |
| Storage | MinIO (S3-compatible) | — |
| Frontend | Next.js (App Router) | 14+ |
| Lenguaje FE | TypeScript | — |
| UI | Tailwind CSS + shadcn/ui | — |
| Mapas | MapLibre GL JS | — |
| Charts | Recharts | — |
| Deploy | Docker Compose → Coolify (Carlos) + Vercel (piloto) | — |

## 3. Comandos exactos (copy-paste)

**Hay dos contextos: contenedores (uso default vía Makefile) y host (scripts ad-hoc con venv).**

### 3.1 Desde el host con `make` (preferido)

```bash
make dev              # Levanta todo (backend :8002, frontend :3000, flower :5555, minio :9001)
make build            # docker compose build
make migrate          # alembic upgrade head DENTRO del container backend
make migrate-create MSG="add foo"  # alembic revision --autogenerate
make seed             # python -m app.scripts.seed
make test             # pytest -v en container backend
make test-cov         # pytest --cov=app
make lint             # ruff check . + mypy . en container backend
make format           # ruff format . + ruff check --fix .
make logs             # docker compose logs -f (todos)
make logs-backend     # solo backend
make shell-db         # psql en container db
make down             # docker compose down (sin -v)
make ps               # docker compose ps
```

**Puertos host CRECE** (NO compartir con otros proyectos — `~/Projects/claude-agents/PORT-REGISTRY.md`):
- Postgres: **5438** (`crece-db` container)
- Backend API: **8002**
- Frontend: **3000**
- Redis: contenedor interno, no expuesto host
- Flower: **5555** · MinIO: **9001**

### 3.2 Desde el host con venv (scripts ad-hoc)

```bash
cd backend
PYTHONPATH=. .venv/bin/python3 scripts/<script>.py [args]
```

El venv vive en `backend/.venv/`. NO lo recrees salvo que falten deps; si faltan, `cd backend && .venv/bin/pip install -r requirements.txt`.

### 3.3 Frontend (host directo, sin container)

```bash
cd frontend
pnpm dev              # next dev (usa lo que esté en :3000)
pnpm build            # next build
pnpm lint             # next lint
pnpm type-check       # tsc --noEmit
pnpm check:no-mocks   # bash scripts/check-no-mocks.sh — bloquea fallback data en UI
pnpm test:e2e         # playwright e2e
```

### 3.4 SQL ad-hoc

```bash
docker exec crece-db psql -U crece -d crece -c "SELECT ..."
```

### 3.5 Cross-audit Gemini (background)

```bash
nohup gemini --yolo -p "$(cat .context/governance/PROMPT-AUDITOR-GEMINI.md | sed 's|<RUTA>|...|; s|<§>|...|')" \
  > .context/audits/2026-MM-DD-<doc>-<seccion>.md 2>&1 &
```

## 4. Estructura del repo (canónica)

```
crece-v2/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # endpoints REST
│   │   ├── core/            # config, auth, DB
│   │   ├── models/          # SQLAlchemy
│   │   ├── schemas/         # Pydantic v2
│   │   ├── services/        # lógica negocio (diagnostico/, sentiment/, plan_generator/)
│   │   ├── scrapers/        # por plataforma
│   │   ├── nlp/             # pysentimiento + spaCy + gemini inline
│   │   └── workers/         # celery tasks
│   ├── migrations/          # alembic — SOLO modificar via `make migrate-create`
│   ├── scripts/             # ingest_radar_*, regen_*, audits ad-hoc
│   └── tests/
├── frontend/
│   └── src/
│       ├── app/             # Next App Router pages
│       ├── components/
│       └── lib/             # api client, hooks, utils, vip-overrides.ts (mockup intencional)
├── docs/
│   ├── adr/                 # ADRs (Nygard format) — SEE §7
│   └── …                    # specs producto
├── .context/                # estado operativo (mayormente trackeado, parcialmente gitignored)
│   ├── governance/          # README + MODELO + PROMPT-AUDITOR + MAPA + PIPELINE + …
│   ├── audits/              # reportes Gemini por sección
│   ├── templates/           # SESSION_HANDOFF.md plantilla
│   ├── STATUS.md            # estado actual append-only (volátil)
│   ├── DECISIONS.md         # changelog narrativo (vive, NO archivos ADR aquí)
│   ├── PLAN-current.md      # roadmap activo
│   ├── BLOCKERS.md          # bloqueos vigentes
│   └── HANDOFF-*.md         # snapshots pre-compactación
├── docker-compose.yml
├── docker-compose.prod.yml
├── Makefile
├── CLAUDE.md                # Claude Code project file (thin, referencia este AGENTS.md)
└── AGENTS.md                # ← ESTE ARCHIVO
```

## 5. Límites duros (nunca tocar sin autorización humana)

| Path / regla | Razón |
|---|---|
| `.env`, `.env.*`, `.env.scraping-keys` | Secretos. CEO decidió 2026-05-25 NO rotar — no re-sugerirlo. |
| `migrations/versions/*.py` directamente | Solo vía `make migrate-create`. NO `git rm` migraciones pasadas. |
| `frontend/src/lib/api/utils/vip-overrides.ts` | Mockup intencional Misael VIP (ADR-0002). NO borrar, NO migrar a BD. |
| `.context/governance/{MODELO-TRABAJO-AUDIT,PROMPT-AUDITOR-GEMINI,README}.md` | Cambios requieren PR humano explícito. Son el contrato de proceso. |
| `docs/adr/000*-*.md` (status `Accepted`) | ADRs aceptados son INMUTABLES — si cambia la conclusión, escribir ADR nuevo que reemplace + cambiar status del viejo a `Superseded by ADR-NNNN`. Nunca editar el contenido. |
| Volumes Docker (`crece-db`, `crece-redis`, etc.) | Acción destructiva (`down -v`, `prune --volumes`, `rm Docker.raw`) requiere confirmación textual del CEO en la sesión actual. Ver postmortem `cfdi-motor/.context/POSTMORTEM-20260413-docker-raw-wipe.md`. |
| `data/` (en su caso), exports con PII | Nunca commit. `.gitignore` aplica. |
| Cualquier acción cross-proyecto (cambiar archivos en `cfdi-motor`, `radar`, `armonia`) | Avisar al CEO + ack del peer correspondiente vía `claude-peers`. |

## 6. Convenciones

### 6.1 Código backend
- Tests con `pytest`, fixtures en `tests/conftest.py`. NO mocks que oculten fallas (regla §11).
- Async por default (FastAPI + SQLAlchemy async + asyncpg).
- Pydantic v2 para schemas; SQLAlchemy 2.0 typed para models.
- Type hints obligatorios en funciones públicas.
- Loguru para logs (ya configurado).

### 6.2 Código frontend
- App Router (no Pages Router). Server Components por default.
- shadcn/ui + Tailwind. Cero inline styles. CSS variables HSL para color.
- Tipografía: NUNCA Inter/Roboto/Arial. Fuentes con personalidad.
- `pnpm check:no-mocks` bloquea fallback data hardcoded en UI (ADR-0004 D-ANTI-MOCK-1).

### 6.3 Geo
- Coordenadas México: lat 14.5–32.7, lon −118.4 a −86.7. SRID 4326. Validar SIEMPRE.

### 6.4 Commits
- Conventional Commits: `feat(api): …`, `fix(ingest): …`, `docs(governance): …`, `chore(ci): …`.
- Trailer obligatorio para commits de agentes IA: `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` (Claude Code lo añade automáticamente; verificar `git log -1 --format=%B`).
- 1 commit = 1 funcionalidad verificada (CLAUDE.md §Regla 5).

### 6.5 Branches
- `main` es la rama oficial deployable.
- Features en `feat/<slug>` o `feat/<sprint>-<fecha>`.
- Multi-sesión simultánea sobre el mismo repo → **git worktree obligatorio** (CLAUDE.md global). Ver `~/.claude/skills/git-worktrees/`.

## 7. Política de decisión humano-vs-agente · ADRs

**Cualquier decisión arquitectónica significativa toma forma de ADR.** "Arquitectónica" significa: estructura del sistema, tecnología, contrato externo, política de datos, decisión irreversible o costosa.

- **Ubicación:** `docs/adr/NNNN-slug.md` (4 dígitos, secuencial, no reusar números).
- **Formato:** Nygard estándar (Title / Status / Context / Decision / Consequences). Para decisiones con múltiples opciones viables que requieren comparación formal: MADR (añade Decision Drivers + Considered Options con pros/contras).
- **Frontmatter obligatorio:**

```yaml
---
adr: 0001
title: Ollama desactivado por timeout Coolify
status: Accepted              # Proposed | Accepted | Deprecated | Superseded by ADR-NNNN
date: 2026-05-17
author: HUMAN ceo             # HUMAN <nombre> | AGENT <tool/model>
deciders: [ceo, linda]        # opcional
supersedes: null              # opcional ADR-NNNN
---
```

- **Inmutabilidad:** un ADR `Accepted` NO se edita. Si cambia la decisión, ADR nuevo + flip del viejo a `Superseded by ADR-NNNN`.
- **Cuándo un agente abre un ADR solo:** si la decisión es necesaria para no bloquearse pero NO es destructiva ni irreversible, el agente puede emitir un ADR con `status: Proposed` y `author: AGENT linda`, y el CEO lo aprueba (flip a `Accepted`) o lo rechaza.
- **Cuándo NO:** decisiones que comprometen estado persistente, dinero, datos del cliente, o credenciales requieren confirmación textual del CEO ANTES de actuar.

## 8. Definition of Done

Una tarea está hecha cuando:

1. **Backend modificado:** `make test` retorna exit 0. Si hay tests nuevos relevantes, están incluidos.
2. **Frontend modificado:** `pnpm type-check` exit 0, `pnpm lint` exit 0, `pnpm check:no-mocks` exit 0.
3. **DB modificada:** migración alembic creada vía `make migrate-create`, aplicada localmente, verificada con query SQL.
4. **Decisión arquitectónica tomada:** ADR escrito y commiteado en el mismo PR.
5. **Commit:** mensaje conventional + trailer Co-Authored-By si fue agente.
6. **Verificación end-to-end:** si hay UI nueva → screenshot con Playwright/chrome-devtools. Si hay endpoint nuevo → llamada con `curl` o test que devuelva 200 contra DB real. Cero datos mock (CLAUDE.md §Reglas de Calidad).
7. **Estado actualizado:** `.context/STATUS.md` con append corto si la sesión fue significativa.

## 9. Cierre de sesión

Cada sesión significativa (>1h o con decisiones arquitectónicas) cierra con:

1. **Handoff:** escribir `.context/HANDOFF-YYYY-MM-DD-<slug>.md` desde plantilla `.context/templates/SESSION_HANDOFF.md`.
2. **Diary opcional:** `~/.claude/sessions/diary/YYYY-MM-DD.md` si hubo aprendizajes patrones.
3. **Memory backup:** si modificaste `~/.claude/skills/learned/writing-review-list.md` u otra memory, ejecuta `bash ~/.claude/scripts/hooks/memory-backup.sh`.
4. **Set summary peer:** `mcp__claude-peers__set_summary` con 1-2 frases para que el siguiente peer entienda.

## 10. Perfiles de prueba (dirigentes reales)

| Nombre | dirigente_id | Plataformas activas | Notas |
|---|---|---|---|
| Alejandro Piña | 1 | X, IG, FB | Piloto MC CDMX. profile_id IG=16 (para scripts ad-hoc). |
| Rafael Solano | (ver DB) | IG personal, LinkedIn 170 | Sin presencia política digital. |
| Saymi (Sayonara) | 3 | FB, IG, TT, YT | Piloto principal post 2026-05-14. |
| Pepe Monroy | 57 | FB, IG, TT, YT | 25 posts + 110 comments full pipeline (2026-05-12). |
| Felipe Martínez | 60 | FB, TT, IG | En ingest activo (Marx/radar). |
| Misael (Fan VIP) | — | — | Mockup en `vip-overrides.ts`, NO en BD. ADR-0002 + ADR-0005. |

## 11. Anti-patrones (NO hacer)

- ❌ Inventar datos (precios, rendimientos, números electorales, follower counts). Si falta dato → reportar blocker, NO llenar con sintético.
- ❌ Fallback data hardcoded en UI con números. Usar `<Skeleton />` o estado vacío explícito (ADR-0004).
- ❌ Auto-generar AGENTS.md o inflarlo con prosa decorativa.
- ❌ Reimplementar parsing de HTML/JSON que ya hace una librería probada (instaloader, twscrape, etc. — ver tabla CLAUDE.md §Librerías OBLIGATORIAS).
- ❌ Acción Docker destructiva sin confirmación textual del CEO en la sesión actual.
- ❌ Editar un ADR `Accepted`. Escribir uno nuevo que lo reemplace.
- ❌ Mezclar archivos del bloque ESTABLE (este AGENTS.md, ADRs, DECISIONS.md, BOOTSTRAP, ARCHITECTURE) con cambios volátiles → rompe el KV-cache de prefijo de prompt (CLAUDE.md global §Cache Hygiene).
- ❌ Proponer cambios sin grep previo en `backend/` y `frontend/`. HARD RULE 2026-05-28: grep concepto antes, leer si existe, declarar 0 matches si no, NUNCA antes (`memory/feedback_buscar_codigo_antes_proponer.md`).
- ❌ Tipografías genéricas (Inter, Roboto, Arial) o gradientes púrpura sobre blanco (`~/.claude/rules/design-standards.md`).

## 12. Glosario rápido

| Sigla | Significado |
|---|---|
| MC | Movimiento Ciudadano |
| MAPA | `.context/MAPA-FUNCIONAL.md` — mapa funcional del producto |
| ER, FODA, IPD | Engagement Rate, FODA, Índice de Penetración Digital (modelos analíticos) |
| RADAR | Repo paralelo (`~/Projects/radar`) que entrega exports a CRECE vía adapters `ingest_radar_*.py` |
| Hugo / Marx | Peer `claude-peers` operando RADAR (mismo humano, mismo modelo) |
| Linda / Joy | Peers operando CRECE (electoral vs B2B) |
| VIP override | Mockup hardcoded para presentaciones (Misael 40/12 fans). NO BD. |
| Veda | Modo electoral previo a comicios con restricciones de comunicación |

## 13. Referencias cruzadas

- **Global (Anthropic Claude Code):** `~/.claude/CLAUDE.md` — instrucciones que aplican a TODO proyecto. Este AGENTS.md NO las duplica.
- **Proyecto Claude Code:** `CLAUDE.md` (raíz repo) — instrucciones Claude Code-específicas para CRECE. Debe quedarse thin y referenciar este AGENTS.md.
- **Gobernanza producto:** `.context/governance/README.md` — los 5 docs operativos.
- **Modelo de trabajo:** `.context/governance/MODELO-TRABAJO-AUDIT.md` — checklist 7 pasos pre-redacción + plantilla evidencia + protocolo auditor.
- **Auditor independiente:** `.context/governance/PROMPT-AUDITOR-GEMINI.md` — prompt canónico copiable.
- **Memoria persistente:** `~/.claude/projects/-Users-marxchavez-Projects-crece-v2/memory/MEMORY.md` — auto-cargada en SessionStart. Lee antes de planear.
- **Error notebook:** `~/.claude/skills/learned/writing-review-list.md` — patrones de error corregidos por el CEO.

---

**Última edición:** 2026-05-28 (Linda · Claude Opus 4.7 · sprint-implement)
**Próxima revisión:** cuando cambien stack, comandos, o políticas de decisión.
