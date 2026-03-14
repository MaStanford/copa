# Copa Tab Menu Select — tab_accept=2 mode
# Shows: ghost text → Tab opens menu → suggestion highlighted → navigate → accept

Output demos/03-tab-menu-select.gif

Require copa
Require fzf

Set Shell "zsh"
Set FontSize 16
Set Width 900
Set Height 500
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 80ms

# Type partial command — ghost text shows
Type "adb "
Sleep 800ms
Type "sh"
Sleep 1.5s

# Tab opens completion menu with suggestion highlighted
Tab
Sleep 2s

# Navigate with arrow keys to show alternatives
Down
Sleep 600ms
Down
Sleep 600ms

# Go back up to the suggestion
Up
Sleep 600ms
Up
Sleep 600ms

# Tab accepts the highlighted item
Tab
Sleep 1.5s

# Clear and demo with another command
Ctrl+C
Sleep 500ms

Type "git "
Sleep 800ms
Type "lo"
Sleep 1.5s

# Tab opens menu
Tab
Sleep 1.5s

# Escape cancels — restores original text
Escape
Sleep 1.5s

# Show the buffer is restored
Sleep 2s
