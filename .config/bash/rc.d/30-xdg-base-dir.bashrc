#!/usr/bin/env bash

: "${HOME?"Undefined variable. (${BASH_SOURCE[0]}:${BASH_LINENO[0]})"}"

# Non-standard.
# For system-dependent files.
# For example, MSYS2 and MinGW64 may use different local directories.
export XDG_LOCAL_HOME="${XDG_LOCAL_HOME:="${HOME}/.local"}"

# Non-standard.
# For files that may be deleted to uninstall an application.
export XDG_LIB_HOME="${XDG_LIB_HOME:="${XDG_LOCAL_HOME}/lib"}"

# For files that may be deleted to save space.
export XDG_CACHE_DIRS="${XDG_CACHE_DIRS:="${HOME}/.cache"}"

# For files that may be deleted to "factory reset" an application.
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:="${HOME}/.config"}"

# For files that may be deleted
# to pretend the application was not used before...
export XDG_DATA_HOME="${XDG_DATA_HOME:="${XDG_LOCAL_HOME}/share"}"

# For files that may be deleted
# to reset runtime customisations and information.
# Files in this directory include: history, layout and logs.
export XDG_STATE_HOME="${XDG_STATE_HOME:="${XDG_LOCAL_HOME}/state"}"
