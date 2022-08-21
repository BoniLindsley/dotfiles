" Change status line colour.
highlight StatusLine   cterm=none ctermfg=blue
highlight StatusLine     gui=none   guifg=blue
highlight StatusLineNC cterm=none ctermfg=magenta
highlight StatusLineNC   gui=none   guifg=magenta

" Always show statusbar instead of for multiple windows.
"set laststatus=1
set laststatus=2

"" " Emulate the default status line.
"" " Useful as a base for customising the status line.
"" " Reference: https://unix.stackexchange.com/a/243667
"" set statusline=
"" set statusline+=%f\                          " filename
"" set statusline+=%h%w%m%r\                    " status flags
"" set statusline+=%=                           " right align remainder
"" set statusline+=%-15(%l,%c%V%)               " line, character
"" set statusline+=%<%P                         " file position

" Reset from a fresh status line.
set statusline=[

" Line number.
set statusline+=L%l
" Column number.
set statusline+=\ C%c%V
set statusline+=]

" Truncation starts here if window too narrow.
set statusline+=%<

set statusline+=\ [
" Line ending.
set statusline+=%{&ff}
set statusline+=]

" File path relative to current directory.
set statusline+=\ %f

set statusline+=\ [
" Buffer number.
set statusline+=B%n
" Last buffer number.
set statusline+=#%{bufnr('#')}
set statusline+=]

" Status flags.
" [filetype, help, preview, modified, readonly]
" Eg. [MARKDOWN,HLP,PRV,+,RO]
set statusline+=%(\ [%Y%H%W%M%R]%)

" Right-align starting here.
set statusline+=%=
