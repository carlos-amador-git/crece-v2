# Revisión visual MVP · Piña (id=1) · 2026-04-20

**Scope:** 33 screenshots en 6 categorías · localhost:3005 (idéntico a Vercel prod commit `a428661`) · 2 sesiones (viewer Piña + admin).

## 01 · Tier 1 Diagnóstico · 12 screenshots

**Renderiza OK:** header "7/10 con datos · 3 insuficiente" · B01 ER 1.2% vs piso 4.6% con contexto D-19 "~100× sobre-estima" + link methodology Zenodo ✅ · B02 Breakout Cat 1 Baseline · B03 Matriz 84/62/0/0 · B05 Plutchik radar 6 emociones · B06 Crisis Spike "Estable" · B09 Share/Like · B10 Humanización con drill-down funcional (drawer top 5+5 posts). Fonts Instrument Sans + DM Sans. Sidebar con IPD 2.6/10 (D-03 correcto como secundario).

**Incompleto:** B04 Benchmark "Datos insuficientes · rivales sin data en ventana 28d" (esperado · proxies D-22 no tienen historial Apify).

## 02 · Tier 2 Diferenciadores · 10 screenshots

**Renderiza OK:** 8/8 con datos · B11 Cross-Partisan 53.9 con donut MC/MORENA/PAN · B12 CIB 2 flagged conf 0.65 · B13 Filtro Realidad 16.9% inauténticos con toggle "Activar filtro" + cards antes/después · B15 Rage Click "Engagement sano" 0.7%. Toggle Filtro Realidad responde + delta visible. Fonts + design consistente con Tier 1.

**Gap documentado:** B14 Topic Drift = 0.997 saturado (gap S4 conocido, Jaccard sobre captions cortos). **Discrepancia:** B16 Promesas UI muestra "0/12 cumplidas" pero DB tiene 10 promesas seed Piña (S4 T-1.1) — frontend no las lee o endpoint falla silencioso.

## 03 · Plan IA cliente · 4 screenshots

**Incompleto / bug crítico:** banner rojo "No se pudieron cargar tus recomendaciones · Not Found". Tabs Pendientes(0)/Seguimiento(0)/Histórico(0) visibles pero todos a 0. **Endpoint frontend→backend está faltando o con path incorrecto** — hay 10+ rows en DB recomendaciones_plan_ia pero UI no las carga. Bloquea demo comercial del ciclo D-17 al cliente.

## 04 · Plan IA Admin HITL · 1 screenshot

**Incompleto / bug crítico idéntico:** banner rojo "No se pudo cargar la cola · Not Found". Header correcto ("Plan IA · Cola MD Review HITL §3.6" · "Recomendaciones generadas por Gemma 3:12b pendientes de aprobación humana"). Filtros Dirigente/Tipo presentes. Pero cola vacía por endpoint 404. Sin esto, MD NO puede aprobar las 10 recs en estado propuesta → clientes nunca las ven. **Bloqueante del flujo HITL obligatorio.**

## 05 · Onboarding wizard · 2 screenshots

**Renderiza OK:** "Asistente de activación · 9 pasos" con stepper visual numerado 1-9 (Perfil · Cuentas · SERP · Validar · Confirmar · OAuth · Competidores · Promesas · Activar) · barra progreso 0% · paso 1 con 4 opciones perfil §1.5 (Político activo · Funcionario · Precampaña · Empresario) con iconos + descripciones · botón "Siguiente" correctamente disabled sin selección (D-23 rigor en el avance).

**No validado:** pasos 2-9 (el wizard bloquea automáticamente hasta que se elija perfil · comportamiento esperado).

## 06 · Settings + OAuth · 4 screenshots

**Renderiza OK (`/dashboard/settings`):** "Configuración · Mi cuenta" (Piña · pina@crece.mx · viewer · dirigente #1 · IPD 2.6/10 · 12.8K audiencia) · Sistema (API URL `http://localhost:8002/api/v1` · workers 2/2 activos · scrapers 0 en ejecución) · Cumplimiento INE visible (cortado parcialmente abajo).

**Rutas inexistentes (404):** `/dashboard/config` · `/dashboard/oauth` · `/dashboard/admin/settings` — redirigieron a login vacío. No hay pantalla dedicada "OAuth upgrade T3→T1" per-plataforma visible; el flujo OAuth vive dentro del onboarding wizard paso 6.

## Problemas obvios a resolver (prioridad)

1. **🔴 Bloqueante MVP:** endpoints Plan IA cliente + Admin HITL devuelven "Not Found" — path/método incorrecto o ausente · sin esto no hay demo comercial ni HITL funcional. Bug a fijar antes de entregar credenciales MC.
2. **🟡 Bug de data:** B16 Promesas UI no lee las 10 seed de Piña — endpoint `promesas_dirigente` list posiblemente faltante o path distinto al que frontend llama.
3. **🟢 Gap conocido:** B14 Topic Drift saturado 0.997 (documentado S4 gap).
4. **🟢 Gap conocido:** B04 Benchmark sin rivales con data — esperable, los proxies D-22 no tienen scrape historial profundo.

## Conclusión

UI + navegación + auth + design correctos. Gap real: **2 endpoints críticos no responden** (Plan IA cliente + Admin review) → bloqueante funcional para el piloto con Ballesteros. Recomiendo diagnóstico de esos endpoints antes de entregar credenciales.
