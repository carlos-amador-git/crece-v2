# DIAGNÓSTICO — NLP local vs LLM, con la data que ya tenemos · 2026-06-12

**Origen:** el CEO objetó la conclusión del agente ("v1 falla → volver a LLM batcheado") por
no estar cross-auditada y por ignorar que la base etiquetada invalida la investigación de abril.
**Proceso:** deep research effort max — Gemini cross-audit (`/tmp/gemini-out-nlp-finetune.md`)
+ literatura externa + fuente interna (`docs/NLP-MODELOS-INVESTIGACION.md`).
**Resultado: el CEO tenía razón. La conclusión de anoche fue prematura.**

## 1. Qué cambió respecto a la investigación de abril (GH)
La Opción B (fine-tune BETO) se descartó en abril por UNA razón: *"requiere dataset etiquetado
que NO tenemos"* (estimaba 2-5k labels manuales = 2-3 semanas). **Ese bloqueo ya no existe:**
hoy hay 9,518 comments con polaridad/tono/target + 7,638 posts con tono/target, etiquetados
por LLM, y la base crece con cada ciclo del pipeline automático.

## 2. Por qué el experimento v1 NO prueba "imposible sin LLM"
- v1 = baseline más débil (MiniLM congelado + LogReg). Gemini: 70% con eso es señal FUERTE,
  no fracaso — "la luz verde para avanzar".
- Literatura: fine-tune completo (RoBERTuito/BETO) sobre el mismo corpus = **+8-15 pts macro-F1**
  → rango esperado **78-83%**.
- La caída held-out (70→56%) NO es fatal: es el modelo "ciego a la entidad". Fix probado en
  target-dependent stance: **inyectar contexto en el input** (`[ENTIDAD: X][PARTIDO: Y] comment…`)
  → generaliza a dirigentes no vistos.

## 3. Los dos techos que la euforia no debe ignorar
- **Acuerdo student-teacher en stance político satura ~82-84%** (ambigüedad intrínseca:
  sarcasmo, albures). El 85-90% como *reemplazo total* es poco probable.
- **El teacher no es ground truth:** si Claude-vs-humano = 90% y local-vs-Claude = 80%,
  el real vs humano ≈ 72%. → **Precondición: correr el gold humano de 100 rows**
  (`backend/scripts/sample_ground_truth_100.py`, existe, NUNCA ejecutado). Si Claude-vs-humano
  < 85%, perseguir 90% local es "perseguir un fantasma".

## 4. La respuesta correcta: CASCADA HÍBRIDA (no el binario local-vs-LLM)
```
comment → RoBERTuito fine-tuned (contexto inyectado) → softmax ≥ T (~0.85 calibrado) → label local ($0)
                                                      → softmax < T → LLM batcheado (solo lo ambiguo)
```
- En redes sociales, **60-70% del tráfico es "obvio"** → se resuelve local a costo ~0.
- El LLM queda solo para el 30-40% difícil → **~60%+ de reducción de costo API** manteniendo
  ≥85% de acuerdo global.
- En VPS corre en CPU (ONNX/quantized, ~400MB RAM). Fine-tune en Mac M4 (MPS), ~6h.
- ADR-0008 NO se tira: su batcheo se convierte en el **tier de fallback** de la cascada.

## 5. Plan de ejecución (Gemini: 12-16h ingeniería · criterios medibles)
| Paso | Qué | Gate de éxito |
|---|---|---|
| 1 (2h) | **Gold humano 100 rows** (CEO/analista etiqueta; script existe) | Claude-vs-humano ≥85% → seguir; si no, recalibrar teacher ANTES |
| 2 (6h) | Fine-tune RoBERTuito en M4/MPS con prefijo de entidad | held-out dirigente ≥78% |
| 3 (2h) | Calibrar umbral T de confianza | acuerdo local-vs-Claude ≥90% en el tramo aceptado |
| 4 (4h) | Inferencia ONNX CPU + ruteo cascada en enrich | ≥60% tráfico resuelto local · costo API −60% |

**¿Esperar más data? NO** — 9.5k es el sweet spot para BERT-style; el retorno marginal de más
labels es menor que el de inyectar contexto.

## 6. Fuentes
- Gemini cross-audit 2026-06-12 (effort max): `/tmp/gemini-out-nlp-finetune.md`
- [Sentiment Analysis in Mexican Spanish: Fine-Tuning vs In-Context Learning (Future Internet 2025)](https://doi.org/10.3390/fi17100445) — fine-tune gana; ICL competitivo en low-resource
- [Fine-Tuning BERT monolingüe es-PE: ~90% acc 3-clases](https://www.tandfonline.com/doi/full/10.1080/08839514.2026.2641381) · [RoBERTuito (pysentimiento)](https://arxiv.org/pdf/2111.09453)
- [Distilling Step-by-Step (teacher-student con menos data)](https://arxiv.org/abs/2305.02301) · [Snorkel: LLM distillation](https://snorkel.ai/blog/llm-distillation-demystified-a-complete-guide/) · [FreeAL: active learning con LLM teacher](https://arxiv.org/pdf/2311.15614)
- Interno: `docs/NLP-MODELOS-INVESTIGACION.md` (abril — supuesto "sin dataset" hoy FALSO)
