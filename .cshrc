#!/usr/bin/env csh

foreach file (${HOME}/.config/csh/rc.d/*.cshrc)
  if (-x "${file}") then
    source "${file}"
  endif
end
