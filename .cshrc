#!/usr/bin/env csh

foreach __file (${HOME}/.config/csh/rc.d/*.cshrc)
  if (-x "${__file}") then
    source "${__file}"
  endif
end
unset __file
