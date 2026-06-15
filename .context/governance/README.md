# Gobernanza CRECE v2 — manual de manuales

**Propósito:** punto único de entrada al conjunto de 5 docs que rigen cómo opera CRECE como producto y como equipo. Antes de proponer cambios, decisiones o features, consultar el doc correspondiente. Si la respuesta no está, agregarla antes de implementar.

## Los 5 docs (orden de consulta)

**Convención de status:**
- ✅ **Cerrado:** redactado + audit Gemini independiente ejecutado + hallazgos aplicados. Sin deuda de gobernanza.
- 🟡 **En curso:** redactado pero audit pendiente o hallazgos no aplicados todavía.
- 📝 **Esqueleto:** estructura sin contenido sustantivo.
- ⚠️ junto a status = pendientes específicos del CEO (input externo, no deuda del agente).

| # | Doc | Cubre | Status |
|---|---|---|---|
| 0 | `MODELO-TRABAJO-AUDIT.md` | **Cómo se documenta y se audita** (meta-doc) | ✅ cerrado 2026-05-28 |
| 1 | `../PIPELINE-RADAR-CRECE.md` | Flujo de datos radar→crece, engines, adapters, gaps | ✅ cerrado 2026-05-28 |
| 2 | `../MAPA-FUNCIONAL.md` | Cada función de la app (qué hace, qué lee, qué muestra) | ✅ §1-10 cerradas (audit Gemini · ajustes aplicados 2026-05-28) |
| 3 | `ORGANIZACION.md` | Roles, peers, handoffs, escalation | ✅ cerrado (audit Gemini · ajustes aplicados 2026-05-28) |
| 4 | `REGLAS.md` | Código de conducta, LFPDPPP, ADRs, error notebook | ✅ cerrado (audit Gemini · ajustes aplicados 2026-05-28) |
| 5 | `PRODUCTO.md` | Misión, visión, roadmap, clientes, posicionamiento | ✅ cerrado ⚠️ pendiente CEO: misión/visión textual + pricing + KPIs (ver `PRODUCTO.md` §10) |

### Histórico de auditorías Gemini

Cada sección/doc fue auditado independientemente por Gemini con prompt canónico (`PROMPT-AUDITOR-GEMINI.md`). Veredictos iniciales y reportes detallados en `.context/audits/2026-05-28-*.md`. Los hallazgos sustantivos están aplicados; las celdas de status arriba reflejan el estado **post-ajustes**, no el veredicto inicial.

| Doc / sección | Veredicto inicial | Ajustes aplicados | Reporte |
|---|---|---|---|
| MAPA §1 Aceptación + Fans | ⚠️ Pasa con ajustes | ✅ | `mapa-funcional-seccion-1.md` |
| MAPA §2 Diagnóstico Tier 1 | ✅ Pasa | (sesgo menor B08 NLP) | `mapa-funcional-seccion-2.md` |
| MAPA §3 FODA | ⚠️ Pasa con ajustes (3) | ✅ | `mapa-funcional-seccion-3.md` |
| MAPA §4 Planes IA | ⚠️ Pasa con ajustes (5 reales, 1 falso positivo) | ✅ | `mapa-funcional-seccion-4.md` |
| MAPA §5 Clima Político | ✅ Pasa | (sesgo menor EXPRESIDENTES list) | `mapa-funcional-seccion-5.md` |
| MAPA §6 Recom/Eval/Reels | ⚠️ Pasa con ajustes (4) | ✅ | `mapa-funcional-seccion-6.md` |
| MAPA §7 Overview+Dirigentes | ⚠️ Pasa con ajustes (4) | ✅ | `mapa-funcional-seccion-7.md` |
| MAPA §8 Diagnóstico Tier 2 | ⚠️ Pasa con ajustes (5) | ✅ | `mapa-funcional-seccion-8.md` |
| MAPA §9 Configuración + Sistema | ⚠️ Pasa con ajustes (4 + cross-doc §10) | ✅ | `mapa-funcional-seccion-9.md` |
| MAPA §10 Admin | ⚠️ Pasa con ajustes (3) | ✅ | `mapa-funcional-seccion-10.md` |
| ORGANIZACION.md | ⚠️ Pasa con ajustes (4) | ✅ | `organizacion.md` |
| REGLAS.md | ⚠️ Pasa con ajustes (4) | ✅ | `reglas.md` |
| PRODUCTO.md | ✅ Aprobado con observaciones (2 reales, 2 falsos positivos) | ✅ | `producto.md` |
| PIPELINE-RADAR-side (Marx) | ✅ Pasa | (sesgo menor pepe_hybrid 82%) | `pipeline-radar-side.md` |

**Totales:** 14 secciones/docs auditados · 0 inventos del redactor detectados · 4 falsos positivos del auditor declarados y descartados · 100% hallazgos sustantivos verificados antes de aplicar (sub-regla `MODELO-TRABAJO-AUDIT.md` §5.4).

## Reglas de uso

1. **Para una pregunta o duda:** consulta primero el doc relevante. Si no responde, NO inventes — investiga primero (grep, queries DB, lecturas) y agrega la respuesta al doc.
2. **Para una propuesta de feature/cambio:** consulta el `MAPA-FUNCIONAL.md` para ver si ya existe. Si existe → ajustar. Si no → agregar sección antes del primer commit.
3. **Cada decisión que se toma debe quedar registrada** en el doc correspondiente, NO en handoffs sueltos.
4. **Auditorías periódicas:** Gemini revisa cada sección según `MODELO-TRABAJO-AUDIT.md §protocolo`. Reporte queda en `.context/audits/<fecha>-<doc>-<seccion>.md`.

## Para futuras apps MD Consultoría

Esta estructura debe replicarse en el bootstrap de cada proyecto. Carpeta `.context/governance/` con los 5 docs (aunque inicien vacíos con esqueleto) desde día 1. Evita la deuda organizacional que CRECE pagó hasta 2026-05-28.

## Vinculación con otros artefactos

- `RUNBOOK-STOP-START-LOCAL-MAC.md` → cómo detener/relevantar el stack local en el Mac Mini sin pelear con el resucitador (`crece-auto-resume` LaunchAgent). `docker stop` solo NO es limpio. (2026-06-08)
- `.context/HANDOFF-*.md` → handoffs operativos puntuales (no reemplazan los 5 docs; sirven para cierre entre sesiones).
- `.context/templates/SESSION_HANDOFF.md` → plantilla formal para handoffs (fusiona disciplina SRE + toma-notas Anthropic + memoria 3 capas).
- `docs/adr/` → ADRs canónicos vigentes en formato Nygard+MADR (5 migrados 2026-05-28; resto en `DECISIONS.md` formato histórico).
- `AGENTS.md` (raíz repo) → contrato operativo único para agentes IA (fuente de verdad agente).
- `memory/` (auto-memory CC) → lecciones específicas + feedbacks del CEO. Cargada por SessionStart hook.
- `CLAUDE.md` (root del proyecto) → instrucciones específicas Claude Code para este proyecto (thin, referencia AGENTS.md).
