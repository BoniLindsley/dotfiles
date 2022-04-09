#!/usr/bin/env bash

# NPM packages in homedir
path="$HOME/.local/lib/npm/packages"
NPM_PACKAGES="$path${NPM_PACKAGES:+:$NPM_PACKAGES}"
export NPM_PACKAGES

# Tell our environment about user-installed node tools
prepend_to_path_if_exists "$NPM_PACKAGES/bin"
prepend_to_manpath_if_exists "$NPM_PACKAGES/share/man"

# Tell Node about these packages
path="$NPM_PACKAGES/lib/node_modules"
NODE_PATH="$path${NODE_PATH:+:$NODE_PATH}"
export NODE_PATH
