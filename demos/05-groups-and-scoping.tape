# Copa Groups — Organize, assign, filter, and cycle
# Shows: Ctrl+G assign, Ctrl+S scope, Ctrl+N cycle

Output 05-groups-and-scoping.gif

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


# First, add some commands with groups via CLI
Type 'copa add "adb devices" -d "List connected devices" -g android'
Enter
Sleep 1s
Type 'copa add "adb logcat" -d "Stream device logs" -g android'
Enter
Sleep 1s
Type 'copa add "docker ps" -d "List running containers" -g devops'
Enter
Sleep 1s
Type 'copa add "docker logs -f" -d "Follow container logs" -g devops'
Enter
Sleep 1.5s

# Open palette
Ctrl+R
Sleep 1.5s

# Cycle groups with Ctrl+N
Ctrl+N
Sleep 1.5s
Ctrl+N
Sleep 1.5s
Ctrl+N
Sleep 1.5s

# Scope with Ctrl+S — opens group picker
Ctrl+S
Sleep 1s
# Select android group
Type "android"
Sleep 500ms
Enter
Sleep 1.5s

# Now we see only android commands
Sleep 1.5s

# Escape back to all
Escape
Sleep 2s
