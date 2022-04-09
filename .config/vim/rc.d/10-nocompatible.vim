" This option needs to be one of the first ones to change.
" Each time it is set or unset,
" it triggers automatic changes to other options, such as `viminfo`
" If it is used later on, in the initialisation process,
" it can lead to surprising effect that is hard to figure out.
" If it must be used, do
" ```vim
" if &compatible
"   set nocompatible
" endif
" ```
" Reference: https://stackoverflow.com/a/39767149
if &compatible
  set nocompatible
endif

" Syntax loading is done by sourcing a file.
" This means it can overwrite configs.
" So it needs to be set early.
syntax enable

" Needed by most plugins.
filetype plugin indent on
