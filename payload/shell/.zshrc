# This profile has its own shell configuration; other profiles are unaffected.
typeset -g ROBCO_ROOT="${ZDOTDIR:A:h}"
mkdir -p "$HOME/.config/robco-terminal"
autoload -Uz compinit
compinit -d "$HOME/.config/robco-terminal/.zcompdump"
bindkey -e
HISTFILE="$HOME/.config/robco-terminal/history"
HISTSIZE=10000
SAVEHIST=10000
setopt append_history
source "${ROBCO_ROOT}/robco.zsh"
# Optional personal aliases/exports, loaded after the theme.
[[ -f "$HOME/.config/robco-terminal/local.zsh" ]] && source "$HOME/.config/robco-terminal/local.zsh"
