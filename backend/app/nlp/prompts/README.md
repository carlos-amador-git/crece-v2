# Prompts productivos del pipeline IA de CRECE v2

Este directorio contiene los **prompts ganadores** de los loops de benchmark
ejecutados en `backend/benchmarks/ai/`. Son los prompts que `plan_generator` y
`content_factory` deben usar contra los LLMs en producción.

## Archivos

### `diagnostico_winner.md`

Prompt ganador del loop S2.6 (Sprint 2, 2026-04-11) para generación de
diagnósticos digitales de dirigentes.

- **Fuente:** idéntico a `backend/benchmarks/ai/prompts/diagnostico_v1.md`
- **Score medido contra gemma3:12b + test case real de Piña Medina:** 81.1 / 100
- **Iteraciones probadas:** v1 (baseline, 81.1), v2 (80.4), v3 (70.7)
- **Conclusión:** v1 baseline ganó el loop. Las iteraciones v2/v3 con
  instrucciones más estrictas (longitud mínima, formato literal,
  anti-hallucination) **empeoraron** el score porque:
  1. Gemma ignora instrucciones numéricas de longitud
  2. Más instrucciones → más superficie para alucinación (v2 y v3 inventaron
     `@martibatres` a pesar de la regla explícita de NO usar @handles)
  3. Formato literal rígido comprimió las recomendaciones y redujo los
     patrones específicos que la rúbrica detecta (9 → 7)

## Flujo de actualización

Cuando se quiera iterar sobre el prompt ganador:

1. Copiar `diagnostico_winner.md` → `backend/benchmarks/ai/prompts/diagnostico_v{N+1}.md`
2. Aplicar cambios experimentales en el archivo v{N+1}
3. Correr `python -m benchmarks.ai.runner --prompt prompts/diagnostico_v{N+1}.md ...`
   contra los 4 test cases reales (Piña + Solano × diagnostico + consolidacion)
4. Correr `python -m benchmarks.ai.compare` vs v1/v2/v3/current_winner
5. Si el nuevo candidato supera el winner en ≥2 dimensiones del rubric:
   - Actualizar `diagnostico_winner.md` con el nuevo contenido
   - Bump de versión en este README
   - Documentar en `.context/DECISIONS.md`
6. Si NO supera: mantener el actual y documentar los learnings.

## Limitaciones conocidas del rubric de benchmark

Documentadas como follow-up en el cierre del Sprint 2:

- **`_score_factual` falso positivo con decimales:** el regex `\b\d{3,}\b`
  extrae `0272` del output cuando el context tiene `0.0272` como float. Los
  ~10 "números sospechosos" reportados en todos los outputs reales son
  fragmentos de decimales legítimos, no alucinaciones. Impacto: el score
  Factual subestima entre -30 y -35 puntos.
- **`_score_specificity` patrones muy estrechos:** solo 6 regex patterns
  detectan "frecuencia", "hora", "responsable", "MXN", "meta" — muchas
  formas válidas de expresar especificidad quedan fuera. El score real de
  Gemma es probablemente más alto en calidad subjetiva que lo que la rúbrica
  captura.
- **`_score_hallucinations`:** solo detecta handles @-prefijados. No detecta
  alucinaciones de números, fechas, o afirmaciones factuales.

Antes de invertir en otro loop de prompt iteration, **arreglar estas tres
limitaciones del rubric** — si no, cualquier mejora real de prompt puede
parecer empate o pérdida solo por ruido de medición.
