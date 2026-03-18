# Copa Completion Modes — hybrid, fallback, always, never
# Shows: how Copa completions mix with native completions in each mode
# Mode is set in ~/.copa/config.toml under [completion] mode = "..."

Output "10-completion-modes.gif"

Require copa
Require fzf

Set Shell "zsh"
Set FontSize 16
Set Width 1000
Set Height 600
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 60ms

# Load copa with hybrid mode (default)
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
Show


# --- HYBRID mode (default) ---
# Copa completions shown alongside native completions
Type "# hybrid mode (default): Copa + native side by side"
Enter
Sleep 1s

Type "git "
Sleep 500ms

# Tab shows both Copa history matches AND native git completions
Tab
Sleep 2s

# Navigate to see Copa section vs native section
Down
Sleep 400ms
Down
Sleep 400ms
Down
Sleep 400ms

Escape
Sleep 1s
Ctrl+C
Sleep 500ms

# --- Switch to FALLBACK mode ---
Hide
Type 'echo -e "[completion]\nmode = \"fallback\"" > ~/.copa/config.toml'
Enter
Sleep 500ms
Type 'eval "$(copa init zsh)"'
Enter
Sleep 1s
Show

Type "# fallback mode: Copa only when native has nothing"
Enter
Sleep 1s

Type "git "
Sleep 500ms

Tab
Sleep 2s

Escape
Sleep 1s
Ctrl+C
Sleep 500ms

# --- Switch to ALWAYS mode ---
Hide
Type 'echo -e "[completion]\nmode = \"always\"" > ~/.copa/config.toml'
Enter
Sleep 500ms
Type 'eval "$(copa init zsh)"'
Enter
Sleep 1s
Show

Type "# always mode: Copa replaces native completions"
Enter
Sleep 1s

Type "git "
Sleep 500ms

Tab
Sleep 2s

Escape
Sleep 1s
Ctrl+C
Sleep 500ms

# Reset to hybrid
Hide
Type 'echo -e "[completion]\nmode = \"hybrid\"" > ~/.copa/config.toml'
Enter
Sleep 500ms
Type 'eval "$(copa init zsh)"'
Enter
Sleep 1s
Show

Type "# never mode: disables Copa tab completion entirely"
Enter
Sleep 1s
Type "# Set mode = 'never' in ~/.copa/config.toml"
Enter
Sleep 2s
