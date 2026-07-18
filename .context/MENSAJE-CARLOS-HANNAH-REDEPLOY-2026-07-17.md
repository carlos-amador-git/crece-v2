# Mensaje para Carlos — Hannah + redeploy con migración de rol político · 2026-07-17

**De:** Marx / Linda (CRECE). **Contexto:** decisiones cerradas del CEO sobre el alta de
Hannah de Lamadrid y cambios nuevos en `origin/main` que afectan tu ambiente.

## Decisiones sobre Hannah (aplicar en tu ambiente)

1. **Cliente aparte — la org propia se queda, pero renómbrala comercial.** No debe llamarse
   "Morena" a secas: el partido no es el tenant (ya nos mordió — en la BD local el id 6 es
   otra cosa). Sugerencia: `nombre = "Equipo Hannah de Lamadrid"`, `slug = "equipo-hannah-de-lamadrid"`.
   **[APLICADO 2026-07-17 en prod — slug canónico CON "de".]**
   A partir de ahora referencia orgs SIEMPRE por `slug`, nunca por id numérico.
2. **Display name:** PATCH a **"Hannah de Lamadrid"** (con doble n, como sus handles).
3. **Rol político:** asígnale `rol_politico = 'oficialismo'`. Es crítico: este campo define
   con qué fórmula la califica la app (el KPI de Actividad Alineada y el NLP dependen de él).
   Sin él, tras la migración el registro no pasa el constraint.
4. **Password:** se queda como está (decisión de Marx).

## Redeploy (cambios en origin/main)

- `fix(api) b303329` — BUG-CRECE-1: `POST /dirigentes/` ya no crea huérfanos (org_id nunca
  NULL) y `PATCH` permite reasignar org (solo admin). Analyst quedó org-scoped.
- `feat(actores) 0ae8829` — ADR-0009: `rol_politico` obligatorio en el alta (el wizard ahora
  pide partido y rol), org sin defaults mágicos (sin org resoluble → 422), y KPI con badge
  "Rol político sin clasificar" en vez de números con fórmula equivocada.

**Pasos:** (1) pull/redeploy → (2) `alembic upgrade head` (migración `5a6505d74dc7`:
backfill de roles NULL por partido + NOT NULL) → (3) verificar:

```sql
SELECT d.id, d.full_name, d.partido, d.rol_politico, o.nombre, o.slug
FROM dirigentes d LEFT JOIN organizaciones o ON o.id = d.org_id
ORDER BY d.id;
```

Cero `rol_politico` NULL y Hannah en su org renombrada = listo.

## Referencia

Guía completa de altas futuras: `.context/governance/RUNBOOK-alta-actores.md` (3 preguntas:
org por contrato, partido como hecho, rol por plaza — con anti-patrones reales).
Decisión de fondo: `docs/adr/0009-actores-politicos-org-partido-rol.md`.
