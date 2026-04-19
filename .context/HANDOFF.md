# HANDOFF — Protocolo de cierre de sesión

**Función:** plantilla obligatoria que toda sesión de Claude Code rellena al cerrar. Reemplaza los `HANDOFF-*.md` históricos que eran ad-hoc. Este documento responde 5 preguntas exactas en menos de 40 líneas, diseñado para que la siguiente sesión arranque con contexto en <2 minutos.

**Regla dura:** si el hook PreCompact de Claude Code dispara antes del cierre manual, que genere este handoff automáticamente con el último estado limpio del contexto. NO esperar a que el humano se acuerde al final de una sesión de 4 horas.

---

## Template (copiar y rellenar al cerrar cada sesión)

```markdown
# HANDOFF — Sesión [nombre-sesion] · [YYYY-MM-DD HH:MM MX]

**Sprint activo:** [S0/S1/S2...] · **Rama:** [feat/X] · **Última hora de trabajo:** [HH:MM MX]

## 1. ¿Qué se logró hoy? (con evidencia)

- [Logro concreto 1] — evidencia: [commit hash · test verde · screenshot path · archivo creado]
- [Logro concreto 2] — evidencia: [...]
- [Logro concreto 3] — evidencia: [...]

## 2. ¿Qué quedó a medias? (dónde exactamente)

- [Tarea inconclusa] — archivo `path/to/file.py` líneas X-Y · falta: [acción específica]
- [Test fallando] — `path/to/test.py::test_name` · último error: [mensaje resumido]
- [Feature parcial] — funciona Y% del caso · falta: [Z] · razón: [bloqueador]

## 3. ¿Qué decisiones se tomaron que deben migrar a MASTER §6?

- [Decisión] — justificación breve · status (🟢 aprobada CEO / 🟡 propuesta / 🟠 condicionada) · pendiente de documentar en MASTER §6 con formato D-YYYY-MM-DD-NN

## 4. ¿Qué se intentó y NO funcionó? (para no repetir)

- [Intento fallido] — enfoque: [X] · razón del fallo: [Y] · alternativa sugerida: [Z]
- [Enfoque descartado] — [...]

## 5. ¿Cuál es el siguiente paso más pequeño posible? (< 1 hora)

- [Acción concreta] — [una frase de descripción] · archivos involucrados: [paths]
- **Por qué este primero:** [razón para que arranque sea trivial]

---

## Checklist auto-verificable al cerrar

- [ ] ¿Las 5 preguntas están respondidas con concreción, no vaguedades?
- [ ] ¿`MASTER §2.1 Snapshot operativo` está actualizado con los cambios del día?
- [ ] ¿`SPRINT-CURRENT.md` refleja las tareas cerradas vs abiertas?
- [ ] ¿Decisiones nuevas están registradas en `MASTER §6`?
- [ ] ¿Si hay deuda técnica nueva detectada, está en `MASTER §7.5`?
- [ ] ¿Archivo `HANDOFF.md` quedó escrito (si esta es sesión productiva, no consulta)?
- [ ] ¿Se recomendó al CEO commit con mensaje sugerido? (recomendar, no auto-commitear)

## Reglas de formato

- **Máximo 40 líneas** del cuerpo del HANDOFF (sin contar este template).
- **Bullets concretos**, no párrafos. Si necesitas explicar, usa MASTER.
- **Archivos con path completo** o relativo al repo — evitar "el archivo del dashboard".
- **Líneas de código con número** cuando aplique (ej. `services/breakout.py:142-156`).
- **No auto-commitear** — recomendar comando al CEO, él decide.
```

---

## Histórico de HANDOFFs

Cuando se rellene este documento al cerrar una sesión, el contenido del template anterior **NO** se sobreescribe. Se **mueve a**:

`.context/archive/handoffs/handoff-YYYY-MM-DD-[sesion].md`

Y este archivo (`HANDOFF.md`) se resetea con la plantilla limpia para la siguiente sesión.

Así acumulamos histórico auditable sin perder el template original.

---

## HANDOFFs legacy (pre-protocolo nuevo)

Los siguientes archivos son handoffs ad-hoc anteriores a este protocolo. **No usarlos como referencia operativa** — son contexto histórico únicamente:

- `.context/HANDOFF` — handoff genérico 2026-04-17
- `.context/HANDOFF-REM-2026-04-18.md` — handoff específico sesión Rem
- `.context/HANDOVER-AI.md` — decisiones extraídas por Sonnet post-compactación
- `.context/handoff-sprint-e-multitenant.md` — handoff sprint E

Cuando se ejecute la primera sesión con el protocolo nuevo, mover los 4 anteriores a `.context/archive/handoffs-legacy/`.

---

**Regla:** ningún HANDOFF se considera completo sin responder las 5 preguntas. Un HANDOFF incompleto es equivalente a no cerrar la sesión — la siguiente sesión arranca sin contexto.
