#!/usr/bin/env bash

# Open on WSL2.
# chromium  --enable-features=UseOzonePlatform --ozone-platform=wayland

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
  local repository='https://github.com/fathyb/carbonyl.git'
  local version_tag='v0.0.3'
  local source_name="${repository##*/}"
  local source_name="${source_name%.git}"
  local version_number="${version_tag#v}"
  local full_name="${source_name}_${version_number}"

  # Ensure install directory is clean and parent directory exists.
  local install_directory="${XDG_LOCAL_HOME}/opt/${full_name}"
  rm -dfr "${install_directory}" || return

  mkdir -p "${install_directory}" || return
  cd "${install_directory}" || return
  wget \
    "${repository%.git}/releases/download/${version_tag}/${source_name}.linux-amd64.zip" ||
    return
  local archive_name="${source_name}.linux-amd64.zip"
  7z x "${archive_name}"
  local archive_subdirectory="${source_name}-${version_number}"
  mv "${archive_subdirectory}"/* .
  rm "${archive_name}"
  rmdir "${archive_subdirectory}"
}

__main "$@"
