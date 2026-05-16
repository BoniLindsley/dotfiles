#!/usr/bin/env bash

main() {
  local script_path
  script_path="$(realpath "${BASH_SOURCE[0]}")" || return
  local script_directory
  script_directory="$(dirname "${script_path}")" || return
  local script_directory_name
  script_directory_name="$(basename "${script_directory}")" || return

  docker build --tag "${script_directory_name}" "${script_directory}" ||
    return
}

main "$@"
