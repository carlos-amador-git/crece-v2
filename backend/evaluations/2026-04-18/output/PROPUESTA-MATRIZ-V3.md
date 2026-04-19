# Propuesta Matriz de Polaridad v3

**Fecha:** 2026-04-18
**Base:** matriz v2 (53 reglas) + triangulación NLP Layer 2 2026-04-18 (60 rows, 3 modelos)
**Status:** propuesta — requiere decisión CEO
**Input:** `REPORTE-TRIANGULACION.md` · `rule_gaps.md` · `research/memory/2026-04-14-matriz-polaridad-v2-comments.md`

> Esta propuesta NO se aplica automáticamente. CEO decide aplicar / iterar / descartar en Fase 4.

---

## 1. Hallazgo central

**Gap de vocabulario entre runner Gemma (producción) y schema matriz v2.**

| Dimensión | Prompt runner (producción) | Matriz v2 schema BD |
|---|---|---|
| tono | elogio · critica · **pregunta** · ataque · informativo · personal · **autopromocion** | critico · **propositivo** · **celebratorio** · informativo · **solidario** · ataque · personal |
| target | dirigente_post · gobierno · oposicion · ciudadania · **institucion** · otros | gobierno · oposicion · ciudadania · **medios** · **autopromocion** · **dirigente** · **tema_especifico** · otro |

**Diferencias netas:**
- Tono: runner tiene `pregunta` y `elogio`; v2 tiene `propositivo`, `celebratorio`, `solidario`; `autopromocion` existe en runner como tono pero en v2 como target (conflicto semántico).
- Target: runner tiene `institucion`; v2 tiene `medios`, `tema_especifico`, `dirigente` (éste solo en comment_tercero).
- `dirigente_post` (runner) ≈ `dirigente` (v2 comment_tercero). Diferencia solo en sufijo.

**Implicación medible:** el output de Gemma actualmente **NO mapea 1:1** a `framework_matrix_defaults.get_polarity()`. El score político que debería aplicarse post-Gemma está indeterminado sin un mapper explícito.

---

## 2. Tres opciones de arquitectura

### Opción A — Adoptar vocab del runner en matriz v3

**Qué:** migrar `framework_matrix_defaults` al vocabulario runner. `elogio` reemplaza `celebratorio`; `critica` reemplaza `critico`; nueva regla para `pregunta`; `autopromocion` retirado como tono (se detecta a nivel runtime via `author == handle_dirigente`).

**Pros:**
- No toca producción (Gemma sigue corriendo como está)
- Prompt V3 del runner se mantiene — benchmark CEO 2026-04-14 intacto
- `pregunta` gana reglas propias (no existía en v2)

**Contras:**
- Perdemos matices de v2: `propositivo`, `solidario` (tonos positivos distintos de `elogio`)
- Requiere retranscribir 53 reglas v2 al nuevo vocab + audit_log migration
- Riesgo de pérdida de granularidad en reportes existentes

**Costo:** ~4-6h (migration ds05 + reseed + tests + patch `get_polarity` + update frontend labels)
**Reversibilidad:** media (el vocab v2 queda en audit_log)

---

### Opción B — Alinear el runner al vocab matriz v2 (re-prompt)

**Qué:** cambiar `PROMPT_TEMPLATE` en `nlp_layer2_gemma_bg.py` para usar el vocab v2. `elogio → celebratorio`, añadir `propositivo` y `solidario`, retirar `pregunta` (mapear a `critico` o `informativo` según contexto).

**Pros:**
- Schema BD es fuente única de verdad
- Granularidad de matriz v2 preservada (53 reglas vivas)
- Alineación con decisiones Sprint B (2026-04-14) intacta

**Contras:**
- **Invalidar benchmark Gemma aceptado CEO 2026-04-14** — re-correr batch ~1,100 comments con nuevo prompt
- Re-validar rate (31.4 min / 400 comments proyectado) contra nuevo prompt
- Triangulación 2026-04-18 queda obsoleta (prompt cambió, benchmark no válido)
- `pregunta` se pierde como categoría de primer nivel — puede degradar detección de preguntas con crítica implícita (P5)

**Costo:** ~6-8h (re-prompt + re-benchmark + re-triangulación + tests + eval prod metrics)
**Reversibilidad:** baja (cambia el output de miles de rows existentes)

---

### Opción C — Mapper intermedio runner↔matriz v2 (sin tocar ninguno)

