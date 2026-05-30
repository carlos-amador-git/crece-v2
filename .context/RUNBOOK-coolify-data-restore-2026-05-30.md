# RUNBOOK — Cargar data operativa real en Coolify (para Carlos Amador)

**Fecha:** 2026-05-30 · **Generado por:** sesión CRECE local
**Problema raíz:** el deploy de Coolify NO popula la BD (el `command` del backend en
`docker-compose.prod.yml` es solo `uvicorn`; no corre `migrate` ni `seed`). Además
`seed.py` quedó congelado el 2026-04-25 con 6 dirigentes + posts sintéticos. Toda la
data operativa real (13 dirigentes, 5 orgs, 7.1k posts, 8.1k comments, NLP) vive solo
en la BD local `:5438` y nunca tuvo pipeline hacia Coolify.

## Artefacto

- `crece-data-20260530.dump` — pg_dump **v16**, formato custom `-Fc`, 23 MB comprimido
  (159 MB descomprimido). Contiene: schema completo + data + extensiones
  (postgis, pgvector) + `alembic_version = oc1`.
- Cobertura: organizaciones (5), dirigentes (13), users, social_profiles,
  social_posts (7,161), social_comments (8,133), sentiment_analyses (2,708),
  watched_profiles (~91k), watched_like_events (~185k), planes_ia, plan_tareas,
  topic_trends, contenido_piezas, snapshots.

## Precondiciones (verificar ANTES de restaurar)

1. **Imagen Postgres de Coolify DEBE tener postgis + pgvector.** El dump hace
   `CREATE EXTENSION postgis, pgvector`. Si la BD de Coolify es postgres oficial sin
   esas extensiones, el restore falla. Imagen local de referencia:
   `crece-db:16-postgis-pgvector`.
2. **Postgres server ≥ 16** en Coolify (el dump es v16).
3. **Coolify = entorno demo** (no piloto). Este restore PISA la data existente de la
   BD de Coolify. Confirmar que no hay data que rescatar ahí.

## Restore (BD de Coolify)

```bash
# 1. Descargar el asset (desde el release de GH donde se publicó)
gh release download <tag> -p 'crece-data-20260530.dump'

# 2. Copiar el dump al container de Postgres de Coolify
docker cp crece-data-20260530.dump <coolify-postgres-container>:/tmp/

# 3. Restaurar PISANDO lo existente (paridad total con local)
docker exec <coolify-postgres-container> \
  pg_restore --clean --if-exists --no-owner --no-privileges \
  -U <POSTGRES_USER> -d <POSTGRES_DB> /tmp/crece-data-20260530.dump
```

- `--clean --if-exists`: dropea objetos previos antes de recrear → reemplazo total.
- `--no-owner --no-privileges`: evita errores si el rol de Coolify difiere del local (`crece`).
- El dump trae el schema, así que **no requiere** correr migrations antes. Restaurar
  sobre BD vacía es lo más limpio.

## Verificación post-restore

```sql
SELECT count(*) FROM dirigentes;        -- esperado: 13
SELECT count(*) FROM organizaciones;    -- esperado: 5
SELECT count(*) FROM social_posts;      -- esperado: 7161
SELECT version_num FROM alembic_version;-- esperado: oc1
```

## Los 3 que pidió Carlos (ya incluidos en el dump)

| id | full_name | cargo | partido | estado | municipio | org_id |
|----|-----------|-------|---------|--------|-----------|--------|
| 8  | Laura Ballesteros Mancilla | Diputada Federal Plurinominal MC LXVI Legislatura | MC | Ciudad de México | — | 1 |
| 57 | Pepe Monroy | Líder Nacional de Partidos Políticos Locales | PAZ | Nacional | — | 4 |
| 60 | Felipe de Jesús Martínez Gómez | Síndico | MORENA | Estado de México | Nicolás Romero | 5 |

> Nota: dir 60 en BD es **Felipe de Jesús Martínez Gómez**, no "Felipe Martínez
> Gallegos". orgs 4 (Proyecto PAZ) y 5 (Gobierno Nicolás Romero) son FK de 57 y 60 y
> también faltaban en seed.py — el dump las incluye.

## Deuda de fondo a cerrar (aparte de este restore)

1. `make seed` apunta a `app.scripts.seed` (módulo inexistente; el real es
   `scripts.seed`). Corregir.
2. El deploy de prod no corre migrate ni seed. Decidir si se añade un init step en
   Coolify o se documenta el restore como paso manual post-deploy.
3. Definir flujo recurrente repo↔data para que esto no vuelva a divergir.
