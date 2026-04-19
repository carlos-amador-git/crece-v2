---
title: "Benchmarks ER políticos mexicanos — CRECE v2 v1"
upload_type: dataset
publication_date: "2026-04-19"
creators:
  - name: "MD Consultoría SC"
    affiliation: "MD Consultoría TI · CRECE v2 team"
    orcid: null
  - name: "CRECE v2 team"
    affiliation: "MD Consultoría SC"
    orcid: null
description: >
  Benchmarks de Engagement Rate (ER) para actores políticos mexicanos, desagregados
  por estrato (Nano / Micro / Mid / Macro / Mega) y plataforma (X / Instagram /
  Facebook / TikTok / YouTube). Primer dataset MX político reproducible con DOI
  asignable. Reemplaza estructuralmente las tablas comerciales de Influencer
  Marketing (Hootsuite, Rival IQ, Influencer Marketing Hub, Emplifi, Sprout
  Social) que no reflejan el comportamiento del universo político-gubernamental
  mexicano. Ver methodology.md para metodología completa y limitaciones.
license: CC-BY-4.0
access_right: open
keywords:
  - political-communication
  - mexico
  - engagement-rate
  - benchmark
  - CRECE-v2
  - social-media-analytics
  - political-campaigns
  - influencer-marketing
  - data-journalism
communities: []
related_identifiers:
  - identifier: "10.5281/zenodo.7877001"
    relation: references
    resource_type: dataset
    description: "Dataset académico MX de referencia — 15M tweets MX 2021 (validación cruzada)"
version: "1.0-preliminar"
language: spa
---

# Benchmarks ER políticos mexicanos — CRECE v2 v1

**Estado:** v1 preliminar · calibración abierta
**Fecha de corte:** 2026-04-19
**Licencia:** [CC BY 4.0](./LICENSE.md) (permite uso comercial derivado con atribución)
**DOI:** TBD (asignable en publicación)

---

## Qué contiene este bundle

| Archivo | Descripción |
|---|---|
| `README.md` | Este archivo · frontmatter Zenodo + resumen ejecutivo |
| `methodology.md` | Metodología completa (9 secciones · 6-10 páginas) |
| `benchmarks_er_politicos_mx_v1.csv` | Matriz 5×5 estrato × plataforma con percentiles p25/p50/p75 e IC 95% |
| `LICENSE.md` | Texto completo de CC BY 4.0 |
| `_calibration_log.json` | Metadata de la ejecución del script generador (timestamp · n_dirigentes · n_observaciones · celdas_validated) |
| `code.zip` | **NO se incluye físicamente** · se genera automáticamente via `scripts/generate_zenodo_bundle.py` del repo fuente (ver §Reproducibilidad) |

---

## Por qué este dataset existe

Dos dictámenes externos (agentes independientes · 2026-04-19) convergieron en un hallazgo crítico: las tablas de benchmarks de ER políticos que circulan en el mercado comercial son adaptaciones casi textuales de los rangos de **Influencer Marketing para creadores de retail / estilo de vida** — no reflejan el comportamiento de perfiles políticos mexicanos. Los políticos sufren niveles más altos de audiencia pasiva (seguidores informativos, no interactivos), una distribución cross-plataforma muy asimétrica (TikTok > IG ≈ FB-gov > X por factor 3-10×), y un ciclo temporal electoral que no está modelado en benchmarks comerciales.

Este dataset es la respuesta estructural de CRECE v2: un bundle reproducible propio, con DOI asignable, actualización periódica, y metodología pública que cualquier investigador puede replicar.

Ver [`methodology.md`](./methodology.md) §1 para discusión completa del gap de mercado.

---

## Estructura del CSV

```
estrato,plataforma,n_observaciones,er_p25,er_p50,er_p75,ic95_low,ic95_high,ventana_inicio,ventana_fin,status
```

- **estrato**: Nano / Micro / Mid / Macro / Mega (cortes definidos en methodology §3)
- **plataforma**: X / Instagram / Facebook / TikTok / YouTube
- **n_observaciones**: número de posts que contribuyen a la celda
- **er_p25, er_p50, er_p75**: percentiles 25/50/75 del Engagement Rate (porcentaje 0-100)
- **ic95_low, ic95_high**: intervalo de confianza 95% sobre la mediana (bootstrap 10,000 it.)
- **ventana_inicio, ventana_fin**: rango de fechas ISO-8601 de los posts incluidos
- **status**: `VALIDATED` (n≥30 · 2+ dirigentes) · `TBD` (n<30 o muestra insuficiente)

Las 25 filas del CSV (5 estratos × 5 plataformas) existen siempre, aunque el `status` sea TBD — esto mantiene la estructura estable entre versiones para facilitar merge-diff en publicaciones futuras.

---

## Citación sugerida

```bibtex
@dataset{mdconsultoria_2026_crece_benchmarks,
  author    = {MD Consultoría SC},
  title     = {Benchmarks ER políticos mexicanos — CRECE v2 v1},
  year      = 2026,
  publisher = {Zenodo},
  version   = {1.0-preliminar},
  doi       = {10.5281/zenodo.TBD},
  url       = {https://doi.org/10.5281/zenodo.TBD}
}
```

**Dataset académico de referencia para validación cruzada:**

Santos Rodríguez, A., Pérez-Rosas, V. et al. (2023). *Mexican Political Tweets 2021 Dataset (15M tweets)*. Zenodo. [10.5281/zenodo.7877001](https://doi.org/10.5281/zenodo.7877001)

---

## Reproducibilidad

Código fuente del generador: https://github.com/MarxCha/crece-v2 · path `backend/scripts/generate_zenodo_bundle.py`.

```bash
git clone https://github.com/MarxCha/crece-v2.git
cd crece-v2
python -m venv backend/venv && source backend/venv/bin/activate
pip install -r backend/requirements.txt
# Requiere DATABASE_URL apuntando a la BD poblada con el corpus político MX
python backend/scripts/generate_zenodo_bundle.py --window-days 90 --output backend/data/zenodo/v1/
```

El script consume `social_posts` + `social_profile_snapshots` + `dirigentes.estrato_politico` y computa los percentiles + IC 95% por celda. Es idempotente (sobrescribe outputs). No incluye credenciales ni PII — solo agregados.

---

## Versionado

| Versión | Fecha | Cambios |
|---|---|---|
| v1-preliminar | 2026-04-19 | Bootstrap del bundle · todas las celdas TBD hasta acumular ≥30d de snapshots |
| v1 | TBD (post 30d cron scraping) | Primera calibración con datos reales |
| v2 | TBD (S2+) | Expansión muestral + separación Reels vs posts IG + temporalidad electoral |

---

## Contacto y contribuciones

- **Maintainer:** MD Consultoría SC (`info@mdconsultoria-ti.org`)
- **Issues / contribuciones:** https://github.com/MarxCha/crece-v2/issues
- **Licencia:** [CC BY 4.0](./LICENSE.md) — cite este dataset como se indica arriba y está permitido cualquier uso derivado incluyendo comercial.

---

## Disclaimer

Este dataset es producto del pipeline de captura interno del producto CRECE v2 (MD Consultoría). No tiene aval académico previo a su publicación — se libera bajo filosofía de "open science pragmática" para permitir que la comunidad valide, critique y mejore la metodología. Los rangos publicados son benchmarks orientativos, no prescriptivos. El uso de este dataset para decisiones de inversión política o mediática es responsabilidad del usuario.
