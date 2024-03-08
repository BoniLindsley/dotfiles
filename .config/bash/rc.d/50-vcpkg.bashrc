#!/usr/bin/env bash

export VCPKG_DISABLE_METRICS=1
export VCPKG_ROOT="${XDG_LOCAL_HOME:="${HOME}/.local"}/opt/vcpkg"

__vcpkg_help() {
  cat << EOF
Usage:
  apt install --no-install-recommends curl git tar unzip zip
  vcpkg-install
  rm -dfr '${VCPKG_ROOT}'

  vcpkg-init
  bash -c 'cd ${VCPKG_ROOT} && git pull && vcpkg update'
  vcpkg search sdl2

  apt install --no-install-recommends \\
    libltdl-dev libx11-dev libxext-dev libxft-dev

  vcpkg install imgui[sdl2-binding,sdl2-renderer-binding]
  cmake \\
    -B "\${CMAKE_BINARY_DIR}" \\
    -S "\${CMAKE_SOURCE_DIR}" \\
    -DCMAKE_TOOLCHAIN_FILE='${VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake'
  cmake --build "\${CMAKE_BINARY_DIR}"
EOF
}
alias vcpkg-help="__vcpkg_help"

__vcpkg_init() {
  prepend_to_path_if_exists "${VCPKG_ROOT}" || exit
  unalias vcpkg-init || exit
}
alias vcpkg-init="__vcpkg_init"


__vcpkg_install() {
  mkdir -p "${VCPKG_ROOT}" || exit
  git clone 'https://github.com/Microsoft/vcpkg.git' "${VCPKG_ROOT}" \
    || exit
  "${VCPKG_ROOT}/bootstrap-vcpkg.sh" -disableMetrics || exit
}
alias vcpkg-install="__vcpkg_install"
