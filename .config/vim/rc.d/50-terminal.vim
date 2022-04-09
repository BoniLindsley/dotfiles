" # Built-in terminal
"
" Start a terminal buffer and a job asynchronously
" using `:term [<prog> [<args...>]]`, or `:term` to start a shell.
"
" New terminal buffer enters Terminal-Job mode by default
" In this mode, cursor is controlled by the terminal pty.
" Key maps in this mode can be specified in `:tmap`.
" Default mappings use a `termwinkey`
" as a sort of terminal mode leader key.
"
" | Mapping                  | Description                       |
" | ------------------------ | --------------------------------- |
" | <termwinkey> :           | Enter Command mode                |
" | <termwinkey> .           | Send <termwinkey> to the terminal |
" | <termwinkey> <termwinkey>| Send <termwinkey> to the terminal |
" | <termwinkey> N           | Enter Terminal-Normal mode        |
" | <termwinkey> " {reg}     | Paste register                    |
" | <termwinkey> <c-c>       | Ends job                          |
" | <termwinkey> <c-n>       | Enter Terminal-Normal mode        |
" | <termwinkey> <c-w>       | Focus next window                 |
" | <termwinkey> <c-\>       | Send CTRL-\ to the terminal       |
" | <termwinkey> gt          | Go to next tabpage                |
" | <termwinkey> gT          | Go to previous tabpage            |
" | <c-\> <c-n>              | Enter Terminal-Normal mode        |

map <C-w><Leader> <Leader>
if has('terminal')
  tmap <C-w><Leader> <C-\><C-n><Leader>
endif

nnoremap <Plug>(Boni.Terminal)<F1>
  \ :echo 'terminal: (space) start '<CR>
nnoremap <Plug>(Boni.Terminal)<Tab>
  \ :call BoniMapWait("\<Plug>(Boni.Terminal)")<CR>
nnoremap <Plug>(Boni.Terminal)<Space> :terminal ++curwin<CR>
