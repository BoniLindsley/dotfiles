#!/usr/bin/env csh

# Do not beep on bell requests.
#set beep
set nobeep

# Do not print `DING!` in place of `%P` in `${prompt}`.
#set ding
set noding

# Provide more information in shell prompt.
# [$?=0][2000-01-01 12:34:56] [user@hostname:/home/user] % command
set prompt='[$?=%?][%Y-%W-%D %P]] [%N@%M:%/] %# '

# Make bell visible (possibly instead of audible if nobeep).
#set novisiblebell
set visiblebell
