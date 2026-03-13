# Copa — shell integration for zsh
# Add to your .zshrc:  eval "$(copa init zsh)"
#
# First time? Run these to get started:
#   copa _init          # create the database
#   copa sync           # import your shell history
#   copa doctor         # check everything is set up
#
# What this does:
#   1. Records every command you run (precmd hook, background, zero latency)
#   2. Replaces Ctrl+R with an fzf command palette that searches across
#      command text AND descriptions — not just raw history
#   3. Ctrl+R cycles modes inside fzf: all → frequent → recent → all
#   4. Composition keys append shell operators (|, &&, &, etc.) to selected commands

# --- Load keybinding config (runs once at shell startup) ---
eval "$(copa _fzf-config 2>/dev/null)" || {
  # Fallback defaults if copa _fzf-config fails
  _COPA_EXPECT='ctrl-v,ctrl-o,ctrl-/'
  _COPA_DESCRIBE_KEY='ctrl-d'
  _COPA_GROUP_KEY='ctrl-g'
  _COPA_FLAGS_KEY='ctrl-f'
  _COPA_FILTER_GROUP_KEY='ctrl-s'
  _COPA_CYCLE_GROUP_KEY='ctrl-n'
  _COPA_TOGGLE_HEADER_KEY='ctrl-h'
  _COPA_SELECT_KEY='ctrl-b'
  _COPA_HEIGHT='80%'
  _COPA_PREVIEW_SIZE='40%'
  _COPA_COMPLETION_BRANDING='true'
  _COPA_COMPLETION_MODE='hybrid'
  _COPA_SUGGEST_ENABLED='true'
  _COPA_SUGGEST_MIN_LENGTH='2'
  _COPA_SUGGEST_TAB_ACCEPT='2'
  _COPA_HEADER=$'Copa | ^R:cycle | ^V:& | ^O:2>&1 | ^X:| | ^T:> | ^A:&& | ^/:quiet | ^H:keys\n^G:grp | ^D:desc | ^F:flag | ^S:scope | ^N:↻grp'
  typeset -gA _COPA_CLOSE_SUFFIXES
  _COPA_CLOSE_SUFFIXES[ctrl-v]=' &'
  _COPA_CLOSE_SUFFIXES[ctrl-o]=' 2>&1'
  _COPA_CLOSE_SUFFIXES[ctrl-/]=' 2>/dev/null'
  typeset -gA _COPA_CONTINUE_SUFFIXES
  _COPA_CONTINUE_SUFFIXES[ctrl-x]=' | '
  _COPA_CONTINUE_SUFFIXES[ctrl-t]=' > '
  _COPA_CONTINUE_SUFFIXES[ctrl-a]=' && '
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
  [[ "$_COPA_SUGGEST_ENABLED" == 'true' ]] && _copa_suggest_clear
  if ! command -v fzf &>/dev/null; then
    zle -M "Copa: fzf not found. Install with: brew install fzf"
    return 1
  fi

  local mode="all"
  local output
  local copa_bin="${commands[copa]:-copa}"
  local _copa_modal_file=$(mktemp -t copa_modal.XXXXXX)
  local _copa_compose_file=$(mktemp -t copa_compose.XXXXXX)
  local accumulated=""

  while true; do
    # Clear compose file for this iteration
    > "$_copa_compose_file"

    # Build prompt showing accumulated chain
    local prompt_text="copa> "
    if [[ -n "$accumulated" ]]; then
      local display="$accumulated"
      # Truncate long chains: show last 30 chars
      if (( ${#display} > 30 )); then
        display="...${display: -30}"
      fi
      prompt_text="copa [${display}]> "
    fi

    # Build fzf args dynamically
    local -a fzf_args=(
        --ansi
        --delimiter '┃'
        --with-nth '2..3'
        --preview "$copa_bin _preview {1}"
        --preview-window "right:${_COPA_PREVIEW_SIZE}:wrap"
        --header "$_COPA_HEADER"
        --prompt "$prompt_text"
        --height "${_COPA_HEIGHT}"
        --layout reverse
        --expect "$_COPA_EXPECT"
        --bind "${_COPA_DESCRIBE_KEY}:execute($copa_bin describe {1})+refresh-preview"
        --bind "${_COPA_FLAGS_KEY}:execute($copa_bin _set-flags {1})+reload($copa_bin fzf-list)+refresh-preview"
        --bind "${_COPA_FILTER_GROUP_KEY}:reload($copa_bin _list-groups)+change-prompt(scope> )+clear-query+hide-preview"
        --bind "${_COPA_GROUP_KEY}:transform:
          echo {1} > ${_copa_modal_file};
          echo \"reload(${copa_bin} _list-groups-for-assign)+change-prompt(group> )+clear-query+hide-preview\""
        --bind "${_COPA_CYCLE_GROUP_KEY}:transform:
          cur_group='(all)';
          if [[ \$FZF_PROMPT =~ 'copa \\[(.+)\\]> ' ]]; then
            cur_group=\"\${match[1]}\";
          fi;
          next=\$(${copa_bin} _next-group \"\$cur_group\");
          if [[ \$next == '(all)' ]]; then
            echo \"reload(${copa_bin} fzf-list --mode all)+change-prompt(copa> )\";
          else
            echo \"reload(${copa_bin} fzf-list --mode group --group \$next)+change-prompt(copa [\$next]> )\";
          fi"
        --bind 'ctrl-r:transform:
          if [[ $FZF_PROMPT == "copa> " ]]; then
            echo "reload('"$copa_bin"' fzf-list --mode frequent)+change-prompt(frequent> )"
          elif [[ $FZF_PROMPT == "frequent> " ]]; then
            echo "reload('"$copa_bin"' fzf-list --mode recent)+change-prompt(recent> )"
          else
            echo "reload('"$copa_bin"' fzf-list --mode all)+change-prompt(copa> )"
          fi'
        --bind "${_COPA_TOGGLE_HEADER_KEY}:toggle-header"
        --bind "${_COPA_SELECT_KEY}:execute-silent(printf 'SELECT' > ${_copa_compose_file})+accept"
        --bind 'enter:transform:
          if [[ $FZF_PROMPT == "scope> " ]]; then
            selected={2};
            if [[ $selected == "(all)" ]]; then
              echo "reload('"$copa_bin"' fzf-list --mode all)+change-prompt(copa> )+clear-query+show-preview"
            else
              echo "reload('"$copa_bin"' fzf-list --mode group --group $selected)+change-prompt(copa [$selected]> )+clear-query+show-preview"
            fi
          elif [[ $FZF_PROMPT == "group> " ]]; then
            cmd_id=$(cat '"${_copa_modal_file}"');
            selected={2};
            '"$copa_bin"' _set-group-direct $cmd_id $selected;
            echo "reload('"$copa_bin"' fzf-list)+change-prompt(copa> )+clear-query+show-preview"
          else
            echo "accept"
          fi'
        --bind 'esc:transform:
          if [[ $FZF_PROMPT == "scope> " || $FZF_PROMPT == "group> " ]]; then
            echo "reload('"$copa_bin"' fzf-list)+change-prompt(copa> )+clear-query+show-preview"
          else
            echo "abort"
          fi'
    )

    # Add continue key bindings dynamically — these write suffix to temp file + accept
    local _ckey _csuffix
    for _ckey _csuffix in "${(@kv)_COPA_CONTINUE_SUFFIXES}"; do
      fzf_args+=(--bind "${_ckey}:execute-silent(printf '%s' '${_csuffix}' > ${_copa_compose_file})+accept")
    done

    output=$("$copa_bin" fzf-list --mode "$mode" | fzf "${fzf_args[@]}")

    # Check if a continue key was pressed (compose file has content)
    local compose_suffix=""
    [[ -s "$_copa_compose_file" ]] && compose_suffix=$(<"$_copa_compose_file")

    if [[ "$compose_suffix" == "SELECT" ]]; then
      # Enter select mode — run a separate fzf with --multi
      _copa_select_mode "$copa_bin"
      break
    fi

    if [[ -n "$output" ]]; then
      local key selected cmd
      key=$(echo "$output" | head -1)
      selected=$(echo "$output" | tail -n +2)

      if [[ -n "$selected" && "$selected" == *┃* ]]; then
        cmd=$(echo "$selected" | cut -d'┃' -f2 | sed 's/^ *//;s/ *$//')

        if [[ -n "$compose_suffix" ]]; then
          # Continue key: accumulate and re-open fzf
          accumulated="${accumulated}${cmd}${compose_suffix}"
          continue
        fi

        # Close key or Enter — finalize
        local suffix="${_COPA_CLOSE_SUFFIXES[$key]}"
        LBUFFER="${accumulated}${cmd}${suffix}"
      fi
    fi
    # ESC, empty output, or no ┃ — break without setting LBUFFER
    break
  done

  [[ -f "$_copa_modal_file" ]] && rm -f "$_copa_modal_file"
  [[ -f "$_copa_compose_file" ]] && rm -f "$_copa_compose_file"

  zle reset-prompt
}

# --- Select mode: multi-select items then batch-operate ---
_copa_select_mode() {
  local copa_bin="${1:-${commands[copa]:-copa}}"
  local select_output

  select_output=$("$copa_bin" fzf-list --mode all | fzf \
    --ansi \
    --multi \
    --delimiter '┃' \
    --with-nth '2..3' \
    --preview "$copa_bin _preview {1}" \
    --preview-window "right:${_COPA_PREVIEW_SIZE}:wrap" \
    --header "SELECT MODE | Tab:toggle | Enter:batch action | Esc:cancel" \
    --prompt "select> " \
    --height "${_COPA_HEIGHT}" \
    --layout reverse \
    --bind 'ctrl-r:transform:
      if [[ $FZF_PROMPT == "select> " ]]; then
        echo "reload('"$copa_bin"' fzf-list --mode frequent)+change-prompt(select [frequent]> )"
      elif [[ $FZF_PROMPT == "select [frequent]> " ]]; then
        echo "reload('"$copa_bin"' fzf-list --mode recent)+change-prompt(select [recent]> )"
      else
        echo "reload('"$copa_bin"' fzf-list --mode all)+change-prompt(select> )"
      fi'
  )

  [[ -z "$select_output" ]] && return

  # Parse selected IDs from output lines
  local -a selected_ids
  local line
  while IFS= read -r line; do
    if [[ "$line" == *┃* ]]; then
      local id_field="${line%%┃*}"
      id_field="${id_field// /}"  # trim spaces
      [[ -n "$id_field" ]] && selected_ids+=("$id_field")
    fi
  done <<< "$select_output"

  (( ${#selected_ids} == 0 )) && return

  # Show batch action menu via tty
  local count=${#selected_ids}
  local action
  local _copa_tty
  exec {_copa_tty}</dev/tty

  echo "Selected $count command(s)." >&$_copa_tty
  echo "  g = assign group" >&$_copa_tty
  echo "  d = delete" >&$_copa_tty
  echo "  a = auto-describe (LLM)" >&$_copa_tty
  echo "  q = cancel" >&$_copa_tty
  echo -n "Action: " >&$_copa_tty
  read -u $_copa_tty action

  exec {_copa_tty}<&-

  case "$action" in
    g)
      "$copa_bin" _batch-group "${selected_ids[@]}"
      ;;
    d)
      "$copa_bin" _batch-delete "${selected_ids[@]}"
      ;;
    a)
      "$copa_bin" _batch-describe "${selected_ids[@]}"
      ;;
  esac
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
# Mode is controlled by _COPA_COMPLETION_MODE (set via copa _fzf-config):
#   fallback — only when native completers found nothing (default)
#   always   — Copa completions replace native completions
#   hybrid   — Copa completions shown alongside native completions
#   never    — disable Copa tab completion entirely
if [[ "$_COPA_COMPLETION_MODE" != 'never' ]]; then

_copa_history_complete() {
    # Hoist pending inline suggestion as a completion candidate
    if [[ -n "$_COPA_SUGGEST_PENDING" ]]; then
        local pending="$_COPA_SUGGEST_PENDING"
        _COPA_SUGGEST_PENDING=""
        local cur_word="${words[CURRENT]}"
        local prefix_len=$(( ${#LBUFFER} - ${#cur_word} ))
        local insert_text="${pending:$prefix_len}"
        if [[ -n "$insert_text" ]]; then
            compadd -U -Q -V 'copa-suggestion' -X 'SUGGESTED' -o nosort -- "$insert_text"
        fi
        compstate[list]='list force'
        compstate[insert]='menu'
    fi
    # In fallback mode, only show when native completers found nothing
    if [[ "$_COPA_COMPLETION_MODE" == 'fallback' ]]; then
        (( compstate[nmatches] > 0 )) && return
    fi
    # Skip bare <TAB> on empty line; allow empty subcommand completion in hybrid/always
    if [[ -z "${words[CURRENT]}" ]]; then
        (( CURRENT <= 1 )) && return
        [[ "$_COPA_COMPLETION_MODE" == 'fallback' ]] && return
    fi
    # Skip internal copa commands
    [[ "${words[CURRENT]}" == _copa_* ]] && return
    local -a results
    results=("${(@f)$(copa _complete-word "${(@)words[1,CURRENT]}" 2>/dev/null)}")
    if (( ${#results} )); then
        if [[ "$_COPA_COMPLETION_MODE" == 'always' ]]; then
            # Replace: clear native matches, add only Copa results
            compadd -U -V 'copa-history' -X 'COPA HISTORY' -o nosort -- "${results[@]}"
        else
            # fallback & hybrid: add Copa results as a separate group
            compadd -V 'copa-history' -X 'COPA HISTORY' -o nosort -- "${results[@]}"
        fi
    fi
}

# Append to existing completers without clobbering user config
() {
    local -a cur
    zstyle -g cur ':completion:*' completer 2>/dev/null
    if (( ! ${cur[(Ie)_copa_history_complete]} )); then
        zstyle ':completion:*' completer ${cur:-_complete} _copa_history_complete
    fi
    # Enable group separation so Copa results appear as a distinct section
    zstyle ':completion:*' group-name ''
    # Copa suggestion first, then Copa history, then native completions
    zstyle ':completion:*' group-order copa-suggestion copa-history
    # Interactive menu with highlighting; Tab accepts the focused item
    zstyle ':completion:*' menu select
    zmodload zsh/complist 2>/dev/null
    bindkey -M menuselect '^I' .accept-line
    # Raise threshold before "show all N?" prompt
    LISTMAX=200
    # Copa completion branding: show group description headers
    if [[ "$_COPA_COMPLETION_BRANDING" != 'false' ]]; then
        zstyle ':completion:*:descriptions' format '%F{cyan}%B──── %d ────%b%f'
    fi
}

fi  # end _COPA_COMPLETION_MODE != 'never'

# --- Inline suggestions (ghost text) ---
# Shows grey suggestion text after the cursor as you type.
# Controlled by _COPA_SUGGEST_ENABLED (set via copa _fzf-config).
if [[ "$_COPA_SUGGEST_ENABLED" == 'true' ]]; then

typeset -g _COPA_SUGGESTION=""
typeset -g _COPA_SUGGEST_LATCHED=0  # 1 = suppressed (backspace latch)
typeset -g _COPA_SUGGEST_PENDING=""  # full suggestion passed to completion system

# _copa_suggest_clear is always defined (used by _copa_fzf_widget)
_copa_suggest_clear() {
  _COPA_SUGGESTION=""
  _COPA_SUGGEST_PENDING=""
  POSTDISPLAY=""
  region_highlight=()
}

_copa_suggest_fetch() {
  _COPA_SUGGESTION=""
  _COPA_SUGGEST_PENDING=""
  POSTDISPLAY=""
  region_highlight=()
  (( _COPA_SUGGEST_LATCHED )) && return  # suppressed by backspace latch
  (( ${#BUFFER} < _COPA_SUGGEST_MIN_LENGTH )) && return
  (( CURSOR != ${#BUFFER} )) && return  # skip if cursor not at end
  local result
  result=$(copa _suggest "$BUFFER" 2>/dev/null)
  if [[ -n "$result" && "$result" != "$BUFFER" ]]; then
    _COPA_SUGGESTION="$result"
    POSTDISPLAY="${result:${#BUFFER}}"
    region_highlight=("P0 ${#POSTDISPLAY} fg=8")
  fi
}

# --- Widget wrappers ---

# self-insert: type a character, then fetch suggestion
_copa_suggest_self_insert() {
  zle .self-insert
  _copa_suggest_fetch
}
zle -N self-insert _copa_suggest_self_insert

# backward-delete-char (Backspace): latch — suppress suggestions until Tab
_copa_suggest_backward_delete_char() {
  _COPA_SUGGEST_LATCHED=1
  _copa_suggest_clear
  zle .backward-delete-char
}
zle -N backward-delete-char _copa_suggest_backward_delete_char

# Tab: accept suggestion or open completion menu.
# Uses menu-complete (not expand-or-complete) to enter menu-select
# mode immediately on the first Tab press.
_copa_suggest_expand_or_complete() {
  if [[ -n "$_COPA_SUGGESTION" ]]; then
    if [[ "$_COPA_SUGGEST_TAB_ACCEPT" == '1' ]]; then
      # tab_accept=1: directly accept the suggestion
      BUFFER="$_COPA_SUGGESTION"
      CURSOR=${#BUFFER}
      _copa_suggest_clear
    else
      # tab_accept=2: open completion menu with suggestion hoisted to top
      local pending="$_COPA_SUGGESTION"
      _copa_suggest_clear
      _COPA_SUGGEST_PENDING="$pending"
      zle expand-or-complete
      _copa_suggest_fetch  # re-suggest after menu closes
    fi
    return
  fi
  if (( _COPA_SUGGEST_LATCHED )); then
    _COPA_SUGGEST_LATCHED=0
    _copa_suggest_fetch
    return
  fi
  zle expand-or-complete
  _copa_suggest_fetch  # re-suggest after menu closes
}
zle -N _copa_suggest_expand_or_complete
bindkey '^I' _copa_suggest_expand_or_complete

# forward-char (Right arrow): accept one word if ghost text showing at EOL
_copa_suggest_forward_char() {
  if [[ -n "$POSTDISPLAY" && -n "$_COPA_SUGGESTION" && $CURSOR -eq ${#BUFFER} ]]; then
    # Accept one word from the suggestion
    local suffix="${_COPA_SUGGESTION:${#BUFFER}}"
    local word
    # Extract leading whitespace + next word
    if [[ "$suffix" =~ ^[[:space:]]*[^[:space:]]+ ]]; then
      word="$MATCH"
    else
      word="$suffix"
    fi
    BUFFER="${BUFFER}${word}"
    CURSOR=${#BUFFER}
    # Update ghost text from existing suggestion (no re-query, no flicker)
    local remaining="${_COPA_SUGGESTION:${#BUFFER}}"
    if [[ -n "$remaining" ]]; then
      POSTDISPLAY="$remaining"
      region_highlight=("P0 ${#POSTDISPLAY} fg=8")
    else
      # Fully accepted; clear and re-fetch for extended suggestions
      _copa_suggest_clear
      _COPA_SUGGEST_LATCHED=0
      _copa_suggest_fetch
    fi
  else
    zle .forward-char
  fi
}
zle -N forward-char _copa_suggest_forward_char

# forward-word: same as forward-char when ghost text showing
_copa_suggest_forward_word() {
  if [[ -n "$POSTDISPLAY" && -n "$_COPA_SUGGESTION" && $CURSOR -eq ${#BUFFER} ]]; then
    _copa_suggest_forward_char
  else
    zle .forward-word
  fi
}
zle -N forward-word _copa_suggest_forward_word

# accept-line (Enter): clear suggestion + latch, then execute
_copa_suggest_accept_line() {
  _copa_suggest_clear
  _COPA_SUGGEST_LATCHED=0
  zle .accept-line
}
zle -N accept-line _copa_suggest_accept_line

# send-break (Esc): dismiss ghost text suggestion or normal
_copa_suggest_send_break() {
  if [[ -n "$POSTDISPLAY" && -n "$_COPA_SUGGESTION" ]]; then
    _copa_suggest_clear
    zle -R  # redraw to remove ghost text
  else
    _COPA_SUGGESTION=""  # clear stored suggestion silently
    zle .send-break
  fi
}
zle -N send-break _copa_suggest_send_break

# History navigation: clear suggestion then call original
_copa_suggest_up_line_or_history() {
  _copa_suggest_clear
  zle .up-line-or-history
}
zle -N up-line-or-history _copa_suggest_up_line_or_history

_copa_suggest_down_line_or_history() {
  if [[ -n "$_COPA_SUGGESTION" ]]; then
    # Suggestion showing: open completion menu with suggestion at top
    local pending="$_COPA_SUGGESTION"
    _copa_suggest_clear
    _COPA_SUGGEST_PENDING="$pending"
    zle expand-or-complete
    _copa_suggest_fetch
  else
    zle .down-line-or-history
  fi
}
zle -N down-line-or-history _copa_suggest_down_line_or_history

_copa_suggest_up_line_or_search() {
  _copa_suggest_clear
  zle .up-line-or-search
}
zle -N up-line-or-search _copa_suggest_up_line_or_search

_copa_suggest_down_line_or_search() {
  if [[ -n "$_COPA_SUGGESTION" ]]; then
    # Suggestion showing: open completion menu with suggestion at top
    local pending="$_COPA_SUGGESTION"
    _copa_suggest_clear
    _COPA_SUGGEST_PENDING="$pending"
    zle expand-or-complete
    _copa_suggest_fetch
  else
    zle .down-line-or-search
  fi
}
zle -N down-line-or-search _copa_suggest_down_line_or_search

# Editing operations: backward-kill latches, forward operations re-fetch
_copa_suggest_backward_kill_word() {
  _COPA_SUGGEST_LATCHED=1
  _copa_suggest_clear
  zle .backward-kill-word
}
zle -N backward-kill-word _copa_suggest_backward_kill_word

_copa_suggest_kill_word() {
  zle .kill-word
  _copa_suggest_fetch
}
zle -N kill-word _copa_suggest_kill_word

_copa_suggest_kill_line() {
  zle .kill-line
  _copa_suggest_fetch
}
zle -N kill-line _copa_suggest_kill_line

_copa_suggest_backward_kill_line() {
  _COPA_SUGGEST_LATCHED=1
  _copa_suggest_clear
  zle .backward-kill-line
}
zle -N backward-kill-line _copa_suggest_backward_kill_line

_copa_suggest_kill_whole_line() {
  _COPA_SUGGEST_LATCHED=1
  _copa_suggest_clear
  zle .kill-whole-line
}
zle -N kill-whole-line _copa_suggest_kill_whole_line

_copa_suggest_yank() {
  zle .yank
  _copa_suggest_fetch
}
zle -N yank _copa_suggest_yank

fi  # end _COPA_SUGGEST_ENABLED == 'true'
