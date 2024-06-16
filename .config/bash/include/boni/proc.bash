#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  if [[ -n "${BONI__PROC__INCLUDED+defined}" ]]; then
    return
  fi
  BONI__PROC__INCLUDED=
fi

proc__pid_maps() {
  local pid="${1?}"

  local data
  local address perms offset dev inode pathname

  while read -r address perms offset dev inode pathname; do
    start="0x${address%-*}"
    end="0x${address##*-}"
    length="$((end - start))"
    data="$(xxd -len 1 -plain -s "$((start))" "/proc/${pid}/mem" 2>/dev/null)" || return
    log_trace "Start: ${start} | End: ${end} | Length: ${length} | Data: '${data}' | Perms: ${perms} | Offset: ${offset} | Dev: ${dev} | Inode: ${inode} | Pathname: ${pathname}" || return
  done <"/proc/${pid}/maps"
}

proc__pid_mem() {
  local pid="${1?}"
  local start="${2?}"
  local length="${3?}"

  log_trace "Reading memory from PID: ${pid} | Start: ${start} | Length: ${length}" || return
  dd bs=1 count="$((length))" if="/proc/${pid}/mem" skip="$((start))" || return
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
      if [[ -z "${arguments[pid]+undefined}" ]]; then
        arguments[pid]="${current_argument}"
        unset current_argument
      else
        log_error "Unexpected argument -- ${current_argument}" || return
        return 1
      fi
      ;;
    esac

    if [[ -z "${current_argument+undefined}" ]]; then
      if [[ $# -gt 0 ]]; then
        current_argument="$1"
        shift
      fi
    fi
  done

  if [[ -z "${arguments[pid]+undefined}" ]]; then
    log_error "Missing argument for pid" || return
    return 1
  fi
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
  source "${script_directory}/argparse.bash" || return

  declare -A arguments
  parse_arguments "$@" || return

  logging__set_verbosity "${arguments[verbose]}" || return
  log_trace "Running script: ${script_path}" || return

  proc__pid_maps "${arguments[pid]}" || return
}

main "$@"
