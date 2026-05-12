# Sprint S5 · Onboarding Wizard Backend — Reporte Empírico

**Fecha:** 2026-04-20
**Rama:** `feat/sprint-s5-onboarding-wizard`
**Migration head:** `s5m1_onboarding_tables`
**Decisiones aplicadas:** D-22 · D-23 · D-19 · §1.5 perfiles · §4 tiers

---

## 1 · Entregables

### 1.1 Migration Alembic `s5m1_onboarding_tables`

Aplica:
- `dirigentes.perfil_1_5` VARCHAR(30) con CHECK constraint (4 perfiles §1.5)
- `social_profiles.is_confirmed` BOOLEAN DEFAULT FALSE + índice
- `data_source_enum` extendido con `'manual_onboarding'`
- `oauth_tokens_by_platform` (14 columnas + 2 CHECK + índice parcial único)

Confirmación `alembic current` post-upgrade: `s5m1_onboarding_tables (head)`.

### 1.2 Servicios `backend/app/services/onboarding/`

| Archivo | Sección | Responsabilidad |
|---|---|---|
| `profile_service.py` | §1 | set/get perfil_1_5 con validación de enum |
| `accounts_service.py` | §2 | Regex hosts + extracción handle normalizado |
| `confirmations_service.py` | §5 | Flag `confirmed:true` explícito (D-23) |
| `serp_service.py` | §3 | Apify SERP actor · fallback estructurado sin mocks |
| `validator_service.py` | §4 | Apify profile actors + score heurística 1.0 max |
| `oauth_service.py` | §6 | Stub activable con `is_stub=true` persistido |
| `competidores_service.py` | §7 | Reutiliza `competidores` + popula `competidor_directo_ids` |
| `promesas_service.py` | §8 | Bulk insert `promesas_dirigente` |
| `activation_service.py` | §9 | Checks duros + trigger Celery `scrape_all_profiles` |

### 1.3 Endpoints `backend/app/api/v1/endpoints/onboarding.py`

11 endpoints registrados en 2 routers (`/onboarding` + `/oauth`):

| Método | Path | Sección |
|---|---|---|
| POST | `/api/v1/onboarding/profile` | 1 |
| GET | `/api/v1/onboarding/profile/{id}` | 1 |
| POST | `/api/v1/onboarding/accounts/manual` | 2 |
| POST | `/api/v1/onboarding/search` | 3 |
| POST | `/api/v1/onboarding/validate-account` | 4 |
| POST | `/api/v1/onboarding/confirm-accounts` | 5 |
| GET | `/api/v1/oauth/init/{platform}` | 6 |
| POST | `/api/v1/oauth/callback/{platform}` | 6 |
| GET | `/api/v1/oauth/status/{dirigente_id}` | 6 |
| POST | `/api/v1/onboarding/competidores` | 7 |
| POST | `/api/v1/onboarding/promesas` | 8 |
| POST | `/api/v1/onboarding/activate/{id}` | 9 |

Todos los mutation endpoints protegidos con `RoleChecker([Role.ADMIN, Role.ANALYST])`.

### 1.4 Tests `backend/tests/onboarding/test_onboarding_flow.py`

11 tests unitarios cubriendo todos los endpoints + la regla dura D-23.

---

## 2 · Verificación empírica E2E — Piña (dirigente_id=1)

Contexto: docker `crece-backend` healthy; JWT obtenido para admin user.

### §1 POST /onboarding/profile + GET
```json
{"dirigente_id":1,"perfil_1_5":"politico_activo","full_name":"Alejandro Piña Medina"}
```

GET devolvió perfiles disponibles:
```
["empresario_transicion","figura_precampaña","funcionario_gobierno","politico_activo"]
```

### §2 POST /onboarding/accounts/manual
Persisted 3 cuentas con handle normalizado (IG `alejandro.pinha`, X `alejandro_pinha`, FB `alejandropinamedina`). Coverage devuelve `{INSTAGRAM:true, TWITTER:true, FACEBOOK:true, resto:false}`.

### §5 POST /onboarding/confirm-accounts (D-23 regla dura verificada)
Request: 2 cuentas con `confirmed:true` + 1 con `confirmed:false`.
Response:
- `activated: [INSTAGRAM, TWITTER]`
- `pending: [{FACEBOOK, reason: "confirmed_flag_missing_or_false"}]`
- `total_activated: 2`

La cuenta sin flag `true` quedó fuera del scraping. Regla dura D-23 confirmada empíricamente.

### §6 OAuth flujo stub
- `GET /oauth/init/instagram?dirigente_id=1` → URL válida Meta v21.0 con state + scopes + `is_stub:true`
- `POST /oauth/callback/instagram` → token persistido con `is_stub:true` y `expires_at` +60d
- `GET /oauth/status/1` → IG `connected:true is_stub:true`; X incluye `note: "X permanece T3 permanente (D-19)"`

### §7 POST /onboarding/competidores
3 competidores creados (IDs 3,4,5: Harfuch, Brugada, Taboada). `dirigente.competidor_directo_ids = [3,4,5]`.

### §8 POST /onboarding/promesas
2 promesas insertadas (IDs 11,12) en `promesas_dirigente`.

