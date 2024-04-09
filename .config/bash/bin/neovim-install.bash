#!/usr/bin/env bash

# Logging Functions
# =================

__log() {
  : "${script_name?}"
  while [[ "$#" -gt 0 ]]; do
    printf 1>&2 '%s: %s\n' "${script_name}" "$1" || return
    shift
  done
}

__log_info() {
  if [[ "${__verbose:-0}" -ge 0 ]]; then
    __log "$@" || return
  fi
}

__log_trace() {
  if [[ "${__verbose:-0}" -ge 2 ]]; then
    __log "$@" || return
  fi
}

# Entry Point
# ===========

__get_source() {
  __log_info "Cloning repository." || return
  local repository='https://github.com/neovim/neovim.git'
  __log_info "  Repository: ${repository}" || return
  local version_tag='v0.9.5'
  __log_info "  Version: ${version_tag}" || return
  __log_info "  Target: ${PWD}" || return
  git clone --branch="${version_tag}" --depth=1 \
    -- "${repository}" "${PWD}" || return
}

__main() {
  unset __main

  __verbose=2

  local script_path
  script_path="$(realpath "${BASH_SOURCE[0]}")" || return
  local script_name
  script_name="$(basename "${script_path}")" || return
  __log_trace "Running script at ${script_path}." || return

  # Download source if not found.
  : "${XDG_LOCAL_HOME:="${HOME}/.local"}"
  local source_directory="${XDG_LOCAL_HOME}/src/neovim"
  if [[ ! -e "${source_directory}" ]]; then
    mkdir -p "${source_directory}" || return
    cd "${source_directory}" || return
    __get_source || return
  else
    __log_info "Source exists: ${source_directory}" || return
  fi

  # Get version number.
  cd "${source_directory}" || return
  local tag_name
  tag_name="$(git describe --tags)" || return
  local version_number="${tag_name#v}"

  # Ensure install directory is clean and parent directory exists.
  local install_directory
  install_directory="${XDG_LOCAL_HOME}/opt/neovim_${version_number}"
  rm -dfr "${install_directory}" || return

  local parent_directory
  parent_directory="$(dirname "${install_directory}")"
  mkdir -p "${parent_directory}" || return

  # Follow build instructions at `BUILD.md` and `INSTALL.md`.
  make \
    CMAKE_BUILD_TYPE=RelWithDebInfo \
    CMAKE_EXTRA_FLAGS="-DCMAKE_INSTALL_PREFIX=${install_directory}" ||
    return
  make CMAKE_INSTALL_PREFIX="${install_directory}" install || return
}

__main "$@"
