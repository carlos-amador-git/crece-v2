# Dual licensing — hybrid model

Copyright (c) 2026 MD Consultoría SC — CRECE v2 team

This bundle uses a **two-track license** that separates reproducible methodology from calibrated proprietary values.

---

## Track A — Methodology, code, and documentation

**License:** Apache License 2.0

**Applies to:**
- `README.md`
- `methodology.md`
- `backend/scripts/generate_zenodo_bundle.py`
- Any future `code/` bundled scripts

**Summary of rights:**

- Free commercial and non-commercial use, modification, and redistribution of the methodology and code.
- Must preserve attribution (the copyright notice above) and include the Apache 2.0 license text in any redistributed form.
- No patent claims by contributors.
- No warranty.

**Full license text:** https://www.apache.org/licenses/LICENSE-2.0

**Rationale:** the methodology and code describe HOW the engagement benchmarks are computed. Publishing them openly strengthens academic credibility, enables independent replication, and invites peer scrutiny of the calculation procedure. Third parties may build on the methodology to calibrate their own datasets.

---

## Track B — Calibrated values (proprietary)

**Status:** All rights reserved · proprietary asset of MD Consultoría SC

**Applies to:**
- `benchmarks_er_politicos_mx_v1.csv` (calibrated engagement rate values per estrato × plataforma)
- `_calibration_log.json` (metadata of calibration runs)
- Any future extended CSV with v2+ additional validated cells

**Summary of restrictions:**

- The calibrated values are commercially confidential and are not redistributed under an open license.
- Access is granted exclusively through the CRECE v2 product dashboard to contracted clients of MD Consultoría SC.
- Redistribution, republishing, extraction, or bulk download of these values without a commercial agreement with MD Consultoría SC is prohibited.
- Use of the methodology (Track A) to independently calibrate new values from third-party data is explicitly permitted and encouraged — what is protected is the specific calibrated values in this dataset, not the act of calibrating.

**Rationale:** the calibrated values are the differentiating asset of CRECE v2 as a commercial product. Two external independent dictamenes (2026-04-19) confirmed that no public empirical benchmark for Mexican political engagement rates existed prior to this dataset. Releasing the raw calibrated values under CC BY 4.0 would permit unrestricted commercial use by competitors and erode the commercial differentiation that motivated the dataset's creation. The hybrid model preserves academic openness of the method while protecting the commercial value of the specific calibration.

---

## Track C — Teaser cells for academic citation

**License:** CC BY 4.0 (subset only)

**Applies to:**
- `teaser_citable_cells.md` (explicitly 2-3 representative cells released for academic citation)

**Summary of rights:** the cells in `teaser_citable_cells.md` may be cited freely in academic and commercial contexts with attribution, as long as the citation points to this bundle's methodology section and the full MD Consultoría SC copyright.

**Rationale:** academic citability requires at least some concrete numeric references to anchor the methodology. The teaser cells are chosen to illustrate the magnitude of divergence from commercial Influencer Marketing benchmarks (the core finding of dictamenes 01 and 02) without releasing the full calibration.

---

## Contact

- Commercial licensing of Track B values: contact `info@mdconsultoria-ti.org`
- Academic use of Track A methodology + Track C teaser: no permission required, cite the bundle
- Issues / methodology clarifications: repository issues at `github.com/MarxCha/crece-v2`

---

## Suggested citations

**Methodology (Track A, Apache 2.0):**

```
MD Consultoría SC. (2026). Engagement rate benchmarks methodology for Mexican
political accounts — CRECE v2 (Apache 2.0). GitHub. commit 6fbe421 (PR #23).
```

**Teaser cells (Track C, CC BY 4.0 subset):**

```
MD Consultoría SC. (2026). Engagement rate benchmarks for Mexican political
accounts — teaser cells v1. CRECE v2. DOI: TBD (hybrid release).
```

**Full calibrated dataset (Track B, proprietary):** cite only with explicit commercial license from MD Consultoría SC.
