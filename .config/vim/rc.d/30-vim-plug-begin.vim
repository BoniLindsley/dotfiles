if &compatible
  echoerr 'vim-plug requires nocompatible'
endif

" Update one plugin at a time.
"let g:plug_threads = 16
let g:plug_threads = 1

" Where plugins are installed to.
let g:plug_home = $VIM_LIB_HOME . '/plugged'

call plug#begin()
