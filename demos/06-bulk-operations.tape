# Copa Bulk Operations — Select mode with batch actions
# Shows: Ctrl+B, multi-select, batch group assign

Output demos/06-bulk-operations.gif

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
Sleep 1.5s

# Enter select mode
Ctrl+B
Sleep 1.5s

# Multi-select: Tab toggles items
Tab
Sleep 500ms
Down
Sleep 300ms
Tab
Sleep 500ms
Down
Sleep 300ms
Tab
Sleep 500ms

# Confirm selection
Enter
Sleep 1.5s

# Choose batch action: g = assign group
Type "g"
Sleep 1s

# Type group name
Type "my-project"
Enter
Sleep 2s

# Verify — open palette and scope to the group
Ctrl+R
Sleep 1s
Ctrl+N
Sleep 1.5s

# See the grouped commands
Sleep 2s

Escape
Sleep 1s
