#!/usr/bin/env bash

dotshare-help() {
  cat << 'EOF'
Usage:
  dotshare-export # or dotshare-export-public
  dotshare-clone <dotfile-repository>
  git [...]
  dotshare-export-reset
  dotshare-status # Reports on both.
EOF
}

dotshare-clone() {
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

__dotshare_setup() {
  home="${HOME-.}"
  xdg_local_home="${XDG_LOCAL_HOME-${home}/.local}"
  xdg_data_home="${XDG_DATA_HOME:-${xdg_local_home}/share}"
  dotshare_data_home="${xdg_data_home}/dotshare"
}

dotshare-export() {
  local home
  local xdg_local_home
  local xdg_data_home
  local dotshare_data_home
  __dotshare_setup
  export \
    "GIT_DIR=${dotshare_data_home}/repos/dotfiles.git" \
    "GIT_WORK_TREE=${home}"
}

dotshare-export-public() {
  local home
  local xdg_local_home
  local xdg_data_home
  local dotshare_data_home
  __dotshare_setup
  export \
    "GIT_DIR=${dotshare_data_home}/repos/dotfiles-public.git" \
    "GIT_WORK_TREE=${home}"
}

dotshare-export-reset() {
  unset GIT_DIR GIT_WORK_TREE
}

dotshare-status() {
  local GIT_DIR
  local GIT_WORK_TREE
  dotshare-export || return
  git status || return
  dotshare-export-public || return
  git status || return
}
