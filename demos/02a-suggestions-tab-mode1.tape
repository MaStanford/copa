# Copa Inline Suggestions — Tab Mode 1 (direct accept)
# Shows: ghost text appearing, Tab directly accepts suggestion, right-arrow
#        word accept, Cmd+Right full accept, backspace latch

Output "02a-suggestions-tab-mode1.gif"

Require copa
Require fzf

Set Shell "zsh"
Set FontSize 16
Set Width 900
Set Height 400
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 80ms

# Load copa, set tab_accept=1 via config file, seed commands
Hide
Type "mkdir -p ~/.copa"
Enter
Sleep 500ms
Type "printf '[suggest]\ntab_accept = 1\n' > ~/.copa/config.toml"
Enter
Sleep 500ms
Type 'eval "$(copa init zsh)"'
Enter
Sleep 1s
Type "copa _record 'git push origin main --force-with-lease'"
Enter
Sleep 500ms
Type "copa _record 'docker compose up -d --build'"
Enter
Sleep 500ms
Type "copa _record 'kubectl get pods -n production'"
Enter
Sleep 500ms
Show


# Start typing — ghost text appears
Type "git "
Sleep 800ms
Type "pu"
Sleep 1s

# Pause to show ghost text
Sleep 1.5s

# Tab directly accepts the full suggestion (mode 1)
Tab
Sleep 1.5s

# Clear and show right-arrow word accept
Ctrl+C
Sleep 500ms

Type "docker "
Sleep 800ms
Type "com"
Sleep 1s

# Right arrow: accept one word at a time
Right
Sleep 800ms
Right
Sleep 800ms
Right
Sleep 1.5s

# Clear and show Cmd+Right (Ctrl+E) — accept full suggestion
Ctrl+C
Sleep 500ms

Type "kube"
Sleep 800ms
Type "ct"
Sleep 1s
Sleep 1s

# Ctrl+E accepts the entire suggestion at once
Ctrl+E
Sleep 1.5s

# Clear and show backspace latch
Ctrl+C
Sleep 500ms

Type "kube"
Sleep 1s
Sleep 1s

# Backspace — suggestion disappears (latched)
Backspace
Sleep 500ms
Backspace
Sleep 500ms

# Type again — suggestion comes back
Type "be"
Sleep 1s
Type "ct"
Sleep 1.5s

# Accept with Tab (mode 1 — direct accept)
Tab
Sleep 2s
