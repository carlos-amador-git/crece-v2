# Re-review post-hotfix PR #2 · 2026-04-20

**Alcance PR `hotfix/pre-piloto-v2`:** F-01, F-02, F-03, F-04, F-05, F-07.
**Screenshots:** `.context/frontend-review-2026-04-20/post-hotfix-v2/` · 15 capturas · 0 errores de consola.

## F-01 · B01 rango benchmark D-19 ✅

**Antes:** rango visible "3-7%" (Influencer Marketing commercial).
**Después:** "Rango empírico MX política **0.01%–1.1%** (Zenodo v1 · n=316 Nano X)" + explicación "El benchmark comercial (Sprout Social · Rival IQ · IM commercial) mostraba rangos **3–7%** que sobre-estimaban el ER político mexicano hasta ~100×".

**Cambios:**
- `backend/app/services/diagnostico/_common.py::MATRIZ_ER_5x5` → Nano/Micro con valores Zenodo v1 p25-p75 (8 celdas 🟢 VALIDATED). Mid/Macro/Mega extrapolados conservadoramente × 0.5 factor por estrato con flag 🟡 TBD.
- Nuevo `ZENODO_VALIDATED_CELLS: set[(estrato, platform)]` marcando 8 celdas con data empírica.
- `backend/app/services/diagnostico/er_service.py` propaga `zenodo_validated: bool` por-plataforma en la respuesta + `matriz_version: "5x5-zenodo-v1-2026-04-19"`.
- `frontend/src/components/diagnostico/cards.tsx::CardB01`: label `BENCHMARK_MX_RANGE_LABEL = "0.01%–1.1%"`, nuevo warning `b01-tbd-warning` si alguna plataforma del estrato no está validada.

**Screenshot:** `02-b01-rango-empirico-zenodo.png`.

## F-02 · B04 competidores demo ✅

**Antes:** card mostraba "Rival A/B/C" sin contexto de que eran proxies de demo.
**Después:** banner persistente ámbar "Competidores de demostración. Configura tus rivales reales en [Onboarding · paso Competidores](link)" — renderiza incluso cuando el estado es `insufficient_data` (caso más frecuente en piloto por proxies sin historial).

**Cambios:**
- `frontend/src/components/diagnostico/card-shell.tsx::CardShell` acepta nueva prop `persistentBanner?: React.ReactNode` que se renderiza arriba del empty/children block.
- `frontend/src/components/diagnostico/cards.tsx::CardB04` detecta modo demo como `origen_competidores === "proxies_s2" || rivales.every(r => r.status !== "ok")` y emite el banner vía `persistentBanner`.

**Screenshot:** `03-b04-demo-banner.png`.

## F-03 · Onboarding 9 pasos + validación D-22/D-23 ✅

**Capturados:** los 9 pasos del wizard (ver `07-onboarding-paso-1.png` a `07-onboarding-paso-9.png`).

**Estado por paso:**
1. Perfil (4 opciones §1.5: Político activo · Funcionario · Precampaña · Empresario) · renderiza OK
2. Cuentas manuales (URLs por plataforma) · renderiza OK
3. SERP asistido (opcional · Brightdata primary, Apify fallback) · renderiza OK con toggle "Activar búsqueda asistida"
4. Validación perfiles (auto Apify) · renderiza OK
5. **Confirmación humana obligatoria (D-23)** · renderiza OK · texto explícito "Esta es la única forma de proteger al dirigente de scrapear a la persona incorrecta. Marca cada cuenta que SÍ es suya. Sin confirmación, no activamos scraping."
6. OAuth (opcional · X grayed D-19) · renderiza OK
7. **Competidores (D-22)** · renderiza OK con copy "Agrega 3-5 contendientes directos del mismo cargo o territorio. Libera el bloque #04 (benchmark vs competidores · D-22)"
8. Promesas (mínimo 1 · D-17) · renderiza OK
9. Activación final · renderiza OK

**Validación D-22/D-23 observada:**
- D-23 (confirmación humana obligatoria) · implementado en paso 5 con texto literal "regla dura". Paso 5 bloquea avance si no hay cuentas validadas.
- D-22 (client-owned competidores) · implementado como **formulario manual** (nombre/cargo/url_ref) en paso 7. **Observación:** el finding F-03 mencionaba "búsqueda tipo Harfuch" (autocomplete/typeahead) — el paso actual usa entrada manual, no typeahead. Ver sección "Gap documentado" al final.

