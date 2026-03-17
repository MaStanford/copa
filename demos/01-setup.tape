# Copa Setup — Installation and first look
# Shows: install, doctor check, quick command list

Output "01-setup.gif"

Require copa
Require fzf

Set Shell "zsh"
Set FontSize 16
Set Width 900
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


# Install Copa
Type "pip install copa-cli"
Enter
Sleep 3s

# Check installation
Type "copa --version"
Enter
Sleep 2s

# Run doctor to verify everything
Type "copa doctor"
Enter
Sleep 3s

# Show available commands
Type "copa list | head -15"
Enter
Sleep 3s

# Sync shell history
Type "copa sync"
Enter
Sleep 3s

# Show updated stats
Type "copa doctor"
Enter
Sleep 3s
