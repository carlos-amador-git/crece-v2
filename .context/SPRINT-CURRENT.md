# SPRINT-CURRENT — Sprint S0 Validación de Supuestos (calibrado v2.4)

**Función:** documento vivo del sprint actualmente en ejecución. Cualquier sesión Claude Code que trabaje en desarrollo lee PRIMERO este documento después de NORTH-STAR.

**Sprint actual:** S0 · **Status:** ⏸ Pending · **Arranque requiere autorización CEO explícita** post-merge MASTER v2.4

---

## Contexto pre-arranque

MASTER v2.4 calibró Sprint S0 tras **audit operativo Gemini 2026-04-19** + **matices CEO**. Expansión de 4 tareas/6-8h → **6 tareas/8-10h** (paralelización óptima ~7h). Todos los criterios de acceptance son cuantitativos binarios — veredicto pass/fail sin ambigüedad interpretativa.

## Requisito transversal de reproducibilidad

Cada reporte generado en S0 debe incluir:
- `system_prompt` exacto utilizado
- `temperature=0.0` (recomendado para validación determinista)
- Modelo + versión específicos (ej. `gemma3:12b-q4_K_M`)
- Paths absolutos de inputs/outputs
- Seeds donde aplique

Sin estos metadatos, los reportes quedan huérfanos en 3 meses e inauditables.

---

## Tareas (6)

### T0.1 — Documentos canónicos ✅ COMPLETADA 2026-04-19
- [x] `.context/NORTH-STAR.md` creado
- [x] `.context/SPRINT-CURRENT.md` creado
- [x] `.context/HANDOFF.md` creado

### T0.2 — Validar benchmarks ER por estrato contra data real
- [ ] Calcular ER real últimos 90 días para los 8 dirigentes × 5 plataformas (Piña, Solano, Pineda, Nolasco, Jiménez, Cravioto, Ballesteros, Máynez)
- [ ] Comparar vs tabla Gemini DR (Nano 6-10% · Micro 3.5-6% · Mid 2-4% · Macro 1.5-2.5% · Mega 1-2%)
- [ ] **Output obligatorio:** `backend/research/2026-04-19/settings_strata.json` con `{dirigente_id: estrato}` (Sprint S1 T2 lo consume DIRECTO)
- [ ] **Output complementario:** `backend/research/2026-04-19/benchmark_validation_er.md` con tabla actual vs esperada + delta
- [ ] **Criterio:** si delta >30% en ≥3 dirigentes → recalibrar rangos en JSON. Si <30% → adoptar tabla Gemini DR

### T0.3 — Pipeline CIB contra post Piña 200 comments
- [ ] Etiquetar manualmente los 200 comments como CIB/no-CIB (baseline humano)
- [ ] Correr infraestructura NLP + patrones ITESO: clustering temporal (>50% 1ra hora), similaridad léxica cosine, account age
- [ ] **Criterio binario pass/fail:** detectar **>60%** de los comments marcados CIB con **<15% falsos positivos**
- [ ] Output: `backend/research/2026-04-19/cib_pilot_test.md` con 200 rows + tasa detección + % FP + decisión (¿infraestructura actual suficiente para bloque #12 MVP o requiere scaffolding S3?)

### T0.4 — Validación ciega DUAL Plutchik + Topics (Gemma vs 3 anotadores humanos)
- [ ] Seleccionar 100 comments aleatorios del dataset 3,709 posts NLP procesado
- [ ] Clasificar con Gemma 3:12b (temperature=0.0, prompt dedicado) en dos dimensiones: **(a)** 6 emociones Plutchik + **(b)** 1-3 topics del seed de 12
- [ ] Clasificar los mismos 100 por **3 anotadores humanos estrictos** (MD Consultoría) con majority vote 2/3 para desempate
- [ ] Calcular Cohen's kappa Plutchik Gemma vs majority + precisión Topics Gemma vs majority + matrices de confusión
- [ ] **Criterios binarios:**
  - Plutchik emoción dominante: **Kappa ≥0.65** (Acuerdo Sustancial)
  - Topic principal: precisión **≥70%** vs majority vote
- [ ] **Fallback si Kappa 0.5-0.65:** NO bloquear S1. Se activa **T1.9** en Sprint S1 con criterio de cierre binario (ver §5 Sprint S1 en MASTER)
- [ ] Output: `backend/research/2026-04-19/plutchik_topics_validation.md` con matrices × 2 dimensiones + kappa + precisión + decisión go/no-go

### T0.5 — Validación lógica `data_fidelity_tier` (NUEVA por Gemini + matiz CEO)
- [ ] Construir matriz 8 dirigentes × 5 plataformas (X, IG, FB, TikTok, YouTube) = **40 celdas** con tier por celda
- [ ] Especificar algoritmo de decisión: qué condiciones de data disponible disparan cada tier **por plataforma** (no por perfil global)
- [ ] Documentar casos edge (dirigente sin presencia scrapeable = N/A, dirigente firmado = T3 directo, cuenta pública vs business/creator)
- [ ] **Output:** `backend/research/2026-04-19/FIDELITY_LOGIC.md` con matriz explícita + algoritmo formalizado + tabla de combinaciones observadas + casos edge
- [ ] **Criterio acceptance:** los 8 dirigentes tienen tier explícito en las 5 plataformas (40/40 celdas) + algoritmo sin ambigüedad + **aprobación CEO del documento antes de codificar en S1 T1**

### T0.6 — Smoke test failover Ollama Coolify (NUEVA por Gemini)
- [ ] `curl` al endpoint Ollama Coolify VPS (§8.6 MASTER): confirmar latencia + disponibilidad + modelo cargado
- [ ] Medir latencia gemma3:12b en Coolify CPU-only (histórico ~17 min — validar vigente)
- [ ] Output: `backend/research/2026-04-19/coolify_failover_smoke.md` con medición p50/p95 + disponibilidad + recomendación: ¿failover directo vs pre-warm + SLA timeout para health-check S1?

---

## Paralelización operativa (recomendada NO obligatoria)

Matiz CEO sobre disponibilidad real de anotadores:
- T0.4 anotación humana (~3h hombre × 3 = ~1h clock paralelizable) puede correr en paralelo con T0.2 script ER + T0.6 smoke test
- Si los 3 anotadores tienen disponibilidad coincidente → sprint cabe en **~7h clock**
- Si ejecución serial → **~9-10h clock**
- Decisión logística del ejecutor según el día

---

## Criterio acceptance del Sprint S0

Sprint S0 se declara completo cuando:
1. ✅ T0.1 completada (ya hecho)
2. T0.2: `settings_strata.json` publicado + delta <30% o recalibración aplicada
3. T0.3: >60% detección CIB con <15% FP (o decisión escalada documentada)
4. T0.4: Kappa Plutchik ≥0.65 + precisión Topics ≥70% (o fallback T1.9 documentado)
5. T0.5: `FIDELITY_LOGIC.md` aprobado por CEO
6. T0.6: medición Coolify documentada con recomendación SLA

Con 6/6 → arranque Sprint S1 autorizado.

---

## Protocolo de actualización

1. **Al inicio de cada tarea:** marcar `- [ ]` → `- [x]` en curso, añadir notas debajo
2. **Al completar tarea:** `- [x]` + link al output generado
3. **Al cerrar sprint:** rellenar `HANDOFF.md` con 5 preguntas + archivar este SPRINT-CURRENT a `.context/archive/sprint-s0-YYYY-MM-DD.md` + resetear para Sprint S1

**Nunca hay 2 sprints activos en este documento.**
