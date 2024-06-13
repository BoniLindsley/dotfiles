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
  : "${version?}"

  __log_info "Cloning repository." || return
  local repository='https://github.com/transmission/transmission.git'
  __log_info "  Repository: ${repository}" || return
  local tag="${version}"
  __log_info "  Tag: ${tag}" || return
  __log_info "  Target: ${PWD}" || return
  git clone --branch="${tag}" --depth=1 --recurse-submodules -- "${repository}" "${PWD}" ||
    return
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
  local package='transmission'
  local version='4.0.5'
  local source_directory="${XDG_LOCAL_HOME}/src/${package}"
  if [[ ! -e "${source_directory}" ]]; then
    mkdir -p "${source_directory}" || return
    cd "${source_directory}" || return
    __get_source || return
  else
    __log_info "Source exists: ${source_directory}" || return
  fi
  cd "${source_directory}" || return

  # Ensure install directory is clean and parent directory exists.
  local install_directory="${XDG_LOCAL_HOME}/opt/${package}_${version}"
  rm -dfr "${install_directory}" || return

  local parent_directory
  parent_directory="$(dirname "${install_directory}")"
  mkdir -p "${parent_directory}" || return

  local build_directory="${source_directory}/build"
  cmake \
    -B "${build_directory}" \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_INSTALL_PREFIX="${install_directory}" \
    -DENABLE_CLI=ON \
    -DENABLE_DAEMON=ON \
    -DENABLE_QT=OFF \
    -DENABLE_UTIL=ON ||
    return
  cmake --build "${build_directory}" || return
  cmake \
    --install "${build_directory}" \
    --prefix "${install_directory}" || return
}

__main "$@"
