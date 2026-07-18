# CRECE v2.0 — Instrucciones de Deploy en Coolify
## Para: Carlos Amador
## Fecha: 2026-04-06
## Servidor: 163.245.208.96 (mismo Coolify que ChatMX)

---

## Resumen

CRECE v2.0 es una plataforma de inteligencia política con:
- **Backend**: FastAPI (Python 3.12) + PostgreSQL/PostGIS + Redis + Celery
- **Frontend**: Next.js 14 (React)
- **7 servicios** Docker orquestados

El patrón es el mismo que ChatMX pero con 2 servicios públicos (frontend + backend API).

---

## PASO 1: Crear Proyecto en Coolify

1. Ir a Coolify → **Projects** → **New Project**
2. Nombre: `CRECE v2.0`
3. Descripción: `Plataforma de inteligencia electoral — MD Consultoría`

---

## PASO 2: Agregar Resource (Docker Compose)

1. Dentro del proyecto → **Add Resource** → **Docker Compose**
2. Source: **GitHub** → Repositorio: `MarxCha/crece-v2`
3. Branch: `main`
4. Docker Compose file: `docker-compose.coolify.yml` (está en la raíz)

---

## PASO 3: Generar Secretos

Ejecutar estos comandos en terminal para generar los valores:

```bash
# Password PostgreSQL
echo "POSTGRES_PASSWORD=$(openssl rand -base64 32)"

# Password Redis (no se usa directamente, Redis sin auth en red interna)
# JWT Secret
echo "JWT_SECRET=$(openssl rand -hex 64)"

# MinIO passwords
echo "MINIO_ROOT_PASSWORD=$(openssl rand -base64 32)"

# n8n webhook secret
echo "N8N_WEBHOOK_SECRET=$(openssl rand -hex 32)"
```

**Guardar todos estos valores** — los necesitarás en el paso 4.

---

## PASO 4: Configurar Environment Variables en Coolify

En Coolify → CRECE v2.0 → **Environment Variables**, pegar:

```env
# ── Base de datos ──
POSTGRES_USER=crece
POSTGRES_PASSWORD=<valor-generado-paso-3>
POSTGRES_DB=crece_production

# ── Autenticación ──
JWT_SECRET=<valor-generado-paso-3>

# ── Claude AI (pedir a Marx) ──
CLAUDE_API_KEY=sk-ant-PEDIR_A_MARX
CLAUDE_MODEL=claude-sonnet-4-20250514

# ── Groq · Llama 3.3 70B (tier gratuito · pedir a Marx) ──
# Usado por /api/v1/reels/generate-script (D-REELS-GROQ-1). Sin esta var,
# reels responde "groq_not_configured". Registro: console.groq.com (30 req/min).
GROQ_API_KEY=gsk_PEDIR_A_MARX

# ── MinIO Storage ──
MINIO_ROOT_USER=crece-minio
MINIO_ROOT_PASSWORD=<valor-generado-paso-3>

# ── n8n Integration ──
N8N_WEBHOOK_SECRET=<valor-generado-paso-3>
```

**NOTA:** `CLAUDE_API_KEY` y `GROQ_API_KEY` las proporciona Marx por canal seguro. El resto se auto-configura en el docker-compose.

---

## PASO 5: Configurar Dominios en Coolify

Configurar **2 servicios públicos** con dominio propio:

