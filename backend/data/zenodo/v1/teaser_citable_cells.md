# Teaser — celdas representativas para citación académica

**Licencia de esta publicación subset:** CC BY 4.0
**Licencia del bundle completo:** ver `LICENSE.md` (modelo híbrido)
**Fecha:** 2026-04-19
**Autor:** MD Consultoría SC — CRECE v2 team

---

## Propósito

Este archivo publica un subconjunto de **3 celdas representativas** del dataset privado `benchmarks_er_politicos_mx_v1.csv`. El objetivo es enable academic citation of the core empirical finding —la sobre-estimación masiva de la tabla comercial de Influencer Marketing cuando se aplica al dominio político mexicano— sin liberar la tabla calibrada completa como open data.

Las 3 celdas se eligieron por representatividad metodológica: cada una ilustra un orden de magnitud distinto de divergencia (10×, 40×, 100×) respecto a los benchmarks IM commercial adoptados erróneamente por Gemini Deep Research (§8.7 MASTER CRECE v2 + dictamenes 01 y 02 del 2026-04-19).

---

## Celdas publicadas

### Celda 1 · Nano X — divergencia ~100×

| Atributo | Valor |
|---|---|
| Estrato | Nano (<10K followers) |
| Plataforma | X (Twitter) |
| n_observaciones | 316 |
| ER percentil 25 | 0.013 % |
| **ER percentil 50 (mediana)** | **0.068 %** |
| ER percentil 75 | 0.213 % |
| Intervalo confianza 95% p50 | [0.056, 0.079] % |
| Ventana observación | 2026-01-19 → 2026-04-19 (90 días) |
| Status | VALIDATED |
| Comparación con Gemini DR (IM commercial) | 6-10% esperado → **~100× sobre-estimación** |

### Celda 2 · Nano Instagram — divergencia ~11×

| Atributo | Valor |
|---|---|
| Estrato | Nano (<10K followers) |
| Plataforma | Instagram |
| n_observaciones | 161 |
| ER percentil 25 | 0.296 % |
| **ER percentil 50 (mediana)** | **0.540 %** |
| ER percentil 75 | 1.134 % |
| Intervalo confianza 95% p50 | [0.472, 0.734] % |
| Ventana observación | 2026-01-19 → 2026-04-19 (90 días) |
| Status | VALIDATED |
| Comparación con Gemini DR | 6-10% esperado → **~11× sobre-estimación** |

### Celda 3 · Micro TikTok — divergencia ~3-5× (menor)

| Atributo | Valor |
|---|---|
| Estrato | Micro (10K-50K followers) |
| Plataforma | TikTok |
| n_observaciones | 155 |
| ER percentil 25 | 0.593 % |
| **ER percentil 50 (mediana)** | **1.163 %** |
| ER percentil 75 | 1.896 % |
| Intervalo confianza 95% p50 | [0.993, 1.307] % |
| Ventana observación | 2026-01-19 → 2026-04-19 (90 días) |
| Status | VALIDATED |
| Comparación con Gemini DR | 3.5-6% esperado → **~3-5× sobre-estimación** |

---

## Interpretación

Las 3 celdas confirman la predicción del Dictamen 01: la divergencia respecto a los benchmarks IM commercial varía por plataforma en el orden **TikTok > Instagram ≈ Facebook-gov > X por factor 3–10×**. El empírico MX confirma el ordenamiento y precisa los factores:

- **TikTok** (Celda 3) es la plataforma donde el ER político MX más se acerca a los benchmarks IM (~3-5×) — consistente con que TikTok favorece viralidad orgánica que neutraliza parcialmente el sesgo de audiencia política pasiva
- **Instagram** (Celda 2) muestra ~11× divergencia — las audiencias políticas en IG son informativas pero participan visualmente (like) más que X
- **X** (Celda 1) exhibe la divergencia más severa (~100×) — las audiencias políticas en X son altamente pasivas / informativas, con comentarios concentrados en cuentas verificadas y polémicas de alto perfil

---

## Citación sugerida

```bibtex
@misc{crece_v2_teaser_2026,
  title        = {Engagement rate benchmarks for Mexican political accounts — teaser cells v1},
  author       = {MD Consultoría SC},
  year         = {2026},
  publisher    = {Zenodo},
  howpublished = {DOI: TBD · License: CC BY 4.0 (subset) · Methodology: Apache 2.0 (see repository)},
  url          = {https://github.com/MarxCha/crece-v2/tree/main/backend/data/zenodo/v1},
  note         = {Full calibrated dataset proprietary; see LICENSE.md dual-track model.}
}
```

---

## Licencia de este archivo

Esta publicación se libera bajo CC BY 4.0. Las 3 celdas mostradas pueden citarse libremente en contextos académicos y comerciales con atribución a MD Consultoría SC. El dataset completo con 25 celdas permanece propietario bajo Track B del `LICENSE.md`.

Ver `LICENSE.md` para el texto completo del modelo de licencia híbrida.
