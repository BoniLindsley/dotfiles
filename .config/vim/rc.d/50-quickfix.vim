" # Quickfix

function! s:QuickfixTodo()
  let l:wildignore_old = &wildignore
  let &wildignore = 'docs/_build/*'
  try
    noautocmd vimgrep /TODO(BoniLindsley):/j **
    echo 'TODO search: completed.'
  catch /^Vim(vimgrep)\=:E480:/
    echo 'TODO search: none found.'
  endtry
  let &wildignore = l:wildignore_old
endfunction

nnoremap <Plug>(Boni.Quickfix)<F1>
  \ :echo 'Quickfix: ( )open (g)rep (l)ocation (n)ext (p)revious (q)uit'
  \ . ' (t)odo'<CR>
nnoremap <Plug>(Boni.Quickfix)<Tab>
  \ :call BoniMapWait("\<Plug>(Boni.Quickfix)")<CR>
nnoremap <Plug>(Boni.Quickfix)<Space> :copen<CR>
nnoremap <Plug>(Boni.Quickfix)g
  \ :noautocmd vimgrep //j **<Left><Left><Left><Left><Left>
nmap <Plug>(Boni.Quickfix)l <Plug>(Boni.Quickfix.Location)
nnoremap <Plug>(Boni.Quickfix)n :cnext<CR>
nnoremap <Plug>(Boni.Quickfix)p :cprevious<CR>
nnoremap <Plug>(Boni.Quickfix)q :cclose<CR>
nnoremap <Plug>(Boni.Quickfix)t :call <SID>QuickfixTodo()<CR>
nnoremap <Plug>(Boni.Quickfix)^ :crewind<CR>
nnoremap <Plug>(Boni.Quickfix)$ :clast<CR>

nnoremap <Plug>(Boni.Quickfix.Location)<F1>
  \ :echo 'Location: ( )open (n)ext (p)revous (q)uit'<CR>
nnoremap <Plug>(Boni.Quickfix.Location)<Tab>
  \ :call BoniMapWait("\<Plug>(Boni.Quickfix.Location)")<CR>
nnoremap <Plug>(Boni.Quickfix.Location)<Space> :lopen<CR>
nnoremap <Plug>(Boni.Quickfix.Location)n :lnext<CR>
nnoremap <Plug>(Boni.Quickfix.Location)p :lprevious<CR>
nnoremap <Plug>(Boni.Quickfix.Location)q :lclose<CR>
nnoremap <Plug>(Boni.Quickfix.Location)^ :lrewind<CR>
nnoremap <Plug>(Boni.Quickfix.Location)$ :llast<CR>
