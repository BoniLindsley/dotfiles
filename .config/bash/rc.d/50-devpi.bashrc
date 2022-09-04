#!/usr/bin/env bash

devpi_user() {
  local getopt_output
  getopt_output=$(
    getopt \
      --options=hx \
      --longoptions=help \
      --name "${FUNCNAME[0]}" \
      -- \
      "$@"
  ) || return
  eval set -- "${getopt_output}"
  while [[ 0 -lt $# ]]; do
    case "$1" in
    '-h' | '--help')
      printf "%s: Run devpi-init on first run.\n" "${FUNCNAME[0]}"
      return 1
      ;;
    --)
      shift
      break
      ;;
    *)
      printf "%s: unexpected option -- %s\n" \
        "${FUNCNAME[0]}" \
        "$1" 1>&2
      return 1
      ;;
    esac
  done
  if [[ 0 -ne $# ]]; then
    printf "%s: No arguments expected.\n" "${FUNCNAME[0]}" 1>&2
    return 1
  fi
  export PIP_INDEX_URL='http://localhost:3141/root/pypi/+simple'
}
