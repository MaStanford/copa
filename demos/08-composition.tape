# Copa Composition — Chain commands with operators
# Shows: pipe (|), chain (&&), background (&), redirect (>)

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

# Pipe into next command (Ctrl+X) — fzf re-opens
Ctrl+X
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

# Demo && chaining
Ctrl+R
Sleep 1s
Type "git pull"
Sleep 800ms

# Chain with && (Ctrl+A) — fzf re-opens
Ctrl+A
Sleep 1.5s

Type "npm"
Sleep 800ms

# Chain again
Ctrl+A
Sleep 1.5s

Type "pytest"
Sleep 800ms
Enter
Sleep 1.5s

# Show the full composed command (don't run it)
Sleep 2.5s
Ctrl+C
Sleep 500ms

# Demo redirect (Ctrl+T)
Ctrl+R
Sleep 1s
Type "kubectl"
Sleep 800ms

# Redirect output (Ctrl+T)
Ctrl+T
Sleep 1.5s

# Show the command with > appended
Sleep 2s
Ctrl+C
Sleep 1s
