" # fugitive.vim

" Upstream: https://github.com/tpope/vim-fugitive

nnoremap <Plug>(Boni.Fugitive)<F1>
  \ :echo 'Fugitive: (space) status (g)utter (h)unk (p)aths (w)rite'<CR>
nnoremap <Plug>(Boni.Fugitive)<Tab>
  \ :call BoniMapWait("\<Plug>(Boni.Fugitive)")<CR>
nnoremap <Plug>(Boni.Fugitive)<Space> :Git<CR>
nnoremap <Plug>(Boni.Fugitive)d :Gdiffsplit<CR>
nmap <Plug>(Boni.Fugitive)p <Plug>(Boni.Fugitive.Path)
nnoremap <Plug>(Boni.Fugitive)w :Gwrite<CR>

nnoremap <Plug>(Boni.Fugitive.Path)<F1> :echo
  \ 'Git paths: (space) reset (d)otfiles (w)ebsite'<CR>
nnoremap <Plug>(Boni.Fugitive.Path)<Tab>
  \ :call BoniMapWait("\<Plug>(Boni.Fugitive.Path)")<CR>

nnoremap <Plug>(Boni.Fugitive.Path)<Space>
  \ :call <SID>GitPathPwd()<CR>
function! s:GitPathPwd()
  unlet $GIT_DIR
  unlet $GIT_WORK_TREE
  execute 'cd' fnameescape($VIM_PWD)
  redraw
  pwd
endfunction

nnoremap <Plug>(Boni.Fugitive.Path)d :call <SID>GitPathDotfiles()<CR>
function! s:GitPathDotfiles()
  let $GIT_DIR = $HOME . '/.local/lib/boni/dotfiles/repos/dotfiles.git'
  let $GIT_WORK_TREE = $HOME
  execute 'cd' fnameescape($GIT_WORK_TREE)
  redraw
  pwd
endfunction

nnoremap <Plug>(Boni.Fugitive.Path)w :call <SID>GitPathWebsite()<CR>
function! s:GitPathWebsite()
  let $GIT_WORK_TREE = $HOME . '/base/src/bonilindsley.gitlab.io'
  let $GIT_DIR = $GIT_WORK_TREE . '/.git'
  execute 'cd' fnameescape($GIT_WORK_TREE)
  redraw
  pwd
endfunction
