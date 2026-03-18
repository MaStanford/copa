# Copa — Short social media demo (<250 frames, <5MB)
# Shows: ghost text → Ctrl+R → sharing — fast and punchy

Output "00-social.gif"

Require copa
Require fzf

Set Shell "zsh"
Set FontSize 16
Set Width 900
Set Height 450
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 25ms
Set Framerate 10

# Setup
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
Type "copa _record 'python3 -m pytest tests/ -v'"
Enter
Sleep 200ms
Type "cd $(dirname $(which copa))/.."
Enter
Sleep 300ms
Show


# --- Ghost text ---
Type "git "
Sleep 300ms
Type "pu"
Sleep 600ms
Sleep 500ms
Tab
Sleep 600ms
Ctrl+C
Sleep 200ms

# --- Ctrl+R ---
Ctrl+R
Sleep 500ms
Type "kube"
Sleep 400ms
Enter
Sleep 500ms
Sleep 500ms
Ctrl+C
Sleep 200ms

# --- Sharing ---
Type "copa share load examples/git.copa"
Enter
Sleep 600ms
Type "copa share list"
Enter
Sleep 800ms

# --- MCP callout ---
Type "# Works with Claude Code via MCP"
Enter
Sleep 1s
