#!/usr/bin/env bash
#
# safe-ops-guard.sh — capa HARNESS del enforcement de gobernanza (docs/adr/0006).
#
# Se invoca como hook PreToolUse(Bash) de Claude Code. Lee el JSON del tool-call
# por stdin, extrae el comando, y BLOQUEA (exit 2) si detecta una operación
# destructiva que AUTONOMY-RULES marca como "requiere OK escrito del CEO":
#   · Docker:  rm *Docker.raw, docker compose down -v, docker volume rm,
#              docker system prune --volumes
#   · BD:      DROP TABLE, TRUNCATE, alembic downgrade base, reset-db
#
# Por qué esta capa: el incidente del 2026-04-13 (rm Docker.raw, ~90% del límite
# semanal de tokens en recovery) fue el AGENTE ejecutando el comando en shell —
# un git-hook no lo atrapa. Esta es la defensa primaria contra ese modo de falla.
#
# Limitación reconocida (auditoría Gemini Puerta 2): solo protege comandos
# emitidos por Claude Code. No cubre la terminal manual ni otros agentes. Defensa
# en profundidad, no infalible. Bypass legítimo: el CEO ejecuta el comando él mismo
# tras decidirlo, o se exporta CRECE_ALLOW_DESTRUCTIVE=1 a conciencia.
#
set -euo pipefail

[ "${CRECE_ALLOW_DESTRUCTIVE:-0}" = "1" ] && exit 0

CMD="$(python3 -c 'import sys,json
try:
    d=json.load(sys.stdin)
    print((d.get("tool_input") or {}).get("command",""))
except Exception:
    print("")' 2>/dev/null || true)"

[ -z "$CMD" ] && exit 0

# Patrones destructivos de alto blast-radius.
if printf '%s' "$CMD" | grep -iEq \
   'rm[^|;&]*Docker\.raw|docker[[:space:]]+(compose[[:space:]]+)?down[^|;&]*-v|docker[[:space:]]+volume[[:space:]]+rm|docker[[:space:]]+system[[:space:]]+prune[^|;&]*--volumes|docker[[:space:]]+system[[:space:]]+prune[[:space:]]+-a|DROP[[:space:]]+TABLE|TRUNCATE[[:space:]]+|alembic[[:space:]]+downgrade[[:space:]]+base|make[[:space:]]+reset-db'; then
  echo "⛔ safe-ops-guard: comando destructivo BLOQUEADO." >&2
  echo "   AUTONOMY-RULES §Operación destructiva exige OK escrito del CEO en la sesión actual." >&2
  echo "   Postmortem de referencia: rm Docker.raw 2026-04-13." >&2
  echo "   Si el CEO lo autorizó: que lo ejecute él, o export CRECE_ALLOW_DESTRUCTIVE=1." >&2
  exit 2
fi

exit 0