**Qué:** mantener runner y matriz v2 como están. Añadir función `_map_runner_to_v2_vocab(runner_output: dict) -> dict` en `services/political_framework.py` con tabla de equivalencias explícita + fallback reglado.

```python
TONO_MAPPING = {
    "elogio": "celebratorio",
    "critica": "critico",
    "ataque": "ataque",
    "informativo": "informativo",
    "personal": "personal",
    "pregunta": "critico",       # decisión: pregunta → crítica
    "autopromocion": "celebratorio",  # si tono=autopromocion Y author == handle_dirigente
}
TARGET_MAPPING = {
    "dirigente_post": "dirigente",  # solo en contexto comment_tercero
    "institucion": "otro",
    "gobierno": "gobierno",
    "oposicion": "oposicion",
    "ciudadania": "ciudadania",
    "otros": "otro",
}
```

**Pros:**
- No rompe producción ni schema BD
- Reversible — si una regla mapping está mal, se corrige sin migración
- Gemma batch actual sigue usable
- Test-drive rápido: se puede calibrar mapping en días y revisar
- Precedente en software: adapters are cheaper than unifying two moving parts

**Contras:**
- Dos vocabularios conviven — onboarding más pesado para quien lea el pipeline
- Gap entre lo que muestra Layer 2 UI y lo que guarda BD
- Pérdida de información: `autopromocion` tono del runner se colapsa a `celebratorio` v2 — pierde el distintivo

**Costo:** ~2-4h (mapper + tests + docstring + regenerar scores sobre comments procesados)
**Reversibilidad:** alta

---

## 3. Recomendación

**Adoptar Opción C (mapper) como MVP** — 2-4h para desbloquear scores políticos contra comments procesados.

**Evaluar Opción B (realinear runner) a 3 meses** — cuando el pipeline esté estable y podamos permitirnos re-benchmark. La triangulación futura tendrá ground truth humano (sprint pendiente) y la decisión estará mejor informada.

**Descartar Opción A** — invalida el esfuerzo de matriz v2 (53 reglas) y pierde matices importantes (`propositivo`, `solidario`).

**Justificación de orden:**
1. C desbloquea valor hoy
2. B es la solución "correcta" pero tiene costo alto y timing malo (pre-benchmark humano)
3. Ground truth humano futuro arbitra entre C estable y B refinado

---

## 4. Ajustes específicos a reglas (independientemente de opción A/B/C)

Basado en los 6 patrones de `rule_gaps.md`:

### 4.1 Distinguir crítica constructiva (P1 — 6 rows)

Comments como "Debieron contemplar el desazolve antes de..." (crítica con propuesta implícita) se clasifican por Claude como `neutral` y por G+M como `rechazo`.

**Propuesta R1:** añadir modificador `_constructivo` al tono crítica:
- `critica_constructiva` → polaridad neutral + score ajuste 0 (oposición) / -1 (oficialismo leve)
- `critica_hostil` → polaridad rechazo (regla v2 actual intacta)

**Heurística detección:** keyword-match de tokens propositivos (`debieron`, `sería mejor`, `contemplar`, `regulen`, `propongo`).

### 4.2 Personal vs elogio en comments cortos con emojis (P2 — 4 rows)

Ejemplos: "💪🧡 Maynez", "Jajjajajajaj ❤️", "con tokio 🟠🦅".

**Propuesta R2:** si comment_length < 30 chars AND emoji_count ≥ 2 AND polaridad >= 0 → fusionar `personal` y `elogio` en `afirmativo_breve` (regla común, score +1 en cualquier rol cuando target=dirigente).

### 4.3 Autopromoción runtime (P3 — 3 rows)

Claude marca `autopromocion` cuando `author == handle_dirigente` (self-RT o self-post anunciado como comment).

**Propuesta R3:** detectar self-authoring a nivel runtime **antes** de invocar Layer 2. Si `author == handle_dirigente`, saltar matriz de sentiment y registrar `tono_politico='autopromocion', target='dirigente_post'` directamente. Libera al LLM de esta decisión y elimina divergencia.

### 4.4 Sarcasmo / ironía — ataque vs crítica (P4 — 3 rows)

Threshold entre `ataque -3` y `critica -2` diverge: Claude más agresivo, Gemma más conservador.

