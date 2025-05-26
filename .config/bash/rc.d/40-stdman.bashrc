#!/usr/bin/env bash

__stdman_setenv() {
  install_directory="${XDG_LOCAL_HOME:="${HOME:=~}/.local"}/opt/stdman"
}

__stdman_set_manpath() {
  declare install_directory
  __stdman_setenv || return

  declare manpath="${install_directory}/share/man"
  if [[ -d "${manpath}" ]]; then
    # Unlike library search path, an "empty" entry
    # is replaced by the default paths, rather than the pwd.
    # So having a trailing colon is expected hre.
    export MANPATH
    MANPATH="${manpath}:${MANPATH}"
  fi
}

__stdman_install() {
  declare install_directory
  __stdman_setenv || return

  declare src_directory="${XDG_LOCAL_HOME:="${HOME:=~}/.local"}/src/stdman"
  if [[ ! -d "${src_directory}" ]]; then
    mkdir -p "${src_directory}" || return
    git clone 'https://github.com/jeaye/stdman.git' "${src_directory}" || return
  fi

  cd "${src_directory}" || return
  ./configure --prefix="${install_directory}" || return
  make install

  __stdman_set_manpath || return
  mandb || return
}
alias stdman-install=__stdman_install

__main() {
  unset __main

  __stdman_set_manpath || return
}

__main "$@"
