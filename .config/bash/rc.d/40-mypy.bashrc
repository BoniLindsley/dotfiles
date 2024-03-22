#!/usr/bin/env bash

# Move mypy cache to a single directory
# to not clutter up project directories.
export MYPY_CACHE_DIR="${XDG_CACHE_HOME:="${HOME}/.cache"}/mypy"
