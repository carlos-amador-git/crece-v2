# Reporte — Acuerdo inter-anotador de las 3 evaluaciones humanas (Benchmark Layer 2)

**Recuperado 2026-06-12** (regla 13 REGLAS.md §5.1 — vivían en Downloads/Drive/disco externo,
fuera del repo). Archivos: `persona_1/2/3.xlsx` (ejercicio ~abril 2026, 4º evaluador=CEO sin
archivo localizado). 54 items con respuesta de los 3 (49 comments + 5 posts), campos tono+target.

## Números (n=54, medidos 2026-06-12)

| Par | Tono (11 clases) | Target (7 clases) |
|---|---|---|
| h1–h2 | 59% | **78%** |
| h1–h3 | 49% | 45% |
| h2–h3 | 51% | 47% |

- Mayoría humana (2-de-3) existe en 48/54 items de tono.
- **Cruce vs labels LLM actuales: NO viable** — los `id` eran PKs de BD de abril; tras los
  re-ingests solo 10/54 validan por texto, y con cambio de taxonomía de era (n inservible).
- **Cruce vs triangulación IA 04-18: NO viable** — 1/51 matchea por texto (fue otro muestreo).

## Lecciones (para el siguiente ejercicio)

1. **El techo humano en tono-11-clases es ~50%.** Exigir 85-90% a un modelo contra "verdad
   humana" con esta taxonomía es incoherente: la verdad misma trae ±50% de ruido. La
   granularidad fina de tono es para el mapper (que la colapsa), no para evaluar acuerdo.
2. **h3 diverge sistemáticamente** (45-49% vs todos) — en el próximo ejercicio: sesión de
   calibración de 10 ejemplos antes de soltar el Excel.
3. **Claves estables obligatorias:** el Excel debe llevar `platform_comment_id` (estable entre
   re-ingests), NUNCA el PK de BD.
4. **Evaluar polaridad (3 clases), no tono (11):** es el campo que gobierna el score político
   y donde el acuerdo humano será medible y útil como gate del teacher.
