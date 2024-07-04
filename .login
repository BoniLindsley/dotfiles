#!/usr/bin/env csh

# Determine current script path.
# Adopted from: https://stackoverflow.com/a/45012783

unset __script_dir

if (! ${?__script_dir}) then
  set __called=($_)
  if ( "${__called}" != '' ) then
    # Directly sourced: `source ~/.login`
    set __script_path=`readlink -f "${__called[2]}"`
    set __script_dir=`dirname "${__script_path}"`
    unset __script_path
  endif
  unset __called
endif

if (! ${?__script_dir}) then
  set __command=`which "$0"`
  set __is_startup=0
  if ( "$0" == '-csh' ) then
    set __is_startup=1
  else if ( "${__command}" == '/bin/csh' ) then
    set __is_startup=1
  else if ( "${__command}" == '/usr/bin/csh' ) then
    set __is_startup=1
  endif
  if ( "${__is_startup}" ) then
    # Source as startup script.
    set __script_dir="${HOME}"
  endif
  unset __command
  unset __is_startup
endif

if (! ${?__script_dir}) then
  # Fallback. Likely run as script: `csh script.csh`.
  set __script_path=`readlink -f "$0"`
  set __script_dir=`dirname "${__script_path}"`
  unset __script_path
endif

# Determined "${__script_dir}" as this point.

set nonomatch=1
pushd "${__script_dir}" >> /dev/null
set __files=( .config/csh/login.d/*.login )
unset nonomatch
if ( "${__files}" != '.config/csh/login.d/*.login' ) then
  foreach __file ( ${__files}  )
    if (-x "${__file}") then
      source "${__file}"
    endif
  end
endif
popd >> /dev/null

unset __file
unset __files
unset __script_dir
