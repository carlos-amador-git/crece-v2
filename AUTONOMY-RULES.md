# AUTONOMY-RULES.md — Modo autónomo de agentes en CRECE v2

> Aprobado por Marx Chávez 2026-05-30 (perímetro · ver `docs/adr/0006`).
> Patrón portado de `MarxCha/radar` (aprobado 2026-05-15) y `cfdi-platform`,
> adaptado al contexto de CRECE. **Enlazado desde `AGENTS.md`.**
>
> Estas reglas definen el perímetro dentro del cual un agente (CC/Gemini) opera
> **sin pedir luz verde intermedia**, y dónde DEBE detenerse. NO duplican
> `CLAUDE.md` ni `AGENTS.md` — los complementan acotando la autonomía operativa.
> Donde una regla de `CLAUDE.md` sea más estricta, **prevalece la más estricta**.

## Filosofía
Autonomía **con guardrails operativos**, no total. El punto de control natural es
el cierre de cada tarea/día: el CEO revisa el reporte y aprueba o pide rollback.
Las reglas mecánicamente verificables están en **3 capas** (git / runtime / harness)
para que el cumplimiento no dependa de la buena voluntad de la sesión.

## Perímetro autorizado (el agente procede sin pedir luz verde)
### Código y arquitectura
- ✅ Implementar tareas planificadas en `.context/PLAN-*.md` aprobados.
- ✅ Crear/modificar/eliminar archivos en `backend/`, `frontend/`, `scripts/`,
  `tests/`, `docs/`, `docs/adr/`.
- ✅ Crear migraciones Alembic nuevas.
- ✅ Crear ADRs nuevos (`docs/adr/NNNN-*.md`) en decisiones estructurales.
- ✅ Escribir handoffs en `.context/` y memoria de ejecución (append-only).

### Operación
- ✅ Commits locales con mensajes convencionales (`feat:`/`fix:`/`chore:`/`docs:`).
- ✅ `docker compose restart`, levantar/bajar servicios (SIN `-v`).
- ✅ Ejecutar tests, aplicar migraciones en BD de desarrollo (`:5438`).
- ✅ Ejecutar scrapers/NLP **attended** contra perfiles de prueba.

### Datos (desarrollo)
- ✅ INSERT/UPDATE en tablas de desarrollo con < 100 filas afectadas.
- ✅ Seed/cleanup que ya estén en migraciones o scripts aprobados.

## Perímetro NO autorizado (el agente DEBE pedir OK escrito del CEO)
### Operación destructiva — *enforced por capa harness (`scripts/safe-ops-guard.sh`)*
- ❌ `rm` de `Docker.raw`, `docker compose down -v`, `docker volume rm`,
  `docker system prune --volumes/-a` (regla universal anti-destructive-Docker;
  postmortem `rm Docker.raw` 2026-04-13).
- ❌ `DROP TABLE`, `TRUNCATE`, `alembic downgrade base`, `make reset-db`,
  `DELETE` de > 100 filas en tablas con datos productivos.
- ❌ Reset de BD del piloto.

### Jobs pesados — *enforced por capa runtime (`backend/scripts/_guard_resources.py`)*
- ❌ Lanzar scripts NLP/ingest **unattended** sin `--allow-unattended` explícito,
  o con RAM disponible < 3500 MB (Mac Mini M4 16 GB). Postmortem crash RAM 2026-05-27.

### Secretos y datos sensibles — *enforced por capa git (`governance_check.py`)*
- ❌ Commitear valores reales de `.env`, tokens, o paths con PII/dumps
  (`*.dump`, `exports/`, `captures/`). Mover secretos a `.env` (leer con `os.getenv`).
- ❌ Rotar credenciales/JWT/passwords (ver memoria: NO rotar `.env.scraping-keys`).

### Cambios estructurales / externos
- ❌ `git push` a cualquier branch remoto. **Requiere OK escrito explícito del CEO
  en la sesión actual.** NO se infiere de instrucciones laterales ("push tras tu OK").
- ❌ Migrar stack, onboardear tenants productivos, llamadas de pago (Apify/PAC/etc.).
- ❌ Comunicación con cliente final (MC CDMX) — pasa por el CEO.

## Reglas de auto-corte (el agente DEBE parar y pedir luz verde si…)
- 3+ tests consecutivos fallan.
- Detecta posible pérdida de datos o exposición de secretos.
- Encuentra una decisión arquitectónica mayor no contemplada en ADRs/planes.
- Se sorprende afirmando "el motor/plataforma no hace X" sin haber verificado un
  caso que SÍ funcionó (regla del error-notebook: buscar el contraejemplo primero).

## Resolución de ambigüedades
Cuando una instrucción puntual del CEO en chat **luce relajar** una regla categórica
de este documento, de `CLAUDE.md` o de un ADR vigente, **prevalece la regla
categórica**. El agente la trata como sugerencia pendiente de clarificación y
pregunta en chat. NO interpreta a favor de más autonomía.

## Reporte de cierre obligatorio
Cada cierre de tarea/día reporta: tareas hechas · archivos cambiados · bugs ·
commits locales (hash + mensaje) · blockers nuevos · ADRs nuevos · **decisiones
tomadas autónomamente y por qué** · resultado de los gates (git/runtime/harness).

## Modo de arranque gradual (non-blocking primero)
Los guards de **runtime** arrancan en `CRECE_GUARD_MODE=warn` el primer sprint y se
promueven a `block`. El gate **git** de secretos/PII arranca **bloqueante desde día 1**
(un secreto commiteado es irreversible; bajo riesgo de falso positivo por diseño).
El destructivo en archivos es warn. `git commit --no-verify` siempre disponible
(queda en reflog). Ver `docs/adr/0006` §non-blocking.

## Instalación de los gates
```bash
bash scripts/install-hooks.sh   # core.hooksPath .githooks (pre-commit + graphify)
```
El hook de harness (`safe-ops-guard.sh`) se registra en `.claude/settings.json`.
⚠️ `.claude/` está en `.gitignore` (config local por máquina) → el hook **NO viaja
en git**; `install-hooks.sh` lo (re)instala idempotente. El script guard sí está
versionado. Correr `install-hooks.sh` en cada máquina activa las 3 capas.
