# Copa Setup — Installation and first look
# Shows: install, version check, doctor

Output "01-setup.gif"

Set Shell "zsh"
Set FontSize 16
Set Width 900
Set Height 500
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 50ms

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

# Load shell integration
Type 'eval "$(copa init zsh)"'
Enter
Sleep 2s

# Show it works
Type "copa list"
Enter
Sleep 3s
