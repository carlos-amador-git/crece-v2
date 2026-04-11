# CRECE v2 — Benchmark de Prompts IA

Runner reproducible para comparar Gemma local vs Claude vs Gemini sobre los mismos
prompts, con rúbrica determinista de 6 dimensiones y loop de mejora continua.

## Uso

```bash
# Generar/refrescar test cases desde DB real (Piña y Solano)
python -m benchmarks.ai.build_test_cases

# Ejecutar un benchmark contra un prompt
python -m benchmarks.ai.runner \
    --prompt prompts/diagnostico_v1.md \
    --test-case test_cases/pina_diagnostico.json \
    --providers ollama,claude

# Comparar dos outputs con la rúbrica
python -m benchmarks.ai.compare \
    --baseline outputs/2026-04-11/iter_01_ollama.md \
    --reference outputs/2026-04-11/iter_01_claude.md \
    --out outputs/2026-04-11/compare_01.md
```

## Estructura

```
backend/benchmarks/ai/
├── prompts/          # Prompts versionados (v1, v2, ...) — fuente de verdad
├── test_cases/       # JSON con contexto real de Piña/Solano desde DB
├── outputs/          # Un subdir por fecha con iter_N_{provider}.md + compare_N.md
├── rubric.py         # Rúbrica 0-100 por 6 dimensiones
├── runner.py         # Envía prompt + test_case a los providers configurados
├── compare.py        # Side-by-side scoring + diff
├── build_test_cases.py  # Genera JSON desde DB real (reutiliza _gather_context)
└── loop.py           # Orquesta 3+ iteraciones con feedback
```

## Rúbrica (6 dimensiones, 0-100 cada una)

1. **Cobertura de temas** — ¿cubre las 10 secciones obligatorias del prompt?
2. **Especificidad accionable** — ¿las recomendaciones tienen frecuencia/formato/responsable concretos?
3. **Adherencia a hechos CRECE** — ¿usa los números reales del test case sin inventar?
4. **Compliance INE** — ¿respeta veda, disclosure IA, no menciona gastos no trazables?
5. **Longitud** — ¿está en rango [1500, 6000] palabras? Penaliza fuera de rango.
6. **Ausencia de alucinaciones** — ¿inventa métricas o datos no presentes en el test case?

Las dimensiones 1, 2, 5 son **deterministas** (regex + conteo).
Las dimensiones 3, 4, 6 requieren **LLM judge** (Claude o Gemini como árbitro).

## Loop de mejora continua

1. `prompts/diagnostico_v{N}.md` se envía a Gemma local
2. Mismo prompt a Claude (referencia) + `/gemini analyze` opcional
3. `compare.py` genera diff + scores
4. Humano (o agente) edita `prompts/diagnostico_v{N+1}.md` basado en gaps
5. Repetir hasta convergencia (mejora <5 puntos entre iteraciones)