**Propuesta R4:** criterio explícito en prompt V3:
- `ataque` = insulto directo sin argumento O reducción al insulto vulgar ("HDP", "idiota", etc.)
- `critica` = desacuerdo fundamentado, incluso con tono burlesco
- Ejemplo few-shot: "no estabas mame y mame que..." → **crítica** (aun con sarcasmo pesado)

### 4.5 Pregunta como categoría (P5 — 2 rows)

Matriz v2 no tiene reglas para `tono=pregunta`.

**Opción 5a (mantener en runner + mapping):** mapper colapsa `pregunta → critico`. Suficiente para MVP.
**Opción 5b (añadir a v2):** 3 nuevas reglas:
- (cualquier rol, pregunta, dirigente) → 0 (engagement neutral)
- (cualquier rol, pregunta, gobierno) → -0.5 (pregunta con crítica implícita leve)
- (cualquier rol, pregunta, otros) → 0

Recomendación: **5a** para MVP, **5b** si se implementa Opción A o B.

### 4.6 3-way divergence (P6 — 1 row)

Caso genuinamente ambiguo ("Se sabe que el origen de muchas de esas colonias..."). No intentar resolverlo con reglas — marcar rows con 3-way divergence en tono para revisión humana obligatoria.

**Propuesta R6:** campo `requires_human_review` en `social_comments` con flag automático cuando Fleiss(tono)=0 sobre 3 modelos.

---

## 5. Cambios al schema BD (solo si se adopta A o B)

### Para Opción A

```sql
-- Migration ds05_vocab_runner
ALTER TABLE framework_matrix_defaults
  ALTER COLUMN tono TYPE VARCHAR(30),
  ADD CONSTRAINT chk_tono CHECK (tono IN (
    'elogio', 'critica', 'pregunta', 'ataque', 'informativo', 'personal'
  ));

ALTER TABLE framework_matrix_defaults
  ALTER COLUMN target TYPE VARCHAR(30),
  ADD CONSTRAINT chk_target CHECK (target IN (
    'dirigente_post', 'gobierno', 'oposicion', 'ciudadania', 'institucion', 'otros'
  ));

-- Retirar 'autopromocion' del tono (ahora es target)
UPDATE framework_matrix_defaults SET tono='celebratorio' WHERE tono='autopromocion';

-- Renombrar 'celebratorio' → 'elogio' en todas las reglas
UPDATE framework_matrix_defaults SET tono='elogio' WHERE tono='celebratorio';
-- (etc. para los demás tonos)
```

### Para Opción B — sin cambios BD

El runner cambia el prompt, el output se alinea al schema actual. Se invalida el benchmark pero BD no se toca.

### Para Opción C — sin cambios BD

El mapper vive en el código aplicación, no en BD.

---

## 6. Tests requeridos

Independientemente de opción:

```python
def test_mapper_roundtrip():
    """Output Gemma → mapper → matriz v2 debe devolver un score válido."""
    gemma_out = {"tono": "elogio", "target": "dirigente_post", ...}
    mapped = map_runner_to_v2(gemma_out)
    assert mapped["tono"] == "celebratorio"
    assert mapped["target"] == "dirigente"
    score = get_polarity(rol="oposicion", **mapped, contexto="comment_tercero")
    assert score == 1

def test_all_runner_tonos_mappeables():
    for t in RUNNER_TONOS:
        assert t in TONO_MAPPING, f"tono runner {t} sin mapping"
```

---

## 7. Riesgos y mitigaciones

| Riesgo | Opción afectada | Mitigación |
|---|---|---|
| Mapper pierde información (autopromocion → celebratorio) | C | Añadir flag `_derived_from_runner_autopromocion=True` en metadata del score |
| Re-benchmark invalida accuracy 2026-04-14 | B | Benchmark paralelo antes de cutover; criterio de aceptación ≤ -5% accuracy |
| Migración A afecta históricos | A | Feature flag `vocab_version` + reescritura gradual |
| Ground truth humano llega y contradice mapper | C | Mapper es tabla — se edita sin migración |

---

## 8. Criterios de aprobación CEO (Fase 4)

1. **¿Aprobar arquitectura?** Opción C (mapper) / B (realinear runner) / A (migrar matriz) / combinación
2. **¿Aprobar los 6 ajustes específicos (R1-R6) o sólo algunos?**
3. **¿Schedule para re-benchmark humano?** Si sí, cuándo y con cuántas muestras
4. **¿Observabilidad mensual aprobada?** (50-100 rows re-trianguladas, alert en kappa < 0.55)

