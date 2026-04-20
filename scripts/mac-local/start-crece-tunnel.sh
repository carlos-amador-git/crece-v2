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
log "levantando tunnel nuevo..."
cloudflared tunnel --url "$BACKEND_URL" --no-autoupdate > "$CF_LOG" 2>&1 &
TUNNEL_PID=$!
log "tunnel PID=$TUNNEL_PID"

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

# 5. Smoke test de que el tunnel public responde
sleep 3
TUNNEL_STATUS=$(curl -sS -o /dev/null -w "%{http_code}" "$NEW_URL/api/v1/health/" --max-time 15 || echo "000")
if [ "$TUNNEL_STATUS" != "200" ]; then
  log "WARN: tunnel responde $TUNNEL_STATUS (no 200). Puede ser transitorio."
fi

# 6. Comparar con URL previa
OLD_URL=""
[ -f "$URL_FILE" ] && OLD_URL=$(cat "$URL_FILE" | head -c 200 | tr -d '[:space:]')

if [ "$NEW_URL" = "$OLD_URL" ]; then
  log "URL sin cambio ($NEW_URL). Vercel env intacto. Fin."
  exit 0
fi

log "URL cambió: $OLD_URL → $NEW_URL"

# 7. Actualizar Vercel env + redeploy
cd "$FRONTEND_DIR" || { log "ERROR cd frontend"; exit 3; }

NEW_API_URL="${NEW_URL}/api/v1"
log "actualizando Vercel env NEXT_PUBLIC_API_URL=$NEW_API_URL"

# Remove + add (Vercel CLI no soporta update in-place)
printf 'y\n' | vercel env rm NEXT_PUBLIC_API_URL production 2>>"$LOG" || true
printf '%s\n' "$NEW_API_URL" | vercel env add NEXT_PUBLIC_API_URL production 2>>"$LOG" || {
  log "ERROR: vercel env add falló"
  exit 4
}

log "disparando redeploy Vercel prod..."
DEPLOY_OUT=$(vercel --prod --yes 2>&1 | tail -5)
log "deploy output: $DEPLOY_OUT"

# 8. Guardar URL nueva como fuente de verdad
printf '%s' "$NEW_URL" > "$URL_FILE"
log "URL persisted a $URL_FILE"

log "=== crece-tunnel done ==="
