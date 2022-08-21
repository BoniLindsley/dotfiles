" # ctrlp.vim

" Upstream: https://github.com/ctrlpvim/ctrlp.vim

" Directories to not show.
"unlet g:ctrlp_custom_ignore
" Default if unset is the same as follows.
"let g:ctrlp_custom_ignore = {
"  \ 'dir':  '\v[\/]\.(git|hg|svn)$',
"  \ }
let g:ctrlp_custom_ignore = {
  \ 'dir' : '\v[\/](',
  \ 'file': '\v(',
  \}
" LaTeX
let g:ctrlp_custom_ignore['dir'] .= 'build-latexmk'

" Python
let g:ctrlp_custom_ignore['dir'] .= '|.*\.egg-info'
let g:ctrlp_custom_ignore['dir'] .= '|\.mypy_cache'
let g:ctrlp_custom_ignore['dir'] .= '|\.pytest_cache'
let g:ctrlp_custom_ignore['dir'] .= '|\.tox'
let g:ctrlp_custom_ignore['dir'] .= '|__pycache__'
let g:ctrlp_custom_ignore['dir'] .= '|build'
let g:ctrlp_custom_ignore['dir'] .= '|dist'
let g:ctrlp_custom_ignore['dir'] .= '|docs/_build'

let g:ctrlp_custom_ignore['file'] .= '.*\.pyi'
let g:ctrlp_custom_ignore['file'] .= '|\.coverage'
" Rust
let g:ctrlp_custom_ignore['dir'] .= '|target'
" Version controls.
let g:ctrlp_custom_ignore['dir'] .= '|\.git'
let g:ctrlp_custom_ignore['dir'] .= '|\.hg'
let g:ctrlp_custom_ignore['dir'] .= '|\.svn'
" Close the regex.
let g:ctrlp_custom_ignore['dir'] .= ')$'
let g:ctrlp_custom_ignore['file'] .= ')$'

" Add modes into the `<c-f>` and `<c-b>` mode toggling.
let g:ctrlp_extensions = ['dir']
" Needed to access dotfiles.
"let g:ctrlp_show_hidden = 0
let g:ctrlp_show_hidden = 1
" Matching window update wait time in ms.
"let g:ctrlp_lazy_update = 0
let g:ctrlp_lazy_update = 128
" Limit searches.
"let g:ctrlp_max_depth = 40
let g:ctrlp_max_depth = 8
"let g:ctrlp_max_files = 10000
let g:ctrlp_max_files = 1024
" Default modes into the `<c-f>` and `<c-b>` mode toggling.
"let g:ctrlp_types = ['fil', 'buf', 'mru']
let g:ctrlp_types = ['fil', 'buf']

" Opens prompt.
function! s:FindEditPrompt(starting_dir)
  if exists("g:loaded_ctrlp") && g:loaded_ctrlp == 1
    call ctrlp#init(0, {'dir': a:starting_dir})
  else
    call feedkeys(':e '. a:starting_dir)
  endif
endfunction

" Edit prompt...
nnoremap <Plug>(Boni.Find)<F1>
      \ :echo 'find: ( /e) PWD (f)ile (h)ome (w) diff'<CR>
nnoremap <Plug>(Boni.Find)<Tab>
      \ :call BoniMapWait("\<Plug>(Boni.Find)")<CR>

" Edit prompt for buffers.
nmap <Plug>(Boni.Find)b :CtrlPBuffer<CR>
" Edit prompt at $PWD
nnoremap <Plug>(Boni.Find)e :call <SID>FindEditPrompt($PWD)<CR>
nnoremap <Plug>(Boni.Find)<Space> :call <SID>FindEditPrompt($PWD)<CR>
" Change $PWD to ...
nmap <Plug>(Boni.Find)E <Plug>(Boni.Find.PWD)
" Edit prompt at parent directory of current file.
nnoremap <Plug>(Boni.Find)f
      \ :call <SID>FindEditPrompt(expand('%:p:h'))<CR>
" Edit prompt at $HOME.
nnoremap <Plug>(Boni.Find)h
      \ :call <SID>FindEditPrompt(fnameescape($HOME))<CR>
" Edit notes.
nnoremap <Plug>(Boni.Find)1
      \ :execute 'edit'
      \ fnameescape($HOME . '/base/documents/notes/README.md')
      \<CR>
" Edit prompt at website.
nnoremap <Plug>(Boni.Find)2
      \ :call <SID>FindEditPrompt(
      \  fnameescape(
      \    $HOME . '/base/src/bonilindsley.gitlab.io/content/pages/'
      \  )
      \)<CR>
" Edit prompt at website.
nnoremap <Plug>(Boni.Find)3
      \ :call <SID>FindEditPrompt(
      \  fnameescape(
      \    $HOME . '/base/src/bonilindsley.gitlab.io/content/article/'
      \  )
      \)<CR>
" Edit prompt at Boba web.
nnoremap <Plug>(Boni.Find)4
      \ :call <SID>FindEditPrompt(
      \  fnameescape(
      \    $HOME . 'base/src/boba/bobalindsley.github.io/content/'
      \  )
      \)<CR>
" Edit Boba diary.
nnoremap <Plug>(Boni.Find)5
      \ :execute 'edit'
      \ fnameescape($HOME
      \ . '/base/src/boba/bobalindsley.github.io/content/'
      \ . strftime('%Y-%m-%d') . '.md')
      \<CR>
" Edit prompt at Vim plugin directory.
nnoremap <Plug>(Boni.Find)9
      \ :call <SID>FindEditPrompt($VIM_CONFIG_HOME . '/plugin')<CR>
" Edit i3 config.
nnoremap <Plug>(Boni.Find)0
      \ :execute 'edit'
      \ fnameescape($HOME . '/.config/sway/config')
      \<CR>

" Diff.
nnoremap <Plug>(Boni.Find)w :call <SID>FindEditDiff()<CR>
function! s:FindEditDiff()
  echo 'find diff: (d) this (D) off'
  let key = nr2char(getchar())
  if key =~ 'd' | redraw | windo diffthis
  elseif key =~ 'D' | redraw | windo diffoff!
  else | redraw | echo 'Unknown key for BoniFind diff.'
  endif
endfunction

" Change $PWD to ...
nnoremap <Plug>(Boni.Find.PWD)<F1>
      \ :echo 'Set PWD: (e) reset (f)ile (h)ome (.) parent'<CR>
nnoremap <Plug>(Boni.Find.PWD)<Tab>
      \ :call BoniMapWait("\<Plug>(Boni.Find.PWD)")<CR>
" Change $PWD to the $PWD Vim started with.
nnoremap <Plug>(Boni.Find.PWD)e
      \ :execute 'cd' fnameescape($VIM_PWD) <Bar> pwd<CR>
" Change $PWD to the parent directory of the current file.
nnoremap <Plug>(Boni.Find.PWD)f :cd %:p:h <Bar> pwd<CR>
" Change $PWD to $HOME.
nnoremap <Plug>(Boni.Find.PWD)h
      \ :execute 'cd' fnameescape($HOME) <Bar> pwd<CR>
" Change $PWD to parent directory of $PWD.
nnoremap <Plug>(Boni.Find.PWD). :cd .. <Bar> pwd<CR>
