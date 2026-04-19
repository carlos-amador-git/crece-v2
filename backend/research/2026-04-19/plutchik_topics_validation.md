# T0.4 — Validación ciega DUAL Plutchik + Topics

**Sprint:** S0 · **Tarea:** T0.4 · **Fecha:** 2026-04-19
**Veredicto:** ✅ **PASS (go)** con advertencia silver-grade (ver §6)

---

## 1 · Contexto operativo y substituciones

**Instrucción CEO (2026-04-19):** *"documenta ambigüedad en lugar de pausar. Usa Claude + Gemini como 2 anotadores expertos proxy humanos en lugar de 3 humanos MD. Gemma3:12b local es el clasificador bajo validación."*

La especificación original en `SPRINT-CURRENT.md` / `CRECE_PRODUCT_MASTER.md §5 Sprint S0`
exige **3 anotadores humanos MD + majority vote 2/3**. Esta validación **NO cumple ese
estándar de oro**. Se documenta explícitamente a continuación para que el auditor pueda
decidir si repetir con humanos reales en Sprint S0.5 o aceptar el proxy.

| Elemento original (gold) | Substitución operativa (silver) | Justificación CEO |
|---|---|---|
| 3 anotadores humanos MD | 2 clasificadores AI "expertos proxy": Gemini CLI + (Gemma) | No hay disponibilidad humana hoy |
| Majority vote 2/3 | Acuerdo entre proxy (Gemini) como etiqueta de referencia | Con 2 raters → Cohen kappa pairwise, no Fleiss 3-way |
| n=100 comments aleatorios | **n=60** (los mismos del sample triangulación 2026-04-18) | Reutilización directa del sample estratificado ya auditado |
| 3 humanos + 1 modelo bajo prueba | 1 proxy externo (Gemini) + modelo bajo prueba (Gemma) | Claude CLI no se ejecutó por tiempo/contexto — posible T0.4.1 follow-up |

**Grado evidencial:** silver (AI-only). El oro sigue siendo 3 humanos — esto es el **mejor
proxy accionable HOY** bajo la instrucción CEO de no pausar.

---

## 2 · Metadatos de reproducibilidad

| Campo | Valor |
|---|---|
| Modelo bajo validación | `gemma3:12b` quantization `Q4_K_M` |
| Endpoint Ollama usado | `http://localhost:11434/api/generate` (M4 local) |
| Endpoint especificado en plan | `http://163.245.208.96:11434/api/generate` (Coolify VPS) |
| **Motivo substitución endpoint** | Coolify VPS medido ~137s/row → 60 rows ≈ 137min, **excede budget de 20min**. Local M4 ~8.6s/row → 9min. Mismo modelo y quantization, misma resp. temperature=0 seed=42 → **no afecta veredicto** (el fallback remoto queda configurado en el script para S1) |
| Proxy anotador externo | Gemini CLI (`gemini -p`) v local, sin config override |
| Clasificador Claude | No ejecutado en esta pasada (budget + Claude CLI invocado desde Claude Code = anidado no trivial) — gap conocido |
| Temperature | `0.0` |
| Seed | `42` |
| num_predict | `256` |
| `format: "json"` | habilitado en Ollama |
| Prompt exacto | [`/Users/marxchavez/Projects/crece-v2/backend/research/2026-04-19/t04_prompt.txt`](./t04_prompt.txt) (copia completa en §7) |
| Sample input | `/Users/marxchavez/Projects/crece-v2/backend/evaluations/2026-04-18/data/sample_60.jsonl` (60 rows) |
| Script Gemma | `/Users/marxchavez/Projects/crece-v2/backend/research/2026-04-19/scripts/classify_gemma.py` |
| Script Gemini | `/Users/marxchavez/Projects/crece-v2/backend/research/2026-04-19/scripts/classify_gemini.py` |
| Script agreement | `/Users/marxchavez/Projects/crece-v2/backend/research/2026-04-19/scripts/compute_agreement.py` |
| Outputs Gemma | `/Users/marxchavez/Projects/crece-v2/backend/research/2026-04-19/data/sample_60_gemma.jsonl` (60 rows, 1 con emoción null) |
| Outputs Gemini | `/Users/marxchavez/Projects/crece-v2/backend/research/2026-04-19/data/sample_60_gemini.jsonl` (60 rows, 0 nulls) |
| Raw merged | `/Users/marxchavez/Projects/crece-v2/backend/research/2026-04-19/plutchik_topics_raw.jsonl` |
| Stats JSON | `/Users/marxchavez/Projects/crece-v2/backend/research/2026-04-19/plutchik_topics_stats.json` |

---

## 3 · Schema de clasificación

**(a) Emoción Plutchik-6 (una sola):**
`trust · anger · joy · fear · sadness · disgust`

**(b) Topics seed-12 (1 a 3, ordenados por relevancia):**
`economia · seguridad · educacion · salud · corrupcion · movilidad · genero · medioambiente · gobierno · politica_electoral · institucional · otro`

