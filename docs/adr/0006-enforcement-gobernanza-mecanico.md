---
adr: 0006
title: Enforcement de gobernanza mecánico · 3 capas (git/runtime/harness)
status: Proposed
date: 2026-05-30
author: AGENTE claude-opus-4-8
deciders: [ceo]
informed: [carlos-amador]
supersedes: null
superseded_by: null
legacy_id: null
legacy_path: null
related_adr: []
cross_audit: Gemini CLI (Puerta 2) · 2026-05-30
---

## Title
ADR-0006 · Enforcement de gobernanza mecánico — 3 capas (git / runtime / harness)

## Status
Proposed — perímetro aprobado por el CEO 2026-05-30; arranque gradual non-blocking.

## Context
CRECE tiene gobernanza masiva **en papel** (`CLAUDE.md`, `AGENTS.md` 15K,
`.context/DECISIONS.md` 158K, 5 ADRs, ~9 scripts `audit_*.py` manuales) pero casi
**cero enforcement mecánico**: un solo CI (`e2e-smoke.yml`), sin pre-commit, hooks
graphify solo locales en `.git/hooks/`. Lección del ecosistema (cfdi-platform
reset 2026-05-11, radar D-045): **las reglas duras viven en CI/hooks, no en
documentos**. Se porta el *mecanismo* probado de cfdi/radar; las *reglas* son las
de CRECE, derivadas de sus propios postmortems.

## Decision
Enforcement en **3 capas**, porque los 2 peores incidentes de CRECE no ocurrieron
en git sino en runtime/harness:

| Capa | Pieza | Regla(s) |
|---|---|---|
| **git** | `backend/scripts/governance_check.py` + `.githooks/pre-commit` + `.github/workflows/governance-gate.yml` | (c) secret-scan + PII-paths; (d) anti-mock adelantado de CI; (warn) destructivo en archivos |
| **runtime** | `backend/scripts/_guard_resources.py` integrado en `post_ingest_enrich.py` | (b) RAM-guard + check unattended + circuit-breaker; (e) SLO cobertura ingest |
| **harness** | `scripts/safe-ops-guard.sh` vía hook PreToolUse(Bash) en `.claude/settings.json` | (a) bloqueo de comandos destructivos Docker/BD |

Instalación: `bash scripts/install-hooks.sh` — activa `core.hooksPath .githooks` Y
registra el hook de harness. NB: `.claude/` está en `.gitignore` → el hook de
harness **no viaja en git** (sí el script guard); `install-hooks.sh` lo reinstala
idempotente en cada máquina. Verificado: el hook se activó en esta misma sesión
(bloqueó comandos destructivos reales, incluidos mensajes de commit que los citan).

### Qué se DESCARTA del paquete cfdi (no se fuerza)
- **Sign-off RFC 2119** (`signoff_rfc2119.py`, `signoff-gate.yml`, `evidence.yaml`):
  depende de `sops/*.sop.md` que CRECE **no tiene** → sería no-op permanente.
  Forzarlo = gobernanza de cartón. **No portado.**

### Decisiones de adaptación
1. **graphify versionado:** copiar `post-commit`/`post-checkout` a `.githooks/`
   (antes solo locales). `core.hooksPath` los preservaría apagando los de
   `.git/hooks/`; versionarlos los salva Y los hace auditables. (Aprobado CEO, R1.)
2. **PII inline NO se escanea:** CRECE maneja datos políticos públicos (nombres de
   dirigentes, IDs de campaña). Regex de CURP/RFC/nombres detonaría sin parar. El
   scan se limita a secretos `.env` + paths de dumps. **(Cambio por auditoría Gemini.)**
3. **RAM medida como `available`, no `free`:** en macOS Unified Memory `free`
   siempre marca bajo y abortaría jobs legítimos. **(Cambio por auditoría Gemini.)**
4. **AUTONOMY-RULES mínimo y enlazado** desde `AGENTS.md`, sin duplicar `CLAUDE.md`.

## Cross-audit (Gemini CLI · Puerta 2 · 2026-05-30)
Hallazgos integrados:
- **PII falsos positivos** → no se escanea PII inline (#2 arriba).
- **RAM en macOS** → `available` en vez de `free` (#3).
- **Vector de pérdida de BD** no cubierto por "solo Docker" → se amplió la regla (a)
  y el scan a `DROP TABLE`/`TRUNCATE`/`alembic downgrade base`.
- **Circuit breaker de costos** en jobs NLP unattended → `iteration_guard()`.
- **Capa harness frágil** (solo cubre Claude Code, no terminal/otros agentes) →
  reconocido como defensa-en-profundidad, no infalible; es la defensa primaria
  contra el modo de falla real (el agente ejecutando el comando).
- **SLO delta vs bootstrap** → el SLO mide cobertura TOTAL del dirigente, no del
  batch; un delta chico no detona falso negativo.

Hallazgos **NO** adoptados ahora (anotados como deuda, no forzados):
- Fuga de PII en logs de Celery/stdout en runtime → fuera del alcance de este sprint.
- Mover AUTONOMY-RULES a `GEMINI.md` en vez de archivo propio → se mantuvo archivo
  propio porque la tarea/patrón cfdi-radar lo especifica; se mitiga el "cartón"
  manteniéndolo mínimo y enlazado.

## Non-blocking primero (con matiz del cross-audit)
El CEO aprobó "warn 1 sprint → blocking". Gemini advirtió **warn-blindness** y deuda
acumulada al encender blocking. **Híbrido adoptado:** los guards de **runtime**
(RAM/SLO) arrancan en `CRECE_GUARD_MODE=warn`; el gate **git de secretos/PII**
arranca **bloqueante desde día 1** (scope reducido, alta confianza: un secreto
commiteado es irreversible). Destructivo-en-archivos = warn. `git commit --no-verify`
siempre disponible. **Pendiente decisión CEO:** ¿confirmar este híbrido o forzar todo
a warn el primer sprint?

## Consequences
**+** Reglas duras dejan de depender de la buena voluntad de la sesión.
**+** graphify deja de ser invisible (versionado).
**+** Defensa en profundidad contra el modo de falla Docker.raw.
**−** El hook de harness solo protege a Claude Code (no terminal manual/otros agentes).
**−** Requiere `bash scripts/install-hooks.sh` por máquina (una vez).
**−** `psutil` recomendado para el RAM-guard (degrada a skip-con-warning si falta).

## Decisiones tomadas autónomamente por el agente (transparencia)
- Ampliar regla (a) de "Docker" a destructivo-BD (por hallazgo Gemini).
- No escanear PII inline (por hallazgo Gemini) — diverge del `governance_check` de radar.
- Proponer el híbrido non-blocking en vez de aplicar warn-total — **se deja a decisión
  del CEO**, no se impuso.
- SLO implementado sobre `post_ingest_enrich.py` (orquestador post-ingest natural) y
  defensivo ante ausencia de `psycopg2`/`DATABASE_URL_SYNC`.
