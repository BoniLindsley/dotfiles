#!/usr/bin/env bash

if ! is_shell_interactive; then return; fi

## Control whether commands are saved on the history list.
## All commands are saved unless it satisfies condition specified
##   by the `HISTCONTROL` environment variable.
## Possible values (colon-separated list)
##   * ignorespace - Lines beginning with a space are not saved.
##   * ignoredup - Lines matching a stored entry are not saved.
##   * ignoreboth = ignorespace,ignoredup
##   * erasedups - Adding duplicate entries removes old ones.
## # unset HISTCONTROL
export HISTCONTROL=ignorespace,erasedups

## Number of commands to save in history list.
## Set to 0 to disable history.
## Set to negative for a unlimited history.
## # HISTSIZE=500
export HISTSIZE=1000

## Append to the history file, don't overwrite it.
## # shopt -u histappend
shopt -s histappend

## Number of line allowed in the history file on exit.
## Also truncates immediately on variable set.
## # HISTFILESIZE=500
export HISTFILESIZE=2000

## If set, `bash` checks the window size after each command and,
##   if necessary, updates the values of `LINES` and `COLUMNS`.
## # shopt -s checkwinsize

## If set, the pattern "**" used in a pathname expansion context
##   will match all files and zero or more directories and subdirectories.
## If the pattern is followed by a `/`,
##   only directries and subdirectories match.
## # shopt -u globstar

## The program `lesspipe`  will toss the contents/info on `STDOUT`
## and less will read them as they come across.
## This means that you do not have to wait for the decoding to finish
## before less shows you the file.
## This also means that you will get a `byte N`
## instead of an `N%` as your file position.
## You can seek to the end and back to get the `N%`
## but that means you have to wait for the pipe to finish.
#if [ -x /usr/bin/lesspipe ]; then eval "$(lesspipe)"; fi

# Detect name of chroot environment, if the shell is in one.
if [[ -z "${debian_chroot:-}" ]] && [ -r /etc/debian_chroot ]; then
  debian_chroot=$(cat /etc/debian_chroot)
fi

## Primary prompt string.
## # PS1='$ '          # Dash default
## # PS1='\s-\v\$ '    # Bash default: 'bash-2.00$ '
# The following is of the form
#     [01:23:45 ?0] user@hostname: ~/full_path$ dir
PS1='[\D{%Y-%m-%d %H:%M:%S}] [\$?=$?]'
PS1+='${debian_chroot:+ [$debian_chroot]}'
PS1+=' [\u@\H:\w]'
PS1+='\n\$ '
export PS1

# Enable color support directory listing.
if [ -x /usr/bin/dircolors ]; then
  eval "$(dircolors -b)"
fi
# List with colours and show hidden files by default.
alias ls='ls --almost-all --color=auto'

# Set colors for GCC stdout text.
GCC_COLORS+='error=01;31'
GCC_COLORS+=':warning=01;35'
GCC_COLORS+=':note=01;36'
GCC_COLORS+=':caret=01;32'
GCC_COLORS+=':locus=01'
GCC_COLORS+=':quote=01'
export GCC_COLORS

# Enable completion features.
if ! shopt -oq posix; then
  source_first_exists                            \
    '/usr/share/bash-completion/bash_completion' \
    '/etc/bash_completion'                       \
  ;
  source_if_exists "$HOME/.bash_completion"
fi

# For screen blanking in tty
if [[ 'linux' == "$TERM" ]]; then
  setterm -blank 1 -powersave powerdown -powerdown 1
fi
