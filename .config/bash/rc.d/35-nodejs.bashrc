#!/usr/bin/env bash

main() {
  local path="$HOME/.local/lib/npm/packages"

  if [[ -d "${path}" ]]; then
    # NPM packages in homedir
    export NPM_PACKAGES="${path}${NPM_PACKAGES:+:$NPM_PACKAGES}"
    # Tell Node about these packages
    export NODE_PATH="${path}/lib/node_modules${NODE_PATH:+:$NODE_PATH}"

    # Tell our environment about user-installed node tools
    prepend_to_path_if_exists "${path}/bin"
    prepend_to_manpath_if_exists "${path}/share/man"
  fi
}

main "$@"