### Frontend (Dashboard)
- Servicio: `frontend`
- Dominio: `crece.mdconsultoria-ti.org`
- Puerto: `3000`
- SSL: **Habilitado** (Let's Encrypt auto)
- Force HTTPS: **Sí**

### Backend (API)
- Servicio: `backend`
- Dominio: `api-crece.mdconsultoria-ti.org`
- Puerto: `8000`
- SSL: **Habilitado** (Let's Encrypt auto)
- Force HTTPS: **Sí**

### Servicios internos (SIN dominio público)
- `db` — PostgreSQL (solo red interna)
- `redis` — Cache (solo red interna)
- `minio` — Storage (solo red interna)
- `celery-worker` — Workers (solo red interna)
- `celery-beat` — Scheduler (solo red interna)

> ⚠️ **DRIFT de command del worker (incidente 2026-07-18).** El servicio
> `celery-worker` DEBE arrancar con la MISMA lista de colas que
> `docker-compose.prod.yml:79`: **`-Q default,scrapers,nlp,data`**. Si Coolify
> tiene un command-override manual, verificar que incluya **`data`** — sin esa
> cola, los jobs de ingesta RADAR→CRECE (`radar-handoff` enruta a `data`,
> `celery_app.py:29`) quedan atorados en `RECEIVED` para siempre (ningún
> consumer). Un command-override viejo se repisa en CADA redeploy → el fix es
> corregirlo EN COOLIFY (o quitar el override y usar el del compose), no solo
> reiniciar. Verificar tras deploy: dentro del worker
> `celery -A app.workers.celery_app inspect active_queues` debe listar `data`.

---

## PASO 6: Configurar DNS

En Cloudflare (mdconsultoria-ti.org), agregar 2 registros A:

| Tipo | Nombre | Valor | Proxy |
|------|--------|-------|-------|
| A | `crece` | `163.245.208.96` | Proxied (naranja) |
| A | `api-crece` | `163.245.208.96` | Proxied (naranja) |

**IMPORTANTE:** Si usas Cloudflare Proxy, en SSL/TLS → Full (strict).

---

## PASO 7: Deploy

1. Clic en **Deploy** en Coolify
2. Monitorear logs — el build tarda ~5-8 minutos la primera vez
3. Esperar a que todos los servicios estén **healthy** (verde)

### Orden de arranque (automático):
```
db (PostgreSQL) → redis → minio → backend (uvicorn) → celery-worker → celery-beat → frontend
```

> ⚠️ **El backend NO corre migraciones automáticamente.** El `command` en
> `docker-compose.prod.yml` y el `CMD` del Dockerfile son solo `uvicorn` — no hay
> `alembic upgrade head` ni entrypoint que lo ejecute. Las migraciones se aplican a
> mano en el PASO 8.0 (abajo). Corregido 2026-05-30 tras verificar Dockerfile + compose
> + main.py.

---

## PASO 8: Post-Deploy (una sola vez)

### 8.0 Aplicar migraciones (manual — NO es automático)

En Coolify → servicio `backend` → **Terminal**:

```bash
alembic upgrade head
```

Sin esto la BD queda sin schema y todo lo demás falla. Verificar:
`SELECT version_num FROM alembic_version;` → debe dar `oc1`.

### 8.1 Datos: elegir UNA de dos vías

**Vía A — Data REAL operativa (lo que normalmente quieres para demo/piloto):**
Restaurar el snapshot **`data-snapshot-2026-06-04`** (el más reciente). Trae los 7
dirigentes con cadena completa: ~8,111 posts, ~10,005 comments, NLP (tono/emotions/
topics), reactors, followers, FODA + planes (consolidación + contenido). pg_dump v16
`-Fc`, 27 MB, 72 tablas + extensiones. Runbook: `.context/RUNBOOK-coolify-data-restore-2026-05-30.md`.

**Procedimiento SEGURO (cross-auditado Gemini 2026-06-04 — no saltarse pasos):**

```bash
# 0. PRE-VUELO: verificar que Coolify tenga las extensiones (si faltan, el restore rompe)
docker exec <pg-coolify> psql -U <USER> -d <DB> -c \
  "SELECT name, installed_version FROM pg_available_extensions WHERE name IN ('postgis','vector');"
# Si installed_version es NULL → instalar/habilitar ANTES de continuar.

# 1. BACKUP PREVIO de lo que hay HOY en Coolify (rollback · SIN esto el riesgo de pérdida es 100% ante fallo)
docker exec <pg-coolify> pg_dump -U <USER> -d <DB> -Fc > pre_restore_safety_$(date +%F).dump

# 2. Descargar el snapshot (repo privado)
gh release download data-snapshot-2026-06-04 -R MarxCha/crece-v2 -p 'crece-data-20260604.dump'
docker cp crece-data-20260604.dump <pg-coolify>:/tmp/

# 3. DETENER el container de la app (backend) — conexiones activas rompen el restore con --clean
#    (en Coolify: parar el servicio backend temporalmente)

# 4. Restore — Opción A (la más segura): a BD NUEVA, luego swap
docker exec <pg-coolify> psql -U <USER> -c "CREATE DATABASE crece_new;"
docker exec -i <pg-coolify> pg_restore -U <USER> -d crece_new --no-owner --no-privileges < /tmp/crece-data-20260604.dump
#    Opción B (misma BD): pg_restore -d <DB> --clean --if-exists --no-owner --no-privileges --disable-triggers
```
> Si usas Vía A, puedes saltarte el PASO 8.0 (el dump trae schema). Requiere Postgres ≥16
> con **postgis + pgvector**. Contiene PII → **borrar el Release tras restore confirmado**.

**5. Smoke test post-restore (Carlos reporta ANTES de dar OK):**
```sql
SELECT count(*) FROM dirigentes;        -- esperado: 7+ (los reales)
SELECT count(*) FROM social_posts;      -- esperado: ~8111
SELECT count(*) FROM social_comments;   -- esperado: ~10005
SELECT postgis_full_version();          -- postgis vivo
SELECT count(*) FROM planes_ia WHERE created_at >= '2026-06-03';  -- ~21 (FODA+planes de hoy)
```
> ⚠️ Verificar `df -h` (espacio) en el VPS. Si Coolify es Postgres alpine y local debian,
> puede haber discrepancias menores en postgis — el pre-vuelo (paso 0) las detecta.

**Vía B — Seed sintético mínimo (solo si no quieres data real):**
```bash
python scripts/seed.py
```
Crea: Admin `admin@consultoriamd.com` / `crece2026!`, 2 dirigentes de prueba
(Piña y Solano) con perfiles, y datos de benchmark/competidores.
> ⚠️ `seed.py` está congelado desde 2026-04-25 (6 dirigentes, posts sintéticos). No
> refleja la BD real. Para demo/piloto usa la Vía A.

### 8.2 Crear usuarios demo por dirigente

```bash
python -c "
import asyncio
from app.core.database import async_session_factory
from app.models.user import User
from app.core.security import get_password_hash

async def create_demo_users():
    async with async_session_factory() as db:
        for email, name, did in [
            ('pina@crece.mx', 'Alejandro Piña Medina', 1),
            ('solano@crece.mx', 'Rafael Solano Pérez', 2),
        ]:
            user = User(
                email=email,
                full_name=name,
                hashed_password=get_password_hash('crece2026!'),
                role='analyst',
                is_active=True,
                dirigente_id=did,
            )
            db.add(user)
        await db.commit()
        print('Demo users created')

asyncio.run(create_demo_users())
"
```

### 8.3 Verificar salud

```bash
# Desde tu máquina local:
curl -s https://api-crece.mdconsultoria-ti.org/api/v1/health/ | jq .
# Esperado: {"status": "healthy", ...}

# Login de prueba:
curl -s -X POST https://api-crece.mdconsultoria-ti.org/api/v1/auth/login \
  -d "username=admin@consultoriamd.com&password=crece2026!" \
  | jq .access_token
# Esperado: un JWT token
```

### 8.4 Verificar frontend

Abrir: `https://crece.mdconsultoria-ti.org`
- Debe mostrar la landing page
- Login con `admin@consultoriamd.com` / `crece2026!`
- Dashboard debe cargar con datos

---

## PASO 9: Activar n8n Scraping (ver documento aparte)

Ya hay instrucciones detalladas en: `.context/N8N-SCRAPING-AUTOMATICO.md`

Resumen rápido:
1. Crear credential "CRECE API" en n8n con el JWT token
2. Crear workflow de scraping diario (6am)
3. Activar los 6 workflows ya importados

---

## Verificación Final (Checklist)

| Servicio | URL/Comando | Esperado |
|----------|-------------|----------|
| Frontend | `https://crece.mdconsultoria-ti.org` | Landing page carga |
| Login | Login con admin@ | Dashboard con KPIs |
| API Health | `curl https://api-crece.../health/` | `{"status":"healthy"}` |
| DB | Coolify → db → Logs | `ready to accept connections` |
| Redis | Coolify → redis → Logs | `Ready to accept connections` |
| Workers | Coolify → celery-worker → Logs | `celery@... ready` |
| Beat | Coolify → celery-beat → Logs | `beat: Starting...` |

---

## Troubleshooting

### Build falla en frontend
```
Error: Cannot find module 'sharp'
```
→ Normal en Alpine. El Dockerfile ya incluye `--platform=linux/amd64`. Verificar que Coolify buildea para amd64.

### Backend no conecta a DB
```
sqlalchemy.exc.OperationalError: connection refused
```
→ El servicio `db` no arrancó. Verificar logs de PostgreSQL. El `depends_on` con healthcheck debería prevenir esto.

### CORS errors en browser
→ Verificar que `CORS_ORIGINS` en el docker-compose incluye el dominio exacto del frontend (ya configurado como `https://crece.mdconsultoria-ti.org`).

### Backend arranca pero la BD está vacía / errores de tabla inexistente
→ El backend NO corre migraciones solo. Ejecutar `alembic upgrade head` a mano
  (PASO 8.0), o restaurar el dump de la Vía A (que trae el schema).

### Frontend muestra "Sin datos"
→ Falta cargar datos (PASO 8.1). Vía A (restore data real) o Vía B (seed sintético).
  Sin esto no hay dirigentes ni perfiles sociales.

---

## Arquitectura de Servicios

```
                    Cloudflare DNS
                    ┌─────────────────────────┐
                    │ crece.mdconsultoria-ti   │
                    │ api-crece.mdconsultoria  │
                    └──────────┬──────────────┘
                               │
                    Coolify (Traefik)
                    ┌──────────┴──────────────┐
                    │     SSL + Routing        │
                    └──┬──────────────────┬───┘
                       │                  │
              ┌────────▼───┐    ┌────────▼────┐
              │  Frontend  │    │   Backend   │
              │  Next.js   │    │   FastAPI   │
              │  :3000     │    │   :8000     │
              └────────────┘    └──┬───┬──────┘
                                   │   │
                          ┌────────┘   └────────┐
                     ┌────▼────┐          ┌─────▼────┐
                     │   DB    │          │  Redis   │
                     │ PostGIS │          │  :6379   │
                     │ :5432   │          └──┬───────┘
                     └─────────┘             │
                                    ┌────────┴────────┐
                               ┌────▼─────┐    ┌─────▼────┐
                               │  Worker  │    │   Beat   │
                               │  Celery  │    │  Celery  │
                               │ scrapers │    │ schedule │
                               └──────────┘    └──────────┘
```

---

## Contacto

- **Marx (CEO/Tech Lead)**: Cualquier duda de configuración o API keys
- **Repo**: github.com/MarxCha/crece-v2 (branch: main)
- **Patrón de referencia**: Deploy de ChatMX en el mismo servidor
