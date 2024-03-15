#!/usr/bin/env bash
#
export EMSDK="${XDG_LOCAL_HOME:="${HOME}/.local"}/opt/emsdk"

__emscripten_help() {
  cat << EOF
Usage:
  emscripten-install
  rm -dfr '${EMSDK}'
  emscripten-init
  GIT_DIR=${EMSDK}/.git git pull
  emsdk list
  emsdk install latest
  emsdk activate latest
  emscripten-init
  vcpkg-init
  vcpkg install boost catch2 imgui[sdl2-binding,sdl2-renderer-binding]

  vcpkg-init
  emscripten-init
  emscripten-cmake -B "\${CMAKE_BINARY_DIR}"
  cmake --build "\${CMAKE_BINARY_DIR}"
  python3 -m http.server -d "\${CMAKE_BINARY_DIR}"
  # Open localhost:8000/project-name.html
EOF
}
alias emscripten-help='__emscripten_help'

__emscripten_cmake() {
  cmake \
    -DBUILD_TESTING=OFF \
    -DVCPKG_CHAINLOAD_TOOLCHAIN_FILE="${EMSDK}/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake" \
    "$@"
}
alias emscripten-cmake='__emscripten_cmake'

__emscripten_init() {
  source "${EMSDK}/emsdk_env.sh" || return

  # For package installation without extra options.
  export VCPKG_DEFAULT_TRIPLET='wasm32-emscripten'
}
alias emscripten-init='__emscripten_init'

__emscripten_install() {
  mkdir -p "${EMSDK}" || return

  git clone 'https://github.com/emscripten-core/emsdk.git' "${EMSDK}" \
    || return
  "${EMSDK}/emsdk" install latest
}
alias emscripten-install='__emscripten_install'
