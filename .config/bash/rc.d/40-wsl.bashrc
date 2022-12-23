#!/usr/bin/env bash

use_wsl_xserver() {
  local ip_address=''
  local x_server=''

  # Reference for WSL1/WSL2 detection:
  # https://github.com/Microsoft/WSL/issues/423#issuecomment-887928913
  if [[ -z "${WSL_DISTRO_NAME}" ]]; then
    # Not WSL.
    printf '%s\n' 'Not WSL.' 1>&2
    return
  fi

  ip_address="$(awk '/nameserver / {print $2; exit}' /etc/resolv.conf 2>/dev/null)"

  if [[ "$(systemd-detect-virt --container)" = 'wsl' ]]; then
    # Is WSL2.
    x_server="${ip_address}"
  fi

  # Reference for DISPLAY:
  # https://wiki/ubuntu.com/WSL
  export PULSE_SERVER="${ip_address}"
  export DISPLAY="${x_server}:0.0"
  export LIB_GL_ALWAYS_INDIRECT=1
}
