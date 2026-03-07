# Copa — shell integration for zsh
# Source this file in your .zshrc:  source ~/workspace/copa/copa.zsh

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
_copa_fzf_widget() {
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
        --bind 'ctrl-r:reload('"$copa_bin"' fzf-list --mode frequent)+change-prompt(frequent> )' \
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
