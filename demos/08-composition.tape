# Copa Composition — Chain commands with operators
# Shows: pipe (|), chain (&&), background (&), redirect (>)

Output demos/08-composition.gif

Require copa
Require fzf

Set Shell "zsh"
Set FontSize 16
Set Width 1000
Set Height 600
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 60ms

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

# Show the composed command in the prompt
Sleep 2s

# Clear and demo && chaining
Ctrl+C
Sleep 500ms

Ctrl+R
Sleep 1s
Type "git pull"
Sleep 800ms

# Chain with && (Ctrl+A) — fzf re-opens
Ctrl+A
Sleep 1.5s

Type "npm install"
Sleep 800ms

# Chain again
Ctrl+A
Sleep 1.5s

Type "npm run build"
Sleep 800ms
Enter
Sleep 2s

# Show the full composed command
Sleep 2.5s
