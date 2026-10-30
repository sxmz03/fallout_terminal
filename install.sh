#!/bin/sh
set -eu
command -v python3 >/dev/null 2>&1 || {
  echo 'Python 3 is required. Install Python 3, then run this installer again.' >&2
  exit 1
}
exec python3 "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/installer.py" "$@"
