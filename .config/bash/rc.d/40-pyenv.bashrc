#!/usr/bin/env bash

# Intentionally not expanding variable in string.
# shellcheck disable=SC2016
# Intentionally expanding alias at definition.
# shellcheck disable=SC2139


__pyenv_help() {
  cat << 'EOF'
Usage:
  pyenv-install
  rm -dfr "${PYENV_ROOT}"

  pyenv-init
  pyenv install --list
  pyenv install 3.11.4 3.10.12 3.9.17 3.8.17 3.7.17 3.6.15 3.5.10
  pyenv uninstall 3.10.12

  pyenv versions
  pyenv global system 3.10.12 3.5.10
  python3.5
EOF
}
alias pyenv-help=__pyenv_help

main() {
  local pyenv_init_command
  local pyenv_install_command

  PYENV_ROOT="${HOME}/.local/opt/pyenv"
  export PYENV_ROOT
  PYENV_REPO='https://github.com/pyenv/pyenv.git'
  export PYENV_REPO

  pyenv_init_command='prepend_to_path_if_exists "${PYENV_ROOT}/shims"'
  pyenv_init_command+=' && prepend_to_path_if_exists "${PYENV_ROOT}/bin"'
  pyenv_init_command+=' && eval "$(pyenv init -)"'
  pyenv_init_command+=' && unalias pyenv-init'
  alias pyenv-init="${pyenv_init_command}"

  pyenv_install_command='mkdir -p "${PYENV_ROOT}"'
  pyenv_install_command+=' && git clone "${PYENV_REPO}" "${PYENV_ROOT}"'
  alias pyenv-install="${pyenv_install_command}"
}

main "$@"
