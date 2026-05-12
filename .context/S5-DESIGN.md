# Sprint 5 — Wizard Onboarding Político — Diseño

**Estado:** Diseño + esqueletos. Ejecución completa requiere sesión dedicada (1.5 días).

## Rutas
- `/dashboard/sistema/onboarding` — solo admin. NO top-level `/admin`.

## Endpoints backend

### `POST /dirigentes/onboard`
Request:
```json
{
  "nombre": "Luis Pérez",
  "cargo": "Diputado Local",
  "estado": "CDMX",
  "municipio": "Coyoacán",
  "handles": {
    "INSTAGRAM": "@luisperez",
    "TWITTER": "@luisperezmx",
    "FACEBOOK": "Luis Pérez Oficial"
  }
}
```

Flujo transaccional:
1. Crea `User` con `org_id` (heredado del admin)
2. Crea `Dirigente` scopado a ese `org_id`
3. Crea `SocialProfile` por cada handle
4. Dispara Celery chain:
   `scrape_initial_profile` → `run_nlp_batch` → `calculate_ipd`
5. Retorna `{dirigente_id, task_chain_id}`

### `GET /dirigentes/{id}/onboarding-progress`
Response:
```json
{
  "overall": 0.65,
  "stages": [
    {"name": "scrape_instagram", "status": "done", "duration_ms": 12500},
    {"name": "scrape_twitter", "status": "done", "duration_ms": 8200},
    {"name": "nlp_processing", "status": "in_progress"},
    {"name": "ipd_calculation", "status": "pending"}
  ]
}
```

Polling cada 2s desde el frontend hasta que `overall === 1.0`.

### `POST /auth/impersonate/{dirigente_id}` (admin only)
Devuelve token temporal con scope del dirigente nuevo. Admin cae en `/dashboard` viendo exactamente lo que verá el cliente. Auto-login S5.5.

## Frontend

### `OnboardingWizard` (3 pasos)
Step 1 — Datos básicos: nombre, cargo, org, estado, municipio.
Step 2 — Handles por plataforma con validación en vivo (pre-scraping ligero para validar que la cuenta existe). Preview del perfil scrapeado en tiempo real.
Step 3 — Confirmación + botón "Crear y scrapear".

### Progress UI
Componente `OnboardingProgressPanel` con:
- Barra general
- Lista de etapas con iconos (scraping IG ✓, Twitter ✓, NLP ⏳, IPD ⏳)
- Botón "Abrir dashboard" habilitado al 100%

### Test E2E
`frontend/e2e/onboarding.spec.ts`:
1. Admin login
2. Navigate `/dashboard/sistema/onboarding`
3. Fill wizard con cuenta real (test fixture)
4. Espera progreso
5. Verifica `/dashboard` popula con datos

## Dependencias duras
- **S1.2** (RLS verificado) es prerequisito. Sin esto el onboarding puede romper aislamiento multi-tenant.
- Cuentas test no deben ser reales — usar stubs controlados o perfiles de dev explícitos.
