#!/usr/bin/env bash

# Intentionally expanding alias at definition.
# shellcheck disable=SC2139

main() {
  PYENV_ROOT="${HOME}/.local/lib/pyenv"
  export PYENV_ROOT

  prepend_to_path_if_exists "${PYENV_ROOT}/bin"
  if command -v pyenv 1>/dev/null; then
    alias pyenv-init='unalias pyenv-init; PATH="${PYENV_ROOT}/shims${PATH:+:${PATH}}"; eval "$(pyenv init -)"'
  fi
}

main "$@"
