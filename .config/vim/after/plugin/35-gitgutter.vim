" # vim-gitgutter

" Upstream: https://github.com/airblade/vim-gitgutter

" Enabled by default.
" Can be toggled on/off, and per buffer.
" But it seems per buffer toggling on applies if the plugin is on.
"let g:gitgutter_enabled = 1
" Disable buffer git-gutter by default.
function! s:GitGutterBufferDisable()
  if exists(":GitGutterDisable")
    call gitgutter#buffer_disable()
  endif
endfunction
autocmd BufReadPre * call s:GitGutterBufferDisable()

" Disable key mappings created by default.
let g:gitgutter_map_keys = 0

" Disable realtime updates
let g:gitgutter_eager = 0
let g:gitgutter_realtime = 0

" Use `:edit` to disable.
nnoremap <Plug>(Boni.GitGutter)<Space> :GitGutterBufferEnable<CR>
nmap <Plug>(Boni.GitGutter)h <Plug>(Boni.GitGutter.Hunk)
nnoremap <Plug>(Boni.GitGutter.Hunk)<F1> :echo
  \ 'Git hunk: (a)dd (p)review (u)ndo ([) previous (]) next'<CR>
nnoremap <Plug>(Boni.GitGutter.Hunk)<Tab>
  \ :call BoniMapWait("\<Plug>(Boni.GitGutter.Hunk)")<CR>
nnoremap <Plug>(Boni.GitGutter.Hunk)a :GitGutterStageHunk<CR>
nnoremap <Plug>(Boni.GitGutter.Hunk)p :GitGutterPreviewHunk<CR>
nnoremap <Plug>(Boni.GitGutter.Hunk)u :GitGutterUndoHunk<CR>
nnoremap <Plug>(Boni.GitGutter.Hunk)[ :GitGutterPrevHunk<CR>
nnoremap <Plug>(Boni.GitGutter.Hunk)] :GitGutterNextHunk<CR>
