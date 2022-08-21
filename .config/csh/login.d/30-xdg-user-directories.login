#!/usr/bin/env csh

if (! ${?XDG_LOCAL_HOME}) then
  setenv XDG_LOCAL_HOME "${HOME}/.local"
endif

if (! ${?XDG_LIB_HOME}) then
  setenv XDG_LIB_HOME "${XDG_LOCAL_HOME}/lib"
endif

if (! ${?XDG_CACHE_HOME}) then
  setenv XDG_CACHE_HOME "${HOME}/.cache"
endif

if (! ${?XDG_CONFIG_HOME}) then
  setenv XDG_CONFIG_HOME "${HOME}/.config"
endif

if (! ${?XDG_DATA_HOME}) then
  setenv XDG_DATA_HOME "${XDG_LOCAL_HOME}/share"
endif

if (! ${?XDG_STATE_HOME}) then
  setenv XDG_STATE_HOME "${XDG_LOCAL_HOME}/state"
endif
