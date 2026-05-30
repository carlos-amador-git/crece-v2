# PLAN (1 pág) — Portar enforcement de gobernanza a CRECE

**Fecha:** 2026-05-30 · **Estado:** PROPUESTA — requiere aprobación de perímetro del CEO antes de ejecutar.
**Reframe acordado:** porto el *mecanismo* de cfdi-platform; las *reglas duras* son las de CRECE (sus propios postmortems). No copio el Sign-off RFC 2119.

## Hallazgo de criterio (lo más importante)
El paquete cfdi es 100% **capa-git** (pre-commit + CI girando alrededor de SOPs RFC 2119).
Pero los 2 peores incidentes de CRECE **no ocurrieron en git**: el Docker.raw wipe y el crash RAM
pasaron en la **capa harness/runtime** (el agente ejecutando comandos), donde un git-hook no llega.
→ Las 5 reglas operan en **3 capas**; portar solo git no previene Docker.raw ni el crash RAM.

## Qué porto / qué descarto del paquete cfdi
| Pieza cfdi | Decisión | Razón |
|---|---|---|
| `install-hooks.sh` (core.hooksPath) | **Porto, adaptado** | Hace que el hook viaje con el repo. ⚠️ pisa los hooks graphify actuales (ver riesgo R1). |
| `pre-commit` (shell gate) | **Porto el esqueleto** | Reutilizo la estructura; cambio el contenido (no SOP). |
| `signoff_rfc2119.py` + `signoff-gate.yml` + `evidence.yaml` | **DESCARTO** | Dependen de `sops/*.sop.md` que CRECE no tiene. El propio pre-commit cfdi hace `exit 0` sin SOPs. Forzarlo = gobernanza de cartón. |
| `AUTONOMY-RULES.md` | **Porto, reescrito a CRECE** | Perímetro autorizado/no-autorizado + auto-corte + resolución de ambigüedades + reporte de cierre. No depende de SOPs. |
| `gen_handoff_index.py` | **Porto, adaptado** | CRECE tiene ~decenas de `.context/HANDOFF-*.md` sin índice. Adapto rutas. |
| ADR template `D-XXX` | **Uso el de CRECE** | `docs/adr/` ya tiene formato propio (frontmatter YAML, 0001-0005). Próximo = **0006**. |

## Las 5 reglas duras — mecanismo, capa y anti-falsos-positivos
| # | Regla (fijada por CEO) | Capa | Mecanismo | Cómo evita falsos positivos |
|---|---|---|---|---|
| a | Hook Docker destructivo | **harness** (PreToolUse Bash en `~/.claude/settings.json`) + git (escaneo de comandos destructivos en archivos staged) | git-hook NO atrapa al agente ejecutando en shell → el atajo real es el hook de harness | Lista cerrada de patrones (`down -v`, `volume rm`, `rm *Docker.raw`, `system prune --volumes`); bypass `--no-verify` registrado en reflog |
| b | Guard RAM / jobs pesados unattended | **runtime** (precondición dentro de los scripts NLP/ingest) | `scripts/_guard_resources.py`: aborta si RAM libre < umbral o modo unattended sin flag explícito | Umbral configurable; flag `--allow-unattended` para correr a propósito; solo aplica a scripts marcados |
| c | Secret-scan + PII-paths | **git** (pre-commit + CI) | Replico patrón de RADAR (`~/Projects/radar/.githooks`); bloquea `.env*`, claves, y paths PII (`*.dump`, watched_*) | Allowlist `.env.example`; marcador `# allow-secret: razón`; escaneo por patrón, no por nombre genérico |
| d | Anti-mock adelantado a pre-commit | **git** (ya en CI `e2e-smoke.yml:107`) | pre-commit llama `npm run check:no-mocks` cuando el stage toca `frontend/` | Solo corre si hay cambios en frontend; reutiliza el script ya validado (cero lógica nueva) |
| e | SLO de ingest | **runtime** (post-ingest) | El script de ingest reporta cobertura y aborta/alerta si < umbral (lección postmortem S-8.1) | **VERIFICADO: no existe gate hoy** (solo `audit_data_quality.py` manual). Umbral acordado con CEO, no inventado; alerta antes de bloquear |

## Qué VERIFIQUÉ vs qué INFERÍ
**Verificado (con evidencia):**
- Anti-mock **sí está en CI** (`e2e-smoke.yml:107` → `npm run check:no-mocks`). *(Corregí mi afirmación previa errónea de "posible papel".)*
- Único CI actual = `e2e-smoke.yml`. Sin pre-commit. Hooks actuales = graphify (post-commit/post-checkout).
- No existe gate de SLO/cobertura de ingest (grep vacío en scripts ingest/enrich).
- Sign-off cfdi depende de `sops/*.sop.md`; CRECE no tiene esa carpeta.
- ADRs CRECE: formato YAML propio, próximo 0006.

**Inferido (a confirmar en implementación):**
- El patrón secret-scan de RADAR vive en `~/Projects/radar/.githooks` (dir existe; leeré el contenido exacto en fase 1).
- Umbral de RAM y de cobertura de ingest: propondré valores; **requieren tu número**.

## Riesgos
- **R1 (alto):** activar `core.hooksPath .githooks` **desactiva los hooks graphify** (auto-rebuild del grafo). Mitigación: incorporar la lógica graphify dentro de `.githooks/post-commit` y `post-checkout` versionados, o no migrar a core.hooksPath y usar `.git/hooks/pre-commit` directo (no viaja con el repo). **Decisión a tomar contigo.**
- **R2 (alto):** pre-commit mal calibrado bloquea todo el flujo. Mitigación: todo gate nuevo arranca **non-blocking (warn)** 1 sprint, luego se promueve a blocking; `--no-verify` siempre disponible.
- **R3:** regla (a) y (b) en harness viven en `~/.claude/settings.json` (global, no en el repo) → no viajan con GH. Documentar en AUTONOMY-RULES que son precondición de máquina.

## Ejecución (DESPUÉS de aprobar perímetro)
1. Leer `~/Projects/radar/.githooks` (patrón secret-scan real).
2. **Gemini CLI Puerta 2** — cross-audit del plan de adaptación (qué porta/descarta/riesgos). Integrar.
3. Implementar las 5 reglas en sus 3 capas (non-blocking primero).
4. `AUTONOMY-RULES.md` de CRECE + `gen_handoff_index.py` adaptado.
5. ADR **0006** citando la auditoría Gemini.
6. Commits locales convencionales. **Sin push** (espera tu OK escrito).

## Lo que necesito que apruebes
1. **El set de 5 reglas + las 3 capas** (¿correcto, o ajustas?).
2. **R1:** ¿incorporo graphify dentro de `.githooks/` versionados (recomendado), o evito core.hooksPath?
3. **Umbrales:** RAM libre mínima para jobs pesados (¿MB?) y cobertura mínima de ingest (¿%?).
4. **Estrategia non-blocking-primero (R2)** — ¿de acuerdo?
