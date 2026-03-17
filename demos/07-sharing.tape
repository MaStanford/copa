# Copa Sharing — Load, create, and share .copa files
# Shows: loading example sets, creating from groups, sharing workflow

Output 07-sharing.gif

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


# Load an example .copa file
Type "copa share load examples/git.copa"
Enter
Sleep 1.5s

Type "copa share load examples/docker.copa"
Enter
Sleep 1.5s

# List shared sets
Type "copa share list"
Enter
Sleep 1.5s

# Search within a shared set
Type 'copa search "stash" --set git'
Enter
Sleep 1.5s

# Create a .copa file from a group
Type "copa create -g android"
Enter
Sleep 1.5s

# Show the generated file
Type "cat android.copa | head -20"
Enter
Sleep 2s

# Share workflow explanation
Type "# Share via git, Slack, or any file share:"
Enter
Sleep 500ms
Type "# copa share load android.copa"
Enter
Sleep 2s
