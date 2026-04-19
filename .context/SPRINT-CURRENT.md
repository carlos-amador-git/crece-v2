# SPRINT-CURRENT — [nombre del sprint activo]

**Función:** documento vivo del sprint actualmente en ejecución. Se actualiza al **inicio** de cada sprint con el scope específico de ese sprint. Se actualiza **diariamente** durante el sprint con progreso. Al cierre del sprint, su contenido se archiva en `.context/archive/sprint-sN-YYYY-MM-DD.md` y este documento se reescribe para el siguiente sprint.

**Regla:** cualquier sesión de Claude Code que trabaje en desarrollo activo lee PRIMERO este documento después de NORTH-STAR. Si lo que propone hacer NO está en este documento, lo consulta con CEO antes de ejecutar (evita deriva de sprint).

---

## Sprint activo: Sprint S0 — Validación de Supuestos (pendiente arranque CEO post-merge v2.3)

**Status del proyecto:** arco estratégico cerrado ✅ con dos iteraciones de cross-audit (PR #16 v2.2 mergeado 2026-04-19 + v2.3 post-Gemini Puerta 2 en PR separado pendiente de merge). MASTER v2.3 integra 3 decisiones nuevas (D-16/D-17/D-18) + 6 ajustes críticos Gemini + 3 mejoras diferidas documentadas + protocolo §9.8 dos puertas. 3 documentos canónicos vivos (NORTH-STAR · SPRINT-CURRENT · HANDOFF). Fase de ejecución oficialmente abierta.

**Próximo trabajo inmediato:** **Sprint S0 — Validación de Supuestos ampliado con T0.4** (ver plantilla abajo). Arranque pendiente de autorización CEO tras merge del MASTER v2.3.

**Cambios del MASTER v2.3 que afectan Sprint S0:**
- **Nueva tarea T0.4 Validación ciega Plutchik Gemma vs humano** con criterio aceptance ≥75% coincidencia emoción dominante (Gemini audit #09)
- Estimación total Sprint S0: expandida de 5-6h a **6-8h**
- Sigue siendo prerequisito duro antes de Sprint S1

**Cambios downstream (Sprint S1 y S4) que hay que conocer antes de arrancar S0:**
- Sprint S1 expandido a 5-6h con: migración `recomendaciones_plan_ia` (D-17) + endpoint ARCO purge-hash (D-18) + Ollama failover health-check
- Sprint S4 expandido a 6-8 días con: ciclo 5 fases Plan IA + admin panel review Human-in-the-loop + UI cliente decisión + servicios seguimiento/cierre + bloques #10.5 #10.7
- Nuevo timeline MVP: **4-5 semanas** (aprobación CEO parámetro 1 D-17)

---

## Template para cuando arranque Sprint 0 (copiar y rellenar)

### Sprint S0 — Validación de Supuestos

**Duración estimada:** 5-6h
**Fecha inicio:** [YYYY-MM-DD]
**Fecha cierre objetivo:** [YYYY-MM-DD]
**Owner:** [sesión Joy o equivalente]

**Objetivo en una frase:** validar que los benchmarks y supuestos de la investigación aplican a la data real antes de codificarlos.

**Bloques del inventario tocados:** ninguno directamente — es preparación para Sprint 1.

**Tareas (3):**

- [ ] **T0.1** Crear 3 documentos canónicos en `.context/`:
  - [ ] `NORTH-STAR.md` — ✅ ya creado 2026-04-19
  - [ ] `SPRINT-CURRENT.md` — este documento ✅ ya creado 2026-04-19
  - [ ] `HANDOFF.md` protocolo 5 preguntas — ✅ ya creado 2026-04-19
  - [ ] Verificar que los 3 están en repo y son legibles por cualquier sesión nueva

- [ ] **T0.2** Validar benchmarks ER por estrato político contra data real
  - [ ] Identificar estrato de cada uno de los 8 dirigentes piloto (Piña, Solano, Pineda, Nolasco, Jiménez, Cravioto, Ballesteros, Máynez)
  - [ ] Script que calcula ER real últimos 90 días por dirigente × plataforma (X, IG, FB, TikTok, YT)
  - [ ] Comparar output vs tabla Gemini DR (Nano 6-10% · Micro 3.5-6% · Mid 2-4% · Macro 1.5-2.5% · Mega 1-2%)
  - [ ] Output: `backend/research/2026-04-19/benchmark_validation_er_strata.md` con tabla actual vs esperado + delta
  - [ ] Decisión: si delta >30% → recalibrar benchmarks antes de Sprint 2. Si <30% → adoptar tabla con pequeños ajustes

- [ ] **T0.3** Pipeline CIB básico contra post Piña 7357909824622890245 (200 comments)
  - [ ] Correr infraestructura NLP actual sobre los 200 comments con detección de patrones ITESO básicos: clustering temporal (>50% comments primera hora), similaridad léxica (cosine embeddings), account age inferida
  - [ ] Output: `backend/research/2026-04-19/cib_pilot_test.md` con 200 rows marcados + tasa detección CIB + porcentaje falsos positivos estimado
  - [ ] Decisión: infraestructura actual suficiente para MVP Tier 2 #12? O requiere scaffolding adicional en Sprint 3?

- [ ] **T0.4** Validación ciega Plutchik Gemma vs humano *(añadida por Gemini audit Puerta 2 #09)*
  - [ ] Seleccionar 100 comments aleatorios del dataset de 3,709 posts NLP ya procesado
  - [ ] Clasificar ciegamente a 6 emociones Plutchik (trust/anger/joy/fear/sadness/disgust) por Gemma 3:12b con prompt Plutchik dedicado
  - [ ] Clasificar los mismos 100 por 2-3 anotadores humanos MD independientes
  - [ ] Calcular Cohen's kappa Gemma vs majority vote humano + matriz de confusión
  - [ ] Output: `backend/research/2026-04-19/plutchik_validation.md` con kappa + matriz + recomendación
  - [ ] **Criterio aceptance ≥75% coincidencia en emoción dominante.** Si falla → bloque #05 requiere re-prompt o modelo superior antes de Sprint S2. Si pasa → #05 aprobado para construcción Sprint S2

**Criterio de acceptance del Sprint:**
- 3 documentos canónicos existen en `.context/` ✅
- Tabla validada ER por estrato con 8 dirigentes publicada
- Reporte CIB piloto publicado con % detección + % falsos positivos + recomendación para Sprint 3

**Riesgos / bloqueadores:**
- Si el API de Apify rate-limitea el recalculo ER, extender a 2 días con rotación
- Si los 200 comments Piña no se pueden re-cargar, usar subset desde BD actual

**HANDOFF al cierre:** responder las 5 preguntas en `HANDOFF.md` formato.

---

## Protocolo de actualización de este documento

1. **Al inicio de cada sprint:** copiar plantilla, rellenar objetivo/tareas/criterios, fijar fechas
2. **Durante el sprint:** marcar `- [x]` las tareas completadas, añadir notas bajo cada tarea si hay hallazgos
3. **Al cerrar el sprint:**
   - Verificar que todas las tareas están completas (o documentar excepciones)
   - Mover contenido a `.context/archive/sprint-sN-YYYY-MM-DD.md`
   - Resetear este documento con la plantilla del siguiente sprint (S1, S2, etc.)
   - Actualizar `MASTER §2.1 Snapshot operativo` con "último sprint cerrado" y "próximo paso"

**Nunca hay 2 sprints activos simultáneos en este documento.** Un sprint a la vez, disciplina.
