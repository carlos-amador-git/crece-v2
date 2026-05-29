# PRODUCTO — CRECE v2

**Última actualización:** 2026-05-28
**Propósito:** referencia única de la visión, misión, segmento, posicionamiento, roadmap y clientes del producto. Este doc forma parte del conjunto de 5 docs de gobernanza (ver `README.md`).

> **Estado del doc:** redactado por Linda (Claude Opus 4.7) consolidando docs vivos existentes (`NORTH-STAR.md`, `CRECE_PRODUCT_MASTER.md`, `RESEARCH-POSICIONAMIENTO-SMB-2026-05-07.md`, `PROPUESTA-POSICIONAMIENTO-SMB.md`). Misión/visión textual y posicionamiento comercial requieren validación del CEO (ver §10 Pendientes CEO).

> **Inspiración estructural:** Vision FAQ (Marty Cagan) + Working Backwards PR/FAQ (Amazon) + Shape Up pitch (Basecamp). Ninguna importada literalmente — adaptadas al contexto MX político.

---

## 1. Qué es CRECE v2 (resumen ejecutivo)

**CRECE v2 es una plataforma de inteligencia digital para políticos profesionales mexicanos** que convierte datos ruidosos de redes sociales en **3 decisiones accionables por semana**. Reemplaza analytics genéricos (IPD 0-10, sentimiento promedio) con:

- 30 bloques de diagnóstico específicos por dirigente (B01-B18 Tier 1+2 implementados, B19-B30 Tier 3 roadmap).
- Plan IA Start/Stop/Continue con criterios de éxito verificables.
- Compliance INE (veda, etiquetado IA, trazabilidad).
- Arquitectura dual-mode por dirigente (T1 scraping público / T2 cookies burner / T3 OAuth oficial cliente).

**Cliente ancla:** Movimiento Ciudadano CDMX (relación MD Consultoría 4+ años · piloto comercial activo desde 2026-04-20 D-PILOTO-01).

---

## 2. Misión, visión, posicionamiento

### 2.1 Misión propuesta (pendiente confirmación CEO)
> Dar a los políticos mexicanos profesionales el control de su narrativa digital con datos verificables, reduciendo la dependencia de consultores opacos y métricas de vanidad.

### 2.2 Visión a 2-5 años (pendiente confirmación CEO)
> Convertirse en la herramienta estándar de inteligencia digital política en México, capturando el segmento "el político serio que sí mide su trabajo" antes que Brandwatch/Meltwater lo descubran.

### 2.3 Posicionamiento defensible (3 killer features verificadas)

| # | Feature | Defensibilidad | Estado producto |
|---|---|---|---|
| 1 | **Breakout Scale Brookings Cat 1-6 aplicado a política MX** | Ninguna competencia lo tiene en este vertical. | ✅ B02 implementado |
| 2 | **Filtro de Realidad con CIB ITESO multinivel** | Captura caso Gálvez 2024 ($75.2M MXN en digital, confundió CIB con apoyo, perdió por 30 puntos). | ✅ B12+B13 implementado |
| 3 | **Arquitectura dual-mode con upgrade comercial por-dirigente** | T1/T2 base + T3 premium. Captura valor incluso si cliente no upgrade. | ✅ T1+T2 operativo, T3 disponible por dirigente |

**Fuente:** `NORTH-STAR.md` líneas 32-47. Validado por research `RESEARCH-POSICIONAMIENTO-SMB-2026-05-07.md`.

---

## 3. Perfiles de cliente (4 segmentos)

| Perfil | Horizonte | Necesidad central |
|---|---|---|
| 1. Político activo en representación | 3-6 años | Consolidar base + expandir sin sacrificar fieles |
| 2. Funcionario en gobierno | Período constitucional | Narrativa de gestión + anticipar crisis |
| 3. Figura en precampaña | 6-18 meses | Velocidad respuesta + compliance INE veda |
| 4. Empresario/figura en transición | Gradual | Formación + autoridad pública desde cero |

