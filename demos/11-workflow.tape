# Copa Workflow — End-to-end: load shared set, use commands, organize, export
# Shows: the real value of Copa when working with shared command knowledge

Output "11-workflow.gif"

Require copa
Require fzf

Set Shell "zsh"
Set FontSize 16
Set Width 1000
Set Height 600
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 50ms

# Load copa shell integration and cd to repo root
Hide
Type 'eval "$(copa init zsh)"'
Enter
Sleep 1s
Type "cd .."
Enter
Sleep 500ms
Show


# --- Step 1: A teammate shared a .copa file ---
Type "# A teammate shared their docker commands..."
Enter
Sleep 1s

Type "copa share load examples/docker.copa"
Enter
Sleep 1.5s

# See what was loaded
Type "copa share list"
Enter
Sleep 1.5s

# --- Step 2: Use commands from the shared set ---
Type "# Now those commands appear in Ctrl+R and suggestions"
Enter
Sleep 1s

# Open palette and search within the shared set
Ctrl+R
Sleep 1s

# Scope to the shared set
Ctrl+S
Sleep 1s
Type "docker"
Sleep 500ms
Enter
Sleep 1.5s

# See all docker commands with descriptions
Sleep 2s

# Select one to use
Enter
Sleep 1.5s

# Show it in the prompt
Sleep 1.5s
Ctrl+C
Sleep 500ms

# --- Step 3: Your own commands accumulate ---
Type "# Your commands are recorded automatically as you work..."
Enter
Sleep 1s

Type "kubectl get pods -n staging"
Enter
Sleep 1s
Type "kubectl logs -f deploy/api -n staging"
Enter
Sleep 1s
Type "kubectl describe pod api-7f8b9c -n staging"
Enter
Sleep 1.5s

# --- Step 4: Bulk organize and export ---
Type "# Organize and share your knowledge back"
Enter
Sleep 1s

# Open palette and select mode
Ctrl+R
Sleep 1s

# Enter select mode
Ctrl+B
Sleep 1s

# Select the kubectl commands
Type "kubectl"
Sleep 800ms
Tab
Sleep 400ms
Down
Sleep 300ms
Tab
Sleep 400ms
Down
Sleep 300ms
Tab
Sleep 400ms

# Confirm
Enter
Sleep 1s

# Assign group
Type "g"
Sleep 500ms
Type "k8s-staging"
Enter
Sleep 1.5s

# Export the group
Type "copa create -g k8s-staging"
Enter
Sleep 1.5s

# Share it
Type "# Now share: copa share load k8s-staging.copa"
Enter
Sleep 2s
