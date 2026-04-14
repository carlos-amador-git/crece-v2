# Investigación de Modelos NLP para CRECE — Estado Real

**Fecha doc:** 2026-04-13
**Razón:** El CEO preguntó dónde quedó la revisión de modelos NLP políticos. La investigación **SÍ se hizo** y **SÍ se integró código**, pero **NUNCA se documentó**. Este doc recupera el estado real.

---

## Modelos YA integrados en el código (no documentados)

**Ubicación:** `backend/app/nlp/huggingface_models.py` (commit `21e23bf`, 2026-04-03)
**Orquestador:** `backend/app/nlp/analyzer.py` → función `analyze_full()`

### Los 6 modelos disponibles HOY

| # | Dimensión | Modelo | Propósito |
|---|---|---|---|
| 1 | Sentiment primario | `pysentimiento/robertuito-sentiment-analysis` | POS/NEG/NEU en español — base para twitter/IG |
| 2 | Sentiment secundario | `finiteautomata/bertweet-sentiment-spanish` (CNN) | Cross-validación — reduce falsos positivos |
| 3 | Emotion | pysentimiento emotion | joy, anger, sadness, surprise, fear, disgust, others |
| 4 | Hate speech | pysentimiento hate_speech | Detección de discurso de odio |
| 5 | **Controversy** | **`cardiffnlp/twitter-roberta-base-offensive`** | Específico Twitter, mide ofensa/controversia |
| 6 | **Toxicity** | **`citizenlab/distilbert-base-multilingual-cased-toxicity`** | Multilingual, robusto para español |
| 7 | **Topics (zero-shot)** | **`joeddav/xlm-roberta-large-xnli`** | Clasifica en 8 temas políticos pre-definidos |

### 8 temas políticos pre-configurados

`POLITICAL_TOPICS` en `huggingface_models.py:23`:
- campaña, gobierno, seguridad, economía, salud, educación, corrupción, medio_ambiente

### Normalización por sesgo de plataforma

**Ubicación:** `backend/app/nlp/platform_weights.py`

Coeficientes derivados de investigación sobre sesgo de redes sociales:

| Plataforma | Corrección sentiment | Peso confianza | Normalización engagement |
|---|---|---|---|
| Twitter | +0.08 (contra sesgo negativo) | 0.85 | 1.00 base |
| Instagram | -0.06 (contra sesgo positivo) | 0.70 (captions cortos) | 0.60 |
| Facebook | -0.04 | 0.90 (posts largos más confiables) | 0.80 |
| TikTok | 0.00 | 0.60 (captions cortos visual) | 0.40 |
| YouTube | +0.03 | 0.80 | 1.20 |
| Bluesky | 0.00 (data insuficiente) | 0.75 | 1.00 |

---

## Problema REAL descubierto por la auditoría

**Los 3,709 posts de la DB fueron analizados con `analyze()` básico, NO con `analyze_full()`.**

Esto significa:
- ✅ Tenemos sentiment + emotion (pysentimiento)
- ❌ NO tenemos controversy_score
- ❌ NO tenemos toxicity_score
- ❌ NO tenemos topics
- ❌ NO aplicamos platform-adjusted sentiment

**Action item #1:** Re-procesar los 3,709 posts con `analyze_full()` + persistir los campos nuevos.

---

## ¿Necesitamos un modelo político específico para México?

### Estado del arte (modelos disponibles en HuggingFace 2026)

**Modelos de sentimiento político mexicano específicos:**
- ❌ **No existe** uno público fine-tuneado sobre discurso político mexicano
- ❌ Pysentimiento/RoBERTuito: entrenado en tweets generales en español
- ❌ Cardiff NLP offensive: mejor que pysentimiento para detectar ataques/insultos pero agnóstico a contexto político
- ❌ Citizenlab toxicity: excelente para toxicidad pero no distingue crítica política legítima de toxicidad

### Opciones reales para mejorar

#### Opción A — LLM contextualizado (fácil, costoso)
**Prompt a Gemma3:12b local** con contexto de rol político:

```
Eres analista de comunicación política. Dado este post del dirigente {nombre}
({rol: oficialismo|oposición|independiente}), clasifica:

1. Tono discursivo: {crítico|propositivo|celebratorio|informativo|solidario|ataque}
2. Target: {gobierno|oposición|ciudadanía|medios|auto-promoción|tema específico}
3. Es RT/amplificación de terceros? SI/NO
4. Relevancia política (0-10): qué tan político es vs personal/trivial
5. Imagen proyectada para el dirigente: {+2|+1|0|-1|-2}

Texto: {content}

Responde SOLO JSON:
{
  "tono": "...",
  "target": "...",
  "es_rt": bool,
  "relevancia_politica": int,
  "imagen_dirigente": int,
  "razon_breve": "..."
}
```

**Ventaja:** Entiende contexto, distingue "oposición criticando" de "víctima de ataque", separa amplificación de contenido propio.
**Costo:** ~3-5 seg por post local en Mac M-series, ~2 min por lote de 30. Total 3,709 posts ≈ 4-5 horas en Mac local.
**Dependencia:** Ollama + Gemma3:12b (ya instalado).

