#!/usr/bin/env bash

# An alternative is to ssh into the machine
# with X forwarding instead.

use_wsl_xserver() {
  # Requires some admin setup on Windows side.
  #
  # -   Run `startxwin -- -listen tcp -nowgl` in a non-X Cygwin shell.
  #     Or modify / create the Cygwin/X shortcut:
  #     `run.exe --quote /usr/bin/bash.exe -l -c "cd; exec /usr/bin/startxwin"
  #     to contain the above flags.
  # -   Allow XWin.exe in inbound Firewall rule.
  #     Or manually add rule for `xwin.exe`.
  #     -   Rule must be for public network profile, or
  #     -   For private and domain network profiles,
  #         if removing `vEthernet (WSL)` from public profile.
  # -   For errors about invalid magic cookies,
  #     `cp /mnt/c/Users/$USER/.Xauthority ~`.
  #     Adjust username as necessary.
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

use_wsl_xserver_xauthority() {
  cp /mnt/c/Users/"${USER}"/.Xauthority "${HOME}"
}