**UI / vocabulario / onboarding / pricing son adaptables por perfil. Arquitectura común.** Fuente: `NORTH-STAR.md` §"4 perfiles de cliente".

---

## 4. Arquitectura dual-mode (tier comercial)

| Tier | Fuente | Cuándo aplica |
|---|---|---|
| **T1** | Scraping público (Apify, Brightdata) | Baseline universal desde día uno. Incluso para prospectos sin firmar. |
| **T2** | Scraping + cookies burner dedicadas (`@RafaRamos72`) | Granularidad mayor sin OAuth. Infraestructura propia. |
| **T3** | OAuth oficial Meta/Google por-dirigente | **Post-venta** con cliente firmado. Mayor cobertura + datos oficiales. |

El mismo dashboard se pinta en cualquier tier con badge:
- `📊 Oficial` para T3
- `📊 Estimación de mercado` para T1/T2

**Decisión defensible:** upgrade T1→T3 es comercial, no técnico. Demo gratuita convierte en argumento de venta.

> **NO confundir con bilateralidad HITL** (MAPA-FUNCIONAL §9 + §10): los endpoints `/hitl/*` son compartidos cliente+admin con scope diferenciado por RBAC. Eso es una decisión de arquitectura de API distinta a este modelo de tiers comerciales. Son conceptos ortogonales — el dirigente cliente puede usar HITL para validar su propia clasificación NLP independientemente del tier (T1/T2/T3) que tenga contratado.

---

## 5. Roadmap del producto

### 5.1 MVP Tier 1+2 (cerrado)
Las 10 fases originales (Sprint 0-5) están cerradas. Los 10 bloques Tier 1 + 8 Tier 2 están operativos en producción. Ver MAPA-FUNCIONAL §2 y §8.

### 5.2 Fase 1 (en operación)
- Diagnóstico Digital (IPD 0-10)
- Monitoreo Social (8 scrapers + NLP)
- Benchmarking vs competidores
- Planes IA (Estrategia + Contenido)

### 5.3 Fase 2 (futuro · no comprometido)
- WhatsApp Campaign Manager
- Smart Canvassing (rutas optimizadas)
- Content Factory con IA
- CRM Político + Voter Scoring
- Participación Ciudadana (Decidim)
- Blindaje Legal

Ver `CRECE_PRODUCT_MASTER.md` §3 para el desglose completo de los 30 bloques B01-B30.

---

## 6. Clientes y pipeline

### 6.1 Cliente activo
| Cliente | Status | Notas |
|---|---|---|
| **Movimiento Ciudadano CDMX** | ✅ Piloto comercial cerrado 2026-04-20 (D-PILOTO-01) | Apertura del piloto: 3 activos (Piña id=1, Máynez id=7, Ballesteros id=8) + 5 shadow. Estado actual 2026-05-28: 13 dirigentes en BD (expansión post-piloto). Relación ConsultoríaMD 4+ años. |

**Desglose 13 actuales** (no todos del piloto original — incluye dirigentes onboarded post-apertura):
- Activos cliente: Piña (1), Solano (2), Saymi (3), Yesenia (4), Gaby (5), Cravioto (6), Máynez (7), Ballesteros (8), Pepe Monroy (57), Felipe (60)
- Cuentas administrativas: Ana García (analista, id=2), Carlos López (campo, id=3), Marx (admin, id=1)
- Otros viewer cuentas conforme onboarding

### 6.2 Pipeline / hipótesis
| Oportunidad | Status | Notas |
|---|---|---|
| Gobierno Oaxaca | Hipótesis · sin avance comprometido | Referenciado en handoffs anteriores. **Confirmar con CEO antes de actuar.** |
| Otros estados MC | No confirmado | Depende de éxito piloto CDMX. |
| B2B PyME (vertical paralelo) | Turf Joy · producto distinto (CRECE-Negocios) | NO competencia con CRECE-electoral. Ver `~/Projects/crece-negocios/docs/PRD-v0.1.md`. |

---

## 7. Diferenciadores frente a competencia

