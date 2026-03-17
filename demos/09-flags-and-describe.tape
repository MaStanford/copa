# Copa Flags & Describe — Document commands with metadata
# Shows: adding flags, viewing flags in preview pane

Output 09-flags-and-describe.gif

Require copa
Require fzf

Set Shell "zsh"
Set FontSize 16
Set Width 1000
Set Height 500
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 50ms

# Load copa shell integration
Hide
Type 'eval "$(copa init zsh)"'
Enter
Sleep 1s
Show


# Add a command with flags via CLI
Type 'copa add "rsync -avz" -d "Sync files" -f "-a: Archive mode" -f "-v: Verbose" -f "-z: Compress"'
Enter
Sleep 2s

# Show the preview with flags
Type "copa list"
Enter
Sleep 2s

# Open palette and preview the flagged command
Ctrl+R
Sleep 1s
Type "rsync"
Sleep 2s

# Preview pane shows flags on the right
Sleep 2s

# Edit flags inline with Ctrl+F
Ctrl+F
Sleep 1s
Type "--progress"
Enter
Sleep 500ms
Type "Show transfer progress"
Enter
Sleep 500ms
# Empty flag name to finish
Enter
Sleep 2s

# Escape
Escape
Sleep 2s
