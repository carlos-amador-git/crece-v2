#!/bin/bash
# start-crece-tunnel.sh
#
# Levanta cloudflared quick tunnel hacia backend Mac local (crece-backend Docker :8002),
# captura la URL pública asignada, y actualiza Vercel env NEXT_PUBLIC_API_URL si cambió.
# Si el env cambia, dispara redeploy Vercel prod para que el alias público quede activo.
#
# Diseñado para correr como LaunchAgent al boot y cada vez que el tunnel muere.
# LaunchAgent en: ~/Library/LaunchAgents/com.mdconsultoria.crece-tunnel.plist
#
# Requisitos:
# - cloudflared instalado (brew install cloudflared)
# - vercel CLI autenticado (cd frontend && vercel login)
# - frontend/.vercel/project.json existente
# - docker compose con crece-backend expuesto en :8002
#
# Logs:
# - /tmp/crece-tunnel.log (rotado por LaunchAgent)
# - /tmp/crece-tunnel.url (URL actual · fuente de verdad para el state)

set -u

PROJECT_ROOT="/Users/marxchavez/Projects/crece-v2"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
LOG="/tmp/crece-tunnel.log"
URL_FILE="/tmp/crece-tunnel.url"
CF_LOG="/tmp/crece-tunnel-cf.log"
BACKEND_URL="http://localhost:8002"
PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/opt/homebrew/opt/node/bin:$PATH"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"
}

log "=== crece-tunnel start ==="

# 1. Verificar backend local responde
if ! curl -sS -o /dev/null -w "%{http_code}" "$BACKEND_URL/api/v1/health/" --max-time 5 | grep -q "200"; then
  log "ERROR: backend local $BACKEND_URL no responde healthy. Saliendo."
  exit 1
fi
log "backend local OK"

# 2. Health check del tunnel actual (si existe). Si vivo → noop + exit 0 (idempotente).
CURRENT_URL=""
[ -f "$URL_FILE" ] && CURRENT_URL=$(cat "$URL_FILE" | head -c 200 | tr -d '[:space:]')
RUNNING_PIDS=$(pgrep -f "cloudflared tunnel --url http://localhost:8002" || true)
if [ -n "$CURRENT_URL" ] && [ -n "$RUNNING_PIDS" ]; then
  # Resolve IP + probe · tolera cache DNS local
  IP=$(dig @1.1.1.1 "${CURRENT_URL#https://}" +short 2>/dev/null | head -1)
  if [ -n "$IP" ]; then
    HEALTH=$(curl -sS -o /dev/null -w "%{http_code}" \
      --resolve "${CURRENT_URL#https://}:443:$IP" \
      "$CURRENT_URL/api/v1/health/" --max-time 10 2>/dev/null || echo "000")
    if [ "$HEALTH" = "200" ]; then
      log "tunnel vivo ($CURRENT_URL · pids $RUNNING_PIDS). Noop."
      exit 0
    fi
    log "tunnel URL responde $HEALTH (no 200). Rotando."
  else
    log "DNS no resuelve $CURRENT_URL. Rotando."
  fi
fi

# 3. Tunnel caído o inexistente → matar viejos + levantar nuevo
if [ -n "$RUNNING_PIDS" ]; then
  log "matando tunnels viejos: $RUNNING_PIDS"
  echo "$RUNNING_PIDS" | xargs -I{} kill {} 2>/dev/null || true
  sleep 3
fi

# 4. Levantar nuevo tunnel en background
# CRITICAL: usar nohup + disown para que cloudflared SOBREVIVA al exit del script.
# Bug 2026-05-07: launchd mata todo el process group cuando el script termina,
# matando también al cloudflared hijo y dejando el tunnel muerto inmediatamente
# después del redeploy de Vercel. Ningún recovery post-apagón funciona si el
# hijo muere con el padre. nohup ignora SIGHUP, disown lo saca del job table del
# shell. macOS no tiene setsid; nohup es el equivalente portable.
log "levantando tunnel nuevo..."
nohup cloudflared tunnel --url "$BACKEND_URL" --no-autoupdate > "$CF_LOG" 2>&1 < /dev/null &
TUNNEL_PID=$!
disown $TUNNEL_PID 2>/dev/null || true
log "tunnel PID=$TUNNEL_PID (detached con nohup+disown)"

