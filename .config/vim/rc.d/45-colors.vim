" Pick a custom colour theme.
colorscheme simple

" Tell Vim the window background is dark, regardless of what it detects.
" This does not change text background colour,
" and themes need to use this variable to change according.
" Changing this forces a reload of the current colorscheme if any.
set background=dark

" Change status line colour.
highlight StatusLine   cterm=none ctermfg=magenta
highlight StatusLine     gui=none   guifg=magenta
highlight StatusLineNC cterm=none ctermfg=blue
highlight StatusLineNC   gui=none   guifg=blue

" Use specified base16 theme if it exists.
" Only usable in GUI mode.
if has("gui_running")
  silent! colorscheme base16-pop
endif
