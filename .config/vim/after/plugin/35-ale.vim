" # ALE

" Upstream: https://github.com/dense-analysis/ale

if !exists('g:loaded_ale_dont_use_this_in_other_plugins_please')
    finish
endif

if v:version < 800
  finish
endif

" Provides completion with `<C-x><C-o>`.
set omnifunc=ale#completion#OmniFunc

"let g:ale_completion_autoimport = 1
let g:ale_completion_autoimport = 0

function! BoniLinterStatus() abort
  let l:bufnr = bufnr('')
  let l:lint_count = getbufvar(l:bufnr, 'ale_linted', 0)

  let l:is_checking = ale#engine#IsCheckingBuffer(l:bufnr)
  if l:is_checking
    return printf(' [ALE#%d:?]', l:lint_count + 1)
  endif

  let l:error_counts = ale#statusline#Count(l:bufnr)
  let l:total_errors = l:error_counts.total
  if l:total_errors
    return printf(' [ALE#%d:%d]', l:lint_count, l:total_errors)
  endif

  if l:lint_count
    return printf(' [ALE#%d]', l:lint_count)
  endif

  return ''
endfunction
set statusline+=%{BoniLinterStatus()}

call ale#fix#registry#Add(
\ 'fprettify',
\ 'ale#fixers#fprettify#Fix', ['fortran'],
\ 'Apply fprettify to a file.'
\)

call ale#fix#registry#Add(
\ 'mdformat',
\ 'ale#fixers#mdformat#Fix', ['markdown'],
\ 'Apply mdformat to a file.'
\)

" cmakeformat: https://github.com/cheshirekow/cmake_format
let g:ale_fixers = {
\ '*': [
\   'remove_trailing_lines',
\   'trim_whitespace',
\ ],
\ 'bash': ['shfmt'],
\ 'cmake': ['cmakeformat'],
\ 'c': ['clang-format'],
\ 'cpp': ['clang-format'],
\ 'css': ['prettier'],
\ 'fortran': ['fprettify'],
\ 'html': ['prettier'],
\ 'javascript': ['prettier'],
\ 'json': ['prettier'],
\ 'markdown': ['mdformat'],
\ 'python': ['black'],
\ 'rust': ['rustfmt'],
\ 'sh': ['shfmt'],
\}

let g:ale_linters = {
\ 'bash': ['shellcheck'],
\ 'c': [
\   'clangd',
\   'clangtidy',
\ ],
\ 'cpp': [
\   'clangd',
\   'clangtidy',
\ ],
\ 'css': ['stylelint'],
\ 'fortran': [
\   'gcc',
\   'language_server',
\ ],
\ 'javascript': ['eslint'],
\ 'python': [
\   'mypy',
\   'pylint',
\   'pylsp',
\ ],
\ 'rust': ['analyzer'],
\ 'sh': ['shellcheck'],
\}
"" Temporarily disable Pylint. It causes problems with PySide6.
"call filter(g:ale_linters['python'], 'v:val != "pylint"')

" Do not try to run every available linter.
"let g:ale_linters_explicit = 0
let g:ale_linters_explicit = 1

let g:ale_fortran_fprettify_options = ''
" `integer::count` -> `integer :: count`
let g:ale_fortran_fprettify_options .= ' --enable-decl'
" `print *   !` -> `print * !`
let g:ale_fortran_fprettify_options .= ' --strip-comments'

" Always use preprocessor.
"let g:ale_fortran_gcc_options = '-Wall'
let g:ale_fortran_gcc_options = '-Wall'
let g:ale_fortran_gcc_options .= ' -Wextra'
let g:ale_fortran_gcc_options .= ' -cpp'

"let g:ale_python_pylsp_config = {}
let g:ale_python_pylsp_config = {
\ 'pylsp': {
\   'plugins': {
\     'black': { 'enabled': v:false },
\     'mypy': {
\       'dmypy': v:true,
\       'enabled': v:false,
\       'live_mode': v:false,
\       'strict': v:true,
\     },
\     'pycodestyle': { 'enabled': v:false },
\     'pyflakes': { 'enabled': v:false },
\     'pylint': { 'enabled': v:false },
\     'yapf': { 'enabled': v:false },
\   }
\ },
\}

nnoremap <Plug>(Boni.ALE)<F1>
  \ :echo 'ALE: ( ) GoTo (D)oc (H)over (r) toggle (s) detail'<CR>
nnoremap <Plug>(Boni.ALE)<Tab>
  \ :call BoniMapWait("\<Plug>(Boni.ALE)")<CR>
nmap <Plug>(Boni.ALE)<Space> <Plug>(ale_go_to_definition)
nmap <Plug>(Boni.ALE)C :ALECodeAction<CR>
nmap <Plug>(Boni.ALE)D <Plug>(ale_documentation)
nmap <Plug>(Boni.ALE)H <Plug>(ale_hover)
nmap <Plug>(Boni.ALE)r <Plug>(ale_toggle_buffer)
nmap <Plug>(Boni.ALE)R <Plug>(ale_toggle)
nmap <Plug>(Boni.ALE)s <Plug>(ale_detail)
