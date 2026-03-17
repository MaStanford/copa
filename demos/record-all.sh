#!/bin/zsh
# Record all Copa demo GIFs using VHS
# Usage: ./record-all.sh

# No set -e: we handle errors per-tape

cd "$(dirname "$0")"

tapes=(*.tape)
total=${#tapes[@]}
done=0
failed=0
failed_names=()

echo "=== Copa Demo Recorder ==="
echo "Found $total tapes to record"
echo ""

for tape in "${tapes[@]}"; do
  done=$((done + 1))
  name="${tape%.tape}"
  echo "[$done/$total] Recording: $name"
  echo "  Input:  $tape"
  echo "  Output: ${name}.gif"

  if vhs "$tape" 2>&1; then
    echo "  Done."
  else
    echo "  FAILED!"
    failed=$((failed + 1))
    failed_names+=("$name")
  fi
  echo ""
done

echo "=== Complete ==="
echo "  Recorded: $((done - failed))/$total"
if (( failed > 0 )); then
  echo "  Failed:   $failed ($failed_names)"
else
  echo "  All tapes recorded successfully!"
fi
echo ""
ls -lh *.gif 2>/dev/null || echo "No GIFs found"
