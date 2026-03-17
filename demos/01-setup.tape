# Copa Setup — Installation and first look
# Shows: install, doctor check, shell integration

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

# Add shell integration
Type "# Add to your .zshrc:"
Enter
Sleep 500ms
Type 'echo '"'"'eval "$(copa init zsh)"'"'"' >> ~/.zshrc'
Enter
Sleep 1s

# Load it now
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
