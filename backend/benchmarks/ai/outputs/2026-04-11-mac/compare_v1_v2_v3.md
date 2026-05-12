# Benchmark Compare — alejandro_piña_medina_diagnostico

**Test case:** `alejandro_piña_medina_diagnostico.json`
**Outputs comparados:** 3

## Scores por rúbrica

| Output | Total | Coverage | Specificity | Factual | Compliance | Length | Hallucinations |
|--------|-------|----------|-------------|---------|------------|--------|----------------|
| `iter_04_ollama.md` | **81.1** | 100.0 | 63 | 61.0 | 100.0 | 85.6 | 85.0 |
| `iter_05_ollama.md` | **80.4** | 100.0 | 63 | 66.0 | 100.0 | 83.1 | 75.0 |
| `iter_06_ollama.md` | **70.7** | 100.0 | 49 | 30.0 | 100.0 | 86.6 | 75.0 |

## Notas por output

### iter_04_ollama.md
- words=1284
- specific_patterns=9 generic_patterns=0
- números sin match en contexto: ['2024', '0272', '3449', '1648', '8889', '3446', '0272', '3449', '8889', '8889']

### iter_05_ollama.md
- words=1247
- specific_patterns=9 generic_patterns=0
- números sin match en contexto: ['0272', '3449', '1648', '8889', '3446', '000', '5000', '0272', '3449', '8889']
- handles desconocidos: ['@martibatres']

### iter_06_ollama.md
- words=1299
- specific_patterns=7 generic_patterns=0
- números sin match en contexto: ['674', '0272', '3449', '290', '1648', '800', '8889', '3446', '0272', '3449']
- handles desconocidos: ['@martibatres']

## Gap análisis

- **Baseline:** `iter_04_ollama.md` = 81.1
- **Referencia:** `iter_06_ollama.md` = 70.7
- **Brecha:** -10.4 puntos

### Dimensiones donde baseline está más atrás
- `length`: +1.0
- `coverage`: +0.0
- `compliance`: +0.0
- `hallucinations`: -10.0
- `specificity`: -14.0
- `factual`: -31.0