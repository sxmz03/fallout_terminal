typeset -g ROBCO_ROOT="${${(%):-%x}:A:h}"
# RobCo prompt status and display hooks; standalone zsh theme.
setopt prompt_subst
zmodload zsh/datetime

function _retro_crt_preexec() {
  _retro_crt_started=$EPOCHREALTIME
}

function _retro_crt_precmd() {
  local result=$?
  local -F elapsed=0
  [[ -n $_retro_crt_started ]] && elapsed=$(( EPOCHREALTIME - _retro_crt_started ))
  unset _retro_crt_started
  typeset -g _retro_crt_result="%F{green}OK%f"
  (( result )) && _retro_crt_result="%F{red}EXIT ${result}%f"
  typeset -g _retro_crt_duration=''
  (( elapsed >= 1 )) && printf -v _retro_crt_duration ' %.1fS' $elapsed

  typeset -g _retro_crt_git=''
  local branch summary line
  local -i staged=0 changed=0 untracked=0 ahead=0 behind=0
  if command git rev-parse --is-inside-work-tree &>/dev/null; then
    branch=$(command git symbolic-ref --quiet --short HEAD 2>/dev/null) || branch="@$(command git rev-parse --short HEAD 2>/dev/null)"
    summary=$(command git --no-optional-locks status --porcelain=v1 --branch 2>/dev/null)
    for line in "${(@f)summary}"; do
      if [[ $line == '## '* ]]; then
        [[ $line =~ 'ahead ([0-9]+)' ]] && ahead=$match[1]
        [[ $line =~ 'behind ([0-9]+)' ]] && behind=$match[1]
      elif [[ $line == '??'* ]]; then
        (( untracked++ ))
      else
        [[ ${line[1]} != ' ' ]] && (( staged++ ))
        [[ ${line[2]} != ' ' ]] && (( changed++ ))
      fi
    done
    # Escape percent signs so branch names cannot inject prompt escapes.
    branch=${branch//\%/%%}
    _retro_crt_git=" %F{green}[GIT:${branch}"
    (( staged )) && _retro_crt_git+=" STAGED:${staged}"
    (( changed )) && _retro_crt_git+=" MODIFIED:${changed}"
    (( untracked )) && _retro_crt_git+=" NEW:${untracked}"
    (( ahead )) && _retro_crt_git+=" AHEAD:${ahead}"
    (( behind )) && _retro_crt_git+=" BEHIND:${behind}"
    (( staged + changed + untracked == 0 )) && _retro_crt_git+=' CLEAN'
    _retro_crt_git+=']%f'
  fi
}

autoload -Uz add-zsh-hook
add-zsh-hook -d preexec _retro_crt_preexec
add-zsh-hook -d precmd _retro_crt_precmd
add-zsh-hook preexec _retro_crt_preexec
add-zsh-hook precmd _retro_crt_precmd


function _robco_display_precmd() {
  local identity="${USER}@${HOST%%.*}"
  local location="$PWD"
  [[ $PWD == $HOME || $PWD == $HOME/* ]] && location="~${PWD#$HOME}"
  typeset -g _robco_identity=${${(U)identity}//\%/%%}
  typeset -g _robco_location=${${(U)location}//\%/%%}
  # DECSCUSR: blinking block, reset after applications change cursor shape.
  printf '\e[1 q'
}
add-zsh-hook -d precmd _robco_display_precmd
add-zsh-hook precmd _robco_display_precmd
PROMPT=$'\n%F{green}+--[${_robco_identity}] [%D{%H:%M:%S}] [${_retro_crt_result}%F{green}${_retro_crt_duration}]%(1j. [JOBS:%j].)%f\n%F{green}| ${_robco_location}%f${_retro_crt_git}\n%F{green}+-->%f '
RPROMPT=''

# RobCo text startup artwork
source "${ROBCO_ROOT}/vault-boy-startup.zsh"
