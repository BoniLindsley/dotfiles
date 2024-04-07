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

__log_error() {
  local exit_code="$?"
  if [[ "${__verbose:-0}" -ge -1 ]]; then
    __log "$@" || return
  fi
  return "${exit_code}"
}

__log_info() {
  if [[ "${__verbose:-0}" -ge 0 ]]; then
    __log "$@" || return
  fi
}

__log_debug() {
  if [[ "${__verbose:-0}" -ge 1 ]]; then
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
  __log_info "Cloning Emacpeak." || return
  local emacspeak_repository='https://github.com/tvraman/emacspeak.git'
  __log_info "  Repository: ${emacspeak_repository}" || return
  local version_tag='59.0'
  __log_info "  Version: ${version_tag}" || return
  __log_info "  Target: ${PWD}" || return
  git clone --branch="${version_tag}" --depth=1 \
    -- "${emacspeak_repository}" "${PWD}" || return
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
  local source_directory="${XDG_LOCAL_HOME}/src/emacspeak"
  if [[ ! -e "${source_directory}" ]]; then
    mkdir -p "${source_directory}" || return
    cd "${source_directory}" || return
    __get_source || return
  else
    __log_info "Source exists: ${source_directory}" || return
  fi

  # Follow build instructions at `etc/install.org`.
  cd "${source_directory}" || return
  make config || return
  make || return
  # Install eSpeak NG if necessary:
  # `apt install --no-install-recommends libespeak-ng-dev`
  # Can be removed afterwards. Just need to keep `libespeak-ng`.
  cd 'servers/native-espeak' || return
  make || return

  local install_directory
  install_directory="${XDG_LOCAL_HOME}/opt/emacspeak"
  local parent_directory
  parent_directory="$(dirname "${install_directory}")"
  mkdir -p "${parent_directory}" || return
  rm -dfr "${install_directory}" || return
  mv "${source_directory}" "${install_directory}" || return
}

__main "$@"
