" # vim-test

" Upstream: https://github.com/vim-test/vim-test

let test#python#runner = 'pytest'
let test#strategy = "dispatch"
nnoremap <Plug>(Boni.VimTest)<F1> :echo
\ 'vim-dispatch: ( ) Nearest! (f)ile (l)ast (s)uite (S)trategy'
\<CR>
nnoremap <Plug>(Boni.VimTest)<Tab>
\ :call BoniMapWait("\<Plug>(Boni.VimTest)")<CR>
nnoremap <Plug>(Boni.VimTest)<Space> :TestNearest<CR>
nnoremap <Plug>(Boni.VimTest)f :TestFile<CR>
nnoremap <Plug>(Boni.VimTest)l :TestLast<CR>
nnoremap <Plug>(Boni.VimTest)s :TestSuite<CR>
nmap <Plug>(Boni.VimTest)S <Plug>(Boni.VimTest.Strategy)

nnoremap <Plug>(Boni.VimTest.Strategy)<F1> :echo
\ 'let test#strategy = ( ) custom (d)ispatch (v)imspector'<CR>
nnoremap <Plug>(Boni.VimTest.Strategy)<Tab>
\ :call BoniMapWait("\<Plug>(Boni.VimTest.Strategy)")<CR>
nnoremap <Plug>(Boni.VimTest.Strategy)<Space>
\ :let test#strategy = ''<Left>
nnoremap <Plug>(Boni.VimTest.Strategy)d
\ :let test#strategy = 'dispatch'<CR>
nnoremap <Plug>(Boni.VimTest.Strategy)v
\ :let test#strategy = 'vimspector'<CR>
