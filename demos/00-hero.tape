# Copa — Hero demo showing all key features in one GIF
# Shows: ghost text → tab accept → Ctrl+R palette → groups → sharing → .copa export

Output "00-hero.gif"

Require copa
Require fzf

Set Shell "zsh"
Set FontSize 16
Set Width 1000
Set Height 550
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 60ms

# Setup: load copa, enable comments, seed commands
Hide
Type "setopt INTERACTIVE_COMMENTS"
Enter
Sleep 500ms
Type "mkdir -p ~/.copa"
Enter
Sleep 500ms
Type 'eval "$(copa init zsh)"'
Enter
Sleep 1s
Type "copa _record 'git push origin main --force-with-lease'"
Enter
Sleep 300ms
Type "copa _record 'docker compose up -d --build'"
Enter
Sleep 300ms
Type "copa _record 'kubectl get pods -n production'"
Enter
Sleep 300ms
Type "copa _record 'kubectl logs -f deploy/api -n staging'"
Enter
Sleep 300ms
Type "copa _record 'python3 -m pytest tests/ -v'"
Enter
Sleep 300ms
Type "copa _record 'npm run build'"
Enter
Sleep 300ms
Type "cd $(dirname $(which copa))/.."
Enter
Sleep 500ms
Show


# --- 1. Inline suggestions (ghost text) ---
Type "# Inline suggestions — ghost text as you type"
Enter
Sleep 800ms

Type "git "
Sleep 600ms
Type "pu"
Sleep 1s

# Show ghost text, then accept with Tab
Sleep 1s
Tab
Sleep 1s
Ctrl+C
Sleep 400ms

# Right arrow word-by-word accept
Type "docker "
Sleep 600ms
Type "com"
Sleep 800ms
Right
Sleep 500ms
Right
Sleep 500ms
Right
Sleep 1s
Ctrl+C
Sleep 400ms

# --- 2. Ctrl+R command palette ---
Type "# Ctrl+R — fuzzy command palette"
Enter
Sleep 800ms

Ctrl+R
Sleep 1s

# Search
Type "kube"
Sleep 800ms

# Select a result
Enter
Sleep 1s

# Show it in the buffer (don't run)
Sleep 1s
Ctrl+C
Sleep 400ms

# --- 3. Command composition ---
Type "# Composition — chain commands with | && >"
Enter
Sleep 800ms

Ctrl+R
Sleep 1s
Type "docker"
Sleep 600ms

# Pipe (Ctrl+X)
Ctrl+X
Sleep 1s

Type "grep"
Sleep 600ms
Enter
Sleep 1s

# Show composed command
Sleep 1s
Ctrl+C
Sleep 400ms

# --- 4. Sharing & onboarding ---
Type "# Sharing — onboard your team with .copa files"
Enter
Sleep 800ms

Type "copa share load examples/git.copa"
Enter
Sleep 1s

Type "copa share list"
Enter
Sleep 1.5s

# --- 5. Export ---
Type "# Export — share your knowledge back"
Enter
Sleep 800ms

Type "copa create -g git-essentials"
Enter
Sleep 1.5s

# --- 6. Claude Code MCP ---
Type "# Claude Code can search, create, and share commands via MCP"
Enter
Sleep 800ms

Type "# Ask Claude: 'make a .copa file of our deploy commands'"
Enter
Sleep 2s
