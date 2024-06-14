#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  if [[ -n "${ARGPARSE__INCLUDED+defined}" ]]; then
    return
  fi
  ARGPARSE__INCLUDED=
fi

argparse__remove_single_option() {
  : "${current_argument?}"
  if [[ "${#current_argument}" -le 2 ]]; then
    unset current_argument
  else
    current_argument="-${current_argument:2}"
  fi
}

if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  return
fi

parse_arguments() {
  local current_argument
  unset current_argument

  if [[ $# -gt 0 ]]; then
    current_argument="$1"
    shift
  fi

  while [[ -n "${current_argument+defined}" ]]; do
    case "${current_argument}" in
    --quiet)
      ((--arguments[verbose]))
      unset current_argument
      ;;
    -q*)
      ((--arguments[verbose]))
      argparse__remove_single_option || return
      ;;
    --verbose)
      ((++arguments[verbose]))
      unset current_argument
      ;;
    -v*)
      ((++arguments[verbose]))
      argparse__remove_single_option || return
      ;;
    *)
      log_error "Unexpected argument -- $1" || return
      return 1
      ;;
    esac

    if [[ -z "${current_argument+undefined}" ]]; then
      if [[ $# -gt 0 ]]; then
        current_argument="$1"
        shift
      fi
    fi
  done
}

main() {
  local script_path
  script_path="$(realpath "${BASH_SOURCE[0]}")" || return
  local script_name
  script_name="$(basename "${script_path}")" || return
  local script_directory
  script_directory="$(dirname "${script_path}")" || return

  local LOGGING__LOG_NAME="${script_name}"
  source "${script_directory}/logging.bash" || return

  declare -A arguments
  parse_arguments "$@" || return

  logging__set_verbosity "${arguments[verbose]}" || return
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