# 4. Esperar hasta que cloudflared imprima el URL (máx 45s)
NEW_URL=""
for i in $(seq 1 45); do
  if grep -qE "https://[a-z0-9-]+\.trycloudflare\.com" "$CF_LOG" 2>/dev/null; then
    NEW_URL=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" "$CF_LOG" | head -1)
    break
  fi
  sleep 1
done

if [ -z "$NEW_URL" ]; then
  log "ERROR: cloudflared no asignó URL en 45s. Log tail:"
  tail -10 "$CF_LOG" | tee -a "$LOG"
  exit 2
fi
log "tunnel URL: $NEW_URL"

# 5. Smoke test del tunnel: HARD-FAIL si no responde 200 tras retries.
# DNS de quick tunnels tarda 5-30s en propagar al edge global; un solo probe
# genera falso negativo (caso 2026-05-04: persistió URL muerta a Vercel).
# Si tras ~30s sigue sin responder → tunnel realmente roto, NO actualizar Vercel.
TUNNEL_STATUS="000"
HOST_ONLY="${NEW_URL#https://}"
for i in $(seq 1 10); do
  IP=$(dig @1.1.1.1 "$HOST_ONLY" +short 2>/dev/null | head -1)
  if [ -n "$IP" ]; then
    TUNNEL_STATUS=$(curl -sS -o /dev/null -w "%{http_code}" \
      --resolve "${HOST_ONLY}:443:$IP" \
      "$NEW_URL/api/v1/health/" --max-time 10 2>/dev/null || echo "000")
    [ "$TUNNEL_STATUS" = "200" ] && break
  fi
  sleep 3
done

if [ "$TUNNEL_STATUS" != "200" ]; then
  log "ERROR: tunnel $NEW_URL no respondió 200 tras 10 intentos (último: $TUNNEL_STATUS). NO actualizando Vercel."
  kill "$TUNNEL_PID" 2>/dev/null || true
  exit 5
fi
log "tunnel verificado healthy ($TUNNEL_STATUS)"

# 6. Comparar con URL previa
OLD_URL=""
[ -f "$URL_FILE" ] && OLD_URL=$(cat "$URL_FILE" | head -c 200 | tr -d '[:space:]')

if [ "$NEW_URL" = "$OLD_URL" ]; then
  log "URL sin cambio ($NEW_URL). Vercel env intacto. Fin."
  exit 0
fi

log "URL cambió: $OLD_URL → $NEW_URL"

# 7. Actualizar Vercel env BACKEND_TUNNEL_URL (server-only, leído por
# el proxy en frontend/src/app/api/v1/[...path]/route.ts).
# NEXT_PUBLIC_API_URL queda fijo en "/api/v1" (mismo origen) · no requiere
# rebuild del frontend cuando rota el tunnel.
cd "$FRONTEND_DIR" || { log "ERROR cd frontend"; exit 3; }

log "actualizando Vercel env BACKEND_TUNNEL_URL=$NEW_URL"

# Remove + add. NO usar printf '%s\n' — el \n entra literal y rompe fetch.
printf 'y\n' | vercel env rm BACKEND_TUNNEL_URL production 2>>"$LOG" || true
printf '%s' "$NEW_URL" | vercel env add BACKEND_TUNNEL_URL production 2>>"$LOG" || {
  log "ERROR: vercel env add falló"
  exit 4
}

# El cambio de env server-only requiere redeploy para que las nuevas
# invocaciones de la API route lo lean. Vercel hace el rebuild en ~50s
# pero el frontend HTML/JS ya cacheado en CDN sigue válido (mismo dominio,
# misma URL pública). Los dirigentes no ven downtime.
log "disparando redeploy Vercel prod..."
DEPLOY_OUT=$(vercel --prod --yes 2>&1 | tail -5)
log "deploy output: $DEPLOY_OUT"

# 8. Guardar URL nueva como fuente de verdad
printf '%s' "$NEW_URL" > "$URL_FILE"
log "URL persisted a $URL_FILE"

log "=== crece-tunnel done ==="
