#!/bin/bash
# Record all Copa demo GIFs using VHS
# Usage: ./record-all.sh
#
# This script uses an isolated Copa database (COPA_DB) so no real
# history leaks into the demo GIFs. Copa must be installed first.

# No set -e: we handle errors per-tape

cd "$(dirname "$0")"
COPA_ROOT="$(cd .. && pwd)"

# --- Ensure copa is installed ---
if ! command -v copa &>/dev/null; then
  echo "Copa not installed. Installing from source..."
  pip3 install -e "$COPA_ROOT" 2>&1 | tail -3
fi

# --- Isolated demo database ---
DEMO_DIR="$(mktemp -d)"
export COPA_DB="$DEMO_DIR/copa.db"

echo "=== Copa Demo Recorder ==="
echo "Using isolated database: $COPA_DB"

# --- Seed curated demo commands ---
echo ""
echo "--- Seeding demo commands ---"
copa _init 2>/dev/null

# Git commands
copa _record "git push origin main"
copa _record "git push origin main --force-with-lease"
copa _record "git pull --rebase origin main"
copa _record "git log --oneline -20"
copa _record "git stash pop"
copa _record "git diff --staged"
copa _record "git checkout -b feature/new-branch"
copa _record "git rebase -i HEAD~3"

# Docker commands
copa _record "docker compose up -d --build"
copa _record "docker compose down -v"
copa _record "docker ps --format 'table {{.Names}}\t{{.Status}}'"
copa _record "docker build -t myapp:latest ."
copa _record "docker logs -f webapp"
copa _record "docker exec -it webapp bash"
copa _record "docker system prune -af"

# Kubernetes commands
copa _record "kubectl get pods -n production"
copa _record "kubectl get pods -n staging"
copa _record "kubectl logs -f deploy/api -n staging"
copa _record "kubectl describe pod api-7f8b9c -n staging"
copa _record "kubectl apply -f k8s/deployment.yaml"
copa _record "kubectl rollout restart deploy/api -n production"
copa _record "kubectl port-forward svc/api 8080:80"

# Common dev commands
copa _record "python3 -m pytest tests/ -v"
copa _record "npm run build"
copa _record "npm run dev"
copa _record "curl -s http://localhost:8080/health | jq ."
copa _record "ssh devserver"
copa _record "rsync -avz ./dist/ server:/var/www/"
copa _record "find . -name '*.pyc' -delete"
copa _record "grep -rn TODO src/"
copa _record "tail -f /var/log/app.log"

echo "  Seeded $(copa list 2>/dev/null | wc -l | tr -d ' ') commands"
echo ""

# --- Record all tapes ---
tapes=(*.tape)
total=${#tapes[@]}
done_count=0
failed=0
failed_names=()

echo "--- Recording ${total} tapes ---"
echo ""

for tape in "${tapes[@]}"; do
  done_count=$((done_count + 1))
  name="${tape%.tape}"
  echo "[$done_count/$total] Recording: $name"
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

# --- Cleanup ---
rm -rf "$DEMO_DIR"

echo "=== Complete ==="
echo "  Recorded: $((done_count - failed))/$total"
if (( failed > 0 )); then
  echo "  Failed:   $failed (${failed_names[*]})"
else
  echo "  All tapes recorded successfully!"
fi
echo ""
ls -lh *.gif 2>/dev/null || echo "No GIFs found"
