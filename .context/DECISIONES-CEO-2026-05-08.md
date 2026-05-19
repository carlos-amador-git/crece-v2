# Paquete decisiones CEO §5 — 2026-05-08

**Para:** CEO MD Consultoría
**De:** Linda (CRECE-electoral)
**Objetivo:** cerrar 3 decisiones pendientes en 1 pasada para desbloquear sprints
post-§9.8 (gate piloto día 30 ≈ 2026-05-20).

---

## Decisión #1 — Índice de Aceptación (IA)

**Origen:** propuesta tuya 2026-04-13. Doc completo: `docs/PROPUESTA-INDICE-ACEPTACION.md` (7.8 KB).

**Pregunta a cerrar:** ¿qué nivel de granularidad implementamos para medir "quién interactúa, quién rechaza, quién ignora" por post?

**Hallazgo técnico clave (de la auditoría 2026-04-13):**
- Cruce follower-por-follower (mapa fantasmas user-level) **solo viable en Twitter/X y en Instagram con Business API**.
- Facebook, TikTok y YouTube cerraron esa puerta post-2018 — solo entregan agregados.
- `social_profile_snapshots` actual NO resuelve mapa fantasmas (necesita tabla `follower_snapshots` user-level que no existe).

**3 opciones sobre la mesa:**

| Opción | Alcance | Esfuerzo | Cobertura plataformas |
|---|---|---:|---|
| **A — MVP agregado** | activación/expansión/aprobación a nivel post (sin user-level) | 1-2 sprints (~10-15h) | 5 plataformas |
| **B — Mapa fantasmas full** | quién ignora sistemáticamente, user-level | 3-4 sprints (~30-40h) | Solo TW + IG |
| **C — Secuenciado (recomendado)** | A primero · B después solo TW+IG | A: 1-2 sprints, B: 3-4 sprints adicionales | 5 plataformas en A, 2 en B |

**Mi recomendación: C — Secuenciado.**

**Razón:** A da valor inmediato a los 7 dirigentes piloto en sus 5 plataformas
(KPI nuevo "Aceptación %" computable desde mañana con datos actuales). B
agrega capa premium solo donde técnicamente es factible, sin esperar
infraestructura nueva en plataformas que no la entregarán nunca.

**Decisión que necesito de ti:** **A · B · C · POSPONER post-piloto**.

---

## Decisión #2 — NLP Layer 2 v3 · arquitectura matriz

**Origen:** triangulación 3-way Claude+Gemini+Gemma sobre 60 comments stratified
(seed=42), 2026-04-18. Doc: `backend/evaluations/2026-04-18/output/RESUMEN-EJECUTIVO-CEO.md`.

**Hallazgo crítico:** el runner de producción `nlp_layer2_gemma_bg.py` tiene
prompt que **NO mapea al schema de matriz v2 (53 reglas)**. Vocabularios
divergentes en `tono` y `target`. **El score político de comments en producción
HOY se computa con un mapping incorrecto.**

**Resultado triangulación 60 comments:**

| Dimensión | Acuerdo 3/3 | Fleiss κ |
|---|---:|---:|
| Tono | 73% | 0.761 (substancial) |
| Target | 63% | **0.418 (cuello de botella)** |
| Polaridad | 77% | 0.744 (substancial) |
| Intensidad bucket | 83% | 0.803 (casi perfecto) |

Gemma3:12b apto para producción, pero requiere realineamiento.

**3 sub-decisiones:**

### 2.A · Arquitectura matriz v3
| Opción | Esfuerzo | Tradeoff |
|---|---:|---|
| **C — Mapper intermedio** | 2-4h | No toca producción, capa de traducción runner→matriz v2. Recomendado MVP |
| **B — Realinear runner** | 6-8h + re-benchmark | Mejor fundamentalmente pero más tiempo. Recomendado a 3 meses |
| **A — Migrar matriz al vocab del runner** | varias h | Pierde matices de matriz v2 política. **Descartada** |

**Mi recomendación: C (mapper intermedio) ahora · B planificada Q3.**

### 2.B · Budget ground truth humano
Para validar la matriz v3, necesitamos N comments con anotación humana
(vos o yo). Opciones: 100 rows (prudente · 1h) · 250 rows (sólido · 2.5h) ·
500 rows (publishable · 5h).

**Mi recomendación: 100 rows ahora.** Stratified seed=42 mismo que la
triangulación. Si la concordancia humano↔Gemma queda >75%, suficiente para
piloto §9.8. Si <75%, escalar a 250.

### 2.C · UI dual labels durante transición
Mientras corre v2 + v3 en paralelo (días/semanas), ¿el dashboard muestra
ambos labels?
- **SÍ:** transparencia, vos comparás. Pequeña fricción visual.
- **NO:** se muestra solo v3, v2 queda en BD para audit. Más limpio UX.

