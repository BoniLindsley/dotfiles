#!/usr/bin/env bash

if (! ${?HOME}) then
  setenv HOME '.'
endif

if (! ${?XDG_LOCAL_HOME}) then
  setenv XDG_LOCAL_HOME "${HOME}/.local"
endif

if (! ${?XDG_DATA_HOME}) then
  setenv XDG_DATA_HOME "${XDG_LOCAL_HOME}/share"
endif

if (! ${?DOTSHARE_DATA_HOME}) then
  setenv DOTSHARE_DATA_HOME "${XDG_DATA_HOME}/dotshare"
endif

alias dotshare-export \
  setenv GIT_DIR "${DOTSHARE_DATA_HOME}/repos/dotfiles.git"
  setenv GIT_WORK_TREE "${HOME}"
alias dotshare-export-public \
  setenv GIT_DIR "${DOTSHARE_DATA_HOME}/repos/dotfiles-public.git"
  setenv GIT_WORK_TREE "${HOME}"
alias dotshare-export-reset \
  unsetenv GIT_DIR
  unsetenv GIT_WORK_TREE
