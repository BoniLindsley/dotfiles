#!/usr/bin/env bash

__main() {
  unset __main

  : "${VCPKG_ROOT?}"

  local script_path="$(readlink -f "$0")"
  local script_dir="$(dirname $script_path)"

  local registry_baseline

  registry_baseline="$(cd "${script_dir}" && git log -1 --format="%H")"
  export registry_baseline
  cat "${script_dir}/vcpkg-configuration.json" | envsubst
}

__main "$@"
