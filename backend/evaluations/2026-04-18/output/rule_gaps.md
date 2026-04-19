# Rule gaps — Triangulación NLP Layer 2 (2026-04-18)

Total rows analizados: **60**
Rows con algún disagreement: **23 (38%)**
Rows con 3/3 consenso en tono+polaridad: **37 (62%)**

Heurística: si los 3 modelos no coinciden en tono AND polaridad, el row entra como gap.

## Tabla de gaps (23 rows)

| ID | Gap type | Tono maj | Target maj | Pol maj | Tonos (C/G/M) | Pols (C/G/M) | Intens (C/G/M) |
|---|---|---|---|---|---|---|---|
| IG_3735502669264799350_18045325463381143 | tono-split + polaridad-split | personal | dirigente_post | aprobacion | personal/informativo/personal | aprobacion/neutral/aprobacion | 1/1/1 |
| IG_3803860272113545357_17976357209809424 | tono-split | elogio | dirigente_post | aprobacion | elogio/personal/elogio | aprobacion/aprobacion/aprobacion | 1/2/2 |
| IG_3828405263968328250_18056458157398724 | polaridad-split | pregunta | dirigente_post | neutral | pregunta/pregunta/pregunta | neutral/neutral/aprobacion | 0/1/1 |
| IG_3859474251099511440_17864677434657041 | tono-split + polaridad-split | critica | dirigente_post | rechazo | informativo/critica/critica | neutral/rechazo/rechazo | 0/-2/-2 |
| IG_3859474251099511440_17986748999974992 | tono-split + polaridad-split | informativo | ciudadania | aprobacion | autopromocion/informativo/informativo | aprobacion/neutral/aprobacion | 1/0/1 |
| IG_3863926554967780493_18322032121266928 | polaridad-split | personal | dirigente_post | aprobacion | personal/personal/personal | neutral/aprobacion/aprobacion | 0/1/1 |
| IG_3866786064979863718_17866479906609089 | polaridad-split | critica | gobierno | rechazo | critica/critica/critica | neutral/rechazo/rechazo | -1/-2/-2 |
| IG_3866786064979863718_18106237537878841 | polaridad-split | critica | gobierno | rechazo | critica/critica/critica | neutral/rechazo/rechazo | -1/-2/-2 |
| IG_3869699613314075094_18113102713702495 | polaridad-split | critica | otros | rechazo | critica/critica/critica | neutral/rechazo/rechazo | -1/-2/-2 |
| IG_3870375015863198197_17936992953035294 | tono-split + polaridad-split | elogio | dirigente_post | aprobacion | personal/elogio/elogio | neutral/aprobacion/aprobacion | 0/2/2 |
| IG_3870375015863198197_18074849840646868 | tono-split | ataque | dirigente_post | rechazo | ataque/critica/ataque | rechazo/rechazo/rechazo | -3/-3/-2 |
| IG_3875196649438253554_17985616574971120 | polaridad-split | critica | — | rechazo | critica/critica/critica | neutral/rechazo/rechazo | -1/-1/-2 |
| IG_3875377511752760072_17914701093163547 | tono-split | critica | gobierno | rechazo | ataque/critica/critica | rechazo/rechazo/rechazo | -3/-2/-2 |
| IG_3875377511752760072_18006235937898539 | tono-split + polaridad-split | critica | gobierno | rechazo | pregunta/critica/critica | neutral/rechazo/rechazo | -1/-2/-2 |
| IG_3875377511752760072_18064529543358280 | tono-split | personal | dirigente_post | aprobacion | personal/personal/elogio | aprobacion/aprobacion/aprobacion | 1/1/2 |
| IG_3875557808506959914_18324627997270426 | tono-split | elogio | dirigente_post | aprobacion | personal/elogio/elogio | aprobacion/aprobacion/aprobacion | 1/2/2 |
| IG_3877048436684554888_18128155336603764 | tono-split | critica | dirigente_post | neutral | critica/critica/informativo | neutral/neutral/neutral | -1/-1/0 |
| IG_3877660082045578213_17974280177862861 | tono-split + polaridad-split | personal | — | neutral | personal/personal/elogio | neutral/neutral/aprobacion | 0/0/1 |
| X_2037379763161940382 | tono-split | informativo | dirigente_post | aprobacion | autopromocion/informativo/informativo | aprobacion/aprobacion/aprobacion | 1/1/1 |
| X_2037892363402477974 | polaridad-split | autopromocion | dirigente_post | neutral | autopromocion/autopromocion/autopromocion | neutral/neutral/aprobacion | 1/0/2 |
| X_2038717965479158244 | tono-split + polaridad-split | pregunta | institucion | rechazo | pregunta/critica/pregunta | neutral/rechazo/rechazo | 0/-1/-1 |
| X_2043431834365653363 | tono-divergence | — | gobierno | rechazo | critica/ataque/pregunta | rechazo/rechazo/rechazo | -1/-2/-1 |
| X_2045407691820896548 | tono-split | ataque | dirigente_post | rechazo | ataque/ataque/critica | rechazo/rechazo/rechazo | -2/-2/-2 |

