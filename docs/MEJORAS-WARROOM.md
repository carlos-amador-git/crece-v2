# CRECE v2.0 — War Room + Multi-Tenant

**Fecha:** 2026-04-13
**Estado:** EN EJECUCION
**Aprobado por CEO:** Si (2026-04-13)
**Branch:** `feat/sprint-c-hardening`

---

## Contexto

War Room plan aprobado 2026-04-10 (3 sprints). Implementacion 70-80% completada
bajo sprints S1-S5 + B + I + J + D. La DB fue borrada por error (sesion Jess
2026-04-12) y restaurada parcialmente. CEO solicita multi-tenant real con 6
usuarios politicos de 3 organizaciones.

## 6 Usuarios Politicos Reales

| # | Nombre | Cargo | Org | Redes |
|---|--------|-------|-----|-------|
| 1 | Alejandro Pina Medina | Coord. Comision Operativa Estatal MC | MC-CDMX | @Alejandro_Pinha, @alejandro.pinha, FB alejandropinamedina |
| 2 | Rafael Solano Perez | Miembro Comision Estatal / Analista La Razon | MC-CDMX | @rafasolanoperez (IG), @rafasolanoperez (X) |
| 3 | Saymi Adriana Pineda Velasco | Secretaria de Turismo Oaxaca | GOB-OAXACA | @saymipinedav (X, 8.8K), @saymipinedavelasco (IG, 12K) |
| 4 | Yesenia Nolasco Ramirez | Secretaria de Movilidad (SEMOVI) Oaxaca | GOB-OAXACA | @Yes_Nolasco (X), FB YesNolasco (32K) |
| 5 | Gabriela Jimenez Godoy | Diputada Federal Morena, Vicecoord. | CDMX-IND | @GabyJimenezMX (X), @gabyjimenezgo (IG), FB 92K, TikTok @gabyjimenezmx |
| 6 | Cesar Cravioto Romero | Secretario de Gobierno CDMX | CDMX-IND | @craviotocesar (X), FB craviotocesar |

## 3 Organizaciones (Multi-Tenant)

| Org | Slug | Usuarios | Datos ciudadanos |
|-----|------|----------|-----------------|
| Movimiento Ciudadano CDMX | mc-cdmx | Pina, Solano | 9,723 reales (zip MC Tablas) |
| Gobierno Oaxaca | gob-oaxaca | Pineda Velasco, Nolasco | Sinteticos INEGI 2020 Oaxaca (is_synthetic=true) |
| CDMX Independiente | cdmx-ind | Jimenez Godoy, Cravioto | Sinteticos INEGI 2020 CDMX (seed diferente a MC) |

**Regla critica:** Cada org ve SOLO sus datos via RLS. Admin ve todas las orgs
separadas, nunca mezcladas. Tenant switcher en header.

## Estado del War Room (pre-Sprint E)

| Feature War Room | Estado | Donde |
|-----------------|--------|-------|
| 4 KPIs politicos (Audiencia, IPD, Conversacion, Tema Urgente) | HECHO | dashboard/page.tsx |
| Filtros periodo (Hoy/7d/30d/90d) | HECHO | dashboard/page.tsx |
| Tendencia sentimiento + Seguidores plataforma | HECHO | dashboard/page.tsx |
| Panel comparativo vs competidor (widget dashboard) | FALTA | benchmark es pagina separada, no widget |
| IPD Radar 6 ejes | HECHO | dirigentes/[id] |
| Kanban 3 columnas | HECHO | planes/[id]/kanban |
| Mapa canvassing 9,631 ciudadanos | HECHO (codigo) | canvassing/page.tsx (necesita datos en DB) |
| Content Factory con IA | HECHO | contenido/page.tsx |
| 5 formatos guiones campo | FALTA | talking_points, guion_contraste, script_puerta, briefing_crisis, narrativa_territorial |
| Flash Analysis (5 min) | FALTA | endpoint + UI |
| Bot Detection / Salud Digital | HECHO | bot-detection/page.tsx |
| Voter Scoring + Segmentacion | HECHO (codigo) | scoring/page.tsx (necesita datos) |
| Compliance / Blindaje Legal | HECHO | compliance/page.tsx |
| CRM Ciudadanos | HECHO | ciudadanos/page.tsx |
| Campanas WhatsApp | HECHO | campanas/page.tsx |
| Participacion Ciudadana | HECHO | participacion/page.tsx |
| NLP pysentimiento | HECHO (codigo) | necesita reprocess sobre posts |
| Wizard Onboarding admin | HECHO | sistema/onboarding |

