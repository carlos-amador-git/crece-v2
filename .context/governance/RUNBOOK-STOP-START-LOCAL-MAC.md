# RUNBOOK — Stop / Start limpio del stack local (Mac Mini)

> Operativo. Cómo detener y relevantar el stack CRECE local **sin pelear con el
> resucitador**. Origen: sesión 2026-06-08 — un `docker stop` "se deshacía solo" en ≤60s.

## La trampa: `docker stop` solo NO es un stop limpio

El stack corre con `restart=unless-stopped` y hay un **LaunchAgent que resucita el backend**:

- `~/Library/LaunchAgents/com.mdconsultoria.crece-auto-resume.plist`
  → corre `scripts/mac-local/auto-resume-crece.sh` cada **60 s** (`StartInterval=60` + `RunAtLoad`).
  → reanuda contenedores `crece-*` en estado `paused` **y** hace `docker restart crece-backend`
    si lo ve `unhealthy`.

**Efecto observado:** al `docker stop` del stack, las dependencias (`crece-db`, `redis`…) caen
→ `crece-backend` queda `unhealthy` → el agente lo reinicia en ≤60 s. Vuelve el backend solo
(flotando sin sus deps). Log: `/tmp/crece-resume.log`.

## Stop limpio (orden correcto)

```bash
# 1. Descargar el resucitador PRIMERO (reversible, solo esta sesión de login)
launchctl bootout gui/$(id -u)/com.mdconsultoria.crece-auto-resume

# 2. Detener el stack (datos intactos en volúmenes — NUNCA `down -v` ni prune)
docker stop crece-backend crece-frontend crece-celery-worker crece-celery-beat \
            crece-flower crece-redis crece-minio crece-db

# 3. Verificar pasada la ventana de 60 s que nada revivió
sleep 75 && docker ps --filter "name=crece" --format '{{.Names}}\t{{.Status}}'
# Esperado: 0 contenedores Up. /tmp/crece-resume.log sin línea nueva.
```

`armonia-postgres` es de otro proyecto — **no tocar**.

## Start (relevantar)

```bash
docker start crece-db crece-redis crece-minio crece-backend \
             crece-celery-worker crece-celery-beat crece-flower crece-frontend
# Re-armar el resucitador:
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.mdconsultoria.crece-auto-resume.plist
```

## Notas

- `bootout` dura la sesión de login actual; el agent **se recarga en el próximo login/reboot**
  (el `.plist` sigue en `LaunchAgents/`). Para que NO resucite tras reboot: `launchctl disable`
  o renombrar el plist — solo si se quiere parada persistente.
- **RAM:** lo pesado es el stack Docker (backend + celery-worker con NLP eager + Postgres).
  El **túnel cloudflared** (`com.mdconsultoria.crece-tunnel`, PIDs cloudflared) pesa ~50 MB
  total — ruido; detenerlo libera poco y tumba la demo Vercel (`frontend-zeta-sepia-46` →
  backend local). No vale la pena por RAM.
- Acciones destructivas Docker (`down -v`, `prune --volumes`, `volume rm`, `rm Docker.raw`)
  → prohibidas sin OK escrito (CLAUDE.md global · postmortem cfdi-motor Docker.raw 2026-04-13).
