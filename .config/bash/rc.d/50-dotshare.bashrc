#!/usr/bin/env bash

__dotshare_help() {
  cat << 'EOF'
Usage:
  dotshare-export # or dotshare-export-public
  dotshare-clone <dotfile-repository>
  git [...]
  dotshare-export-reset
  dotshare-status # Reports on both.
EOF
}
alias dotshare-help=__dotshare_help

__dotshare_clone() {
  local remote_url="${1?Provide repository to clone from.}"
  local branch="${2-origin/main}"
  : "${GIT_DIR?Use dotshare-export first.}"
  : "${GIT_WORK_TREE?Use dotshare-export first.}"
  mkdir -p "${GIT_DIR}" || return
  git init || return
  git remote add origin "${remote_url}" || return
  # Do not scan the entire `${HOME}`.
  git config status.showuntrackedfiles no || return
  git fetch || return
  git reset "${branch}" || return
  git branch --set-upstream-to="${branch}" || return
  git checkout -- "${GIT_WORK_TREE}" || return
}
alias dotshare-clone=__dotshare_clone

__dotshare_setup() {
  home="${HOME-.}"
  xdg_local_home="${XDG_LOCAL_HOME-${home}/.local}"
  xdg_data_home="${XDG_DATA_HOME:-${xdg_local_home}/share}"
  dotshare_data_home="${xdg_data_home}/dotshare"
}

__dotshare_export() {
  local home
  local xdg_local_home
  local xdg_data_home
  local dotshare_data_home
  __dotshare_setup
  export \
    "GIT_DIR=${dotshare_data_home}/repos/dotfiles.git" \
    "GIT_WORK_TREE=${home}"
}
alias dotshare-export=__dotshare_export

__dotshare_export_public() {
  local home
  local xdg_local_home
  local xdg_data_home
  local dotshare_data_home
  __dotshare_setup
  export \
    "GIT_DIR=${dotshare_data_home}/repos/dotfiles-public.git" \
    "GIT_WORK_TREE=${home}"
}
alias dotshare-export-public=__dotshare_export_public

__dotshare_export_reset() {
  unset GIT_DIR GIT_WORK_TREE
}
alias dotshare-export-reset=__dotshare_export_reset

__dotshare_status() {
  local GIT_DIR
  local GIT_WORK_TREE
  dotshare-export || return
  git status || return
  dotshare-export-public || return
  git status || return
}
alias dotshare-status=__dotshare_status
