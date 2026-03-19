# Copa Compose Submenu — Chain commands with operators
# Shows: compose menu with |, &&, >, &, 2>&1, 2>/dev/null

Output "08-composition.gif"

Require copa
Require fzf

Set Shell "zsh"
Set FontSize 16
Set Width 1000
Set Height 600
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 60ms

# Load copa shell integration
Hide
Type 'eval "$(copa init zsh)"'
Enter
Sleep 1s
Show


# Open palette
Ctrl+R
Sleep 1s

# Search for a command
Type "docker ps"
Sleep 1s

# Open compose menu (Ctrl+X)
Ctrl+X
Sleep 1.5s

# Select pipe (1) — fzf re-opens
Type "1"
Sleep 1.5s

# Select next command to pipe into
Type "grep"
Sleep 800ms
Enter
Sleep 1.5s

# Show the composed command in the prompt (don't run it)
Sleep 2s
Ctrl+C
Sleep 500ms

# Demo && chaining via compose menu
Ctrl+R
Sleep 1s
Type "git pull"
Sleep 800ms

# Open compose menu and select && (2) — fzf re-opens
Ctrl+X
Sleep 1s
Type "2"
Sleep 1.5s

Type "npm"
Sleep 800ms

# Chain again with compose menu
Ctrl+X
Sleep 1s
Type "2"
Sleep 1.5s

Type "pytest"
Sleep 800ms
Enter
Sleep 1.5s

# Show the full composed command (don't run it)
Sleep 2.5s
Ctrl+C
Sleep 500ms

# Demo background (&) via compose menu
Ctrl+R
Sleep 1s
Type "kubectl"
Sleep 800ms

# Open compose menu and select background (4) — closes immediately
Ctrl+X
Sleep 1s
Type "4"
Sleep 1.5s

# Show the command with & appended
Sleep 2s
Ctrl+C
Sleep 1s