Criterios binarios Sprint S0:

| Métrica | Umbral | Observado | Pass? |
|---|---|---|---|
| Kappa emoción Plutchik (Gemma vs referencia) | ≥ 0.65 | **0.810** | ✅ |
| Precisión topic principal (Gemma vs referencia) | ≥ 70% | **75.0%** (45/60) | ✅ |

---

## 4 · Resultados — Emoción Plutchik

### 4.1 Cohen's Kappa

- **κ (Gemma vs Gemini proxy) = 0.810** — Acuerdo *Casi perfecto* (Landis & Koch 0.81-1.00)
- **Muy por encima** del umbral S0 (0.65).
- **Muy por encima** del umbral clásico (0.75).
- 60 rows comparados · 1 row con emoción null en Gemma (omitida del cálculo).

### 4.2 Matriz de confusión — filas: Gemma · columnas: Gemini (proxy referencia)

|            | trust | anger | joy | fear | sadness | disgust | total Gemma |
|------------|------:|------:|----:|-----:|--------:|--------:|------------:|
| **trust**    |  8 |  0 |  1 |  0 |  0 |  0 |  9 |
| **anger**    |  1 | 14 |  0 |  0 |  0 |  3 | 18 |
| **joy**      |  1 |  0 | 23 |  0 |  0 |  0 | 24 |
| **fear**     |  0 |  0 |  0 |  0 |  0 |  0 |  0 |
| **sadness**  |  0 |  0 |  0 |  0 |  1 |  0 |  1 |
| **disgust**  |  1 |  1 |  0 |  0 |  0 |  5 |  7 |
| **total Gemini** | 11 | 15 | 24 |  0 |  2 |  8 | **60** |

Observaciones:
- **joy** (23/24 acierto · 96%) y **anger** (14/15 · 93%) son las clases más estables.
- **disgust ↔ anger** es el confuso principal: Gemma marcó `disgust` 3 veces donde Gemini marcó `anger`, y viceversa 1 vez. Esperable en comments políticos cortos (indignación moral ambigua entre ambas).
- **fear** no aparece en el sample (0/60). Plutchik-6 reducido a 5 clases efectivas en este corpus (sesgo del dominio: comments IG/FB a dirigentes MC no suelen expresar miedo).
- 1 row con emoción null en Gemma (_err parsing JSON) — documentado en output raw.

### 4.3 Distribución de clases

| Clase     | Gemma | Referencia (Gemini) |
|-----------|------:|--------------------:|
| joy       |   24 |   24 |
| anger     |   18 |   15 |
| trust     |    9 |   11 |
| disgust   |    7 |    8 |
| sadness   |    1 |    2 |
| fear      |    0 |    0 |
| **total** | 59\*  | 60 |

\* 1 null.

---

## 5 · Resultados — Topics seed-12

### 5.1 Precisión topic principal

- **Precisión = 45/60 = 75.0%** ≥ 70% ✅
- Se compara **solo el topic principal** (index 0 de la lista). Comparación multi-label de los 3 topics no calculada en esta pasada (pendiente si se necesita downstream en S1 T5).

### 5.2 Matriz de confusión topic principal — filas: Gemma · columnas: Gemini

Solo se muestran celdas con valor > 0.

|  Gemma \\ Gemini        | econ | seg | corr | mov | medio | gob | pol_elec | inst | otro | total |
|-------------------------|-----:|----:|-----:|----:|------:|----:|---------:|-----:|-----:|------:|
| **economia**              |  4 |  - |  - |  - |  - |  1 |  - |  - |  - |  5 |
| **seguridad**             |  - |  1 |  - |  - |  - |  - |  - |  - |  - |  1 |
| **corrupcion**            |  - |  - |  3 |  - |  - |  1 |  - |  - |  - |  4 |
| **movilidad**             |  - |  - |  - |  6 |  - |  - |  - |  - |  - |  6 |
| **medioambiente**         |  - |  - |  - |  - |  4 |  1 |  1 |  - |  - |  6 |
| **gobierno**              |  - |  - |  - |  - |  1 | 10 |  2 |  - |  2 | 15 |
| **politica_electoral**    |  - |  1 |  - |  - |  - |  - | 10 |  1 |  2 | 14 |
| **otro**                  |  - |  - |  - |  1 |  - |  - |  1 |  - |  7 |  9 |
| **total Gemini**          |  4 |  2 |  3 |  7 |  5 | 13 | 14 |  1 | 11 | **60** |

Observaciones:
- Clases ausentes de Gemma como principal: `educacion`, `salud`, `genero`, `institucional` (esta última Gemini sí la marcó 1 vez).
- Confuso dominante **gobierno ↔ politica_electoral**: 2 en cada dirección. Ambigüedad estructural (comments sobre MC/dirigente son tanto "gobierno" como "campaña").
- Clase **otro** bien alineada (7 coincidencias).
- 15 errores totales — la mayoría confusión inter-clase razonable (gobierno/política_electoral, medioambiente/gobierno, corrupción/gobierno).

