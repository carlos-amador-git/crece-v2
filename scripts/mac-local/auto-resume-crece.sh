#!/bin/bash
# auto-resume-crece.sh
#
# Detecta containers crece-* en estado Paused (post-sleep del Mac) o
# crece-backend unhealthy y los reanuda automáticamente.
#
# Diseñado para correr cada 60s vía LaunchAgent. Idempotente.
# Si todo está sano: noop + exit 0. Sin ruido en logs.
#
# Logs:
# - /tmp/crece-resume.log (sólo escribe en transición o error)

set -u

LOG="/tmp/crece-resume.log"
PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"
}

# Si Docker no responde, salir sin error (probablemente apagado a propósito)
if ! docker info >/dev/null 2>&1; then
  exit 0
fi

# 1. Reanudar containers crece-* en estado Paused
PAUSED=$(docker ps --filter "name=crece-" --filter "status=paused" --format '{{.Names}}')
if [ -n "$PAUSED" ]; then
  log "containers paused: $(echo $PAUSED | tr '\n' ' ')"
  echo "$PAUSED" | while read -r name; do
    [ -z "$name" ] && continue
    docker unpause "$name" >/dev/null 2>&1 && log "  unpaused $name" || log "  FAIL unpause $name"
  done
fi

# 2. Restart crece-backend si quedó unhealthy
BACKEND_STATUS=$(docker inspect --format='{{.State.Health.Status}}' crece-backend 2>/dev/null || echo "missing")
if [ "$BACKEND_STATUS" = "unhealthy" ]; then
  log "crece-backend unhealthy → restart"
  docker restart crece-backend >/dev/null 2>&1
fi

exit 0
