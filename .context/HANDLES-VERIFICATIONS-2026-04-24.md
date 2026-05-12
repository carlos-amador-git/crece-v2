# Verificaciones manuales de social_profiles · 2026-04-24

**Propósito:** registrar el contexto/razón de cada verificación manual aplicada a `social_profiles.is_confirmed`. La tabla no tiene columna `verification_note` (cumplir regla "NO schema changes" per instrucción CEO 2026-04-24) · este doc es el SSOT de razones.

---

## 2026-04-24 · Cravioto Instagram · id=21

| Campo | Valor |
|---|---|
| dirigente | César Cravioto Romero (id=6) |
| platform | INSTAGRAM |
| handle | `@cesarcravioto` |
| url | `https://www.instagram.com/cesarcravioto/` |
| cambio SQL | `UPDATE ... SET is_confirmed = true, last_manual_update = NOW() WHERE id = 21;` |
| motivo | Verificado visualmente por CEO (Marx Chávez) el 2026-04-24 · handle correcto es `@cesarcravioto` (no `@craviotocr` ni `@cesar_craviotor` que probó Chrome AI · ambos false negatives) |
| evidencia contra | BD tenía 50 posts reales con IDs IG válidos, contenido coherente mencionando `@clara_brugada_m` (Jefa Gob CDMX), fechas 2026-04-11/12/13 previas al scrape · no-sintético |
| lección operativa | **Handles por plataforma, no handle único inferido** · cada plataforma requiere verificación independiente antes de scraping · Cravioto tiene `cesarcravioto` en IG pero `cesar_craviotor` en TikTok y `craviotocesar` en X (handles divergentes entre plataformas · patrón común en political accounts) |

---

## Uso futuro

Cuando se ejecute `UPDATE social_profiles SET is_confirmed = ...` manualmente, agregar entrada aquí con:
1. Cambio SQL exacto
2. Motivo documentado
3. Evidencia
4. Lección operativa si aplica

Reemplazo temporal por `verification_note` column que Joy puede agregar en F1.1 o sprint subsecuente si se decide.
