# RUNBOOK — Alta de actores políticos (dirigentes) · CRECE v2

**Para:** operadores (deploy/Carlos, agentes, CEO). **Origen:** ADR-0009 + incidente alta
Hannah 2026-07-16 (org duplicada por partido + rol sin asignar).
**Regla de oro:** org ≠ partido ≠ rol. Cada eje responde UNA pregunta.

## Antes de crear NADA — 3 preguntas en orden

### 1 · ¿Qué ORG (tenant)? — "¿quién paga y quién debe VER estos datos?"
- Buscar org existente: `SELECT id, nombre, slug FROM organizaciones WHERE is_active;`
- ¿El nuevo dirigente comparte contrato/equipo/acceso con dirigentes ya existentes?
  → usar ESA org (por `slug`, no por id — los ids divergen entre ambientes).
- ¿Cliente nuevo que no debe ver ni ser visto por otros? → org NUEVA con **nombre
  comercial** (cliente/equipo/campaña). PROHIBIDO nombrarla por partido a secas
  ("Morena" ❌ · "Equipo Hannah de Lamadrid" ✅).
- NUNCA agrupar por afinidad política: dos clientes del mismo partido con contratos
  distintos = dos orgs.

### 2 · ¿Qué PARTIDO? — hecho del mundo
String tal como el partido se identifica ("MORENA", "MC", "PAZ"). No inventa rol.

### 3 · ¿Qué ROL_POLITICO? — "¿con qué fórmula se le califica?" (OBLIGATORIO)
∈ `oficialismo` · `oposicion` · `independiente`, calibrado a SU plaza principal:
- Gobierna su plaza o su partido la gobierna (MORENA en CDMX/Oaxaca hoy) → `oficialismo`.
- Compite contra quien gobierna su plaza (MC en CDMX hoy) → `oposicion`.
- Partido nuevo/sin bloque claro (PAZ) → `independiente`.
- Duda real → preguntar al CEO ANTES del alta. El KPI "Actividad Política Alineada"
  y el NLP usan este campo — mal asignado = cliente calificado con fórmula equivocada.

## Alta (wizard admin o API)
`POST /api/v1/dirigentes/onboard` con `org_id` + `rol_politico` + handles. El backend
rechaza (422) sin rol o sin org resoluble. El scraping inicial arranca solo.

## Verificación post-alta (obligatoria, 1 query)
```sql
SELECT d.id, d.full_name, d.partido, d.rol_politico, o.nombre, o.slug
FROM dirigentes d JOIN organizaciones o ON o.id = d.org_id
WHERE d.id = <nuevo_id>;
```
Rol NULL o org equivocada → corregir vía PATCH (org_id/rol: admin) ANTES de entregar acceso.

## Anti-patrones (todos ocurrieron de verdad)
- ❌ Crear org por partido cuando ya existe tenant para ese cliente (Hannah 2026-07-16).
- ❌ Alta sin rol → KPI con fórmula indefinida (Pepe/Ivette/Harp, detectado 2026-07-16).
- ❌ Referenciar orgs por id numérico en scripts/mensajes cross-ambiente (org 6 local=test,
  org 6 deploy=Morena).
- ❌ Password default de demos (`demo2026!`) para cliente real sin decisión explícita del CEO.