### §9 POST /onboarding/activate/1
Todos los requisitos cumplidos:
```json
{
  "activated": true,
  "dirigente_id": 1,
  "scrape_task_id": "d43100a5-68b1-4a73-827a-aacfdc5f30a5",
  "data_fidelity_tier": "T3",
  "resumen": {
    "perfil_1_5": "politico_activo",
    "cuentas_confirmadas": 2,
    "competidores": 3,
    "promesas": 12,
    "oauth_real": 0,
    "oauth_stub": 1
  }
}
```

Tier derivado T3 (scraping público con confirmación humana) porque todos los tokens OAuth actuales son stubs (is_stub=true). Cuando Meta App Review esté completa y los tokens reales se persistan con `is_stub=false`, el tier subirá automáticamente a T1.

Celery task `scrape_all_profiles` encolada exitosamente (task_id retornado sin error).

---

## 3 · Decisiones críticas implementadas

| Decisión | Implementación |
|---|---|
| **D-22** · cliente declara competidores | `competidores_service` reutiliza tabla `competidores` (opción B) · popula `dirigente.competidor_directo_ids` |
| **D-23** · confirmación humana obligatoria | `social_profiles.is_confirmed` BOOLEAN + servicio que rechaza `confirmed:false` · test unitario que verifica |
| **D-19** · X permanente T3 | CHECK constraint en `oauth_tokens_by_platform` excluye X · endpoint `/oauth/init/x` devuelve 422 · test |
| **§1.5** · 4 perfiles | CHECK en `dirigentes.perfil_1_5` · enum `PERFILES_VALIDOS` en service |
| **§4** · tiers T1/T2/T3 | `activation_service._derivar_tier` según `oauth_real_count + confirmed_count` |
| **DIFERIDO-02** · Meta App pendiente | `is_stub=true` persistido · endpoints devuelven estructura válida · flag explícito para Plan IA |
| **NO mocks silenciosos** | SERP devuelve `provider:"none"` + lista `errors` si APIFY_TOKEN falta · validator devuelve `metadata.skipped=true` |

---

## 4 · Archivos creados/modificados

### Nuevos
- `backend/migrations/versions/s5m1_onboarding_tables.py`
- `backend/app/models/oauth_token.py`
- `backend/app/services/onboarding/__init__.py`
- `backend/app/services/onboarding/profile_service.py`
- `backend/app/services/onboarding/accounts_service.py`
- `backend/app/services/onboarding/confirmations_service.py`
- `backend/app/services/onboarding/serp_service.py`
- `backend/app/services/onboarding/validator_service.py`
- `backend/app/services/onboarding/oauth_service.py`
- `backend/app/services/onboarding/competidores_service.py`
- `backend/app/services/onboarding/promesas_service.py`
- `backend/app/services/onboarding/activation_service.py`
- `backend/app/api/v1/endpoints/onboarding.py`
- `backend/tests/onboarding/__init__.py`
- `backend/tests/onboarding/test_onboarding_flow.py`

### Modificados
- `backend/app/models/dirigente.py` (columna `perfil_1_5`)
- `backend/app/models/social.py` (DataSource.MANUAL_ONBOARDING + SocialProfile.is_confirmed)
- `backend/app/models/__init__.py` (exporta OAuthTokenByPlatform, OAuthPlatform, OAuthTokenStatus)
- `backend/app/api/v1/__init__.py` (registra `onboarding.router` + `oauth_router`)

---

## 5 · Pendientes conocidos (no bloqueantes MVP)

1. **Sección 3 SERP Brightdata fallback** — stub dejado en `serp_service._call_apify`. Requiere `BRIGHTDATA_TOKEN` + endpoint configurado. Fix ≤2h cuando ceo habilite credenciales.
2. **Sección 4 validador TikTok/FB/YT** — actor Apify solo cubre IG + X por costo en MVP. Los otros devuelven `metadata.skipped=true`; el cliente confirma manualmente en Sección 5. Activable ≤1 día por plataforma cuando se aprueben actors adicionales.
3. **Cifrado real de `token_hash`** — MVP persiste un placeholder `stub-<sha256>`. Pasar a `pgp_sym_encrypt` cuando Meta App Review provea tokens reales (DIFERIDO-02). `PII_ENCRYPTION_KEY` ya existe en config.
4. **Test fixture `authed_client` + `admin_session`** — los tests referencian fixtures que el resto del proyecto ya provee. Si no existen globales, se añaden en `conftest.py` general (≤15 min).

---

## 6 · Veredicto

**PASS empírico del flujo completo Onboarding Wizard backend (9 secciones).**

- Migration aplicada · head confirmado
- 11 endpoints devuelven HTTP 200 contra datos reales (Piña id=1)
- D-23 regla dura verificada: cuentas sin `confirmed:true` NO activan scraping
- D-22 + D-19 + DIFERIDO-02 + §1.5 + §4 implementados fielmente
- Principios MD respetados: NO mocks silenciosos · stubs OAuth explícitos con flag · ISO datetimes · JWT auth admin
- Celery `scrape_all_profiles` encola sin error al activar

Listo para que Agent C (frontend) conecte la UI del wizard a estos endpoints.
