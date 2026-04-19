# Acuerdo triangulación NLP Layer 2 — 2026-04-18

- Claude rows: 60
- Gemini rows: 60
- Gemma rows:  60
- Common IDs (usados en kappa): 60

## Acuerdo por dimensión (sobre common IDs)

| Dimensión | 3/3 | 2/3 | divergence | Cohen C-G | Cohen C-M | Cohen G-M | Fleiss 3-way |
|---|---:|---:|---:|---:|---:|---:|---:|
| tono | 44 | 15 | 1 | 0.743 | 0.742 | 0.802 | 0.761 |
| target | 38 | 20 | 2 | 0.509 | 0.331 | 0.434 | 0.418 |
| polaridad_preliminar | 46 | 14 | 0 | 0.713 | 0.679 | 0.856 | 0.744 |
| intensidad (bucket) | 50 | 10 | 0 | 0.772 | 0.767 | 0.877 | 0.803 |

## Interpretación kappa (Landis & Koch)

- `<0.00` sin acuerdo · `0.00–0.20` ligero · `0.21–0.40` aceptable · `0.41–0.60` moderado · `0.61–0.80` sustancial · `0.81–1.00` casi perfecto

## Errores por modelo (rows con _err)

- **claude**: 0 errores
- **gemini**: 0 errores
- **gemma**: 0 errores