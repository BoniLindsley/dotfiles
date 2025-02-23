#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  if [[ -n "${BONI__INCLUDED+defined}" ]]; then
    return
  fi
  BONI__INCLUDED=
fi

__source_boni() {
  unset __source_boni

  declare script_path
  script_path="$(realpath "${BASH_SOURCE[0]}")" || return
  declare script_directory
  script_directory="$(dirname "${script_path}")" || return

  source "${script_directory}/boni/argparse.bash" || return
  source "${script_directory}/boni/logging.bash" || return
}

__source_boni

if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  return
fi

__help() {
  declare REPLY
  : "${script_name?}"

  read -d '' -r <<EOF || printf '%s' "${REPLY}" 1>&2
Usage: "${script_name}"
Prints one argument per line.

Example:
  "${script_name}" --help
  "${script_name}" -vvv
  "${script_name}" --unknown-option-errors
  "${script_name}" argument --verbose two 3
EOF
}

parse_arguments() {
  declare current_argument
  unset current_argument

  if [[ $# -gt 0 ]]; then
    current_argument="$1"
    shift
  fi

  while [[ -n "${current_argument+defined}" ]]; do
    case "${current_argument}" in
    --help)
      unset kwargs[help]
      unset current_argument
      ;;
    -h*)
      kwargs[help]=1
      argparse__remove_single_option || return
      ;;
    --quiet)
      ((--kwargs[verbose]))
      unset current_argument
      ;;
    -q*)
      ((--kwargs[verbose]))
      argparse__remove_single_option || return
      ;;
    --verbose)
      ((++kwargs[verbose]))
      unset current_argument
      ;;
    -v*)
      ((++kwargs[verbose]))
      argparse__remove_single_option || return
      ;;
    --*)
      log_error "Unexpected option '${current_argument}'" || return
      return 1
      ;;
    -*)
      log_error "Unexpected short option '${current_argument}'" || return
      return 1
      ;;
    *)
      args+=("${current_argument}")
      unset current_argument
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
  declare script_path
  script_path="$(realpath "${BASH_SOURCE[0]}")" || return
  declare script_name
  script_name="$(basename "${script_path}")" || return
  declare script_directory
  script_directory="$(dirname "${script_path}")" || return

  declare LOGGING__LOG_NAME="${script_name}"

  declare -A kwargs
  declare -a args
  parse_arguments "$@" || return

  logging__set_verbosity "${kwargs[verbose]}" || return
  log_trace "Running script: ${script_path}" || return

  if [[ -n "${kwargs[help]+defined}" ]]; then
    __help
    return
  fi

  log_debug 'Listing arguments.'
  for argument in "${args[@]}"; do
    printf '  %s\n' "${argument}"
  done

  logging__log 1 "Everything: 1" || return
  logging__log 5 "Trace: 5" || return
  log_debug "Debug: 10" || return
  log_info "Info: 20" || return
  log_warning "Warning: 30" || return
  log_error "Error: 40" || return
  log_critical "Critical: 50" || return
}

main "$@"
