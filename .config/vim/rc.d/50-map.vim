" # Custom hotkey maps

" Use backspace.
noremap! <C-?> <C-h>

" Echo help string, and then wait for keys that follows the prefix.
function! BoniMapWait(prefix)
  execute 'normal ' . a:prefix . "\<F1>"
  let l:key = getchar()
  call feedkeys(a:prefix)
  call feedkeys(nr2char(l:key))
endfunction

nmap <Leader> <Plug>(Boni)
nnoremap <Plug>(Boni)<F1> :echo
  \ '<lt>Leader>: (a)utoformat (c) quickfix (d)ispatch (e) find (g)it'
  \<CR>
nnoremap <Plug>(Boni)<Tab> :call BoniMapWait("\<Plug>(Boni)")<CR>

nmap <Plug>(Boni)a <Plug>(Boni.Application)
nnoremap <Plug>(Boni.Application)<F1> :echo 'application: (g)it'<CR>
nnoremap <Plug>(Boni.Application)<Tab>
  \ :call BoniMapWait("\<Plug>(Boni.Application)")<CR>
nmap <Plug>(Boni.Application)G <Plug>(Boni.Fugitive)
nmap <Plug>(Boni.Application)T <Plug>(Boni.Terminal)
nmap <Plug>(Boni.Application)g <Plug>(Boni.Application)G<Space>
nmap <Plug>(Boni.Application)s :call g:boni#speech#init()<CR>
nmap <Plug>(Boni.Application)t <Plug>(Boni.Application)T<Space>

nmap <Plug>(Boni)d <Plug>(Boni.Do)
nnoremap <Plug>(Boni.Do)<F1> :echo
  \ 'do: ( /d)ispatch de(b)ug (f)ormat (g)it (h)int bookma(r)k'
  \ '(s)yntax (t)est'
  \<CR>
nnoremap <Plug>(Boni.Do)<Tab>
  \ :call BoniMapWait("\<Plug>(Boni.Do)")<CR>
nmap <Plug>(Boni.Do)<Space> <Plug>(Boni.Dispatch)<Space>
nmap <Plug>(Boni.Do)B <Plug>(Boni.Vimspector)
nmap <Plug>(Boni.Do)D <Plug>(Boni.Dispatch)
nmap <Plug>(Boni.Do)E <Plug>(Boni.Find)
nmap <Plug>(Boni.Do)G <Plug>(Boni.GitGutter)
nmap <Plug>(Boni.Do)H <Plug>(Boni.ALE)
nmap <Plug>(Boni.Do)L <Plug>(Boni.Quickfix)
nmap <Plug>(Boni.Do)T <Plug>(Boni.VimTest)

nmap <Plug>(Boni.Do)b <Plug>(Boni.Do)B<Space>
nmap <Plug>(Boni.Do)d <Plug>(Boni.Do)D<Space>
nmap <Plug>(Boni.Do)f <Plug>(ale_fix)
nmap <Plug>(Boni.Do)g <Plug>(Boni.Do)G<Space>
nmap <Plug>(Boni.Do)h <Plug>(Boni.Do)H<Space>
nmap <Plug>(Boni.Do)l <Plug>(Boni.Quickfix)
nmap <Plug>(Boni.Do)r <Plug>(Boni.Bookmarks)
nmap <Plug>(Boni.Do)s <Plug>(ale_lint)
nmap <Plug>(Boni.Do)t <Plug>(Boni.Do)T<Space>
nmap <Plug>(Boni.Do)v <Plug>(Boni.Perforce)

nnoremap <Plug>(Boni)n :bnext<CR>
nnoremap <Plug>(Boni)p :bprevious<CR>
" Disables auto formatting for pasted text.
" Note that when nopaste is active,
" vim-latex environment insertion (<F5>)
" is unavailable in insert mode.
nnoremap <Plug>(Boni)P :set invpaste paste?<CR>
nnoremap <Plug>(Boni)q :buffer #<Bar> bdelete #<CR>
nnoremap <Plug>(Boni)w :write<CR>
nnoremap <Plug>(Boni)<Bar> :let @/ = '\<'.expand('<cword>').'\>'<CR>
" Toggle search highlighting.
nnoremap <Plug>(Boni)<Bslash> :set hlsearch! hlsearch?<CR>
" This was used for closing netrw buffers.
" Does not seem to be working anymore though.
nnoremap <Plug>(Boni)Q :execute 'bd' (bufnr('%') - 1)<CR>:bprevious<CR>
