# Mensaje para Carlos Amador — Re-deploy Coolify (2026-06-05)

> LISTO para enviar. Release de datos `data-snapshot-2026-06-05` YA cortado en GH
> (FB+IG completo, 2026-06-05). Código ya en GH. Todo disponible para Carlos.

---

Hola Carlos. Hay actualización para el re-deploy de CRECE en Coolify. **Todo está en GitHub**
(repo privado `MarxCha/crece-v2`), no necesitas nada fuera de ahí. Son dos partes: **código** y **datos**.

## Qué cambió (por qué el re-deploy)
- **Fixes de cards** (dedup de posts duplicados misma-red, badge de plataforma, etiqueta de cobertura parcial en B04).
- **Override Misael "Fan #1"** actualizado (400) — ADR-0007.
- **Backfill de reacciones FB** — se llenó el hueco de la gráfica "Interacción diaria" (datos, no código).
- ADRs nuevos (gobernanza).

## PARTE 1 · Código (ya en GH)
- Rama `main`, commit **`0a0aa23`** (o el más reciente — `git log -1`). Sync limpio, CI verde.
- En Coolify: dispara el **redeploy del servicio** (pull de `main`). Eso actualiza frontend + backend.
- Env: `GROQ_API_KEY` ya está en `docker-compose.coolify.yml` (commit `7125452`). Verifica que la variable esté seteada en Coolify.

## PARTE 2 · Datos (GitHub Release)
La data operativa de hoy va por **GitHub Release** (no en el repo, por tamaño + PII).
- Release: **`data-snapshot-2026-06-05`** en `MarxCha/crece-v2` (privado).
- Sigue el runbook **`.context/DEPLOY-COOLIFY-CARLOS.md` · PASO 8.1** (restore endurecido por cross-audit Gemini). Resumen:

```bash
# 1. Descargar el dump del Release
gh release download data-snapshot-2026-06-05 -R MarxCha/crece-v2 -p 'crece-data-20260605.dump'

# 2. Restaurar a BD nueva (Vía A · más segura — el dump trae schema, Postgres ≥16)
docker exec <pg-coolify> psql -U <USER> -c "CREATE DATABASE crece_new;"
docker exec -i <pg-coolify> pg_restore -U <USER> -d crece_new --no-owner --no-privileges < crece-data-20260605.dump
# 3. Apuntar el backend a crece_new (o swap) y reiniciar.
```

### Smoke test (verificar tras restore — conteos esperados HOY)
```sql
SELECT count(*) FROM dirigentes;          -- esperado: 13 (7 clientes + competidoras/proxies)
SELECT count(*) FROM social_posts;        -- esperado: 8,118
SELECT count(*) FROM social_comments;     -- esperado: 11,208 (Saymi+Pepe+Felipe, 4 redes)
SELECT count(*) FROM watched_like_events; -- esperado: 344,644 (FB+IG reactors + fans canónicos)
```
Si los 4 cuadran → el restore quedó bien.

### IMPORTANTE
- **Borra el Release `data-snapshot-2026-06-05` después del restore** — contiene PII (LFPDPPP).
- Login admin para verificar: `admin@consultoriamd.com` / `crece2026!`.
- Si algo no cuadra, avísame (vía el CEO) antes de seguir; no fuerces.

Gracias.
