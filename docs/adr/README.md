# Architecture Decision Records · CRECE v2

Decisiones arquitectónicas significativas tomadas durante el desarrollo de CRECE v2, registradas en formato [Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) con extensiones [MADR](https://adr.github.io/madr/) en el frontmatter.

## ¿Cuándo se escribe un ADR?

Una decisión califica para ADR cuando es **arquitectónicamente significativa**: cambia la estructura del sistema, tecnología, contrato externo, política de datos, o es irreversible/costosa. Decisiones menores (formato de un componente, naming local) NO van aquí.

Ver `AGENTS.md` §7 raíz repo para el contrato completo.

## Reglas de mantenimiento

1. **Inmutabilidad post-acceptance.** Un ADR con status `Accepted` NO se edita. Si la decisión cambia → ADR nuevo + flip del viejo a `Superseded by ADR-NNNN`.
2. **Numeración secuencial** sin reusar. 4 dígitos zero-padded (`0001`, `0002`, …).
3. **Frontmatter obligatorio** con `adr`, `title`, `status`, `date`, `author`, `deciders`, `supersedes`, `superseded_by`.
4. **Autor:** `HUMAN <nombre>` para decisión del CEO; `AGENT <tool/model>` para propuesta de agente IA.
5. **Status válidos:** `Proposed`, `Accepted`, `Deprecated`, `Superseded by ADR-NNNN`.

## Índice

| # | Título | Status | Fecha | Autor |
|---|---|---|---|---|
| [0001](0001-ollama-off-plan-ia-pausado.md) | Ollama OFF · Plan IA pausado · migración a Claude Code + Gemini CLI | Accepted | 2026-05-15 | HUMAN ceo |
| [0002](0002-vip-overrides-mockup-frontend.md) | VIP overrides como mockup frontend-only (BD jamás se toca) | Accepted | 2026-05-19 | HUMAN ceo |
| [0003](0003-anti-fallback-data-ui.md) | Anti-fallback data en UI · guardrail automatizado | Accepted | 2026-05-11 | HUMAN ceo |
| [0004](0004-fans-perfiles-sidebar-invariante.md) | Fans y Perfiles sidebar invariante · NO eliminar | Accepted | 2026-05-19 | HUMAN ceo |
| [0005](0005-misael-vip-override-250-12.md) | Misael VIP override 250/12 · supersedes ADR-NNNN inicial 40/12 | Superseded by ADR-0007 | 2026-05-20 | HUMAN ceo |
| [0006](0006-enforcement-gobernanza-mecanico.md) | Enforcement gobernanza mecánico (git/runtime/harness) | Accepted | 2026-05-30 | HUMAN ceo |
| [0007](0007-misael-vip-override-400-12.md) | Misael VIP override 400/12 · supersedes ADR-0005 | Accepted | 2026-06-04 | HUMAN ceo |
| [0008](0008-nlp-routing-token-eficiente.md) | NLP routing token-eficiente · textual local + político LLM batcheado | Proposed | 2026-06-04 | AGENT linda |
| [0009](0009-actores-politicos-org-partido-rol.md) | Actores políticos — org ≠ partido ≠ rol_politico (tres ejes) | Accepted | 2026-07-16 | AGENT linda |

## Migración legacy

Esta carpeta migra ADRs canónicos vigentes desde `.context/DECISIONS.md` (formato narrativo histórico). Los ADRs migrados son los **vigentes y arquitectónicos** — `DECISIONS.md` retiene los 73 ADRs históricos completos (no todos arquitectónicos · ver `REGLAS.md` §6 nota cobertura).

## Cross-references

- `~/.claude/CLAUDE.md` global — convenciones meta-organizacionales
- `AGENTS.md` raíz — contrato operativo de agente IA
- `.context/governance/REGLAS.md` §6 — catálogo de los 35 ADRs representativos
- `.context/DECISIONS.md` — registro histórico narrativo completo
