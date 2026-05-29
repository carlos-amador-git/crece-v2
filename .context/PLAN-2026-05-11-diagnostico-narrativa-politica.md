# PLAN · narrativa política · cards diagnóstico B01-B10
**Generado:** 2026-05-11 tarde
**Mandato CEO:** "consulta los otros cards con /gemini · me gustaron las ideas que propuso · aplica al resto · que la metodología quede resguardada en Configuración"
**Sesión:** Linda (peer uji6x64w · CRECE-electoral) · branch `feat/phase-b-pesos-editables` · HEAD `1aa9ca1`+ pendientes

---

## Contexto

Gemini (vía /gemini review) entregó 2026-05-11 una crítica concreta de las 10 cards del Diagnóstico Tier 1 con el lente "¿un político lo entiende en 5 segundos?". 10 propuestas narrativas + 1 alternativa de UX para link a metodología + 1 hallazgo extra sobre signal warning. Mi review honesta concuerda con narrativas y propuesta de icono ℹ️ tooltip; defiero B03 matriz 2x2 y B08 gauge a sprint posterior (rediseños mayores, no cambios textuales).

---

## OBJETIVOS

1. Las 10 cards del diagnóstico hablan en lenguaje político sin jerga académica ni IDs internos.
2. Toda la metodología sigue viviendo en `/dashboard/sistema/metodologia` (Sidebar → Configuración → Metodología), accesible a un click desde cualquier card vía icono ℹ️.
3. Signal warning aplicado donde hay esfuerzo desperdiciado o percepción problemática (no neutralizar problemas).
4. Cero strings hardcoded mock (preservar D-ANTI-MOCK-1).
5. Deploy productivo en `frontend-zeta-sepia-46.vercel.app` con verificación visual.

---

## SPRINTS

### S1 · Anchors metodología (15 min) 🟢

**Acción**
- En `/dashboard/sistema/metodologia/page.tsx`, agregar `id` y `scroll-mt-20` a las secciones que cubren cada bloque del diagnóstico.
- Bloques a anchor: `#b01` (ya existe `#er-mx` · agregar alias), `#b02` (viralidad), `#b03` (cuadrantes), `#b04` (benchmark), `#b05` (sentimiento/Plutchik), `#b06` (detector crisis), `#b07` (atribución crecimiento), `#b08` (share of voice), `#b09` (poder movilización), `#b10` (humanización).
- Si la sección no existe en metodología, crearla con contenido mínimo (1-2 párrafos extractados de la card original eliminada o conocimiento del bloque).

**Criterio aceptación**
- `<a href="/dashboard/sistema/metodologia#b07">` navega y hace scroll a la sección B07 sin overlap con sticky header.

---

### S2 · Tooltip ℹ️ en CardShell (30 min) 🟡

**Acción**
- En `frontend/src/components/diagnostico/card-shell.tsx`:
  - Nuevo prop opcional `methodologyAnchor?: string` (ej: "b01")
  - Nuevo prop opcional `methodologyDescription?: string` (1-2 líneas plain text)
  - Renderiza un icono `Info` de lucide pequeño al lado derecho del título.
  - On click/hover: tooltip Radix con `methodologyDescription` + link "Ver metodología completa →" que apunta a `/dashboard/sistema/metodologia#{anchor}`.
- Mantener compat: si los nuevos props no se pasan, no se renderiza el icono.

**Criterio aceptación**
- CardShell sin props nuevos sigue renderizando igual (no rompe cards externos al diagnóstico).
- CardShell con `methodologyAnchor="b01"` muestra ℹ️ → tooltip con link funcional.

---

### S3 · Narrativas Gemini en B01-B10 (45 min) 🟡

**Cambios textuales puros (sin rediseño visual mayor)**:

| Card | Cambio narrativa headline |
|---|---|
| B01 | "Generas **{N} veces más** interacción que otros políticos con tu mismo alcance." (quita estrato Micro técnico) |
| B02 | "Alcance Regional · 60% hacia impacto nacional." (sustituye "Nivel 3") + labels CAT actualizados |
| B03 | (sin cambio mayor de narrativa, los 4 cuadrantes ya son amigables; ver S4 para signal) |
| B04 | "Eres el **#1 entre tus 5 competidores directos**." (quita "analizados") |
| B05 | Traducir Joy→Alegría · Anticipation→Anticipación · Sadness→Tristeza · Fear→Miedo · Narrativa: "Generas el **doble** de Confianza que de Enojo." |
| B06 | "Alerta: **N comentarios negativos inusuales** en las últimas 2 horas." (quita "pico anómalo") |
| B07 | Lista top posts: mostrar excerpt 40 chars del post real (no `twitter #abc123`) |
| B08 | "12% **de toda la conversación** sobre 'reforma laboral'." (sustituye "del total de menciones") |
| B09 | "Poder Viral: Alto (**N/10**)" escala cualitativa derivada del ratio. Quita "0.8 índice de difusión". |
| B10 | "Tu audiencia te percibe como **'persona real'** (por encima del promedio institucional)." Quita "65/100" como headline. |

