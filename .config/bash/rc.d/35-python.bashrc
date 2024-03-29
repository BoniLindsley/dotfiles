#!/usr/bin/env bash

# Use the `site` module to check for module search paths.
# That is, `python -m site`.
case "${MSYSTEM}" in
MINGW32 | MINGW64)
  # Need a non-zero value to disable search in `$HOME/.local`
  export PYTHONNOUSERSITE=1
  ;;
esac

# Move compiled bytecode `.pyc` files to a single directory
# to not clutter up project directories.
# Requires Python 3.8.
export PYTHONPYCACHEPREFIX="${XDG_CACHE_DIRS:="${HOME}/.cache"}/python"

__main() {
  local config_path
  config_path="${XDG_CONFIG_HOME:="${HOME}/.config"}/python/startup.py"

  if [[ -x "${config_path}" ]]; then
    export PYTHONSTARTUP="${config_path}"
  fi

  prepend_to_path_if_exists "${XDG_LIB_HOME:="${XDG_LOCAL_HOME:="${HOME:=.}"/.local}"/lib}"/python/venv/default/bin
}

__main "$@"
unset __main
