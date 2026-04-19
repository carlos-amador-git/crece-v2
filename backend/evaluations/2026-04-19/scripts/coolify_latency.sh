#!/bin/bash
# T0.6 Coolify failover smoke test
# Mide latencia p50/p95 gemma3:12b en VPS Coolify

set -e

ENDPOINT="http://163.245.208.96:11434"
OUT="/Users/marxchavez/Projects/crece-v2/backend/evaluations/2026-04-19/output/coolify_latencies.txt"
mkdir -p "$(dirname "$OUT")"
: > "$OUT"

PROMPT='Clasifica el tono de este comentario político mexicano en una palabra: "Corruptazo el hdp". Responde solo con una palabra.'

echo "=== Ping /api/tags ==="
for i in 1 2 3 4 5; do
  t=$(curl -sS -o /dev/null -w "%{time_total}" "$ENDPOINT/api/tags")
  echo "ping_$i=${t}s" | tee -a "$OUT"
done

echo ""
echo "=== Inferencia gemma3:12b (10 calls) ==="
for i in $(seq 1 10); do
  t_start=$(date +%s.%N)
  curl -sS "$ENDPOINT/api/generate" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"gemma3:12b\",\"prompt\":\"$PROMPT\",\"stream\":false,\"options\":{\"temperature\":0.0,\"num_predict\":20}}" \
    > /tmp/gemma_resp_$i.json 2>&1
  t_end=$(date +%s.%N)
  elapsed=$(echo "$t_end - $t_start" | bc -l)
  resp=$(jq -r '.response // "err"' /tmp/gemma_resp_$i.json 2>/dev/null | head -c 40)
  echo "inference_$i=${elapsed}s  resp=\"$resp\"" | tee -a "$OUT"
done

echo ""
echo "=== Stats ==="
grep inference_ "$OUT" | awk -F'=' '{gsub("s","",$2); print $2}' | sort -n > /tmp/lat.txt
count=$(wc -l < /tmp/lat.txt)
p50_idx=$(( (count + 1) / 2 ))
p95_idx=$(( (count * 95 + 50) / 100 ))
p50=$(sed -n "${p50_idx}p" /tmp/lat.txt)
p95=$(sed -n "${p95_idx}p" /tmp/lat.txt)
min=$(head -1 /tmp/lat.txt)
max=$(tail -1 /tmp/lat.txt)
echo "n=$count  min=${min}s  p50=${p50}s  p95=${p95}s  max=${max}s" | tee -a "$OUT"