**Mi recomendación: SÍ por 7 días, después solo v3.** Aprendizaje observacional
+ rollback fácil si v3 falla.

---

## Decisión #3 — Real Users Roster

**Estado actual:** ✅ **YA RESUELTA** — verificado en BD `2026-05-08`.

Los 6 dirigentes propuestos en la memoria de `2026-04-13` **ya existen** como
dirigentes con user login:

| # | Nombre | Email | Estado |
|---|---|---|---|
| 1 | Alejandro Piña Medina | `pina@crece.mx` | ✅ |
| 2 | Rafael Solano Pérez | `solano@crece.mx` | ✅ |
| 3 | Saymi Adriana Pineda Velasco | `pineda@crece.mx` | ✅ |
| 4 | Yesenia Nolasco Ramírez | `nolasco@crece.mx` | ✅ |
| 5 | Gabriela Jiménez Godoy | `jimenez@crece.mx` | ✅ |
| 6 | César Cravioto Romero | `cravioto@crece.mx` | ✅ |
| 7 | Laura Ballesteros Mancilla | `ballesteros@crece.mx` | ✅ (added) |
| 8 | Jorge Álvarez Máynez | (sin login) | dirigente only |

**No hay decisión que tomar aquí — está cerrada.** Memoria actualizada.

---

## Resumen de decisiones que necesito de vos

| # | Decisión | Recomendación Linda |
|---|---|---|
| 1 | IA agregado · fantasmas · secuenciado · posponer | **C — Secuenciado** |
| 2.A | Matriz v3 · A · B · C | **C — Mapper intermedio** ahora |
| 2.B | Ground truth · 100 · 250 · 500 rows | **100 rows ahora** |
| 2.C | UI dual labels · SÍ · NO | **SÍ por 7 días** |
| 3 | Real Users Roster | **CERRADA** (ya implementado) |

**Tiempo total ejecución si decidís todo según mi rec:** ~3-5h dev (mapper v3
+ ground truth 100 rows) + 1-2 sprints IA Fase A.

Si ponés "C / C / 100 / SÍ / cerrada" en una sola línea, arranco mañana.

---

## ✅ DECISIONES FINALES CEO 2026-05-08

| # | Decisión | Resolución | Notas |
|---|---|---|---|
| 1 | Índice de Aceptación | **C — Secuenciado** (A primero, B después) | Aceptada |
| 2.A | Matriz NLP v3 arquitectura | **C — Mapper intermedio** | Aceptada |
| 2.B | Ground truth humano | **100 rows** | Aceptada · stratified seed=42 |
| 2.C | UI dual labels durante transición | **SÍ por 7 días · estilo B** | CEO eligió opción B (destacar solo divergencias con badge ⚠ + label v2 viejo, default v3 limpio cuando ambos concuerdan) |
| 3 | Real Users Roster | **CERRADA** | Ya implementado, verificado en BD |

### Contrato implementación UI dual labels (opción B)

**Aplica en:**
1. Cards de comment en `/dashboard/aceptacion`
2. Tabla admin HITL `/admin/comments-review`
3. KPI cards con badge `+X% según v3` cuando delta agregado >5pp

**Render:**
```
"texto del comment"
Tono:      crítica   ⚠ v2 decía "ataque"        ← solo si v2 ≠ v3
Target:    tema                                  ← sin ⚠ si v2 = v3
Polaridad: 🔴 -0.7
```

- Default: label v3 limpio sin sufijo
- Si v2 ≠ v3: chip principal = v3 + ícono ⚠ amarillo + caption pequeño "v2 decía: <label_v2>"
- Color stripe lateral opcional: azul = match, naranja = diff
- Tooltip ⓘ en header: "v2 = matriz política original · v3 = matriz armonizada (mapper intermedio)"

**Ventana temporal:** 7 días desde despliegue v3. Tras día 7, switch a solo v3
y v2 queda en BD para audit.

**Esfuerzo dev:** 1.5h frontend (badge ⚠ + caption + tooltip) + integración
con response API que expone ambos labels.

### Próximos pasos (Linda arranca tras este registro)

1. **Mañana AM:** mapper intermedio v2→v3 (`backend/nlp/matriz_v3_mapper.py`)
2. **Mañana mediodía:** stratified sample 100 rows seed=42 + UI form anotación
3. **Mañana tarde:** anotación humana 100 rows (1h CEO o Linda)
4. **D+1:** medir concordancia humano↔Gemma, ajustar mapper si <75%
5. **D+2:** UI dual labels opción B en frontend (1.5h)
6. **D+3..D+7:** ventana observacional, monitor delta v2 vs v3
7. **D+8:** switch a solo v3, archivar v2 (queda en BD)

**Sprint A IA secuenciado:** se planifica post-§9.8 (post 2026-05-20).
Documentación adicional cuando arranque.
