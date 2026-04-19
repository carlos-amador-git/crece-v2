# Dictamen 01 — Benchmarks de engagement político MX: investigación empírica

**Fecha:** 2026-04-19
**Autor de la investigación:** agente externo (3.5 horas, 58 tool uses, 18 fuentes con N declarado)
**Archivo original de salida:** `analysis/2026-04-19-benchmarks-engagement-politicos-mx.md`
**Motivo de archivo:** input para la decisión D-19 en CRECE_PRODUCT_MASTER.md §6
**Conclusión estructural:** la tabla 1×5 de Gemini Deep Research es estructuralmente inadecuada para el dominio político mexicano

---

## Hallazgo crítico principal

La tabla 1×5 del Gemini Deep Research es estructuralmente inadecuada. Asume ER único por estrato sin desagregar plataforma, pero la evidencia empírica muestra que TikTok > IG ≈ FB-gov > X por factor 3–10x. Una tabla 1×5 induce falsos positivos en TikTok y falsos negativos en X/FB.

## Evidencia por estrato

| Estrato | Rango original Gemini DR | Evidencia recuperada |
|---|---|---|
| Nano (1K–10K) | 6–10% | 🔴 Sin datos MX políticos directos |
| Micro (10K–50K) | 3.5–6% | 🔴 Sin datos MX políticos directos |
| Mid-Tier (50K–100K) | 2–4% | 🟡 Parcial — mantener |
| Macro (100K–500K) | 1.5–2.5% | 🟢 Gálvez FB 2024 ~2.2% por post |
| Mega (500K+) | 1–2% | 🟢 AMLO/RAC/JAMK 2018 X ~0.45–0.66%; Sheinbaum IG 2024 ~1.65% |

## Recomendación priorizada

1. **Reemplazar por matriz 5×5** (estrato × plataforma) — propuesta en Sección 3 del archivo original
2. **Si se mantiene 1×5** — ajustes: Nano 6–10% → 3–7%; Micro 3.5–6% → 2–4.5%; Macro 1.5–2.5% → 1–2.5%; Mega 1–2% → 0.5–1.8%
3. **Follow-up alto valor / bajo esfuerzo:** descargar dataset Zenodo 10.5281/zenodo.7877001 (15M tweets MX 2021) y recalcular ER por tier — primer benchmark MX reproducible

## Gaps explícitos (no fabricados)

- Nano y Micro políticos MX: cero evidencia pública directa
- 6 pendientes documentados con costo/valor en sección final del archivo original

## Estado del dictamen

Investigación completada. Archivo consumido por D-19 del MASTER como evidencia para reemplazo estructural de la tabla Gemini DR.
