#!/usr/bin/env bash

__help() {
  declare REPLY
  : "${script_name?}"

  read -d '' -r <<EOF || printf '%s' "${REPLY}" 1>&2
Usage: "${script_name}" [--docker-options ... --] [--kilo-options]
Launch Kilo inside Docker.

If no arguments are given, defaults to '--tty --'.
If arguments are given, '--tty' is excluded by default.

Example:
  "${script_name}"                               # Start TUI.
  "${script_name}" --tty --                      # Same.
  "${script_name}" --entrypoint bash --tty --    # Start a shell.
  "${script_name}" acp                           # Run kilo acp.
EOF
}

main() {
  declare script_path
  script_path="$(realpath "${BASH_SOURCE[0]}")" || return
  declare script_name
  script_name="$(basename "${script_path}")" || return
  local script_directory
  script_directory="$(dirname "${script_path}")" || return
  local script_directory_name
  script_directory_name="$(basename "${script_directory}")" || return

  declare docker_home='/home/dev'
  declare gid
  gid="$(id -g)" || return

  declare agents_dir='.agents'
  mkdir -p "${HOME}/${agents_dir}" || return

  declare kilo_auth='.local/share/kilo'
  mkdir -p "${HOME}/${kilo_auth}" || return

  declare kilo_config='.config/kilo'
  mkdir -p "${HOME}/${kilo_config}" || return

  declare -a docker_command=(
    docker
    run
    --env TERM
    --interactive
    --mount "type=bind,src=${HOME}/${agents_dir},dst=${docker_home}/${agents_dir}"
    --mount "type=bind,src=${HOME}/${kilo_auth},dst=${docker_home}/${kilo_auth}"
    --mount "type=bind,src=${HOME}/${kilo_config},dst=${docker_home}/${kilo_config}"
    --mount "type=bind,src=${PWD},dst=${PWD}"
    --mount "type=volume,src=${script_directory_name}--cache,dst=${docker_home}/.cache"
    --mount "type=volume,src=${script_directory_name}--local,dst=${docker_home}/.local"
    --name "${script_directory_name}"
    --network host
    --rm
    --user "${UID}:${gid}"
    --workdir "${PWD}"
  )

  declare -a argv=("$@")
  if [[ "${#argv[@]}" -eq 0 ]]; then
    argv=('--tty' '--')
  fi

  declare placeholder_found
  for i in "${!argv[@]}"; do
    if [[ "${argv[$i]}" == "--" ]]; then
      argv[i]="${script_directory_name}"
      placeholder_found=true
      break
    fi
  done
  if [[ -z "${placeholder_found+undefined}" ]]; then
    docker_command+=("${script_directory_name}")
  fi

  exec "${docker_command[@]}" "${argv[@]}"
}

main "$@"
