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

# Load copa shell integration
Hide
Type 'eval "$(copa init zsh)"'
Enter
Sleep 1s
Show


# --- HYBRID mode (default) ---
# Copa completions shown alongside native completions
Type "# Mode: hybrid (default) -- Copa + native side by side"
Enter
Sleep 1s

# Show current config
Type "cat ~/.copa/config.toml"
Enter
Sleep 1.5s

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

# --- FALLBACK mode ---
# Copa only appears when native completions find nothing
Type "# Mode: fallback -- Copa fills in when native has nothing"
Enter
Sleep 1s

# Edit config to switch mode
Type "echo '[completion]' > ~/.copa/config.toml && echo 'mode = "
Type 'fallback"'
Type "' >> ~/.copa/config.toml"
Enter
Sleep 500ms

# Reload shell to pick up new config
Type "exec zsh"
Enter
Sleep 1.5s

Type "adb "
Sleep 500ms

# Tab -- native completions first; Copa only if nothing matches
Tab
Sleep 2s

Escape
Sleep 1s
Ctrl+C
Sleep 500ms

# --- ALWAYS mode ---
# Copa completions replace native completions entirely
Type "# Mode: always -- Copa replaces native completions"
Enter
Sleep 1s

Type "echo '[completion]' > ~/.copa/config.toml && echo 'mode = "
Type 'always"'
Type "' >> ~/.copa/config.toml"
Enter
Sleep 500ms
Type "exec zsh"
Enter
Sleep 1.5s

Type "git "
Sleep 500ms

# Tab -- only Copa history matches, no native completions
Tab
Sleep 2s

Escape
Sleep 1s
Ctrl+C
Sleep 500ms

# Reset to hybrid
Type "echo '[completion]' > ~/.copa/config.toml && echo 'mode = "
Type 'hybrid"'
Type "' >> ~/.copa/config.toml"
Enter
Sleep 500ms
Type "exec zsh"
Enter
Sleep 1.5s

Type "# Mode: never -- disables Copa tab completion entirely"
Enter
Sleep 1s
Type "# Set mode = 'never' in ~/.copa/config.toml"
Enter
Sleep 2s
