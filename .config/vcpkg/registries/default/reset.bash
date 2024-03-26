#!/usr/bin/env bash

__main() {
  unset __main

  local script_path="$(readlink -f "$0")"
  local script_dir="$(dirname $script_path)"

  if ! command -v vcpkg ; then
    printf 'vcpkg: command not found\n' 1>&2
    exit 1
  fi

  pushd "${script_dir}" > /dev/null || exit
  rm -dfr ".git" || exit
  git init . || exit

  rm -dfr versions || exit
  mkdir versions || exit
  cat << EOF > versions/baseline.json || exit
{
  "default": {}
}
EOF
  git add versions || exit
  git commit -m 'add: empty vcpkg registry' || exit

  git add . || exit
  git commit -m 'add: existing vcpkg ports' || exit

  vcpkg \
    --x-builtin-ports-root='ports' \
    --x-builtin-registry-versions-dir='versions' \
    x-add-version --all --verbose \
   || exit
  git add . || exit
  git commit -m 'update:version database' || exit

  printf 'Registry:\n'
  printf '      "baseline": "%s",\n' "$(git log -1 --format="%H")"
}

__main "$@"
