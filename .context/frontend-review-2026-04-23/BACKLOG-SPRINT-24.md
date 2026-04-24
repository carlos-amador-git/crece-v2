# Backlog Sprint 24 · Rewrite estructural Tier 1 + Tier 2

**Origen:** CEO feedback sobre cierre Sprint 23-D — *"F-23-10/11 dice CALIB pero el texto mismo reconoce patrón estructural pendiente. La reclasificación de Gemini no debería disolver la deuda, solo moverla de fila."*

**Clasificación ticket:** 🟡 CALIB en UI (Fase 1 + 4) · 🔴 §9.8 en backend (Fase 2 + 3 — tocan shape de API de diagnóstico).

**Scope:** 18 bloques (10 Tier 1 + 8 Tier 2) aplicando el patrón *"qué mide / cómo te fue / qué hacer"*.

---

## 3 preguntas de arquitectura (requieren sesión dedicada)

Estas NO se contestan al vuelo. Cada una tiene trade-offs que se discuten con plan escrito antes de implementar.

### Q1 · ¿Verdict se computa server-side o frontend?

**Server-side (backend):**
- ✅ Riguroso: el backend ya tiene los thresholds (Zenodo v1, p25/p75 por plataforma y estrato)
- ✅ Consistencia: mismo cómputo para UI, Plan IA, reporte semanal PDF
- ❌ Cambio shape API: cada endpoint de bloque agrega `verdict: {status, label, interpretation}`
- ❌ Migración de consumers existentes

**Frontend:**
- ✅ Sin tocar backend, velocidad
- ✅ Agnóstico del endpoint — cada componente decide su lógica
- ❌ Divergencia potencial: Plan IA y UI podrían interpretar el mismo número distinto
- ❌ Duplicación de thresholds (ya definidos en backend)

**Recomendación preliminar:** Server-side. Consistencia > velocidad cuando el output va a un documento legal (Plan IA, reporte PDF).

### Q2 · ¿De dónde salen las recomendaciones?

**Opción A — Plan IA (dinámico):**
- Deep-link al plan existente del dirigente con el filtro del bloque
- Pros: una sola fuente de verdad
- Contras: si el dirigente no tiene Plan IA activo, el CTA rompe

**Opción B — Plantillas estáticas por bloque:**
- `RECOMENDACION_B01`, `RECOMENDACION_B02`, etc. en un JSON o DB
- Pros: siempre disponibles
- Contras: descontextualizadas del dirigente

**Opción C — Híbrido:**
- Plantilla default por bloque
- Si hay Plan IA → reemplaza plantilla con recomendación específica
- Recomendación preliminar: **C** si se implementa Q1 server-side; **B** en otro caso.

### Q3 · ¿Qué pasa con la "pregunta" actual en el tooltip?

Hoy `CardShell.pregunta` vive en un Tooltip en el botón `[i]` del header. Opciones:

**Mantener en tooltip:** más discreto, espacio limpio.
**Mover a accordion "¿cómo se calcula?":** más visible + espacio para métodología.
**Eliminar:** redundante con el título si el título ya responde la pregunta.

---

## Fases propuestas (post-Q1/Q2/Q3 respondidas)

### Fase 1 · Extender `CardShell` (🟡 CALIB UI)

- Agregar props opcionales `verdict`, `recommendation`, `methodologyContent`.
- Renderizar condicional — sin romper ningún caller actual.
- **Esfuerzo:** 1-2h frontend.

### Fase 2 · Verdict server-side si Q1 = server (🔴 §9.8)

- Por bloque, backend devuelve `{status, label, interpretation}`.
- Nuevas rutas en `/diagnostico/tier1/{id}` y `/diagnostico/tier2/{id}` o extensión de las actuales.
- **Esfuerzo:** 3-4h backend + 2h frontend integration.

### Fase 3 · Wire recommendations según Q2 (🔴 §9.8 si C o A)

- Join con Plan IA actual o carga de plantillas.
- **Esfuerzo:** 2h.

### Fase 4 · Accordion "¿cómo se calcula?" (🟡 CALIB UI)

- Mover referencias académicas (Brookings, Zenodo, Plutchik, ITESO, DFRLab) que hoy viven en `cards.tsx` como comentarios o tooltips.
- Mostrar bajo accordion Radix UI.
- Contenido: 1 párrafo + link a metodología completa.
- **Esfuerzo:** 1h.

---

## Trazabilidad a CEO feedback 2026-04-20..23

- F-23-09 · "Metodología completa" → resuelto parcialmente en Sprint 23 (página pública en `/dashboard/sistema/metodologia`); los 18 bloques linkean ahí vía Fase 4 accordion.
- F-23-10 · Tier 1 copy académico → 8/10 títulos cerrados en 23-D; patrón completo en Fase 1+2+3.
- F-23-11 · Tier 2 copy académico → 5/8 títulos cerrados en 23-D; patrón completo en Fase 1+2+3.
- Referencias Brookings/Plutchik/ITESO/DFRLab → Fase 4 accordion (CEO: *"nota al pie si son mucho texto, o al menú de sistema"*).

## Criterio de éxito Sprint 24

- ✅ Los 18 bloques responden las 3 preguntas del patrón sin que el CEO pida clarificación.
- ✅ Tests visuales Playwright con fixtures de `verdict=success/warning/danger` rendereando correctamente.
- ✅ Una ronda de review visual CEO antes de merge a main.
