# DISEÑO — Modelado y gobernanza de actores políticos · 2026-07-16

**Método:** `/verifica --diseño` tríada (Claude + Gemini/agy + GPT/Codex) · deliberación
independiente anti-anclaje → síntesis → ronda de consenso. **Resultado: CONSENSO 3/3 en 2 rondas.**
**Disparador:** alta de Hannah de Lamadrid (MORENA, Coyoacán) con org nueva "Morena" en deploy +
3 dirigentes con `rol_politico NULL` en BD + CEO: "el oficialismo en la app no se califica igual
que los opositores".
**Evidencia base:** `models/dirigente.py:76-78` · `nlp/political_llm_prompt.py:46` ·
`services/political_framework.py` · D-23-H (DECISIONS.md:1040) · query roster 2026-07-16.
**Artefactos de la deliberación:** scratchpad sesión `839268d5` (`diseno-*.md`, R1+R2 completas).

## Decisión de diseño (pendiente ratificación CEO → ADR)

### 1 · Tres ejes, función única — "org ≠ partido ≠ rol"
| Eje | Pregunta que responde | Regla |
|---|---|---|
| `org_id` | ¿Quién paga y quién VE estos datos? | Tenant comercial/acceso. JAMÁS afinidad política. Naming por cliente/contrato (nunca "Morena" a secas). Referencia SIEMPRE por `slug` — los ids numéricos divergen entre ambientes (medido: org 6 local=test RLS, org 6 deploy=Morena). |
| `partido` | ¿Qué identidad política declara? | Hecho del mundo. String hoy; catálogo `partidos` con aliases = futuro. |
| `rol_politico` | ¿Con qué fórmula se califica? | Parámetro del motor (KPI D-23-H + prompts NLP + framework). Explícito, humano, auditado, calibrado a la PLAZA principal del dirigente. NUNCA derivación silenciosa. |

### 2 · Alta sin huecos — orden de implementación
1. **Backfill manual** de NULL actuales: Ivette (58) y Harp (59) → `oficialismo`;
   **Pepe (57, PAZ) → decisión CEO** (valida el override manual). Hannah (env deploy) → `oficialismo`.
   Verificación: 0 dirigentes reales con rol NULL.
2. **Campo obligatorio en alta:** `rol_politico` requerido en `DirigenteCreate` +
   `OnboardingRequest` + wizard UI. Sin rol → 422.
3. **NOT NULL en BD** (migración post-backfill).
4. **Fallo visible, nunca número falso:** KPI/NLP con rol NULL no computa — badge "sin
   clasificar" (extensión de D-ANTI-MOCK-1). **Incluye agregados**: un dirigente sin rol
   no entra a dashboards agregados con apariencia válida (precisión Codex R2).
5. *(Iteración siguiente)* Catálogo seed `partido×ámbito→rol` como SUGERENCIA pre-llenada
   en el wizard — el humano confirma; sugerencia visible ≠ auto-persistencia.
6. **Trazabilidad** al asignar rol: quién/cuándo/manual-vs-sugerido (patrón audit
   `last_modified_*` de `pesos_target_politico`).

### 3 · Multi-nivel
UN rol principal por dirigente hoy (plaza documentada). Multi-rol por ámbito
(`dirigente_roles_contextuales`) DIFERIDO — romper D-23-H/prompts/UI no se justifica aún.

### 4 · Gobernanza
- ADR nuevo (org≠partido≠rol + slug + naming) — requiere ratificación CEO.
- Seed idempotente de organizaciones canónicas POR SLUG (sin reserva rígida de rangos de id).
- Runbook de alta de actores para operadores de deploy (el error de hoy es la motivación).
- CEO decide política; agente propone con fuente; cliente solo overrides auditados en su tenant.
- `competidores` sigue diferido (B-COMPETIDORES-MODELO-1). Dirigentes-referencia (Máynez)
  también llevan rol NOT NULL.

### 5 · Caso Hannah (aplicación)
`partido=MORENA` · `rol_politico=oficialismo` (plaza CDMX) · display "Hannah" (doble-n,
confirmado CEO por imagen) · **tenant = decisión de contrato del CEO**: ¿comparte acceso
con Gaby/Cravioto (→ slug `cdmx-independiente`) o cliente aparte (→ org propia con nombre
comercial)? La org "Morena" del deploy se renombra/reasigna según eso.

## Riesgo #1 (acordado 3/3)
Scoring silenciosamente mal: rol NULL o mal asignado produce KPIs con apariencia válida.
HOY activo en 3 dirigentes (Pepe/Ivette/Harp). Por eso el paso 4 es diseño, no adorno.

## Decisiones que quedan del CEO
1. Rol de Pepe Monroy (PAZ): ¿independiente/oposición/oficialismo local?
2. Tenant de Hannah: ¿org 3 (`cdmx-independiente`) o propia?
3. ¿D16 default org: la 3 (CDMX Independiente, comportamiento actual) era la intención,
   o debía ser MC CDMX (org 1)? (comentario del código contradice BD).
4. GO a implementar pasos 1-4 (sprint chico, ~1 sesión).
