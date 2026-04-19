# Evaluación Triangulación NLP Layer 2 — 2026-04-18

Plan completo: `.context/PLAN-triangulacion-nlp-2026-04-18.md`
Bitácora viva en Obsidian: `productos/gobierno/crece-v2/bitacora/2026-04-18-triangulacion.md`

## Qué es esto

Triangulación 3-way de clasificadores sobre comments de redes sociales:

1. **Gemma3:12b** (local Ollama) — corriendo batch completo ~1,100 comments
2. **Claude Code** (esta sesión) — clasifica muestra stratified 60 comments
3. **Gemini CLI** (local) — clasifica la misma muestra 60

Objetivo: construir golden set silver-grade sin 100h humanas + calibrar matriz v2 (53 reglas).

## Estructura

```
2026-04-18/
├── README.md                  — este archivo
├── data/                      — inputs y outputs raw por clasificador
│   ├── sample_60.jsonl        — muestra stratified
│   ├── sample_60_claude.jsonl — output Claude Code
│   ├── sample_60_gemini.jsonl — output Gemini CLI
│   └── sample_60_gemma.jsonl  — output Gemma extraído del batch
├── scripts/                   — sampler + triangulación
│   ├── stratified_sample.py   — sampler determinista
│   └── triangulate.py         — matriz acuerdo + kappa
├── prompts/
│   └── layer2_triangulation.md — prompt congelado (SHA256 vs runner Gemma)
└── output/
    ├── triangulation_matrix.csv
    ├── agreement_summary.md
    ├── REPORTE-TRIANGULACION.md   — reporte principal
    ├── rule_gaps.md               — Fase 3
    └── PROPUESTA-MATRIZ-V3.md     — Fase 3
```

## Schema unificado

Cada fila de los `sample_60_*.jsonl`:

```json
{
  "id": "X_2044905890109952401",
  "source_model": "claude-opus-4-7 | gemini-cli | gemma3:12b",
  "tono": "elogio | critica | pregunta | ataque | informativo | personal | autopromocion",
  "target": "dirigente_post | gobierno | oposicion | ciudadania | institucion | otros",
  "intensidad": -3,
  "polaridad_preliminar": "aprobacion | neutral | rechazo",
  "razon_corta": "una frase",
  "classified_at": "ISO-8601"
}
```

## Estado al momento de setup

- Gemma corriendo PID 42073, Ollama PID 42077 (runner cargado)
- Output Gemma: `backend/benchmarks/scraping/results/2026-04-19/nlp_layer2_gemma_out.jsonl` (284/~1,100 al arranque de esta evaluación)
- Ritmo observado: ~10 s/item

## Reglas del experimento

1. Claude y Gemini clasifican **sin ver output Gemma** ni entre sí
2. El prompt es idéntico, checksum validado
3. Output normalizado al schema antes de merge
4. Sin retries silenciosos — errores se loggean
5. Idempotente — re-correr `stratified_sample.py` con seed=42 devuelve los mismos 60 IDs