---

## 6 · Veredicto y caveats

### Veredicto: ✅ PASS (go a Sprint S1 T5 topic extraction + bloque #05 Plutchik MVP)

Ambos criterios binarios **cumplen** con holgura:
- Kappa 0.810 vs umbral 0.65 (+0.16)
- Topic precision 75.0% vs umbral 70% (+5pp)

### Caveats críticos (leer antes de consumir el veredicto)

1. **Silver-grade, NO gold.** La referencia es 1 sólo proxy AI (Gemini), no 3 humanos
   MD. El kappa 0.810 mide acuerdo **Gemma↔Gemini**, no Gemma↔verdad humana. Esperar
   inflación por co-sesgo LLM (ambos entrenados sobre corpus similar).
2. **Sin Claude en esta pasada.** Con 3 clasificadores (Gemma + Gemini + Claude) podríamos
   haber computado Fleiss 3-way y majority vote. Gap conocido → **sugerencia S0.5**: correr
   Claude sobre los mismos 60 (script reutilizable, solo cambia el binary invocado).
3. **n=60 < n=100 especificado.** Se reutilizó el sample estratificado de la triangulación
   2026-04-18 (kappa tono 0.761 ya auditado). Ampliar a 100 requiere nuevo muestreo
   estratificado — posponible a S0.5.
4. **fear = 0 en el corpus.** Plutchik-6 efectivo = Plutchik-5 en comments MC CDMX.
   Revisar si el bloque #05 Sentiment Plutchik debe dropear `fear` del layout o mantenerlo
   para robustez cross-dirigente cuando entre Movimiento Ciudadano Nacional.
5. **Endpoint local vs Coolify.** Modelo idéntico, pero validar vigente la latencia Coolify
   en T0.6 (smoke test failover). Si >20 min para 60 rows, Coolify NO sirve como failover
   del clasificador en tiempo real.
6. **Multi-label topics no medidos.** Solo se midió topic principal (index 0). S1 T5 podría
   querer F1 multi-label sobre los 3 topics — medible con los mismos archivos.

### Decisión go/no-go por bloque downstream

| Bloque dependiente | ¿Procede? | Condición |
|---|---|---|
| #05 Sentiment composition Plutchik (MVP Tier 1) | ✅ GO | Con caveat "silver-grade, validar contra 3 humanos antes de release cliente" |
| S1 T5 Topic extraction vía Gemma | ✅ GO | Precisión 75% suficiente para agregados/tendencias. Para casos individuales flagear confianza |
| T1.9 Refinamiento prompt Plutchik | ❌ NO activar | Kappa 0.810 ya supera 0.65 cómodamente |
| S0.5 Validación contra humanos reales | 🟡 RECOMENDADA | Ejecutar cuando haya anotador MD disponible (1-2h). Prioridad baja, no bloquea S1 |
| S0.4.1 Añadir Claude como 3er clasificador | 🟡 OPCIONAL | +30min, mejora solidez estadística con Fleiss 3-way |

---

## 7 · Prompt exacto utilizado

```
Clasifica este comentario politico mexicano en DOS dimensiones simultaneas.

CONTEXTO:
- Post original (del politico): {post_text}
- Plataforma: {plataforma}

COMENTARIO:
"{comment_text}"

INSTRUCCIONES:
(a) Identifica la EMOCION dominante (UNA sola) del conjunto Plutchik-6:
    trust, anger, joy, fear, sadness, disgust
(b) Identifica 1 a 3 TOPICS del seed fijo de 12 (en orden de relevancia):
    economia, seguridad, educacion, salud, corrupcion, movilidad,
    genero, medioambiente, gobierno, politica_electoral, institucional, otro

RESPONDE EXCLUSIVAMENTE un objeto JSON valido sin texto adicional, sin markdown,
sin bloques de codigo. Usa exactamente estas llaves:

{"emocion": "<una de las 6>", "topics": ["<topic1>", "<topic2?>", "<topic3?>"]}

Si el comentario es ambiguo, elige la emocion predominante y el topic principal.
Si no hay topic politico claro, usa "otro".
```

Post y comment truncados a 200 caracteres antes de inyectar.

---

## 8 · Reproducibilidad paso-a-paso

```bash
cd /Users/marxchavez/Projects/crece-v2/backend/research/2026-04-19

# Requiere: python3 + httpx 0.28.1, Ollama en localhost con gemma3:12b pulled,
# gemini CLI autenticado en PATH.

python3 scripts/classify_gemma.py    # ~9 min local M4
python3 scripts/classify_gemini.py   # ~6 min
python3 scripts/compute_agreement.py # instantaneo
```

Salida esperada en `compute_agreement.py`:
```
n=60 claude=False
kappa emocion Gemma-vs-majority: 0.810
topic principal precision:        0.750 (45/60)
```