| Competencia | Por qué CRECE gana |
|---|---|
| Brandwatch / Meltwater | Hechos para marcas comerciales, no política. Sin CIB ITESO, sin compliance INE, sin perfiles del político serio. |
| Consultores de campaña tradicionales | Opacidad ("confía en mi expertise"). CRECE muestra el dato verificable. |
| Apify / Brightdata directo | Datos crudos sin contexto político MX. CRECE hace el processing + matriz por estrato + framework. |
| Métricas de vanidad (followers, likes) | CRECE reemplaza con ER normalizado por estrato + Plan IA Start/Stop/Continue accionable. |

---

## 8. Pricing (input CEO requerido)

⚠️ **No documentado en este doc.** El modelo de pricing (suscripción mensual, anual, por-dirigente, T1 vs T3) requiere validación CEO antes de exponerse. Verificar con CEO antes de mencionar números a cualquier prospecto.

---

## 9. Métricas de éxito del producto (KPI norte)

Pendiente cuantificación CEO. Propuestas basadas en evidencia:

| KPI | Razón |
|---|---|
| **Dirigentes activos T1+T2+T3** | Indicador de adopción. Hoy 13 en BD. Meta: ¿? |
| **% retención mes a mes** | Indicador de valor real. Pendiente medición histórica. |
| **Tareas accionables Start/Stop/Continue ejecutadas / dirigente / semana** | "3 decisiones accionables por semana" del posicionamiento. Pendiente instrumentación. |
| **Upgrade T1→T3 conversion rate** | Modelo comercial defensible. Pendiente medición. |
| **NPS / satisfacción CEO + equipo dirigente** | Calidad percibida. Pendiente proceso. |

---

## 10. Pendientes que requieren input directo del CEO

1. **Misión y visión textual** — confirmar o reescribir las propuestas §2.1 y §2.2.
2. **Pricing** — modelo, monto, política de upgrade T1→T3.
3. **KPIs norte** — cuantificación de metas (§9).
4. **Pipeline confirmación** — Gobierno Oaxaca y otros estados (§6.2): ¿qué se compromete vs qué es hipótesis?
5. **Roadmap Fase 2 priorización** — cuál de los 6 módulos Fase 2 se ataca primero post-MVP.
6. **Estrategia de adquisición de clientes** — ¿outbound, inbound, referidos MC?
7. **PR/FAQ "Working Backwards"** — escribir el comunicado de prensa futuro de CRECE v2 GA. Sirve como ancla anti-deriva.

---

## 11. Cross-references

- **NORTH-STAR.md** — briefing 2 minutos de visión estratégica. Mantener sincronizado.
- **CRECE_PRODUCT_MASTER.md** — SSOT detallado de visión + estado + decisiones. Vive en `/Users/marxchavez/Projects/crece-v2/.context/`.
- **MAPA-FUNCIONAL.md** — qué hace cada función del producto (10 secciones documentadas).
- **PIPELINE-RADAR-CRECE.md** — flujo de datos radar→crece, engines, adapters.
- **RESEARCH-POSICIONAMIENTO-SMB-2026-05-07.md** — research base del posicionamiento.
- **PROPUESTA-POSICIONAMIENTO-SMB.md** — propuesta derivada.

---

## 12. Versión y cambios

| Fecha | Cambio |
|---|---|
| 2026-05-28 | Versión inicial. Linda redactó consolidando NORTH-STAR + MASTER + research posicionamiento. Misión/visión textual + pricing + KPIs marcados como input CEO requerido. |
| 2026-05-28 (mismo día) | Audit Gemini ✅ Aprobado con observaciones (reporte: `.context/audits/2026-05-28-producto.md`). Ajustes aplicados: §4 aclaración Dual-mode tiers ≠ bilateralidad HITL · §6.1 desglose 3 activos piloto + expansión post-piloto. **Falsos positivos del auditor declarados:** Gemini inventó pricing "Core $1.5k - Enterprise $15k" y feature "IA Predictiva de Riesgos Q3-Q4 2026" que NO están en este doc. Sub-regla §5.4 MODELO aplicada: no aceptar hallazgos automáticamente, verificar contra realidad. |
