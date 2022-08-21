" # vim-autoformat

" Upstream: https://github.com/Chiel92/vim-autoformat

if !exists('g:autoformat_verbosemode')
  finish
endif

"" For debugging.
""let g:autoformat_verbosemode=0
"let g:autoformat_verbosemode=1

" Use JS-based formatter: `npm install -g js-beautify`
"let g:formatters_json = ['jsbeautify_json', 'fixjson', 'prettier']

" In Windows, we cannot execute `.pl` scripts directly by default.
" But MiKTeX provides a binary wrapper.
" So we can run `latexindent.exe` instead.
" And, as of writing (2019-11-24),
"   latexindent.pl writes a prompt message to stderr.
" This makes vim-autoformat think there was an error,
"   and fail the formatting.
" So we need to pipe it away into the void.
"let g:formatdef_latexindent = '"latexindent.pl -"'
if has('win32')
  " Also using `-l` flag to load project settings.
  let g:formatdef_latexindent = '"latexindent -l -m 2> NUL"'
endif

" Use JS-based `remark`: `npm install -g remark-cli`
"let g:formatters_markdown = ['remark_markdown', 'prettier', 'stylelint']

" Use Google yapf for formatting Python3.
" For Windows, `py install --compile --upgrade yapf`.
" For Debian, `python3 install --user --compile --upgrade yapf`.
"let g:formatters_python = ['autopep8', 'yapf', 'black']
let g:formatters_python = ['black', 'yapf', 'autopep8']

" shfmt is a Go-based formatter.
" Install with `go get -u mvdan.cc/sh/v3/cmd/shfmt`
"let g:formatters_sh = ['shfmt']

" Do not fallback to built-in Vim indent file config.
let g:autoformat_autoindent = 0
let g:autoformat_retab = 0
let g:autoformat_remove_trailing_spaces = 0

nnoremap <Plug>(Boni.Autoformat)<Space> :Autoformat<CR>
