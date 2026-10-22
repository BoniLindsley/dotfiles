#!/usr/bin/env bash

__main() {
  unset main

  declare home="${HOME=.}"
  declare xdg_config_home="${XDG_CONFIG_HOME="${home}/.config"}"
  declare docker_files_config_home="${xdg_config_home}/docker-files"

  prepend_to_path_if_exists "${docker_files_config_home}/dockered-claude/bin"
}

__main "$@"
