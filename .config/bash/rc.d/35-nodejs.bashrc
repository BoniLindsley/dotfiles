#!/usr/bin/env bash

# # Create user setting in "${HOME}/.npmrc"
# npm config set prefix "${HOME}/.local/lib/npm/packages"
# npm config get prefix
#
# npm --global install npm@latest
# npm --global install node@latest

__main() {
  local path="${HOME}/.local/lib/npm/packages"

  if [[ -d "${path}" ]]; then
    # Tell our environment about user-installed node tools
    prepend_to_path_if_exists "${path}/bin"
    prepend_to_manpath_if_exists "${path}/share/man"
  fi
}

__main "$@"
unset __main