**Criterio aceptación**
- Cero ocurrencias de strings: "Estrato Micro", "analizados", "Joy", "Anticipation", "Sadness", "Fear", "pico anómalo", "índice de difusión", "del total de menciones" en cards.tsx.
- B07 muestra excerpt del post real, no ID interno.
- TypeScript verde, build OK.

---

### S4 · Signal warning B03/B10 (10 min) 🟢

**Acción** (hallazgo extra Gemini):
- B03 "Sin Eco" (MUERTA): si predomina → signal warning amber (era neutral).
- B10 "Institucional" (score < 40): signal warning amber (era warning ya, validar texto).

**Criterio aceptación**
- B03 con >50% MUERTA → "Esfuerzo Sin Retorno" amber.
- B10 con score < 40 → "Distante" amber (en lugar de "Institucional" que no señala problema).

---

### S5 · Mover tip educativo (10 min) 🟢

**Acción**
- Quitar de B10 card: "Usar la primera persona ('Yo') y emojis aumenta este puntaje."
- Agregar a `/dashboard/sistema/metodologia` sección `#b10`: bullet "Acciones que aumentan el score: usar 1ª persona, emojis, narrativa propia, fotos personales, lenguaje coloquial".

**Criterio aceptación**
- Card B10 no contiene texto educativo "Usar... aumenta".
- Sección B10 de metodología lista acciones recomendadas.

---

### S6 · Validación + Deploy (15 min) 🟢

**Acción**
- `npx tsc --noEmit` → cero errores.
- `npm run check:no-mocks` → cero violaciones (preserva D-ANTI-MOCK-1).
- Commit con detalle de los 5 sprints.
- `vercel deploy --prod --yes` desde `frontend/`.
- Verificar alias `frontend-zeta-sepia-46.vercel.app` apunta al nuevo build.
- Smoke con `curl` al endpoint metodología (HTTP 200, contiene anchors).

**Criterio aceptación**
- Build Vercel OK.
- Alias prod en deploy nuevo.
- Página metodología responde 200 y HTML contiene `id="b07"` etc.

---

## ETA Total

| Sprint | ETA | Acumulado |
|---|---:|---:|
| S1 Anchors metodología | 0:15 | 0:15 |
| S2 Tooltip ℹ️ CardShell | 0:30 | 0:45 |
| S3 Narrativas B01-B10 | 0:45 | 1:30 |
| S4 Signal warning B03/B10 | 0:10 | 1:40 |
| S5 Mover tip educativo | 0:10 | 1:50 |
| S6 Validación + deploy | 0:15 | 2:05 |

**Total: ≈ 2h05 min.**

---

## DIFERIDO a sprint posterior

- **B03 matriz 2x2 "Lo que funciona / Lo que te daña"** (rediseño visual del scatter actual). Justificación: cambio mayor de layout, no de texto. Riesgo de romper interacciones existentes. Backlog.
- **B08 gauge en lugar de pie chart**: mismo motivo. Gauge requiere componente nuevo (radial chart de Recharts no está usado aún). Backlog.

---

## RIESGOS

| Riesgo | Mitigación |
|---|---|
| Crear anchors en metodología requiere texto nuevo si no existe sección | Extractar de cards eliminadas o conocimiento del dominio · contenido mínimo viable, no enciclopédico |
| Tooltip Radix puede chocar con Tooltip Recharts ya importado | Usar alias diferente o el TooltipProvider Radix ya importado en cards.tsx |
| Vercel deploy aterriza en proyecto equivocado (incidente prior) | `cat .vercel/project.json` antes de `vercel deploy` para confirmar `projectName: "frontend"` |
| Política CSS variable inexistente (incidente barra invisible) | Solo usar `--chart-accent/positive/negative/neutral` confirmadas en `globals.css` |
| Romper la metodología page para usuarios actuales | No quitar contenido existente, solo agregar anchors y secciones nuevas |

---

## EJECUCIÓN

Plan a validar con `/gemini plan` (Fase 2 del orchestrator) antes de Sprint 1. Si Gemini detecta riesgos no listados, integrar al plan y reportar al CEO. Si valida sin objeción, arrancar S1 inmediatamente. Reporte al cierre de cada sprint.
