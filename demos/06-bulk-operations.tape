# Copa Bulk Operations — Select, group, and export
# Shows: Ctrl+B select mode, multi-select, batch group assign, export as .copa file

Output "06-bulk-operations.gif"

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
Sleep 1.5s

# Enter select mode with Ctrl+B
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

# Verify — open palette and cycle to the group
Ctrl+R
Sleep 1s
Ctrl+N
Sleep 1.5s

# See the grouped commands
Sleep 2s

Escape
Sleep 1s

# Now export the group as a shareable .copa file
Type "copa create -g my-project"
Enter
Sleep 2s

# Show the generated file
Type "cat my-project.copa | head -20"
Enter
Sleep 3s

# Share it
Type "# Share: copa share load my-project.copa"
Enter
Sleep 2s
