#!/usr/bin/env csh

# Disable automatic margins wrapping.
# For multi-line prompt. Without it, new line disappears on resize.
# Reference: https://unix.stackexchange.com/a/534824
settc am no

# Do not beep on bell requests.
#set beep
set nobeep

# Do not print `DING!` in place of `%P` in `${prompt}`.
#set ding
set noding

# Provide more information in shell prompt.
#
# ```
# [2000-01-01 12:34:56] [$?=0] [user@hostname:/home/user]
# % command
# ```
set prompt='[%Y-%W-%D %P] [$?=%?] [%N@%M:%/]\n%# '

# Make bell visible (possibly instead of audible if nobeep).
#set novisiblebell
set visiblebell
