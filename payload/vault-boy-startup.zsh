# Apply prompt styling before the startup player renders its first prompt.
source "${ROBCO_ROOT}/inverted-prompt.zsh"

# Clear any inherited/saved badge before playback starts.
if [[ ${TERM_PROGRAM:-} == iTerm.app && -z ${TMUX:-}${STY:-} && -t 1 ]]; then
  printf '\033]1337;SetBadgeFormat=\007'
  # Hide the background for playback; the image sender restores its blend.
  printf '\033]1337;SetProfileProperty=Blend=MA==\007'
fi

# Match %F{green} in the prompt and pace every visible boot character.
function _robco_boot_message() {
  local message='Welcome to ROBCO Industries (TM) Termlink...'
  local i
  printf '\033[0;32m'
  for (( i = 1; i <= ${#message}; i++ )); do
    printf '%s' "${message[i]}"
    if [[ ${message[i]} == . ]]; then
      sleep 0.4
    else
      sleep 0.030
    fi
  done
  printf '\033[0m\n\n'
}

# Show the native GIF first, then type out the first prompt before zsh takes over.
function _robco_startup_art() {
  local previous_status=$?
  add-zsh-hook -d precmd _robco_startup_art
  [[ -o interactive && -t 1 && ${TERM:-dumb} != dumb ]] || return 0
  [[ -z ${_ROBCO_ART_SHOWN:-} ]] || return 0
  typeset -g _ROBCO_ART_SHOWN=1
  local python=${ROBCO_PYTHON:-python3}
  if [[ -n ${ROBCO_NO_ANIMATION:-} ]] || ! command -v "$python" >/dev/null 2>&1; then
    source "${ROBCO_ROOT}/show-image-logo.zsh"
    _robco_boot_message
    return 0
  fi
  local header
  header=$(print -Pn -- "${(e)PROMPT}")
  if ! command "$python" "${ROBCO_ROOT}/startup-animations/play.py" "$header"; then
    _robco_boot_message
  fi
  # Restore the real image background after playback, without splitting panes.
  source "${ROBCO_ROOT}/show-image-logo.zsh"
  return 0
}
autoload -Uz add-zsh-hook
add-zsh-hook -d precmd _robco_startup_art
add-zsh-hook precmd _robco_startup_art
