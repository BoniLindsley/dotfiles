#!/usr/bin/env bash

__parse_arguments() {
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
      log_error "Unexpected option -- $1"
      return 1
      ;;
    esac
  done
}

__main() {
  local script_path
  script_path="$(realpath "${BASH_SOURCE[0]}")" || return
  local script_name
  script_name="$(basename "${script_path}")" || return
  local script_directory
  script_directory="$(dirname "${script_path}")" || return

  export LOGGING__LOG_NAME="${script_name}"
  source "${script_directory}/../include/boni/logging.bash" || return

  declare -i __option_verbose=0
  __parse_arguments "$@" || return

  logging__set_verbosity __option_verbose || return
  log_trace "Running script at ${script_path}." || return

  # Download source if not found.
  : "${XDG_LOCAL_HOME:="${HOME}/.local"}"
  local repository='https://github.com/nodejs/node.git'
  local version_tag='v22.2.0'
  local source_name="${repository##*/}"
  local source_name="${source_name%.git}"
  local version_number="${version_tag#v}"
  local full_name="${source_name}_${version_number}"
  local source_directory="${XDG_LOCAL_HOME}/src/${full_name}"
  if [[ ! -e "${source_directory}" ]]; then
    mkdir -p "${source_directory}" || return
    cd "${source_directory}" || return
    log_info "Cloning repository." || return
    log_info "  Repository: ${repository}" || return
    log_info "  Version: ${version_tag}" || return
    log_info "  Target: ${PWD}" || return
    git clone --branch="${version_tag}" --depth=1 \
      -- "${repository}" "${PWD}" || return
  else
    log_info "Source exists: ${source_directory}" || return
  fi

  # Get version number.
  cd "${source_directory}" || return
  version_tag="$(git describe --tags)" || return
  version_number="${version_tag#v}"
  full_name="${source_name}_${version_number}"

  # Ensure install directory is clean and parent directory exists.
  local install_directory="${XDG_LOCAL_HOME}/opt/${full_name}"
  rm -dfr "${install_directory}" || return

  local parent_directory
  parent_directory="$(dirname "${install_directory}")"
  mkdir -p "${parent_directory}" || return

  ./configure || return
  make install PREFIX="${install_directory}" || return
}

__main "$@"
