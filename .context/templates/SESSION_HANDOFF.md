# SESSION_HANDOFF.md · Plantilla

**Cómo usar:** copiar este archivo a `.context/HANDOFF-YYYY-MM-DD-<slug>.md` al cerrar una sesión significativa (>1h o con decisiones arquitectónicas). Rellenar campos. El nombre `HANDOFF-<fecha>-<slug>.md` permite que el SessionStart hook lo detecte y lo cargue.

Esta plantilla fusiona 3 estándares:
- **Disciplina de email-handoff SRE** (Google SRE Book) — al final del turno se manda un resumen estructurado.
- **Primitiva de toma-de-notas Anthropic** (Anthropic context engineering 2025-09) — agente escribe notas a archivo externo que sobreviven a `/compact`.
- **Modelo de memoria 3 capas** (CLAUDE-md + MEMORY-md + handoff) — handoff es la capa episódica.

---

```markdown
# HANDOFF — <slug descriptivo> · YYYY-MM-DD <mañana|tarde|noche>

**Status:** <activa | cierre limpio | cierre con bloqueador | abandonada por X>
**Reason for handoff:** <fin de sesión planificada | /compact | bloqueador externo | apagón | cambio de prioridad>
**Sesión origen:** <originSessionId si lo conoces | "esta sesión">
**Próxima sesión arranca con:** <ruta del próximo plan/sprint o "sin plan, esperar CEO">

---

## ⚠️ LEER PRIMERO

Lista de 1-3 ítems que la próxima sesión DEBE leer antes de actuar:

1. **<Marco / regla nueva / patrón aprendido>** · ruta exacta o cita.
2. **<Bloqueador activo>** · ruta o ADR.
3. **<Decisión CEO no escrita en otros docs>** · texto verbatim del CEO si aplica.

---

## What was done (qué cambió esta sesión)

### Bloque 1 · <Nombre del bloque>
- Qué archivos se tocaron (paths exactos)
- Qué decisiones se tomaron
- Qué se verificó (queries SQL, tests, screenshots)
- Cita a commits relevantes

### Bloque 2 · <Nombre>
- ...

### Decisiones tomadas — autor: [HUMAN <nombre> | AGENT <tool/model>]
Cada decisión arquitectónica con:
- Autor (humano vs agente)
- Enlace a ADR si se escribió (`docs/adr/NNNN-slug.md`)
- Notas de razón

---

## What's left to do (cola priorizada)

### 🔴 P0 — Bloqueador / urgente
1. <Ítem con criterio de aceptación verificable>

### 🟡 P1 — Importante no urgente
1. <Ítem>

### 🟢 P2 — Mejora / deuda
1. <Ítem>

### ⏸ Bloqueado por
- **Por CEO:** decisiones pendientes (listar)
- **Por peer:** qué esperando (listar)
- **Por sistema externo:** rate limits, deploys, OAuth aprobaciones

---

## Estado actual / qué funciona

| Componente | Estado | Verificado con |
|---|---|---|
| <Componente 1> | ✅ Funcional | SQL/test/screenshot |
| <Componente 2> | ⚠️ Parcial | Notas de qué parte |
| <Componente 3> | ❌ Roto | Error específico |

---

## Bloqueado / preguntas abiertas para CEO

1. <Pregunta concreta> · contexto: ...
2. <Pregunta> · 2 opciones: (a) ... (b) ...

---

## Key decisions / state operativo

- **Rama git:** `<nombre>`
- **Commit HEAD al cierre:** `<sha>`
- **Cambios sin commitear:** <lista o "ninguno">
- **DB modificada:** <lista o "ninguna">
- **Archivos `.env*` tocados:** <NO por default>

---

## Files modified / created

| Commit | Archivos |
|---|---|
| `<sha>` <tipo>(<scope>): <mensaje> | <paths>|

---

## Coordinación con peers

- **<Nombre peer> (<peer-id>, cwd <ruta>):** <qué se acordó>

---

## ¿Nuevos hechos a promover a MEMORY.md / AGENTS.md / ADRs?

| Hecho | Destino | Status |
|---|---|---|
| <Hecho concreto> | MEMORY.md / AGENTS.md / docs/adr/ | ☐ pendiente / ✅ escrito |

---

## Cómo retomar (próxima sesión)

1. SessionStart hook cargará: MEMORY.md (con pointers nuevos si los hay), error notebook, context anchor (STATUS + DECISIONS + BLOCKERS + PLAN-current).
2. Leer este handoff (auto-detectado por nombre `HANDOFF-YYYY-MM-DD-*`).
3. Leer `.context/governance/MODELO-TRABAJO-AUDIT.md` antes de cualquier redacción de doc.
4. Si vas a tocar código: aplicar HARD RULE grep-antes-de-proponer (`AGENTS.md` §11 anti-patrones).
5. Si vas a tocar producto / commercials: leer `.context/governance/PRODUCTO.md` para inputs CEO pendientes.

---

## Cierre

- Próximo paso recomendado: <verbo concreto + criterio de aceptación>
- ¿Necesita confirmación CEO antes de arrancar? <sí/no + qué>
```

---

## Notas para Linda (la redactora)

- **Mantén el handoff conciso.** El cap natural es 200-400 líneas. Si crece más → revisa qué es redundante con STATUS.md o BLOCKERS.md.
- **Las decisiones del CEO en texto verbatim importan.** Cuando el CEO dice algo crítico, copialo entre comillas (`"..."`).
- **Cuando un peer aprueba algo, no confíes en su buffer** — persiste en DECISIONS.md INMEDIATAMENTE (regla `feedback_persist_peer_decisions`).
- **El handoff es el último commit de la sesión, no el primero.** Después de escribirlo, push/commit y cierre.
- **NO hagas handoff antes de ejecutar.** El handoff describe lo hecho, no lo planeado. Para planes futuros usa `PLAN-YYYY-MM-DD-<slug>.md`.
