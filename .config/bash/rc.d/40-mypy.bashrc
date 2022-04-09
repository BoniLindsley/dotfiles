#!/usr/bin/env bash

# Move mypy cache to a single directory
# to not clutter up project directories.
MYPY_CACHE_DIR="$HOME/.cache/mypy"
export MYPY_CACHE_DIR
