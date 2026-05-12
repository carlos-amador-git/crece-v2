# Audit — Endpoints que ignoran el usuario autenticado

**Fecha:** 2026-04-14
**Contexto:** derivado del fix P0 #5 (data leak `GET /dirigentes/{id}`). El endpoint
afectado tenía la firma `_current_user: Annotated[User, Depends(get_current_user)]`
— el underscore indica que el objeto User se carga para satisfacer el Depends
pero no se lee. Eso deshabilita cualquier check de scope (org_id, dirigente_id,
role).

Este archivo lista los otros endpoints con el mismo patrón. No todos son leaks —
algunos operan sobre data global sin necesidad de scope (ej. benchmark de
competidores públicos). Pero cada uno debe auditarse manualmente en el próximo
sprint de seguridad.

## Criterios de triage sugeridos

- **Leak confirmado:** el endpoint devuelve data sensible por `org_id`/`dirigente_id`
  y cualquier user autenticado puede pedirla. Ej. `GET /dirigentes/{id}` (YA FIJADO).
- **Revisar:** operates over multi-tenant data but may accidentally leak cross-org.
- **Aceptable:** data global (alcaldías, catálogos, métricas públicas).

## Lista (salida de `grep -rn "_current_user: Annotated\[User" backend/app/api/v1/endpoints/`)

```
backend/app/api/v1/endpoints/geo.py:22:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/metricas_sociales.py:26:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/metricas_sociales.py:44:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/electoral.py:29:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/electoral.py:75:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/social.py:116:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/benchmark.py:29:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/benchmark.py:66:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/benchmark.py:134:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/osint.py:60:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/ciudadanos.py:30:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/ciudadanos.py:96:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/ciudadanos.py:129:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/ciudadanos.py:164:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/ciudadanos.py:197:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/contenido.py:138:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/canvassing.py:155:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/canvassing.py:196:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/canvassing.py:286:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/bot_detection.py:33:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/blindaje.py:42:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/blindaje.py:233:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/blindaje.py:337:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/blindaje.py:352:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/campanas.py:41:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/campanas.py:115:    _current_user: Annotated[User, Depends(get_current_user)],
backend/app/api/v1/endpoints/campanas.py:349:    _current_user: Annotated[User, Depends(get_current_user)],
...
```

## Candidatos prioritarios a auditar

- **`canvassing.py`** (3 endpoints) — rutas y puntos por `encuestador_id`/`org_id`.
- **`ciudadanos.py`** (5 endpoints) — data PII por org, muy sensible.
- **`blindaje.py`** (4 endpoints) — fondos + trazabilidad de gastos electorales.
- **`campanas.py`** (3 endpoints) — campañas segmentadas por org.
- **`contenido.py`** — biblioteca de contenido por dirigente.
- **`social.py:116`** — posts segmentados por profile/dirigente.

## Candidatos probablemente OK (data global)

- `geo.py`, `electoral.py` — secciones INE públicas, sin org_id.
- `benchmark.py` — competidores globales.
- `osint.py` — fuentes abiertas.
- `metricas_sociales.py` — depende del profile_id (hay que verificar).
- `bot_detection.py` — servicio stateless sobre handles públicos.

## Siguiente paso

Sprint dedicado de seguridad: revisar cada endpoint, decidir si necesita
`current_user` activo, aplicar checks `org_id`/`dirigente_id`/role y cubrir
con tests de integración cross-tenant (analyst-A pide data-B → 403).
