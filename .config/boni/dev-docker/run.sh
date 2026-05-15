#!/usr/bin/env bash

__help() {
  declare script_path
  script_path="$(realpath "${BASH_SOURCE[0]}")" || return
  declare script_name
  script_name="$(basename "${script_path}")" || return

  declare REPLY
  : "${script_name?}"

  read -d '' -r <<EOF || printf '%s' "${REPLY}" 1>&2
Usage: "${script_name}"
Launch development tools inside Docker.

Example:
  "${script_name}"              # opens NeoVim in the current directory
  "${script_name}" kilo         # opens the Kilo Code CLI instead
  "${script_name}" bash         # drops into a shell

The container's "dev" user is re-mapped to your host UID:GID at runtime so
that files written inside ~/work are owned by you on the host.
EOF
}

main() {
  declare gid
  gid="$(id -g)"

  declare -a docker_command=(
    docker
    run
    --interactive
    --name dev-docker
    --network host
    --rm
    --tty
    --user "${UID}:${gid}"
    --volume "${PWD}:/home/dev/work"
    dev-docker
  )

  exec "${docker_command[@]}" "$@"
}

main "$@"
