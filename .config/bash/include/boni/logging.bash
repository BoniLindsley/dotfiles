#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  if [[ -n "${LOGGING__INCLUDED+defined}" ]]; then
    return
  fi
  LOGGING__INCLUDED=
fi

logging__log() {
  local level="$1"
  shift

  local current_level="${LOGGING__LOG_LEVEL:-30}"
  if [[ "${level}" -lt "${current_level}" ]]; then
    return
  fi

  local log_name="${LOGGING__LOG_NAME:-root}"
  while [[ "$#" -gt 0 ]]; do
    printf 1>&2 '%s: %s\n' "${log_name}" "$1" || return
    shift
  done
}

log_trace() {
  logging__log 5 "$@"
}

log_debug() {
  logging__log 10 "$@"
}
log_info() {
  logging__log 20 "$@"
}

log_warning() {
  logging__log 30 "$@"
}
log_error() {
  logging__log 40 "$@"
}

log_critical() {
  logging__log 50 "$@"
}

logging__set_verbosity() {
  local verbosity="${1?}"
  local level_name

  export LOGGING__LOG_LEVEL
  if [[ verbosity -ge 4 ]]; then
    LOGGING__LOG_LEVEL=1
    level_name='ALL'
  elif [[ verbosity -ge 3 ]]; then
    LOGGING__LOG_LEVEL=5
    level_name='TRACE'
  elif [[ verbosity -ge 2 ]]; then
    LOGGING__LOG_LEVEL=10
    level_name='DEBUG'
  elif [[ verbosity -ge 1 ]]; then
    LOGGING__LOG_LEVEL=20
    level_name='INFO'
  elif [[ verbosity -ge 0 ]]; then
    LOGGING__LOG_LEVEL=30
    level_name='WARNING'
  elif [[ verbosity -ge -1 ]]; then
    LOGGING__LOG_LEVEL=40
    level_name='ERROR'
  else
    LOGGING__LOG_LEVEL=50
    level_name='CRITICAL'
  fi

  log_debug "Setting log level to ${LOGGING__LOG_LEVEL} (${level_name})."
}

if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  return
fi

parse_arguments() {
  while [[ 0 -lt $# ]]; do
    case "$1" in
    -q)
      ((--__option_verbose))
      shift
      ;;
    -v)
      ((++__option_verbose))
      shift
      ;;
    *)
      log_error "Unexpected argument -- $1"
      return 1
      ;;
    esac
  done
}

main() {
  local script_path
  script_path="$(realpath "${BASH_SOURCE[0]}")" || return
  local script_name
  script_name="$(basename "${script_path}")" || return

  export LOGGING__LOG_NAME="${script_name}"

  declare -i __option_verbose=0
  parse_arguments "$@" || return

  logging__set_verbosity __option_verbose || return
  log_trace "Running script: ${script_path}" || return

  logging__log 1 "Everything: 1" || return
  logging__log 5 "Trace: 5" || return
  log_debug "Debug: 10" || return
  log_info "Info: 20" || return
  log_warning "Warning: 30" || return
  log_error "Error: 40" || return
  log_critical "Critical: 50" || return
}

main "$@"
