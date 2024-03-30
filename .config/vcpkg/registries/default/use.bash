#!/usr/bin/env bash

__registry_baseline() {
  cd "$1" || exit 1
  git log -1 --format="%H"
  cd "${OLDPWD}"
}

__main() {
  unset __main

  : "${VCPKG_ROOT?}"

  local script_path="$(readlink -f "$0")"
  local script_dir="$(dirname $script_path)"

  local registry_baseline="$(__registry_baseline "${script_dir}")"
  local vcpkg_baseline="$(__registry_baseline "${VCPKG_ROOT}")"

  export registry_baseline
  export vcpkg_baseline
  cat "${script_dir}/vcpkg-configuration.json" \
    | envsubst \
    > vcpkg-configuration.json
}

__main "$@"
