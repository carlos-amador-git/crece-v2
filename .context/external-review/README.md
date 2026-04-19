# External Review — Trazabilidad de dictámenes externos

Esta carpeta acumula los dictámenes, revisiones y auditorías externas (Claude.ai, Gemini, terceros) que modifican decisiones en el MASTER. Cada dictamen queda archivado tal cual se recibe, sin edición, para preservar trazabilidad y poder reconstruir el razonamiento detrás de cada decisión en el Decision Log de MASTER §6.

## Convención de nombrado

```
<tipo>-<NN>-<tema-corto>.md
```

- `tipo`: `dictamen` (external review estructurado), `audit` (review técnico), `propuesta` (diseño a incorporar), `seccion` (sección redactada externamente)
- `NN`: ordinal del tipo (01, 02, 03...)
- `tema-corto`: kebab-case descriptivo

## Referencias desde MASTER

Cuando una decisión en MASTER §6 se fundamenta en un dictamen externo, debe citarlo en la columna `Ref` con la ruta relativa exacta:

```
| D-NN | ... | ... | `.context/external-review/<archivo>.md` · ... |
```

## Índice actual (2026-04-19)

| Archivo | Origen | Fecha | Dispara |
|---|---|---|---|
| `PLAN-MAESTRO-CRECE-V2.docx` + `.txt` | Claude.ai Opus 4.7 | 2026-04-19 | Puerta 1 del MASTER v2 |
| `propuesta-d17-consolidada.md` | Claude.ai Opus 4.7 | 2026-04-19 | D-17 (cierre ciclo Plan IA) |
| `seccion-2-5-economia-conductual.md` | Claude.ai Opus 4.7 | 2026-04-19 | §2.6 Behavioral Economics |
| `dictamen-01-gemini-dr-im-origin.md` | 🟡 **pendiente pegar contenido** | 2026-04-19 | D-19 reescrita (reemplazo estructural Gemini DR) |
| `dictamen-02-gemini-dr-im-origin.md` | 🟡 **pendiente pegar contenido** | 2026-04-19 | D-19 reescrita (reemplazo estructural Gemini DR) |

## Hallazgo convergente de los 2 dictámenes (resumen CEO 2026-04-19)

Ambos dictámenes convergen en que la tabla 1×5 de estratos ER de Gemini Deep Research (Nano 6-10% · Micro 3.5-6% · Mid-Tier 2-4% · Macro 1.5-2.5% · Mega 1-2%) se deriva de benchmarks de Influencer Marketing y branded social (Hootsuite · Rival IQ · Emplifi · Sprout Social — ver MASTER §8.7 líneas 916-919) que miden engagement de marcas comerciales y creadores de entretenimiento, NO actores políticos mexicanos sujetos a movilización electoral, polarización afectiva y veda INE.

**Conclusión operativa:** el error no es de cuantificación (no es adopción provisional con recalibración) sino de ORIGEN (dominio equivocado). Se descarta estructuralmente en D-19 reescrita y se reemplaza por:

1. Matriz 5×5 estrato × plataforma (MASTER §3.1 #01) con celdas 🟡 TBD hasta calibración interna
2. Factor temporalidad electoral (multiplicador hasta 2.5× en ventana 90d pre-comicio)
3. Perfil `figura_precampaña` (§1.5) consume benchmarks con modificador temporal **on** por default
4. Dataset Zenodo reproducible (Sprint S1 T10) como ground-truth propio que sustituye la tabla IM a 3-6 meses

## Pendiente de archivo completo

Los dictámenes originales completos (con metodología, fuentes citadas, análisis bibliográfico que triangulen Hootsuite/Rival IQ/Emplifi/Sprout Social → tabla Gemini DR) deben pegarse en los archivos:

- `.context/external-review/dictamen-01-gemini-dr-im-origin.md`
- `.context/external-review/dictamen-02-gemini-dr-im-origin.md`

Mientras ese contenido completo no esté archivado, la trazabilidad de D-19 reescrita queda apoyada sólo en el resumen CEO de arriba. El PR de esta corrección debe quedar mergeado solo cuando los dos archivos contengan el texto completo de cada dictamen.