---

## 9. Cross-audit Gemini

Ejecutado 2026-04-18 con `gemini -p` sobre la versión previa a esta sección. Output crudo en `/tmp/gemini_audit_response.txt`. Resumen integrado abajo.

### Veredicto Gemini
**Aceptar con ajustes** — priorizar Opción C como puente táctico hacia la B.

### Fortalezas reconocidas
- **Opción C pragmática** — desbloquea valor sin invalidar benchmark Gemma aceptado
- **R3 (autopromoción runtime) "brillante"** — desacopla lógica determinística del LLM
- **R6 (human review via Fleiss divergence)** formaliza gestión estadística de incertidumbre

### Debilidades señaladas
1. **Mapping `pregunta → critico` es riesgoso** — inflaría polaridad de rechazo artificialmente. Gemini recomienda `pregunta → informativo` por defecto, solo a `critico` si hay flag de hostilidad detectado.
2. **Deuda técnica** — dos vocabularios conviviendo aumentan complejidad onboarding y riesgo en futuras migraciones
3. **Versionado de mapper faltante** — si Gemma cambia sutilmente, mapper falla silenciosamente

### Ajustes aceptados de Gemini (integrar a la propuesta)

| # | Ajuste | Acción propuesta |
|---|---|---|
| G1 | Refinar R5: `pregunta → informativo` default, `→ critico` solo con hostility flag | Reemplazar `"pregunta": "critico"` por lógica condicional en `TONO_MAPPING` |
| G2 | R3 prioritario a middleware | Mover detección `author == handle_dirigente` al ingest pipeline, antes de llamar LLM |
| G3 | Versionar mapping en BD | Añadir columna `mapping_version VARCHAR(10)` a `social_comments_scores`; tag con cada score |
| G4 | R2 condicional a target | Regla "emoji-breve → afirmativo_breve" solo si `target=dirigente`; evita ironía-hacia-oposición clasificada como elogio |
| G5 | Dashboard de fallbacks del mapper | Métrica `mapper_fallback_rate`; alert si >5% del volumen |

### Gaps no detectados en la propuesta original (aportados por Gemini)

1. **Drift monitoring del runner Gemma** — no hay plan para detectar cambios en comportamiento del modelo post-update de Ollama o del prompt. Mitigación: añadir a observabilidad mensual un test de regresión con 10 rows golden.
2. **Coherencia UI / dual labels** — la UI muestra `Elogio` pero la BD guarda `celebratorio`. Cómo se reconcilian las etiquetas en frontend no está resuelto. Propuesta: vista BD `vw_comment_scores_ui` que traduce vocab v2 → vocab runner para display.
3. **Re-etiquetado histórico** — no detalla cómo se actualizan scores de comments procesados antes del mapper. Mitigación: job batch `backfill_scores_with_mapper.py` + criterio (últimos N días vs histórico completo).

### Preguntas adicionales para el CEO (de Gemini)

1. ¿Presupuesto para ground truth humano (1,100+ rows) este mes para validar Opción B como meta definitiva?
2. ¿Threshold de kappa Fleiss mínimo para detener pipeline y forzar revisión humana? Sugerencia inicial: Fleiss < 0.5 en cualquier dimensión en muestra mensual.
3. ¿Aceptable UI dual (display `Elogio` / BD `celebratorio`) durante transición?

---

## 10. Cambios aplicados tras audit

Se actualiza la sección 4 (ajustes R1-R6) con los 5 ajustes Gemini. Los ajustes R1-R6 quedan:

- **R1** (crítica constructiva) — sin cambios
- **R2** (emojis breves) — **condicionado a `target=dirigente`** (G4)
- **R3** (autopromoción runtime) — **elevar a prioridad alta, implementar primero** (G2)
- **R4** (sarcasmo/ataque vs crítica) — sin cambios
- **R5** (pregunta) — **default `informativo`, `critico` solo con hostility flag** (G1)
- **R6** (3-way divergence → human review) — sin cambios

Se añaden 3 sprints nuevos:

- **R7** (versionado mapper) — columna `mapping_version` en BD + tag por score (G3)
- **R8** (dashboard fallback rate) — métrica y alert (G5)
- **R9** (drift monitoring) — 10 rows golden en test regresión mensual (Gemini gap 1)

Status: **propuesta cerrada — lista para decisión CEO (F4.1)**.

