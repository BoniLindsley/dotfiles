#!/usr/bin/env bash

# Intentionally not expanding variable in string.
# shellcheck disable=SC2016
# Intentionally expanding alias at definition.
# shellcheck disable=SC2139

main() {
  local pyenv_init_command
  PYENV_ROOT="${HOME}/.local/lib/pyenv"
  export PYENV_ROOT

  prepend_to_path_if_exists "${PYENV_ROOT}/bin"

  pyenv_init_command='unalias pyenv-init'
  pyenv_init_command+='; prepend_to_path_if_exists "${PYENV_ROOT}/shims"'
  pyenv_init_command+='; eval "$(pyenv init -)"'
  alias pyenv-init="${pyenv_init_command}"
}

main "$@"
