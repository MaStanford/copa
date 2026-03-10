# Copa — shell integration for zsh
# Source this file in your .zshrc:  source /path/to/copa/copa.zsh
#
# What this does:
#   1. Records every command you run (precmd hook, background, zero latency)
#   2. Replaces Ctrl+R with an fzf command palette that searches across
#      command text AND descriptions — not just raw history
#   3. Ctrl+R cycles modes inside fzf: all → frequent → recent → all

# Ensure copa is available
if ! command -v copa &>/dev/null; then
  if [[ -x "$HOME/bin/copa" ]]; then
    export PATH="$HOME/bin:$PATH"
  else
    return
  fi
fi

# --- precmd hook: record last command ---
_copa_precmd() {
  local last_cmd
  last_cmd="$(fc -ln -1 2>/dev/null)"
  last_cmd="${last_cmd## }"  # strip leading space
  if [[ -n "$last_cmd" && "$last_cmd" != _copa_* ]]; then
    copa _record "$last_cmd" &!
  fi
}

# Add to precmd hooks (avoid duplicates)
autoload -Uz add-zsh-hook
add-zsh-hook precmd _copa_precmd

# --- Ctrl+R: fzf-powered command palette ---
# Replaces default zsh reverse-search. fzf searches all visible fields:
# command text, description, group badges, shared-set names, and frequency.
# Selected command is placed into the prompt without executing.
# Requires fzf: brew install fzf
_copa_fzf_widget() {
  if ! command -v fzf &>/dev/null; then
    zle -M "Copa: fzf not found. Install with: brew install fzf"
    return 1
  fi

  local mode="all"
  local selected
  local copa_bin="${commands[copa]:-copa}"

  selected=$("$copa_bin" fzf-list --mode "$mode" | \
    fzf --ansi \
        --delimiter '┃' \
        --with-nth '2..' \
        --preview "$copa_bin _preview {1}" \
        --preview-window 'right:40%:wrap' \
        --header 'Copa — Ctrl+R to cycle: all → frequent → recent' \
        --prompt 'copa> ' \
        --height '80%' \
        --layout reverse \
        --bind 'ctrl-r:transform:
          if [[ $FZF_PROMPT == "copa> " ]]; then
            echo "reload('"$copa_bin"' fzf-list --mode frequent)+change-prompt(frequent> )"
          elif [[ $FZF_PROMPT == "frequent> " ]]; then
            echo "reload('"$copa_bin"' fzf-list --mode recent)+change-prompt(recent> )"
          else
            echo "reload('"$copa_bin"' fzf-list --mode all)+change-prompt(copa> )"
          fi' \
        --bind 'enter:accept' \
  )

  if [[ -n "$selected" ]]; then
    # Extract command text (second field after ┃)
    local cmd
    cmd=$(echo "$selected" | cut -d'┃' -f2 | sed 's/^ *//;s/ *$//')
    LBUFFER="$cmd"
  fi

  zle reset-prompt
}

zle -N _copa_fzf_widget
bindkey '^R' _copa_fzf_widget
