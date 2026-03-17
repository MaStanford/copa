# Copa Tab Menu Select — tab_accept=2 mode
# Shows: ghost text -> Tab opens menu -> suggestion highlighted -> navigate -> accept
#        Down arrow opens menu, Cmd+Right accepts full suggestion without menu

Output "03-tab-menu-select.gif"

Require copa
Require fzf

Set Shell "zsh"
Set FontSize 16
Set Width 900
Set Height 500
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 80ms

# Load copa shell integration
Hide
Type 'eval "$(copa init zsh)"'
Enter
Sleep 1s
Show


# Type partial command — ghost text shows
Type "adb "
Sleep 800ms
Type "sh"
Sleep 1.5s

# Tab opens completion menu with suggestion highlighted at top
Tab
Sleep 2s

# Navigate with arrow keys to see alternatives
Down
Sleep 600ms
Down
Sleep 600ms

# Go back up to the suggestion
Up
Sleep 600ms
Up
Sleep 600ms

# Enter accepts the highlighted item (without executing)
Enter
Sleep 1.5s

# Clear and demo Down arrow opening the menu
Ctrl+C
Sleep 500ms

Type "git "
Sleep 800ms
Type "lo"
Sleep 1.5s

# Down arrow also opens menu when ghost text is showing
Down
Sleep 2s

# Escape cancels — restores original text
Escape
Sleep 1s

# Ghost text reappears after typing
Type "g"
Sleep 1s

# Cmd+Right accepts full suggestion without opening the menu
Ctrl+E
Sleep 1.5s

# Show the accepted text
Sleep 2s