#### Opción B — Fine-tune BETO sobre corpus etiquetado
Requiere dataset etiquetado que NO tenemos. Estimación: 2,000-5,000 posts etiquetados a mano por analista MC = 2-3 semanas de trabajo manual.

#### Opción C — Cardiff NLP específico para Spanish political
Existe `VictorAtPL/spanish-political-tweets-ner` pero es NER (entidades), no sentiment. No encontramos un sentiment político mexicano público.

---

## Recomendación

**Ejecutar las 3 en orden:**

1. **Inmediato:** Re-procesar con `analyze_full()` existente → 7 dimensiones adicionales
2. **Sprint siguiente:** Opción A — LLM contextualizado con Gemma local. El prompt de arriba es el punto de partida para iterar.
3. **Deuda larga:** Opción B si en el roadmap real se busca precisión nivel producción

---

## Prompt para research externo (pedir review a Gemini)

```
Necesito validar mi stack NLP para análisis de discurso político mexicano en redes sociales.

Contexto:
- 3,709 posts scrapeados de 6 dirigentes (MC oposición, MORENA oficialismo, gobierno Oaxaca)
- Posts de Twitter, IG, FB, TikTok
- Plataforma: CRECE v2.0 — inteligencia política

Stack actual:
- pysentimiento/robertuito-sentiment (POS/NEG/NEU español)
- cardiffnlp/twitter-roberta-base-offensive (controversy)
- citizenlab/distilbert-base-multilingual-cased-toxicity
- joeddav/xlm-roberta-large-xnli (zero-shot topics)
- Platform bias coefficients (Twitter +0.08, IG -0.06, etc.)

Problema encontrado en auditoría:
- Sentimiento técnico (texto) != imagen política. Dirigente opositor criticando gobierno → NEGATIVE pero es estrategia válida, no imagen negativa.
- 29-52% de tweets son RTs — contenido ajeno contamina score.
- Posts duplicados cross-platform (FB+IG+TW del mismo contenido) cuentan 3-4 veces.

Preguntas:
1. ¿Existe un modelo en HuggingFace 2026 fine-tuneado específicamente sobre discurso político mexicano o latinoamericano que deba considerar?
2. ¿Alternativas al zero-shot topic classifier con mejor precisión para política MX?
3. Para distinguir "sentimiento del discurso" vs "sentimiento hacia el dirigente" (comments), ¿qué approach recomiendas sin tener que re-scrapear todos los comments?
4. ¿Conoces benchmarks públicos para evaluar modelos de sentiment político en español?
5. Opción A de LLM local (Gemma3 12B) con prompt contextualizado — ¿es la mejor opción o hay algo más eficiente que me estoy perdiendo?

Enfoque: calidad real de señal > velocidad. CEO valora insights correctos sobre métricas planas.
```

---

---

## Validación externa (Gemini 2.5 Flash, 2026-04-13)

Le pregunté a Gemini por modelos específicos. Sus respuestas + verificación anti-alucinación:

| Modelo sugerido | Existe en HF? | Verdad |
|---|---|---|
| `BSC-TeMU/roberta-base-spanish-political-tweets` | ❌ 401 | **Alucinación** |
| `dccuchile/bert-base-spanish-wwm-cased-finetuned-mlsum-sentiment` | ❌ Modelo base sí, fine-tune NO | **Alucinación parcial** |
| `Aylén/LatAm-BERT` | ❌ 401 | **Alucinación** |
| `finiteautomata/beto-sentiment-analysis` (ya conocido) | ✅ 200 | Existe pero no político |

**Conclusión verificada:** No existe modelo público fine-tuneado sobre discurso político mexicano. Gemini tiende a alucinar nombres plausibles en este dominio.

### Confirmaciones útiles de Gemini

- **NER + prompting con LLM** es la ruta correcta para distinguir "sentimiento del discurso" vs "hacia el político": detectar entidades políticas en el texto y luego prompt al LLM inferir sentimiento dirigido.
- **TASS** (Taller de Análisis de Sentimientos en Español) tiene datasets históricos útiles para benchmarking. **SemEval-2017 Task 4** tuvo track español.
- **Plan Gemma3:12b con prompt contextualizado = correcto.** Es la ruta pragmática que supera las limitaciones actuales.

### Benchmarks públicos útiles confirmados

- **TASS** (IberLEF Workshop): datasets históricos, disponibles bajo solicitud académica
- **SemEval-2017 Task 4** track español: tweets clasificados POS/NEG/NEU
- **Datasets de elecciones** publicados por papers académicos (requieren búsqueda caso por caso)

---

## Deuda documental rescatada

Archivos que debieron existir desde que se hizo la investigación (commit `21e23bf` del 2026-04-03):

- ❌ `docs/NLP-MODELOS-INVESTIGACION.md` (este — creado hoy 2026-04-13, 10 días tarde)
- ❌ `docs/PLATFORM-BIAS-RESEARCH.md` (documentar origen de coeficientes de platform_weights.py)
- ❌ `docs/ANALYZE-FULL-ROLLOUT.md` (por qué `analyze_full()` existe pero no se usa en producción)

**Acción:** crear los tres docs antes de seguir con más NLP work.
