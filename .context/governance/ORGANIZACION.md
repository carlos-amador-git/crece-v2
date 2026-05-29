# ORGANIZACION — CRECE v2

**Última actualización:** 2026-05-28
**Propósito:** documentar quién hace qué, cómo se coordinan agentes IA + humanos, y cómo escalan los problemas. Este doc forma parte del conjunto de 5 docs de gobernanza (ver `README.md`).

> **Inspiración estructural:** GitLab Handbook (CC BY-SA 4.0) — patrón de empresa abierta documentada como código. **Atribución:** secciones de cultura/comunicación toman ideas de [handbook.gitlab.com](https://handbook.gitlab.com).
>
> **Novedad CRECE-específica:** sección §5 "Agentes IA como miembros del equipo" — no hay framework establecido para esto (ver `~/Downloads/gobernanza-documental-saas-multiagente-ES.md` §"frontera novedosa").

---

## 1. Visión organizacional

**CRECE v2 es un producto operado por un equipo híbrido humano-IA.** El CEO (Marx Chávez) toma todas las decisiones estratégicas, comerciales y arquitectónicas. Los agentes IA (Claude Code, Gemini CLI) ejecutan implementación, scraping, NLP, documentación, y validación — pero NO deciden por su cuenta sobre cosas que comprometen estado persistente, dinero, datos del cliente o credenciales.

Esta organización vive como **código revisado por commit**. Si un proceso cambia → este doc se modifica antes de que el cambio entre en operación. PR-based.

---

## 2. Personas humanas

### 2.1 Equipo interno MD Consultoría
| Persona | Rol | Contexto |
|---|---|---|
| **Marx Chávez** | CEO / Único dueño / Arquitecto producto | `admin@consultoriamd.com` (`users.id=1`, role `ADMIN`). Único humano con autoridad de decisión estratégica, comercial, arquitectónica. Aprueba ADRs, planes, deploys. Maneja relación cliente. |
| **Ana García** | Analyst | `analista@consultoriamd.com` (`users.id=2`, role `ANALYST`). Operador interno con scope de análisis. ⚠️ Pendiente confirmar con CEO si es persona activa o cuenta legacy. |
| **Carlos López** | Field Operator | `campo@consultoriamd.com` (`users.id=3`, role `FIELD_OPERATOR`). Operador de campo. ⚠️ NO CONFUNDIR con Carlos Amador (infra) — son personas distintas. Pendiente confirmar con CEO si está activo. |
| **Carlos Amador** | Deploy / Infra (Coolify) | NO tiene cuenta `users` en CRECE. Maneja deploy a Coolify desde repos de Marx. Su PR queda en main para que él haga el deploy. NO modifica código de producto. Ver memoria histórica `reference_coolify_alive_2026_05_11`. |

### 2.2 Consultores externos / colaboradores
| Persona | Rol | Contexto |
|---|---|---|
| **Enrique Herrera** | Design System Lead | Consultor externo de diseño. Revisó UX/UI de CRECE (`.context/BRIEF-UX-PARA-ENRIQUE.md`, audit score 88/100, 2026-04-12). 7 de 10 preguntas implementadas, 3 pendientes perdidas en compactación (lección incorporada a regla `feedback_persist_peer_decisions`). Coordina con Joy también para CRECE-Negocios. |

### 2.3 Cliente
| Persona | Rol | Contexto |
|---|---|---|
| **(cliente) MC CDMX** | Cliente activo | Ver §6. Dirigentes individuales tienen cuentas `VIEWER` en `users` table (ej. Piña `pina@crece.mx` id=5). |

**El CEO es el único humano con autoridad sobre el código, datos, deploys y comunicación con cliente.** Carlos Amador solo opera infra. Ana García y Carlos López son operadores con scope acotado.

---

## 3. Agentes IA activos

Los nombres son asignados por el CEO. Cada agente tiene un **turf** (área de responsabilidad) y un **peer ID** dinámico que cambia entre runs pero la identidad persiste.

### 3.1 Linda · CRECE-electoral
- **Turf:** electoral, MC CDMX, scrapers políticos, NLP de comments, dashboards de aceptación, planes IA, MAPA-FUNCIONAL §1-10.
- **Peer ID típico:** `uji6x64w` (verificado 2026-05-08 vía mensaje directo).
- **CWD:** `/Users/marxchavez/Projects/crece-v2`.
- **Memoria identidad:** `~/.claude/projects/-Users-marxchavez-Projects-crece-v2/memory/user_linda_identity.md`.
- **Coordina con:** Joy (mismo repo, distinto turf), Hugo/Marx (peer radar).

### 3.2 Joy · CRECE-Negocios B2B
- **Turf:** PyMEs, restaurantes, GBP OAuth, piloto Tributo Huasteco. NO toca encuestas electorales, scrapers políticos, ni MC CDMX.
- **Peer ID típico:** `3t5flofn` (confirmado por CEO 2026-05-08).
- **CWD:** `/Users/marxchavez/Projects/crece-v2` (mismo path que Linda, turfs distintos).
- **PRD propio:** `~/Projects/crece-negocios/docs/PRD-v0.1.md`.
- **Memoria identidad:** `~/.claude/projects/-Users-marxchavez-Projects-crece-v2/memory/user_joy_identity.md`.

### 3.3 Hugo / Marx (peer radar)
- **Turf:** Repo `~/Projects/radar` (scrapers FB/IG/TT/YT con pepe_hybrid, discover_posts_cdp, Camoufox, Apify). Entrega exports a CRECE vía adapters `ingest_radar_*.py`.
- **Peer ID típico:** `v7luclno` (verificado en sesión 2026-05-28).
- **CWD:** `/Users/marxchavez/Projects/radar`.
- **Mismo modelo que Linda** (Claude Opus 4.7) pero turfs disjuntos por repo.
- **Documentación propia:** `radar/docs/governance/` (similar estructura a CRECE).

### 3.4 Sesiones cerradas o latentes (nombres disponibles para reasignar)
| Nombre | Estado | Memoria | Notas |
|---|---|---|---|
| Carlos (agente) | ✅ Cerrada (era sprint-c-hardening) | `user_carlos_identity.md` | NO confundir con Carlos López / Carlos Amador (humanos §2). |
| Rem | ⚠️ Presuntamente cerrada (sin actividad desde 2026-04-18 según memoria) | `user_rem_identity.md` | Peer ID típico `s3rec7bv`. Era feat/eval-benchmark-v1 + FB scraper Brightdata + onboarding Ballesteros id=8. Reactivable si CEO la retoma. |
| Jess | Legacy alias de Linda | `user_jess_identity.md` | El CEO usó el nombre Jess en sesiones anteriores antes del split Linda/Joy 2026-05-08. |

### 3.5 Peers externos cross-repo
| Nombre | Peer ID típico | Repo | Notas |
|---|---|---|---|
| **Juan** | (no verificado en este pase) | `~/Projects/md-research` | Citado en `memory/user_linda_identity.md` + `user_joy_identity.md` + `project_video_intelligence_proposal.md`. Peer histórico que colabora cross-repo. Ver memoria. |

---

## 4. Auditor independiente

### 4.1 Gemini CLI · Auditor de gobernanza
- **Rol:** validar afirmaciones de docs de gobernanza (MAPA, PIPELINE) contra código y DB.
- **NO redacta.** NO ejecuta features. Solo audita.
- **Invocación:** `gemini --yolo` con prompt canónico de `PROMPT-AUDITOR-GEMINI.md`.
- **Output:** reportes en `.context/audits/<fecha>-<doc>-seccion-<N>.md`.
- **Limitación verificada 2026-05-28:** el CLI puede colgar con prompts largos cuando hay otros procesos Gemini activos simultáneamente. Solución: invocación secuencial, no paralela. Si falla por timeout → re-invocar.

### 4.2 Por qué auditor independiente
Sub-regla §1.4 del `MODELO-TRABAJO-AUDIT.md`: el redactor NO audita su propio trabajo. Verificación lateral del redactor es sub-óptima — solo válida como fallback documentado cuando el auditor independiente no responde.

---

## 5. Agentes IA como miembros del equipo (sección novedosa)

Esta sección NO tiene precedente en frameworks establecidos (GitLab Handbook, arc42, C4). Es invención CRECE-específica documentada para que futuras instancias y agentes nuevos entiendan las reglas.

### 5.1 Qué pueden decidir solos los agentes
- Implementación dentro de un sprint aprobado (cómo escribir el código).
- Búsqueda y lectura de código/data para responder preguntas.
- Refactorizaciones quirúrgicas (mover líneas, renombrar locales, no cross-archivo).
- Mensajes a otros peers (`claude-peers send_message`).
- Notas de auto-aprendizaje en error notebook (`writing-review-list.md`).
- Commits en feature branches dedicadas (NO main).

### 5.2 Qué NO pueden decidir solos
- Acción destructiva sobre Docker volumes o BD (ver `~/.claude/CLAUDE.md` §"Regla de Acciones Destructivas Docker").
- Cambios a configuración de producción (Coolify, Vercel deploy, DNS).
- Rotación de credenciales (`.env*` regla CEO 2026-05-25: NO rotar).
- Aprobar / rechazar ADRs.
- Merge a `main`.
- Comunicar con cliente (MC CDMX o cualquier otro).
- Cambios arquitectónicos significativos (estructura sistema, contratos externos, política datos).
- Apagar / encender Coolify, Vercel, Mac Mini local.

### 5.3 Qué deben escalar al CEO INMEDIATAMENTE
- Pérdida de datos detectada (incluso parcial).
- Bug que afecta cliente en producción.
- Credenciales comprometidas o filtradas.
- Disco lleno > 85%.
- Process colgado bloqueando otros procesos del CEO.
- Decisión arquitectónica que no estaba en el sprint plan aprobado.
- Si un peer hace algo que pone en riesgo trabajo de otro peer.

### 5.4 Cómo se coordinan agentes entre sí
- **claude-peers** MCP: `list_peers`, `send_message`, `set_summary`, `check_messages`.
- **Mismo filesystem en mismo repo → git worktrees obligatorio** (regla `~/.claude/CLAUDE.md` §"Regla de Git Worktrees para Multi-Sesión").
- Linda + Joy comparten cwd `/Users/marxchavez/Projects/crece-v2`. Trabajos paralelos requieren worktree (regla cumplida 2026-05-28 con `feat/post-ingest-hugo-2026-05-20` por Linda).
- Decisiones tomadas entre peers (sin CEO presente) deben persistirse en `DECISIONS.md` INMEDIATAMENTE (regla `feedback_persist_peer_decisions`).

### 5.5 Cómo se nombra y reconoce a un agente
- CEO asigna nombre vía instrucción directa o vía persistencia en `memory/user_<nombre>_identity.md`.
- El agente NO se renombra a sí mismo.
- El agente debe declarar su identidad si otro peer pregunta vía `set_summary` o respuesta directa.
- Memoria `user_<nombre>_identity.md` tiene precedencia sobre asunciones de continuación.

---

## 6. Cliente actual

### 6.1 Movimiento Ciudadano CDMX (MC CDMX)
- **Status:** Cliente activo, piloto comercial cerrado 2026-04-20 (D-PILOTO-01).
- **Dirigentes activos:** 3 + 5 shadow al inicio del piloto. Hoy 13 en BD (ver §7 MAPA).
- **Relación:** ConsultoríaMD (CEO) tiene relación de 4+ años con MC.
- **Producto entregado:** dashboard de inteligencia electoral y social (CRECE-electoral, turf Linda).

### 6.2 Posibles clientes / oportunidades (no comprometidos)
- Gobierno Oaxaca (referenciado en handoffs anteriores, sin acción confirmada).
- Mercado B2B PyME via CRECE-Negocios (turf Joy, otro producto).

**Estos clientes son hipótesis de pipeline, no compromisos.** Verificar con CEO antes de actuar.

---

## 7. Protocolos de handoff

### 7.1 Handoffs operativos (entre sesiones)
- Cada sesión significativa (>1h o con decisiones arquitectónicas) cierra con `.context/HANDOFF-YYYY-MM-DD-<slug>.md`.
- Plantilla: `.context/templates/SESSION_HANDOFF.md` (pendiente Sprint B.3).
- Próxima sesión arranca leyendo el último HANDOFF.
- Hooks `SessionStart` cargan automáticamente: STATUS, DECISIONS, BLOCKERS, PLAN-current, último HANDOFF.

### 7.2 Handoffs peer-to-peer (claude-peers)
- Mensajes vía `mcp__claude-peers__send_message`.
- Si la decisión queda compromiso de hacer algo → escribir en `DECISIONS.md` del lado que ejecutará.
- NO confiar en que el otro peer recordará lo que se dijo en su buffer de conversación.

### 7.3 Handoffs CEO → agente
- Vía CLI (input del usuario en la sesión activa).
- Si el CEO está fuera de la sesión y necesita comunicar → `~/.claude/sessions/diary/` o nota en `STATUS.md`.

### 7.4 Handoffs agente → CEO
- Mensaje al final del turno con: qué se hizo, qué falló, qué decisiones pendientes.
- Si hay bloquedo crítico → mencionar al inicio del mensaje, no al final.

---

## 8. Escalation

| Situación | Cómo escalar | Tiempo de respuesta esperado |
|---|---|---|
| Pérdida de datos / corrupción BD | CEO en sesión activa O WhatsApp si fuera | Inmediato |
| Bug producción afecta cliente | CEO + handoff con detalle del impacto | <30 min |
| Decisión arquitectónica fuera de sprint | CEO en sesión activa con propuesta + alternativas | Siguiente respuesta CEO |
| Conflicto entre peers (filesystem, decisión contradictoria) | CEO + nota en handoff del peer iniciador | Siguiente sesión |
| Bloqueo por feature pausada / no disponible | Documentar como BLOCKER + handoff | No-urgente |

---

## 9. Cómo se modifica este doc

1. CEO o Linda detecta que un rol o protocolo cambió.
2. Se redacta el cambio en una sub-sección clara.
3. Si afecta protocolo de coordinación → notificar a peers afectados vía `claude-peers send_message`.
4. Commit con mensaje `docs(governance): ORGANIZACION § X cambio`.
5. Si el cambio es estructural → ADR en `docs/adr/` (cuando exista carpeta) o nota en `DECISIONS.md`.

---

## 10. Versión y cambios

| Fecha | Cambio |
|---|---|
| 2026-05-28 | Versión inicial. Linda (Claude Opus 4.7) redactó tras `/sprint-implement` luz verde CEO. |
| 2026-05-28 (mismo día) | Audit Gemini ⚠️ Pasa con ajustes. Ajustes aplicados: §2.1 Ana García + Carlos López + diferenciación Carlos Amador; §2.2 Enrique Herrera (consultor externo); §3.4 Rem reclasificada "presuntamente cerrada"; §3.5 Juan (peer cross-repo md-research). Reporte: `.context/audits/2026-05-28-organizacion.md`. |
