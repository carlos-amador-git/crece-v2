#!/usr/bin/env bash
# Lint guardrail · CRECE v2 anti-mock-data
#
# Falla si encuentra patrones de hardcoded fallback data en el frontend.
# Origen: incidente 2026-05-11 — `CompetitorSnapshotCard` mostró 8.8K mock
# cuando el dato real era 89.8K (factor 10x). Ver D-ANTI-MOCK-1.
#
# Reglas de Calidad CRECE (CLAUDE.md): "NUNCA crear mocks, stubs, o datos
# inventados. Si algo no funciona, reportarlo como blocker." Este script
# convierte la regla informal en check automatizado.
#
# Uso:
#   ./scripts/check-no-mocks.sh
#   exit 0 = limpio, exit 1 = violaciones encontradas

set -u
cd "$(dirname "$0")/.." || exit 2

VIOLATIONS=0
SRC_DIR="src"

# Patrón 1 · objetos *_FALLBACK con followers/engagement/sentiment numéricos
#   Ej: const FOO_FALLBACK = { followers: 8_764, ... }
MATCHES_FALLBACK=$(grep -rnE \
  "_FALLBACK\s*[:=]\s*\{[^}]{0,200}(followers|engagement|sentiment)\s*:\s*[0-9_]{3,}" \
  --include="*.ts" --include="*.tsx" "$SRC_DIR" 2>/dev/null || true)

if [ -n "$MATCHES_FALLBACK" ]; then
  echo "❌ Hardcoded *_FALLBACK con metrics numéricos:"
  echo "$MATCHES_FALLBACK"
  echo ""
  VIOLATIONS=$((VIOLATIONS + 1))
fi

# Patrón 2 · arrays DEMO_/MOCK_/FAKE_ con followers numéricos altos
MATCHES_DEMO_ARR=$(grep -rnE \
  "(DEMO|MOCK|FAKE|PLACEHOLDER)_[A-Z]+\s*[:=]\s*\[" \
  --include="*.ts" --include="*.tsx" "$SRC_DIR" 2>/dev/null \
  | grep -v "/* allow-mock:" || true)

if [ -n "$MATCHES_DEMO_ARR" ]; then
  echo "⚠️  Constantes DEMO_/MOCK_/FAKE_ encontradas (revisar manualmente):"
  echo "$MATCHES_DEMO_ARR"
  echo "   (si es legítimo en test fixture, agregar comentario '/* allow-mock: razón */')"
  echo ""
  VIOLATIONS=$((VIOLATIONS + 1))
fi

# Patrón 3 · TODO replace con número grande cerca (placeholder visible al usuario)
MATCHES_TODO_REPLACE=$(grep -rnE \
  "(TODO|FIXME).*(replace|wire|hook|cable).*(API|backend|endpoint)" \
  --include="*.ts" --include="*.tsx" "$SRC_DIR" 2>/dev/null || true)

if [ -n "$MATCHES_TODO_REPLACE" ]; then
  echo "⚠️  Comentarios TODO/replace-with-API encontrados:"
  echo "$MATCHES_TODO_REPLACE"
  echo "   (cada uno debe tener issue/blocker asociado — no quedar indefinido)"
  echo ""
  VIOLATIONS=$((VIOLATIONS + 1))
fi

if [ "$VIOLATIONS" -eq 0 ]; then
  echo "✓ Sin patrones de hardcoded fallback detectados."
  exit 0
fi

echo "─────────────────────────────────────────────────────────"
echo "Violaciones: $VIOLATIONS pattern(s)."
echo ""
echo "Si necesitas un placeholder mientras el endpoint backend está"
echo "pendiente: usa <Skeleton /> o estado de carga indefinido."
echo "NO uses números falsos visibles al usuario."
echo ""
echo "Ver: CLAUDE.md § Reglas de Calidad · D-ANTI-MOCK-1"
exit 1
