# Modelo de trabajo y auditoría — gobernanza documental

**Última actualización:** 2026-05-28
**Propósito:** definir un método replicable para que el agente IA (Linda, futuras instancias) documente funciones, módulos y procesos de la app SIN inventar, y para que un auditor independiente (Gemini) valide cada entrega contra evidencia verificable.

Este es el meta-doc: rige cómo se redactan los otros 4 docs de gobernanza.

---

## 1. Principios duros (sin excepción)

1. **Buscar antes de proponer.** Toda afirmación debe estar respaldada por cita verificable (`archivo:línea`, query SQL ejecutada con su output, o referencia explícita a otro doc de gobernanza). Si no hay cita, no es afirmación: es invención.
2. **Calidad > tiempo.** Si una sección requiere 2 sesiones para hacerse bien, se hace en 2 sesiones. No se aceptan compromisos de tipo "30% mejor que 0%".
3. **Trazabilidad.** Todo lo que se documenta debe poder ser re-verificado por otro agente. Si la verificación falla → la afirmación se elimina o se corrige.
4. **Auditor independiente.** El redactor (Linda) no audita su propio trabajo. El auditor (Gemini) valida sin haber participado en la creación.
5. **Afirmaciones absolutas requieren query de cobertura, no solo lectura de código.** (Sub-regla agregada 2026-05-28 tras auditoría cross-doc Gemini). Frases tipo "X nunca hace Y", "X siempre hace Y", "X no existe" deben acompañarse de query SQL ejecutada o `grep -c` que dé 0 matches. Patrón detectado: ambos lados tendíamos a absolutos verbales cuando la realidad era 82% intermitente (pepe_hybrid captura texto) o asimétrica (CRECE tiene POST endpoint pero no hook FE). Si solo leíste código y no mediste cobertura → no afirmes "nunca/siempre/no existe", afirma "no encontré en la lectura limitada que hice".
6. **Sesgo CRUD simétrico.** (Sub-regla agregada 2026-05-28). NO asumir que porque existe GET/PATCH/DELETE también existe POST hook FE (o vice versa). Cada par endpoint-hook se verifica independientemente con `grep -nE "^export function useCreate|useMutation"` antes de afirmar que existen ambas mitades.

---

## 2. Template de sección (estructura fija)

Cada sección del `MAPA-FUNCIONAL.md` (y de cualquier otro doc de gobernanza que documente funciones) sigue esta estructura. Las casillas son obligatorias; si una no aplica, decirlo explícitamente con razón.

### Estructura

```markdown
## N. Nombre del módulo / función ✅|⚠️|❌|📝

**Concepto:** 1-2 frases sobre qué resuelve el módulo.

### N.1 Vistas FE del sidebar (o internas)
Por cada vista:
- **Archivo:** ruta exacta del page.tsx
- **Función:** qué ve el usuario
- **Hook(s) usado(s):** nombre del hook + archivo
- **Endpoint(s) backend llamado(s):** ruta + método
- **Response type:** tipo TS retornado

### N.2 Endpoints backend del módulo
Tabla: endpoint → response type → función → hook FE
Citas: archivo backend + número de línea del decorator @router.

### N.3 Tablas DB que el módulo lee/escribe
Tabla con columnas que pobla/lee. Citar al PIPELINE-RADAR-CRECE.md para origen del dato.

### N.4 Deuda y estado real conocido
Tabla: item → estado (✅/⚠️/❌) → notas con cita.

### N.5 Cómo responder preguntas comunes
Tabla: "pregunta común" → "ruta exacta a la respuesta en código/data".
```

---

## 3. Checklist pre-redacción

Antes de redactar una sección, ejecutar **en orden** y guardar los outputs como evidencia:

1. `grep -rln "<concepto-clave>" backend/ frontend/` — buscar el término en código.
2. Listar archivos resultantes. Para cada uno, identificar si es endpoint / hook / componente / model.
3. Leer los endpoints relevantes (`backend/app/api/v1/endpoints/<modulo>.py`):
   - Listar todos los decoradores `@router.<method>` con líneas.
   - Para cada uno: response_model + SQL/service que ejecuta + tablas que toca.
4. Leer los hooks FE relevantes (`frontend/src/lib/api/hooks/use-<modulo>.ts`):
   - Listar todas las funciones `export function`.
   - Mapear cada hook → endpoint que llama (`api.get("/...")`).
5. Identificar las páginas FE relevantes (`frontend/src/app/dashboard/<modulo>/`):
   - Para cada `page.tsx`: qué hooks usa, qué componentes pinta.
6. Verificar contra DB:
   - `docker exec crece-db psql -U crece -d crece -c "\d <tabla>"` para confirmar columnas.
   - Queries de cobertura/sample para confirmar lo que el adapter pobla.
