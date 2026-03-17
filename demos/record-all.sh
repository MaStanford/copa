#!/bin/zsh
# Record all Copa demo GIFs using VHS
# Usage: ./record-all.sh
#
# This script uses an isolated Copa database so no real history leaks
# into the demo GIFs. It uninstalls copa first (for tape 01 which shows
# installation), then installs and seeds curated commands for the rest.

# No set -e: we handle errors per-tape

cd "$(dirname "$0")"
COPA_ROOT="$(cd .. && pwd)"

# --- Isolated demo environment ---
# Use a fake HOME so ~/.copa/copa.db is always empty/isolated.
# This works with both old (PyPI) and new (COPA_DB) versions.
DEMO_HOME="$(mktemp -d)"
mkdir -p "$DEMO_HOME"
export HOME="$DEMO_HOME"
export COPA_DB="$DEMO_HOME/.copa/copa.db"

echo "=== Copa Demo Recorder ==="
echo "Using isolated HOME: $DEMO_HOME"
echo "Using isolated database: $COPA_DB"

# --- Step 1: Uninstall copa for tape 01 (install demo) ---
echo ""
echo "--- Uninstalling copa for install demo ---"
pip3 uninstall -y copa-cli 2>/dev/null
echo ""

# --- Step 2: Record tape 01 (shows installation) ---
echo "[1] Recording: 01-setup"
if vhs 01-setup.tape 2>&1; then
  echo "  Done."
else
  echo "  FAILED!"
fi
echo ""

# --- Step 3: Install copa from local source ---
echo "--- Installing copa from source ---"
pip3 install -e "$COPA_ROOT" 2>&1 | tail -3
echo ""

# --- Step 4: Seed curated demo commands ---
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

# --- Step 5: Record remaining tapes ---
tapes=(*.tape)
# Remove 01-setup since we already recorded it
tapes=("${(@)tapes:#01-setup.tape}")
total=${#tapes[@]}
done_count=0
failed=0
failed_names=()

echo "--- Recording ${total} remaining tapes ---"
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
rm -rf "$DEMO_HOME"

echo "=== Complete ==="
echo "  Recorded: $((done_count + 1 - failed))/$((total + 1))"
if (( failed > 0 )); then
  echo "  Failed:   $failed (${(j: :)failed_names})"
else
  echo "  All tapes recorded successfully!"
fi
echo ""
ls -lh *.gif 2>/dev/null || echo "No GIFs found"
