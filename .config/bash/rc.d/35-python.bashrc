#!/usr/bin/env bash

# Use the `site` module to check for module search paths.
# That is, `python -m site`.
case "${MSYSTEM}" in
  MINGW32|MINGW64)
    # Need a non-zero value to disable search in `$HOME/.local`
    PYTHONNOUSERSITE=1
    export PYTHONNOUSERSITE
    ;;
esac

# Move compiled bytecode `.pyc` files to a single directory
# to not clutter up project directories.
PYTHONPYCACHEPREFIX="$HOME/.cache/python"
export PYTHONPYCACHEPREFIX