7. Buscar deuda en handoffs y memoria:
   - `grep -lE "<modulo>" .context/HANDOFF-*.md ~/.claude/projects/.../memory/*.md`
8. Solo después de estos 7 pasos: redactar la sección con el template del §2.

**Si algún paso devuelve 0 matches**, declararlo explícitamente: "buscó `<termino>`, 0 matches en `<ruta>`, por eso afirmo que no existe."

---

## 4. Plantilla de evidencia (cómo se cita)

| Tipo de afirmación | Cómo se cita | Ejemplo |
|---|---|---|
| Endpoint backend | `archivo.py:línea` del decorator `@router.<method>` | `indice_aceptacion.py:394 @router.get("/aceptacion/fantasmas-por-plataforma")` |
| Hook FE | `archivo.ts:línea` del `export function` | `use-aceptacion.ts:46 export function useFantasmasPorPlataforma()` |
| Service backend | `archivo.py:línea` de la función | `er_service.py:64 async def compute(...)` |
| Query SQL ejecutada | bloque ` ```sql ` con la query + su output | `SELECT COUNT(*) FROM watched_profiles WHERE dirigente_observador_id=3 → 28649` |
| Tabla DB columnas | `\d <tabla>` ejecutado vía docker exec | (output de psql) |
| Cobertura por columna | `SELECT COUNT(*) FILTER (WHERE col IS NOT NULL)` | "`avatar_url` cubierto 0/28,649" |
| Decisión/regla | referencia a ADR o DECISIONS.md | "D-3: BD jamás se toca" |
| Concepto en handoff | `archivo.md` cita | `HANDOFF-2026-05-28-radar-ingest-pendiente.md §residual` |

**Una afirmación sin cita = falla de auditoría.**

---

## 5. Protocolo de auditoría (Gemini auditor)

### 5.1 Cuándo auditar

Después de redactar (o re-redactar) cualquier sección de un doc de gobernanza. Antes de avanzar a la siguiente sección.

### 5.2 Qué pasa Linda al auditor

1. Ruta al doc completo (`.context/governance/<doc>.md` o `.context/<doc>.md`).
2. Identificación de la sección a auditar (§N.).
3. Acceso de lectura al repo (Gemini puede grep + leer archivos + ejecutar queries SQL contra `crece-db`).
4. El prompt canónico (ver `PROMPT-AUDITOR-GEMINI.md` en governance/, generado a continuación).

### 5.3 Qué entrega el auditor

Reporte estructurado en `.context/audits/<YYYY-MM-DD>-<doc>-seccion-N.md` con:

```markdown
# Auditoría sección N — <nombre módulo>
**Fecha:** YYYY-MM-DD
**Auditor:** Gemini
**Doc auditado:** ruta
**Sección:** §N

## Citas verificadas
- ✅ N afirmaciones con cita verificable (lista cada una con check).

## Citas sin verificar
- ⚠️ Afirmación "X" en línea L: no encontré evidencia en `<ruta esperada>`.

## Omisiones detectadas
- ❌ Endpoint `/Y` existe en `<archivo:línea>` pero no aparece en la sección.
- ❌ Tabla `Z` se referencia en hook `useW` pero no está en §N.3.

## Sesgo del redactor
- 🔍 Cobertura solo verificada para dirigentes 1,2,3,5,8,57,60. Dirigentes 4 y 6 no auditados.

## Veredicto
- ✅ Pasa | ⚠️ Pasa con ajustes (lista) | ❌ Re-trabajo (motivo)
```

### 5.4 Qué hace Linda con el reporte

1. Si pasa: avanza a siguiente sección.
2. Si pasa con ajustes: corrige las afirmaciones señaladas + responde a las omisiones. Re-audita si cambia >20% del contenido.
3. Si re-trabajo: descarta la sección, vuelve a §3 (checklist pre-redacción) desde cero.

### 5.5 Frecuencia

- Por sección al primer paso.
- Cada N=3 secciones, auditoría transversal: ¿hay duplicación entre secciones? ¿hay inconsistencias?

---

## 6. Cómo se actualiza este modelo

Cuando una auditoría revela un patrón sistémico (no un error puntual), el modelo se actualiza. Ejemplo: si Gemini detecta 3 sesiones distintas donde Linda no buscó `useX` antes de proponer integración, agregar a §3 paso "8: si la sección involucra una integración con hook nuevo, primero `grep -rln \"use\" frontend/src/lib/api/hooks/`".

Cambios al modelo deben quedar en este archivo con fecha. No en otra parte.

---

## 7. Aplicabilidad

- **CRECE v2:** este modelo se aplica a partir de 2026-05-28.
- **Futuros proyectos MD Consultoría:** la carpeta `.context/governance/` debe formar parte del bootstrap del proyecto. Los 5 docs nacen como esqueletos vacíos y se llenan conforme la app crece. El `MODELO-TRABAJO-AUDIT.md` se copia tal cual.
