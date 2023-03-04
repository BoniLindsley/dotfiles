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
else if ( "$0" == '-csh' ) then
  set __script_dir="${HOME}"
# Directly run: `csh .cshrc`. Probably not useful for `.cshrc`.
else
  set __script_path=`readlink -f "$0"`
  set __script_dir=`dirname "${__script_path}"`
  unset __script_path
endif
unset __called

foreach __file (${__script_dir}/.config/csh/rc.d/*.cshrc)
  if (-x "${__file}") then
    source "${__file}"
  endif
end

unset __file
unset __script_dir