## F-04 · B13 narrative comercial ✅

**Antes:** números visibles (pct inauténtico · orgánico · excluidos) sin frase de impacto.
**Después:** recuadro resaltado abajo del card con texto comercial directo.

Ejemplo capturado: "**16.9%** de tu engagement en comments es inauténtico — nivel medio, monitorea tendencia."

Variantes semánticas según `impact_hint`:
- `alto`: "nivel alto, revisa fuentes de amplificación" (fondo rojo)
- `medio`: "nivel medio, monitorea tendencia" (fondo ámbar)
- `bajo` / default: "dentro del ruido orgánico esperado" (fondo neutro)

**Cambios:** `frontend/src/components/diagnostico_tier2/cards.tsx::CardB13` — nuevo slot `data-testid="b13-narrative"`.

**Screenshot:** `05-b13-narrative-comercial.png`.

## F-05 · Overview Tier 1 contexto D-19 ✅

**Antes:** B01 rojo sin explicación en vista agregada · el contexto D-19 vivía sólo dentro de la card B01.
**Después:** banner de contexto permanente en el header del dashboard Tier 1 · explica rango empírico MX (Zenodo v1 n=316 Nano X), contrasta con rango comercial IM (3-7%), link a metodología, y aclara que "rojo no significa que estés 'mal' según el estándar global — significa que estás bajo el piso del estrato político mexicano".

**Cambios:** `frontend/src/app/dashboard/diagnostico/[dirigenteId]/page.tsx` — nuevo bloque `data-testid="tier1-contexto-d19"` arriba del grid de cards.

**Screenshot:** `01-tier1-overview-d19.png`.

## F-07 · B14 warning calibración ✅

**Antes:** score 0.997 mostrado sin contexto · cliente podía interpretar "parece buen número".
**Después:** warning ámbar explícito "⚠️ Detector en calibración. Jaccard sobre captions cortos tiende a saturar cerca de 1.0 — los scores individuales todavía no son interpretables de manera confiable. Úsalo como señal relativa entre posts, no como medida absoluta."

**Cambios:** `frontend/src/components/diagnostico_tier2/cards.tsx::CardB14` — nuevo slot `data-testid="b14-calibration-warning"`.

**Screenshot:** `06-b14-warning-calibracion.png`.

## Gap documentado (fuera de scope hotfix)

**Paso 7 Competidores · sin búsqueda tipo Harfuch.**
El paso actual usa formulario manual (nombre · cargo · url_ref) que respeta D-22 (ownership del cliente). La frase "búsqueda tipo Harfuch" del finding F-03 sugiere autocomplete/typeahead sobre catálogo de políticos, pero esto **no está implementado**. El paso 3 (SERP asistido) sí hace búsqueda, pero para las redes del **propio dirigente**, no para competidores.

**Recomendación:** si el cliente espera typeahead en paso 7, crear finding nuevo F-16 post-piloto · revisar con CEO si el paradigma manual actual es suficiente (ownership explícito) o si agregar typeahead sobre dirigentes conocidos.

## Checklist final

| Finding | Estado | Screenshot |
|---|---|---|
| F-01 · B01 rango Zenodo | ✅ verificado | `02-b01-rango-empirico-zenodo.png` |
| F-02 · B04 demo banner | ✅ verificado | `03-b04-demo-banner.png` |
| F-03 · Onboarding 9 pasos | ✅ capturados | `07-onboarding-paso-{1..9}.png` |
| F-04 · B13 narrative | ✅ verificado | `05-b13-narrative-comercial.png` |
| F-05 · Overview D-19 | ✅ verificado | `01-tier1-overview-d19.png` |
| F-07 · B14 warning | ✅ verificado | `06-b14-warning-calibracion.png` |

**Consola:** 0 errores en toda la sesión (login Piña + Tier 1 + Tier 2 + 9 pasos onboarding).
**TypeScript:** `npx tsc --noEmit` · No errors found.
**Backend smoke:** `GET /diagnostico/1` retorna `matriz_version: "5x5-zenodo-v1-2026-04-19"` + `zenodo_validated=true` en 4/4 plataformas (Piña Nano).

## Listo para merge

Sin bloqueantes detectados. Credenciales Ballesteros entregables. Demo Piña agendable.
