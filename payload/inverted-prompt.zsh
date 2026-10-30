# Refresh the Fallout-style header address for each prompt.
autoload -Uz add-zsh-hook
_robco_header_address() {
  typeset -g _robco_header_hex
  printf -v _robco_header_hex '0x%04x' $(( (RANDOM * 2 + RANDOM % 2) & 65535 ))
}
_robco_header_address
add-zsh-hook -d precmd _robco_header_address
add-zsh-hook precmd _robco_header_address

# Plain green prompts; only editable command text uses black on green.
PROMPT=$'\n %F{green}[${_robco_header_hex}] [${_robco_identity}] [%D{%H:%M:%S}] [${_retro_crt_result}%F{green}${_retro_crt_duration}]%(1j. [JOBS:%j].)%f\n%F{green}  ${_robco_location/#[~]//home}%f${_retro_crt_git}\n %F{green}[>]%f  '
RPROMPT=''
# ZLE confines this style to input and resets it before command output.
# Save the previous array once so re-sourcing is safe and undo is exact.
if (( ! ${+_robco_input_highlight_saved} )); then
  typeset -ga _robco_previous_zle_highlight=( "${zle_highlight[@]}" )
  typeset -g _robco_input_highlight_saved=1
fi
typeset -ga zle_highlight
zle_highlight=( "${(@)zle_highlight:#default:*}" )
zle_highlight=( "${(@)zle_highlight:#none}" 'default:fg=black,bg=green' )
