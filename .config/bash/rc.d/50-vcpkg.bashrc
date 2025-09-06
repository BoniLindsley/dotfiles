#!/usr/bin/env bash

export VCPKG_DISABLE_METRICS=1
export VCPKG_ROOT="${XDG_LOCAL_HOME:="${HOME}/.local"}/opt/vcpkg"

__vcpkg_help() {
  cat <<EOF
Usage:
  apt install --no-install-recommends curl git tar unzip zip
  vcpkg-install

  vcpkg-init
  bash -c 'cd ${VCPKG_ROOT} && git pull && vcpkg update'
  vcpkg search sdl2

  vcpkg new --application
  vcpkg add port boost imgui[sdl2-binding,sdl2-renderer-binding]
  vcpkg install catch2 imgui[sdl2-binding,sdl2-renderer-binding]

  apt install --no-install-recommends \\
    libltdl-dev libx11-dev libxext-dev libxft-dev

  # {
  #   "dependencies": [],
  #   "features": {
  #     "dev": {
  #       "description": "For testing.",
  #       "dependencies": [
  #         "catch2"
  #       ]
  #     }
  #   }
  # }

  cmake \\
    -B "\${CMAKE_BINARY_DIR}" \\
    -S "\${CMAKE_SOURCE_DIR}" \\
    -DBUILD_TESTING=ON \\
    -DCMAKE_TOOLCHAIN_FILE='${VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake' \\
    -DVCPKG_MANIFEST_FEATURES="dev"
  cmake --build "\${CMAKE_BINARY_DIR}"
EOF
}
alias vcpkg-help="__vcpkg_help"

__vcpkg_init() {
  prepend_to_path_if_exists "${VCPKG_ROOT}" || return
  export CMAKE_TOOLCHAIN_FILE="${VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake"
  unalias vcpkg-init || return
}
alias vcpkg-init="__vcpkg_init"

__vcpkg_init_registry() {
  local xdg_config_home="${XDG_CONFIG_HOME:="${HOME}/.config"}"

  local vcpkg_registries=()
  if [[ "$#" -eq 0 ]]; then
    vcpkg_registries+=("${xdg_config_home}/vcpkg/registries/default")
  else
    vcpkg_registries+=("$@")
  fi

  local script_name='vcpkg-init-registry'
  printf 1>&2 '%s: %s\n' "${script_name}" \
    "Creating ${#vcpkg_registries[@]} registries."
  for vcpkg_registry in "${vcpkg_registries[@]}"; do
    printf 1>&2 '%s: %s\n' "${script_name}" "Creating ${vcpkg_registry}"
    mkdir -p "${vcpkg_registry}/ports"
    mkdir -p "${vcpkg_registry}/versions"

    local baseline_path="${vcpkg_registry}/versions/baseline.json"
    if [[ ! -e "${baseline_path}" ]]; then
      cat <<EOF >"${baseline_path}"
{
  "default": {}
}
EOF
    fi
  done
}
alias vcpkg-init-registry="__vcpkg_init_registry"

__vcpkg_install() {
  if [[ ! -d "${VCPKG_ROOT}" ]]; then
    mkdir -p "${VCPKG_ROOT}" || return
    git clone 'https://github.com/Microsoft/vcpkg.git' "${VCPKG_ROOT}" ||
      return
    "${VCPKG_ROOT}/bootstrap-vcpkg.sh" -disableMetrics || return
  fi
}
alias vcpkg-install="__vcpkg_install"