## Patrones identificados

### P1 — Claude es más conservador al asignar polaridad "rechazo" a críticas constructivas
**Volumen:** 6 rows (26% de gaps)
**IDs:** IG_3866786064979863718_17866479906609089, IG_3866786064979863718_18106237537878841, IG_3869699613314075094_18113102713702495, IG_3875196649438253554_17985616574971120, IG_3875377511752760072_18006235937898539, IG_3859474251099511440_17864677434657041

**Patrón:** Los 3 modelos coinciden en `tono=critica`, pero Claude marca `polaridad=neutral` (la crítica viene con una propuesta) mientras Gemini y Gemma marcan `rechazo`.

**Ejemplos:**
- "El tema es que con solo estar un rato caminando a la hora del calor se vuelve insoportable el olor a las aguas negras, debieron contemplar el desazolve..." → Claude neutral (propositivo), Gemini/Gemma rechazo
- "Sería maravilloso que el rio llevara agua limpia y no aguas negras" → mismo patrón
- "Que ponga q verter a los encargados de basura..." → mismo patrón

**Implicación para matriz:** la distinción `critica_constructiva` vs `critica_hostil` no existe en matriz v2. Dos opciones:
  - (a) Añadir modificador `_constructivo` al tono (polaridad +1 respecto al hostil equivalente)
  - (b) Gemini/Gemma están siendo demasiado literales — no distinguen crítica con propuesta. Prompt V3 podría incluir ejemplo few-shot.

### P2 — Personal vs elogio en comments cortos con emojis
**Volumen:** 4 rows (17% de gaps)
**IDs:** IG_3870375015863198197_17936992953035294 ("con tokio 🟠🦅"), IG_3803860272113545357_17976357209809424 ("Houmito niño y bensita niña ❤️❤️❤️❤️"), IG_3875557808506959914_18324627997270426 ("Jajjajajajaj ❤️"), IG_3875377511752760072_18064529543358280 ("Gusto saludarte secretario")

**Patrón:** Claude tiende a `personal` cuando detecta afectividad interpersonal; Gemini y Gemma tienden a `elogio` por la polaridad positiva.

**Implicación:** los dos tonos **sí son distintos** en matriz v2 (personal=0 neutro, elogio/celebratorio=+1). La divergencia en comments cortos afecta el score político. Requiere criterio explícito en prompt o reducir granularidad (fusionar personal+elogio cortos).

### P3 — Autopromoción vs informativo en self-posts de dirigentes
**Volumen:** 3 rows
**IDs:** X_2037379763161940382, IG_3859474251099511440_17986748999974992, (y borderline X_2037892363402477974 donde los 3 coinciden `autopromocion` pero disagree polaridad)

