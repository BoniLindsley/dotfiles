" Change status line colour.
highlight StatusLine cterm=none
highlight StatusLine ctermfg=blue
highlight StatusLineNC cterm=none
highlight StatusLineNC ctermfg=magenta

" Always show statusbar
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
set statusline=%<

" File path relative to current directory.
set statusline+=%f


set statusline+=\ [
" Line ending.
set statusline+=%{&ff}
" Line number.
set statusline+=,L%l/%L
" Column number.
set statusline+=,C%c%V
set statusline+=]

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
