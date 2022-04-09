#!/usr/bin/env bash

# Contains useful functions for other scripts to use.

is_shell_interactive() {
  [[ $- == *i* ]]
}

is_shell_login() {
  shopt -q login_shell
}

prepend_to_ld_library_path_if_exists() {
  local path
  for path in "$@"; do
    if [[ -d "${path}" ]]; then
      LD_LIBRARY_PATH="${path}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
    fi
  done
}

prepend_to_manpath_if_exists() {
  local path
  for path in "$@"; do
    if [[ -d "${path}" ]]; then
      # Unlike library search path, an "empty" entry
      # is replaced by the default paths, rather than the pwd.
      # So having a trailing colon is expected hre.
      MANPATH="${path}:${MANPATH}"
    fi
  done
}

prepend_to_path_if_exists() {
  local path
  for path in "$@"; do
    if [[ -d "${path}" ]]; then
      PATH="${path}${PATH:+:${PATH}}"
    fi
  done
}

prepend_to_pkg_config_path_if_exists() {
  local path
  for path in "$@"; do
    if [[ -d "${path}" ]]; then
      PKG_CONFIG_PATH="${path}${PKG_CONFIG_PATH:+:${PKG_CONFIG_PATH}}"
    fi
  done
}

source_executables_in_dir() {
  local dir_path
  local path
  for dir_path in "$@"; do
    for path in "${dir_path}"/*; do
      # Only source executable scripts.
      if [[ -x "${path}" ]]; then
        # shellcheck disable=SC1090 # Dynamic loading.
        source "${path}"
      fi
    done
  done
}

source_first_exists() {
  local path
  for path in "$@"; do
    if [[ -f "${path}" ]]; then
      # shellcheck disable=SC1090 # Dynamic loading.
      source "${path}"
      return
    fi
  done
}

source_if_exists() {
  local path
  for path in "$@"; do
    if [[ -f "${path}" ]]; then
      # shellcheck disable=SC1090 # Dynamic loading.
      source "${path}"
    fi
  done
}
