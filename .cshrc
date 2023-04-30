#!/usr/bin/env csh

# Determine current script path.
# Adopted from: https://stackoverflow.com/a/45012783
set __called=($_)
# Directly sourced: `source ~/.cshrc`
if ( "$__called" != '' ) then
  set __script_path=`readlink -f "${__called[2]}"`
  set __script_dir=`dirname "${__script_path}"`
  unset __script_path
# Source as startup script.
else if ( "$0" == '-csh' || "$0" == '/bin/csh' ) then
  set __script_dir="${HOME}"
# Directly run: `csh .cshrc`. Probably not useful for `.cshrc`.
else
  set __script_path=`readlink -f "$0"`
  set __script_dir=`dirname "${__script_path}"`
  unset __script_path
endif
unset __called

set nonomatch=1
pushd "${__script_dir}" >> /dev/null
set __files=( .config/csh/rc.d/*.cshrc )
unset nonomatch
if ( "__files" != '.config/csh/rc.d/*.cshrc' ) then
  foreach __file ( ${_files} )
    if (-x "${__file}") then
      source "${__file}"
    endif
  end
endif
popd >> /dev/null

unset __file
unset __files
unset __script_dir