**Patrón:** Claude marca `autopromocion` cuando el autor del comment ES el dirigente (self-RT, anuncio oficial). Gemini y Gemma marcan `informativo`.

**Implicación:** si el comment fue emitido por el propio handle del dirigente (self-author), debería detectarse a nivel runtime (comparar `author` vs `handle_dirigente`) y NO depender del LLM. Es señal determinística, no semántica.

### P4 — Ataque vs crítica en sarcasmo e ironía
**Volumen:** 3 rows
**IDs:** IG_3870375015863198197_18074849840646868, IG_3875377511752760072_17914701093163547, IG_3877048436684554888_18128155336603764, X_2045407691820896548

**Patrón:** Claude es más agresivo marcando `ataque` cuando hay sarcasmo ("no estabas mame y mame que..."). Gemma es más conservador, tiende a `critica`. Gemini intermedio.

**Implicación:** el umbral ataque/critica afecta intensidad (ataque suele ser -3, critica -1/-2). Impacta score político directamente. Requiere criterio explícito: ¿cuándo una crítica con tono burlesco se clasifica como ataque?

### P5 — Preguntas con crítica implícita
**Volumen:** 2 rows
**IDs:** X_2038717965479158244 ("taxis con polarizados ?"), IG_3875377511752760072_18006235937898539 ("Que harán con los perritos del refugio franciscano?")

**Patrón:** Claude + Gemma mantienen `pregunta`; Gemini rompe a `critica`. Matriz v2 no tiene regla para `tono=pregunta` (no está en vocab v2).

**Implicación:** si `pregunta` se mantiene como tono distinto en runner (vs eliminarlo), matriz v2 debe añadir reglas para él. O el prompt debe mapear pregunta crítica → critica.

### P6 — 3-way divergence real (1 caso único)
**ID:** X_2043431834365653363 — "Se sabe que el origen de muchas de esas colonias iniciaron por la vía del paracaidismo. Legalizado lo ilegal"

**Tonos:** critica (C) / ataque (G) / pregunta (M). Polaridad coincide (rechazo).

**Implicación:** este tipo de comment (afirmación factual con critica implícita a gobierno) es genuinamente ambiguo. Candidato a anotación humana prioritaria.

## Relación con matriz v2 (53 reglas)

### Target-agreement es el cuello de botella

- **60 rows**, de los cuales 38 (63%) tienen consenso 3/3 en target
- 20 rows (33%) tienen split 2/3 — típicamente entre `dirigente_post` vs `gobierno`
- 2 rows con 3-way divergence en target

El vocabulario de target del **runner (6 opciones)** no coincide con **matriz v2 (8 opciones)**. Específicamente:
- `dirigente_post` (runner) vs `dirigente` (v2, solo para comment_tercero)
- `institucion` (runner) no existe en v2
- `medios` (v2) no existe en runner
- `tema_especifico` (v2) no existe en runner

**Implicación principal:** la propuesta matriz v3 debe decidir qué vocabulario adoptar como autoridad (ver PROPUESTA-MATRIZ-V3.md).

### Gaps del vocabulario de tono

| Tono runner | Matriz v2 equivalente | Observación |
|---|---|---|
| elogio | celebratorio | sinónimo funcional, retipificar en v3 |
| critica | critico | morfología, alinear en v3 |
| pregunta | **NO EXISTE** | añadir a v3 o mapear a `critico/informativo` |
| ataque | ataque | idéntico |
| informativo | informativo | idéntico |
| personal | personal | idéntico |
| autopromocion | (target en v2) | **conflicto**: en runner es tono, en v2 es target |

## Siguientes pasos

- [x] Mapear divergencias (este doc)
- [ ] Escribir `PROPUESTA-MATRIZ-V3.md` con ajustes concretos basados en P1-P6
- [ ] Cross-audit Gemini de la propuesta
- [ ] Decisión CEO
