#!/usr/bin/env csh

foreach __file (${HOME}/.config/csh/login.d/*.login)
  if (-x "${__file}") then
    source "${__file}"
  endif
end
unset __file