**Resumen:** 14/17 features hechas en codigo. 3 faltan. Problema principal:
DB vacia hace que todo se vea en empty state.

## Plan de Ejecucion — Sprint E

### Fase 0: Restaurar datos MC-CDMX (~2h)
Objetivo: que la org MC-CDMX se vea completa en el dashboard.

| ID | Tarea | Criterio |
|----|-------|---------|
| E.0.1 | Seed alcaldias CDMX PostGIS (16 alcaldias) | ST_Contains funciona |
| E.0.2 | Seed ciudadanos sinteticos scoring (606) | voter scoring muestra datos |
| E.0.3 | Reprocess NLP sobre posts existentes | pie chart social != 100% neutral |
| E.0.4 | Seed demo data (planes, contenidos, gastos) | paginas no muestran empty |
| E.0.5 | Verificar login Pina y Solano | ambos entran y ven SOLO sus datos |

### Fase 1: Multi-Tenant 3 Orgs (~3h)
Objetivo: aislamiento real entre las 3 organizaciones.

| ID | Tarea | Criterio |
|----|-------|---------|
| E.1.1 | Crear org GOB-OAXACA y CDMX-IND en tabla organizaciones | 3 orgs existen |
| E.1.2 | Crear 4 users nuevos (Pineda, Nolasco, Jimenez, Cravioto) | login funciona para los 6 |
| E.1.3 | Crear 4 dirigentes nuevos con social_profiles | perfiles visibles en /dirigentes |
| E.1.4 | Test aislamiento RLS: user org A no ve datos org B | test explicito verde |
| E.1.5 | Admin tenant switcher en header | admin puede cambiar de org |
| E.1.6 | Watermark "DATOS SIMULACION" en orgs con datos sinteticos | visible en UI |

### Fase 2: Poblar Orgs (~4h)
Objetivo: cada org tiene datos propios para que el dashboard funcione.

| ID | Tarea | Criterio |
|----|-------|---------|
| E.2.1 | Scraping perfiles reales de los 4 nuevos dirigentes | posts reales en DB |
| E.2.2 | NLP sobre posts scrapeados | sentimiento calculado |
| E.2.3 | Ciudadanos sinteticos Oaxaca (INEGI 2020, is_synthetic=true) | scoring Oaxaca funciona |
| E.2.4 | Ciudadanos sinteticos CDMX-IND (seed diferente a MC) | scoring CDMX-IND funciona |
| E.2.5 | Generar plan IA con Gemma para cada dirigente | 6 planes, 1 por dirigente |

### Fase 3: Login + UX (~1h)
Objetivo: presentacion profesional.

| ID | Tarea | Criterio |
|----|-------|---------|
| E.3.1 | Login: 1 solo boton demo, credenciales reales privadas | login limpio |
| E.3.2 | Campos se llenan visualmente al click demo | feedback visual |

### Fase 4: War Room Pendientes (~6h)
Objetivo: completar el 20-30% que falta del War Room.

| ID | Tarea | Criterio |
|----|-------|---------|
| E.4.1 | Panel comparativo vs competidor como widget en dashboard | visible en overview |
| E.4.2 | 5 formatos guiones campo en Content Factory | formatos seleccionables |
| E.4.3 | Flash Analysis endpoint + UI | analizar actor en 5 min |

### Fase 5: Competidores (~4h, al final)
Objetivo: cada dirigente tiene sus competidores reales.

| ID | Tarea | Criterio |
|----|-------|---------|
| E.5.1 | Investigar competidores por dirigente y demarcacion | lista documentada |
| E.5.2 | Seed competidores con perfiles sociales | dropdown benchmark poblado |
| E.5.3 | Scraping perfiles competidores | datos reales para comparacion |

---

## Decisiones Tecnicas

- Gemma 3:12b local (localhost:11434) para generacion de planes IA
- RLS existente por org_id — solo necesita poblar correctamente
- Campo is_synthetic en ciudadanos para auditar datos reales vs sinteticos
- Impersonation mode para admin (ya existe endpoint POST /auth/impersonate)
- Datos MC (zip): SOLO visibles para org mc-cdmx

## Gemini Cross-Audit (2026-04-13)

Aprobado con ajustes:
- Multi-tenant ANTES de poblar datos (evitar re-migracion)
- Test aislamiento RLS obligatorio antes de crear orgs
- Watermark en orgs con datos sinteticos
- Tenant switcher con colores por org
- Campo is_synthetic para auditar mezcla datos reales/sinteticos
