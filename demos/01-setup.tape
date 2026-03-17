# Copa Setup — Getting started
# Shows: install command, version check, doctor, shell integration

Output "01-setup.gif"

Require copa

Set Shell "zsh"
Set FontSize 16
Set Width 900
Set Height 500
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 50ms

# Show the install command (but don't run it — already installed)
Type "pip install copa-cli"
Sleep 2s
Ctrl+C
Sleep 500ms

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

# Show it works — type something and see suggestion
Type "copa "
Sleep 1s
Type "li"
Sleep 1.5s
Tab
Sleep 2s
