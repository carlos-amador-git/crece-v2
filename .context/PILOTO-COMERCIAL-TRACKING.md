# PILOTO-COMERCIAL-TRACKING — Ventana calibración 2-3 semanas + piloto 90d §7.4

**Fecha arranque:** 2026-04-20 (post-merge PR #30 · MVP cerrado)
**Autorización CEO:** 2026-04-20 revisión §9.8 final del arco MVP aprobada
**Ventana inicial de calibración:** 2-3 semanas (2026-04-20 → 2026-05-04 / 2026-05-11)
**Ventana piloto §7.4 métrica 1:** 90 días (hasta 2026-07-19 aprox post-expansión)

---

<!-- 2026-04-21: reclasificación documental — Ballesteros (id=8) movida de shadow a activo.
     Status real desde apertura del piloto por solicitud expresa de MC.
     No es promoción nueva, es cierre de gap documental. Ver D-PILOTO-03 en DECISIONS.md. -->

## Dirigentes activos (Plan IA visible al cliente · HITL admin panel operativo)

### 1. Alejandro Piña Medina (id=1)

| Campo | Valor |
|---|---|
| Cargo | Coordinador Comisión Operativa Estatal MC CDMX |
| Perfil §1.5 | `politico_activo` |
| Estrato | Nano (~3.1K X · 2.2K IG · 1.8K FB) |
| data_origin | T3 (scraping público · pre-OAuth) |
| data_fidelity_tier | X: T3 · IG: T3 · FB: T3 · TT: N-A · YT: N-A |
| Plan IA status | ✅ Activo · recomendaciones visibles cliente post-MD review |
| Competidores declarados | {2, 5, 8} (fixture S2 · reemplazable Onboarding) |
| Promesas seed S4 | 10 promesas plausibles con fecha_compromiso próximos 6 meses |
| Acción CEO pendiente | **Sesión 60 min demo en vivo + firma participación formal 90d** |

### 2. Jorge Álvarez Máynez (id=7)

| Campo | Valor |
|---|---|
| Cargo | Ex-candidato presidencial MC 2024 · Diputado federal |
| Perfil §1.5 | `politico_activo` · potencial cambio a `figura_precampaña` si confirma candidatura 2030 |
| Estrato | Macro (500K+ X) |
| data_origin | T3 |
| data_fidelity_tier | 5 plataformas T3 |
| Plan IA status | ✅ Activo post-Onboarding completo |
| Competidores declarados | {5, 8} (fixture) |
| Acción CEO pendiente | Contacto + acuerdo piloto (perfil Macro ayuda a calibrar ER real del estrato) |

### 3. Laura Ballesteros Mancilla (id=8)

| Campo | Valor |
|---|---|
| Cargo | Diputada Federal Plurinominal MC |
| Perfil §1.5 | `politico_activo` |
| Estrato | Micro |
| data_origin | T3 (scraping público · pre-OAuth) |
| Plan IA status | ✅ Activo desde apertura del piloto · 4 recomendaciones MD-aprobadas visibles en prod |
| Acción CEO pendiente | Seguimiento continuo · revisión feedback semanal |

**Nota reclasificación:** Ballesteros fue activa desde 2026-04-20 por solicitud expresa de MC (cliente). Credenciales entregadas conforme a esa solicitud. El gap documental (TRACKING.md la listaba como shadow) fue corregido el 2026-04-21. Ver D-PILOTO-03 en DECISIONS.md.

### ⚠️ Bandera operativa 2026-04-24

**Máynez Plan IA bloqueado adicional más allá de F1.1:** sesión 2026-04-24 intentó scraping inicial de Máynez · falló 5 plataformas consecutivas por bugs en el stack de scrapers (Twitter async, Instagram auth, Facebook chromedriver · TikTok+YouTube abortados). Detalle completo en `.context/SCRAPING-MAYNEZ-2026-04-24.md` · ticket remediación en `.context/BACKLOG.md#B-SCRAPE-01`.

Ruta de desbloqueo secuencial:
1. F1.1 Schema restauración (pendiente Joy + revisor §9.8)
2. B-SCRAPE-01 Fix stack scrapers (pendiente Joy post-F1.1)
3. Re-ejecutar scraping Máynez (post-fix)
4. reprocess_nlp, FODA, Plan v3

Hasta entonces Máynez permanece **activo documental** (Plan IA visible al cliente habilitado) pero **sin datos reales** · dashboard mostrará estado onboarding o empty states donde apliquen.

**⚠️ Observación métrica §7.4:** los 3 activos son `politico_activo`. La métrica 1 de §7.4 requiere **3 perfiles distintos** (político activo + funcionario + empresario/precampaña). Si Máynez confirma precampaña 2030 sigue contando como `politico_activo` (no suma perfil nuevo). Se necesita expansión Fase 2 del piloto a 1 funcionario para cerrar métrica 1 completa (actualmente 1/3 perfiles distintos).

---

## Dirigentes shadow mode (data processing sin Plan IA cliente-visible)

Estos 5 dirigentes procesan scraping + diagnóstico 18 bloques pero **NO tienen recomendaciones Plan IA visibles al cliente**. Sirven para:
- Calibración estadística continua de la matriz 5×5 Zenodo (más data en Nano/Micro)
- Validación de la pipeline contra casos diversos sin compromiso comercial
- Expansión candidata post-calibración (días 14-21 del piloto)

| id | Nombre | Cargo | Perfil candidato §1.5 | Uso shadow |
|---|---|---|---|---|
| 2 | Rafael Solano Pérez | Miembro Comisión MC / Analista La Razón | empresario_transicion | Caso borde Nano extremo (8 comments 90d) |
| 3 | Saymi Pineda Velasco | Secretaria Turismo Oaxaca | funcionario_gobierno | **Candidato fuerte métrica §7.4 #3** |
| 4 | Yesenia Nolasco Ramírez | Secretaria Movilidad SEMOVI Oaxaca | funcionario_gobierno | Candidato expansión |
| 5 | Gabriela Jiménez Godoy | Diputada Federal Vicecoord MC | politico_activo | Benchmark comparación Piña (mismo perfil) |
| 6 | César Cravioto Romero | Secretario de Gobierno CDMX (MORENA) | funcionario_gobierno | Cross-partisan · caso §7.4 #3 ideal |

**Hallazgos handles Cravioto (2026-04-24 · post-falso-negativo Chrome AI):**

| Plataforma | Handle correcto confirmado | Notas |
|---|---|---|
| X | `@craviotocesar` | ya verificado |
| Facebook | `craviotocesar` | ya verificado |
| Instagram | `@cesarcravioto` | ✅ Verificado visualmente CEO 2026-04-24 · Chrome AI produjo falso negativo probando `@craviotocr` + `@cesar_craviotor` que NO existen, omitió `@cesarcravioto` que SÍ es Cravioto · social_profiles.id=21 · `is_confirmed=true` · 50 posts reales ingestados 2026-04-13 · ver `.context/HANDLES-VERIFICATIONS-2026-04-24.md` |
| TikTok | `@cesar_craviotor` (underscore) | diferente del IG · ya confirmado |
| YouTube | `@CesarCraviotoR` | ⚠️ canal legacy de etapa Senador · solo 27 suscriptores · sin contenido activo como Secretario de Gobierno CDMX · considerar excluir YT del scoring digital de Cravioto |

**Lección operativa del piloto · handles por plataforma:**

**NO INFERIR UN HANDLE ÚNICO DESDE OTRO.** Cada plataforma requiere verificación independiente. Cravioto demuestra:
- X: `craviotocesar`
- FB: `craviotocesar` (coincide con X)
- **IG: `cesarcravioto` (SIN sufijo "-cesar" final · distinto de X/FB)**
- **TT: `cesar_craviotor` (underscore · distinto de todos los anteriores)**
- YT: `CesarCraviotoR` (CamelCase · distinto)

Patrón común en political accounts · el handle depende de disponibilidad histórica de cada plataforma al momento de creación.

**Regla operativa al bootstrapear dirigente nuevo (aplica para Máynez y futuros):**
1. Obtener handles individualmente por plataforma (búsqueda en cada UI oficial)
2. Verificar `is_confirmed=true` SOLO si 2 fuentes independientes confirman el handle específico de esa plataforma
3. Probar varios deletreos antes de asumir que un perfil no existe (Chrome AI con Cravioto probó 2 variaciones, dio por perdido antes de probar la tercera que era la correcta)
4. Registrar razón de cada verificación en `.context/HANDLES-VERIFICATIONS-YYYY-MM-DD.md`

**Recomendación expansión Fase 2** (día 14-21 del piloto): promover Cravioto (id=6) o Pineda (id=3) a activo para cerrar perfil `funcionario_gobierno` y cumplir §7.4 métrica 1 (3 perfiles distintos).

---

## Criterios binarios de éxito §7.4 (heredados MASTER §7.4 tracción comercial 90d)

### Métrica 1 · 3 pilotos reales con perfiles distintos

- [ ] Piña activo con contrato fecha-cierre 90d firmado (político activo)
- [ ] Máynez activo con contrato fecha-cierre 90d firmado (político activo o precampaña según se confirme)
- [ ] +1 funcionario firmado (candidato: Cravioto o Pineda post-calibración) → 3/3 perfiles

### Métrica 2 · ≥1 recomendación ejecutada con resultado medible

- [ ] Cliente activo publica 1 post que vincula a recomendación Plan IA (T7 del wizard)
- [ ] Seguimiento 14d detecta resultado empírico (SoV delta · breakout · rage click reduction)
- [ ] Veredicto `exitosa` o `parcial` registrado en DB

### Métrica 3 · ≥1 conversión T3 → T1 OAuth firmado

- [ ] Cliente activo completa OAuth Meta (IG/FB) o TikTok Business o YouTube Data real
- [ ] `data_origin` del dirigente transiciona T3 → T1 en DB con `data_origin_checkpoint` timestamp
- [ ] Badge fidelity cambia en dashboard

**Criterio definitivo §7.4 cierre 90d:** si se logra mover aguja real en ≥1 caso real → producto vendible + caso de estudio autovendible. Si no → recalibración estructural.

---

## Protocolo durante piloto

### Captura de feedback

Todo feedback del cliente se documenta como **GitHub issue** con:
- Label obligatorio: `piloto-feedback`
- Labels opcionales: `dirigente-1` · `dirigente-7` · `plataforma-ig` · `plataforma-x` · `bloque-B01`...`B18`
- Template en el issue: { cliente · contexto · qué reportó · criticidad · acción sugerida }

### Decisiones estructurales que emerjan

Pasan por protocolo §9.8 regular (dos puertas Claude.ai + Gemini) **antes** de cualquier modificación al MASTER o código core. No se reabren D-01 a D-24 sin este protocolo.

### Calibraciones operativas (sin §9.8)

Permitidas como PRs incrementales dentro del scope aprobado:
- Umbrales Topic Drift (post-30d · recalibración §T-1.2 UMBRALES-OPERATIVOS-S4.md)
- Prompt Plan IA v1.0 → v1.1 con feedback MD review (changelog obligatorio D-24)
- Refinamientos UI basados en usabilidad cliente
- Seeds adicionales de promesas / competidores que el cliente declare

### Hotfix producción

Bugs críticos afectando clientes activos → hotfix PR directo a main con notificación CEO. No requiere sprint formal.

---

## Checkpoints durante piloto

### Semana 1 (2026-04-20 → 2026-04-27)

- [ ] CEO agenda + ejecuta demo 60 min con Piña + firma de participación
- [ ] CEO contacta Máynez para onboarding + firma
- [ ] Joy: vigilar issues `piloto-feedback` diarios · responder en <24h con análisis + recomendación
- [ ] Cron `scrape-all-profiles-daily` corriendo sin WAL recovery (validar memory_limit S3 T0)

### Semana 2-3 (2026-04-27 → 2026-05-11)

- [ ] Al menos 2 recomendaciones Plan IA generadas por dirigente activo
- [ ] MD review aprueba ≥1 por dirigente
- [ ] Cliente ejecuta al menos 1 recomendación
- [ ] Seguimiento 14d activo para las ejecutadas
- [ ] Feedback acumulado ≥10 issues `piloto-feedback`

### Día 30 (2026-05-20 aprox) · Revisión §9.8 intermedia

CEO + Joy revisan:
- Feedback acumulado · patrones recurrentes
- Hallazgos operativos inesperados
- Decisión: continuar scope MVP · ajustar con Sprint S6 · cambio estratégico

### Día 60 (2026-06-19 aprox)

- [ ] Expansión candidata: +1 funcionario (Cravioto o Pineda) activo
- [ ] 3/3 perfiles §7.4 métrica 1 cumpliendo

### Día 90 (2026-07-19 aprox) · Revisión §9.8 terminal del arco MVP comercial

Evaluación binaria §7.4:
- Métrica 1: 3 pilotos 90d firmados? ✅/❌
- Métrica 2: ≥1 recomendación ejecutada con resultado? ✅/❌
- Métrica 3: ≥1 conversión T3→T1 OAuth? ✅/❌

3/3 → producto vendible · arco comercial probado · siguiente arco: expansión pago (piloto → producción comercial escalable).
<3/3 → recalibración estructural · Sprint S6 iteración producto basada en evidencia empírica.

---

## Gaps no-bloqueantes heredados del MVP (retomar post-calibración si aplica)

- DIFERIDO-02 Meta App Review submission → activa OAuth real (4-8 semanas) · arrancar cuando cliente #15 firmado
- DIFERIDO-04 audit deuda técnica heredada repo
- DIFERIDO-05 memory_limit Docker refinamiento con carga real
- ✅ DIFERIDO-06 httpx async hang → CERRADO S5 T0 Celery migration
- Zenodo v1 → v2 con más muestras calibradas (trigger: ≥30d snapshots piloto activos)
- Validator actors TikTok/FB/YouTube → stubs actuales · reemplazar con Apify actors reales cuando aumente demanda
- Brightdata SERP fallback → activable con credenciales cliente si SERP automático crece en uso
