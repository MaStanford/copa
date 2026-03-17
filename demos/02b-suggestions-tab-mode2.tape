# Copa Inline Suggestions — Tab Mode 2 (menu select, default)
# Shows: ghost text appearing, Tab opens completion menu with suggestion
#        highlighted, second Tab or Enter accepts, right-arrow word accept

Output "02b-suggestions-tab-mode2.gif"

Require copa
Require fzf

Set Shell "zsh"
Set FontSize 16
Set Width 900
Set Height 500
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 80ms

# Load copa, ensure tab_accept=2 (default), seed commands
Hide
Type "mkdir -p ~/.copa"
Enter
Sleep 500ms
Type "printf '[suggest]\ntab_accept = 2\n' > ~/.copa/config.toml"
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

# Tab opens completion menu with suggestion highlighted (mode 2)
Tab
Sleep 1.5s

# Tab again accepts the highlighted suggestion
Tab
Sleep 1.5s

# Clear and try another command
Ctrl+C
Sleep 500ms

Type "docker "
Sleep 800ms
Type "com"
Sleep 1s

# Tab opens menu — you can arrow through options
Tab
Sleep 1s

# Navigate the menu
Down
Sleep 500ms
Down
Sleep 500ms
Up
Sleep 500ms

# Enter accepts the selected item
Enter
Sleep 1.5s

# Clear and show right-arrow still works for word accept
Ctrl+C
Sleep 500ms

Type "kube"
Sleep 800ms
Type "ct"
Sleep 1s
Sleep 1s

# Right arrow: accept one word at a time (works in both modes)
Right
Sleep 800ms
Right
Sleep 800ms
Right
Sleep 1.5s

Sleep 2s
