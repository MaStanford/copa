# Copa Recipes — Multi-step command sequences
# Shows: creating a recipe, listing, showing, dry-run, and running it

Output "12-recipes.gif"

Require copa
Require fzf

Set Shell "zsh"
Set FontSize 16
Set Width 1000
Set Height 600
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 60ms

# Load copa
Hide
Type "setopt INTERACTIVE_COMMENTS"
Enter
Sleep 500ms
Type 'eval "$(copa init zsh)"'
Enter
Sleep 1s
Show


# --- Create a recipe ---
Type "# Create a multi-step deploy recipe"
Enter
Sleep 1s

Type "copa recipe add deploy -d 'Build and deploy' -s 'npm run build :: Build project' -s 'npm run test :: Run tests' -s 'docker push app :: Push image'"
Enter
Sleep 2s

# --- List recipes ---
Type "copa recipe list"
Enter
Sleep 1.5s

# --- Show recipe steps ---
Type "copa recipe show deploy"
Enter
Sleep 2s

# --- Dry run ---
Type "# Preview without executing"
Enter
Sleep 800ms

Type "copa recipe run deploy --dry-run"
Enter
Sleep 2s

# --- Remove ---
Type "copa recipe remove deploy"
Enter
Sleep 1.5s

Sleep 2s
