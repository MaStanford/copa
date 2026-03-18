# Copa — Hero demo showing all key features in one GIF
# Shows: ghost text → tab accept → Ctrl+R palette → sharing → MCP

Output "00-hero.gif"

Require copa
Require fzf

Set Shell "zsh"
Set FontSize 16
Set Width 1000
Set Height 550
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 30ms

# Setup: load copa, enable comments, seed commands
Hide
Type "setopt INTERACTIVE_COMMENTS"
Enter
Sleep 300ms
Type "mkdir -p ~/.copa"
Enter
Sleep 300ms
Type "printf '[suggest]\ntab_accept = 1\n' > ~/.copa/config.toml"
Enter
Sleep 300ms
Type 'eval "$(copa init zsh)"'
Enter
Sleep 1s
Type "copa _record 'git push origin main --force-with-lease'"
Enter
Sleep 200ms
Type "copa _record 'docker compose up -d --build'"
Enter
Sleep 200ms
Type "copa _record 'kubectl get pods -n production'"
Enter
Sleep 200ms
Type "copa _record 'kubectl logs -f deploy/api -n staging'"
Enter
Sleep 200ms
Type "copa _record 'python3 -m pytest tests/ -v'"
Enter
Sleep 200ms
Type "cd $(dirname $(which copa))/.."
Enter
Sleep 300ms
Show


# --- 1. Inline suggestions (ghost text) ---
Type "# Ghost text suggestions as you type"
Enter
Sleep 500ms

Type "git "
Sleep 400ms
Type "pu"
Sleep 700ms

# Show ghost text, then accept with Tab
Sleep 700ms
Tab
Sleep 800ms
Ctrl+C
Sleep 300ms

# Right arrow word-by-word
Type "docker "
Sleep 400ms
Type "com"
Sleep 600ms
Right
Sleep 350ms
Right
Sleep 350ms
Right
Sleep 700ms
Ctrl+C
Sleep 300ms

# --- 2. Ctrl+R command palette ---
Type "# Ctrl+R — searchable command palette"
Enter
Sleep 500ms

Ctrl+R
Sleep 700ms
Type "kube"
Sleep 500ms
Enter
Sleep 700ms
Sleep 700ms
Ctrl+C
Sleep 300ms

# --- 3. Sharing & onboarding ---
Type "# Share .copa files — instant team onboarding"
Enter
Sleep 500ms

Type "copa share load examples/git.copa"
Enter
Sleep 800ms

Type "copa share list"
Enter
Sleep 1s

# --- 4. Claude Code MCP ---
Type "# Claude Code integration via MCP"
Enter
Sleep 500ms
Type "# Ask: 'make a .copa file of our deploy commands'"
Enter
Sleep 1.5s
