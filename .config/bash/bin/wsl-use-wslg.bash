#!/usr/bin/env bash

__parse_arguments() {
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
      log_error "Unexpected argument -- $1" || return
      return 1
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

__main() {
  local script_path
  script_path="$(realpath "${BASH_SOURCE[0]}")" || return
  local script_name
  script_name="$(basename "${script_path}")" || return
  local script_directory
  script_directory="$(dirname "${script_path}")" || return

  export LOGGING__LOG_NAME="${script_name}"
  source "${script_directory}/../include/boni/logging.bash" || return

  source "${script_directory}/../include/boni/argparse.bash" || return
  declare -A arguments
  __parse_arguments "$@" || return

  logging__set_verbosity "${arguments[verbose]}" || return
  log_trace "Running script at ${script_path}." || return

  printf 1>&2 '%s\n' 'Removing /tmp/.X11-unix.'
  sudo sudo rm -dfr /tmp/.X11-unix
  printf 1>&2 '%s\n' 'Use X11 from WSLg.'
  sudo ln -s /mnt/wslg/.X11-unix /tmp/.X11-unix
  # --enable-features=UseOzonePlatform \
  # --ozone-platform=wayland ||
  # --disable-infobars \
  # --disable-session-crashed-bubble \
  # --enable-accelerated-2d-canvas \
  # --enable-accelerated-vpx-decode \
  # --enable-gpu \
  # --enable-gpu-memory-buffer-video-frames \
  # --enable-native-gpu-memory-buffers \
  # --enable-zero-copy \
  # --gpu-no-context-lost \
  # --ignore-certificate-errors \
  # --ignore-gpu-blacklist \
  # --in-process-gpu \
  # --no-first-run \
  # --no-sandbox \
  # --user-data-dir=/home/root/.chromium/ \
  # --window-position=0,0 \
}

__main "$@"
