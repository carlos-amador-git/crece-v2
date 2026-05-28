# PLAN · Palabras de moderación configurables por admin · 2026-05-26

**Origen:** revisión visual CEO 2026-05-26 de cards diagnóstico Tier 2 (B18 violencia, B15 hostilidad). Propuesta del CEO: mover los diccionarios de palabras agresivas a configuración para que el admin las amplíe y ajuste el "scope". Mi recomendación validada: opción (2) — primero cerrar B15 (hecho), luego este sprint.

## Problema que resuelve

Los diccionarios viven **hardcodeados** en `backend/app/services/diagnostico_tier2/_common.py`:
- `HATE_SPEECH_KEYWORDS` (21) · `VIOLENCIA_GENERO_KEYWORDS` (11) · `AMENAZAS_KEYWORDS` (11) → B18
- `RAGE_KEYWORDS` (16) → B15

Consecuencias verificadas esta sesión:
- Falso positivo "diputado→puta" (substring sin límite de palabra) — parchado con word-boundary, pero la causa de fondo es la rigidez.
- Gaps de género: "vendido" sí / "vendida" no · "ratero" sí / "ratera" no · faltan "inepta", "ladrona". Saymi da 0 pero otra dirigente mujer sí los recibiría.
- Cambiar una palabra hoy requiere edit de código + deploy. No es escalable ni per-cliente.

## Diseño (mínimo, sin gold-plating)

### Tabla `palabras_moderacion`
| col | tipo | nota |
|---|---|---|
| id | PK | |
| palabra | text | la palabra/frase (lowercase) |
| categoria | enum | `hate_speech` / `violencia_genero` / `amenaza` / `rage` |
| severidad | enum | `leve` / `medio` / `grave` (alimenta escala B18) |
| scope | enum | `exacta` (default) / `raiz` / `contiene` |
| org_id | FK nullable | null = global · con valor = override por cliente |
| activo | bool | soft-delete |
| creado_por | FK user | trazabilidad (audit_log) |
| created_at / updated_at | ts | |

### Semántica de `scope` (controla el tradeoff falso+/falso−)
- **exacta** → `\bpalabra\b` · "puta" NO matchea "diputado" ni "putada". Default seguro.
- **raiz** → `\bpalabra` · "pendej" → pendejo/pendeja.
- **contiene** → substring · amplio y riesgoso (reabre el bug del "diputado"). Requiere confirmación explícita en UI.

### Backend
- Servicio `moderacion_keywords.py`: `load_keywords(categoria, org_id)` con **cache 5 min** (cambian rara vez).
- Helper de matching por scope (reusa `_kw_hits` con word-boundary ya implementado en `violencia_politica_service.py`).
- Refactor B18 (`violencia_politica_service`) y B15 (`rage_click_service`) para leer de BD en vez de constantes `_common.py`.
- `_common.py` queda como **seed** (no se pierde nada).

### Migración
- Alembic: crea tabla + seed con las 59 palabras actuales (categoría correcta, severidad inferida: amenaza=grave, vpg=medio, hate=leve, rage=rage; scope=exacta salvo stems conocidos = raiz).

### Frontend (admin)
- Vista en `/dashboard/sistema` (Configuración): tabla CRUD con filtros por categoría.
- Form: palabra + categoría + severidad + scope (default exacta, warning al elegir "contiene").
- Botón **"Probar"**: corre el match contra los comentarios actuales y devuelve *"matchea N comentarios"* + 3 ejemplos ANTES de guardar → el admin ve el scope real y no genera ruido.

## Fases
1. Migración + tabla + seed (backend).
2. Servicio `moderacion_keywords` + cache + helper scope.
3. Refactor B18 + B15 a leer de BD (verificar paridad: mismos resultados que hoy con el seed).
4. Endpoint admin CRUD + endpoint "Probar" (count + samples).
5. Vista admin frontend.
6. Verificación E2E + deploy.

## Caveats / riesgos
- **Default scope = exacta** + warning en "contiene" → no reabrir el bug del "diputado".
- **Preview "Probar"** obligatorio antes de guardar palabra nueva.
- Cambios al diccionario → `audit_log` (quién agregó qué).
- LFPDPPP: es config de moderación, riesgo bajo; no se persisten valores de comentarios, solo reglas.

## Pendiente decisión CEO al arrancar
- ¿Severidad por palabra editable o fija por categoría? (propongo editable).
- ¿Per-org desde el inicio o global primero? (propongo global + columna org_id lista para override después).

**Estado:** PLAN escrito · NO iniciado · siguiente sprint formal tras cerrar recorrido visual de cards.
