typeset -g ROBCO_ROOT="${${(%):-%x}:A:h}"
# Source to show the fixed image logo in the current iTerm2 session.
# SetBackgroundImageFile may ask for permission in iTerm2 itself.
if [[ ${TERM_PROGRAM:-} == iTerm.app && -z ${TMUX:-}${STY:-} && -t 1 ]]; then
  printf '\033]1337;SetBadgeFormat=\007'
  # Fill the pane without the centred top gap; full blend keeps the image visible.
  # Stretch can slightly change logo proportions when the window aspect ratio changes.
  printf '\033]1337;SetProfileProperty=Background Image Mode=MA==;Blend=MQ==\007'
  printf '\033]1337;SetBackgroundImageFile=%s\007' "$(printf '%s' "${ROBCO_ROOT}/logo.png" | /usr/bin/base64 | /usr/bin/tr -d '\r\n')"
fi
