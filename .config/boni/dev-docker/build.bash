#!/usr/bin/env bash

main() {
  local script_path
  script_path="$(realpath "${BASH_SOURCE[0]}")" || return
  local script_name
  script_name="$(basename "${script_path}")" || return
  local script_directory
  script_directory="$(dirname "${script_path}")" || return
  local script_directory_name
  script_directory_name="$(basename "${script_directory}")" || return

  declare -x XDG_CONFIG_HOME="${XDG_CONFIG_HOME:="${HOME}/.config"}"

  # Use current user config.
  declare CONFIG_HOME="${script_directory}/.config"
  if [[ ! -d "${CONFIG_HOME}" ]]; then
    mkdir -p "${CONFIG_HOME}" || return
    cp -r "${XDG_CONFIG_HOME}/nvim" "${script_directory}/.config" ||
      return
    cp -r "${XDG_CONFIG_HOME}/vim" "${script_directory}/.config" ||
      return
  else
    printf '%s\n' "Not copying config home. Already exists." 1>&2
  fi

  docker build --tag "${script_directory_name}" "${script_directory}" ||
    return
}

main "$@"
