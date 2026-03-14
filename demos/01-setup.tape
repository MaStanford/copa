# Copa Setup — First-time installation walkthrough
# Shows: pip install, copa setup wizard, first sync

Output demos/01-setup.gif

Require copa
Require fzf

Set Shell "zsh"
Set FontSize 16
Set Width 900
Set Height 500
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 50ms

# Title
Type "# Copa — Command Palette for your shell"
Enter
Sleep 1s
Type "# Let's set it up!"
Enter
Sleep 1.5s
Ctrl+L

# Install
Type "pip install copa-cli"
Enter
Sleep 2s

# Run setup wizard
Type "copa setup"
Enter
Sleep 1.5s

# Confirm shell integration
Type "y"
Enter
Sleep 500ms

# Choose tab style (menu select)
Type "2"
Enter
Sleep 500ms

# Import history
Type "y"
Enter
Sleep 2s

# Source zshrc
Type "source ~/.zshrc"
Enter
Sleep 1s

# Verify
Type "copa doctor"
Enter
Sleep 2s

# Done
Type "# Ready to go! Press Ctrl+R to open the command palette"
Enter
Sleep 3s
