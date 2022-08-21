if !exists("g:syntax_on")
  echoerr 'rust.vim requires :syntax enable'
endif

" Also wants filetype plugin indent on
" I think it gets enabled by vim-plug.

" Rust file detection, syntax highlighting, formatting.
Plug 'rust-lang/rust.vim'
