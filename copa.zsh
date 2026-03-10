# Copa — shell integration for zsh
# Source this file in your .zshrc:  source /path/to/copa/copa.zsh
#
# What this does:
#   1. Records every command you run (precmd hook, background, zero latency)
#   2. Replaces Ctrl+R with an fzf command palette that searches across
#      command text AND descriptions — not just raw history
#   3. Ctrl+R cycles modes inside fzf: all → frequent → recent → all
#   4. Composition keys append shell operators (|, &&, &, etc.) to selected commands

# Ensure copa is available
if ! command -v copa &>/dev/null; then
  if [[ -x "$HOME/bin/copa" ]]; then
    export PATH="$HOME/bin:$PATH"
  else
    return
  fi
fi

# --- Load keybinding config (runs once at shell startup) ---
eval "$(copa _fzf-config 2>/dev/null)" || {
  # Fallback defaults if copa _fzf-config fails
  _COPA_EXPECT='ctrl-v,ctrl-o,ctrl-x,ctrl-t,ctrl-a,ctrl-/'
  _COPA_DESCRIBE_KEY='ctrl-d'
  _COPA_GROUP_KEY='ctrl-g'
  _COPA_FLAGS_KEY='ctrl-f'
  _COPA_HEADER='Copa | ^R:cycle | ^V:& | ^O:2>&1 | ^X:| | ^T:> | ^A:&& | ^/:quiet | ^G:grp | ^D:desc | ^F:flag'
  typeset -gA _COPA_SUFFIXES
  _COPA_SUFFIXES[ctrl-v]=' &'
  _COPA_SUFFIXES[ctrl-o]=' 2>&1'
  _COPA_SUFFIXES[ctrl-x]=' | '
  _COPA_SUFFIXES[ctrl-t]=' > '
  _COPA_SUFFIXES[ctrl-a]=' && '
  _COPA_SUFFIXES[ctrl-/]=' 2>/dev/null'
}

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
# Composition keys (configured via copa _fzf-config) append shell operators.
# Requires fzf: brew install fzf
_copa_fzf_widget() {
  if ! command -v fzf &>/dev/null; then
    zle -M "Copa: fzf not found. Install with: brew install fzf"
    return 1
  fi

  local mode="all"
  local output
  local copa_bin="${commands[copa]:-copa}"

  output=$("$copa_bin" fzf-list --mode "$mode" | \
    fzf --ansi \
        --delimiter '┃' \
        --with-nth '2..3' \
        --preview "$copa_bin _preview {1}" \
        --preview-window 'right:40%:wrap' \
        --header "$_COPA_HEADER" \
        --prompt 'copa> ' \
        --height '80%' \
        --layout reverse \
        --expect "$_COPA_EXPECT" \
        --bind "${_COPA_DESCRIBE_KEY}:execute($copa_bin describe {1})+refresh-preview" \
        --bind "${_COPA_GROUP_KEY}:execute($copa_bin _set-group {1})+reload($copa_bin fzf-list)+refresh-preview" \
        --bind "${_COPA_FLAGS_KEY}:execute($copa_bin _set-flags {1})+reload($copa_bin fzf-list)+refresh-preview" \
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

  if [[ -n "$output" ]]; then
    # --expect output: line 1 = key pressed (empty for Enter), line 2+ = selected item
    local key selected cmd suffix
    key=$(echo "$output" | head -1)
    selected=$(echo "$output" | tail -n +2)

    if [[ -n "$selected" ]]; then
      cmd=$(echo "$selected" | cut -d'┃' -f2 | sed 's/^ *//;s/ *$//')
      suffix="${_COPA_SUFFIXES[$key]}"
      LBUFFER="${cmd}${suffix}"
    fi
  fi

  zle reset-prompt
}

zle -N _copa_fzf_widget
bindkey '^R' _copa_fzf_widget

# --- Tab completion ---
# Ensure zsh completion system is available, then register Copa completions.
if ! (( $+functions[compdef] )); then
  autoload -Uz compinit && compinit -i -C
fi
eval "$(copa completion zsh)"

# --- Supplemental tab completion from Copa database ---
# Registers as a fallback completer so that any command (e.g. adb <TAB>)
# gets completion candidates from Copa's command history.
_copa_history_complete() {
    local -a results
    results=("${(@f)$(copa _complete-word "${(@)words[1,CURRENT]}" 2>/dev/null)}")
    (( ${#results} )) && compadd -- "${results[@]}"
}

# Append to existing completers without clobbering user config
() {
    local -a cur
    zstyle -g cur ':completion:*' completer 2>/dev/null
    if (( ! ${cur[(Ie)_copa_history_complete]} )); then
        zstyle ':completion:*' completer ${cur:-_complete} _copa_history_complete
    fi
}
