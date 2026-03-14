# Copa Ctrl+R — fzf Command Palette
# Shows: opening palette, fuzzy search, modes, composition keys

Output demos/04-ctrl-r-palette.gif

Require copa
Require fzf

Set Shell "zsh"
Set FontSize 16
Set Width 1000
Set Height 600
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 60ms

# Open the command palette
Ctrl+R
Sleep 1.5s

# Fuzzy search
Type "docker"
Sleep 1.5s

# Clear search and try another
Ctrl+U
Sleep 500ms
Type "bluetooth"
Sleep 1.5s

# Cycle modes: all → frequent → recent
Ctrl+R
Sleep 1s
Ctrl+R
Sleep 1s
Ctrl+R
Sleep 1s

# Clear search
Ctrl+U
Sleep 500ms

# Composition: select a command and chain with &&
Type "git pull"
Sleep 1s
Enter
Sleep 1.5s

# Open palette again
Ctrl+R
Sleep 1s

# Toggle header for more space
Ctrl+H
Sleep 1.5s
Ctrl+H
Sleep 1s

# Escape to close
Escape
Sleep 2s
