" # YouCompleteMe

" Upstream: https://github.com/ycm-core/YouCompleteMe

if !exists("g:loaded_youcompleteme")
  finish
endif

"" Preview window is used to show extra information such as prototypes.
"let g:ycm_autoclose_preview_window_after_completion = 1
"let g:ycm_autoclose_preview_window_after_insertion = 1
" Disable documentation pop-up. Gets in the way of reading.
"let g:ycm_auto_hover = 'CursorHold'
let g:ycm_auto_hover = ''

" Only use YCM completion on specific file types.
"let g:ycm_filetype_whitelist = {'*': 1}
let g:ycm_filetype_whitelist = {
  \ 'cpp': 1,
  \ 'markdown': 1,
  \ 'python': 1,
  \ 'rust': 1,
  \ }

"let g:ycm_global_ycm_extra_conf = ''
let g:ycm_global_ycm_extra_conf = fnamemodify( $MYVIMRC, ':p:h')
      \ . '/' . '.ycm_extra_conf.py'

" GoTo commands can only in the 'same-buffer', 'split'
" or 'split-or-existing-window'.
"let g:ycm_goto_buffer_command = 'same-buffer'

" Change autocomplete hotkey to not use `<tab>`.
"let g:ycm_key_detailed_diagnostics = '<leader>d'
let g:ycm_key_detailed_diagnostics = ''
"let g:ycm_key_list_previous_completion = ['<S-TAB>', '<Up>']
let g:ycm_key_list_previous_completion = ['<C-p>']
"let g:ycm_key_list_select_completion = ['<TAB>', '<Down>']
let g:ycm_key_list_select_completion = ['<C-n>']
"let g:ycm_key_list_stop_completion = ['<C-y>']

nnoremap <Plug>(Boni.YouCompleteMe)<F1>
  \ :echo 'YouCompleteMe: ( ) GoTo (C)ommand (D)oc (H)over (R)estart'<CR>
nnoremap <Plug>(Boni.YouCompleteMe)<Tab>
  \ :call BoniMapWait("\<Plug>(Boni.YouCompleteMe)")<CR>
nnoremap <Plug>(Boni.YouCompleteMe)<Space> :YcmCompleter GoTo<CR>
nnoremap <Plug>(Boni.YouCompleteMe)C :YcmCompleter<Space>
nnoremap <Plug>(Boni.YouCompleteMe)D :YcmCompleter GetDoc<CR>
nmap <Plug>(Boni.YouCompleteMe)H <plug>(YCMHover)
" Force refresh.
nnoremap <Plug>(Boni.YouCompleteMe)r :YcmForceCompileAndDiagnostics<CR>
nnoremap <Plug>(Boni.YouCompleteMe)R :YcmRestartServer<CR>
nnoremap <Plug>(Boni.YouCompleteMe)s :YcmShowDetailedDiagnostic<CR>
nnoremap <Plug>(Boni.YouCompleteMe)N :lnext<CR>
nnoremap <Plug>(Boni.YouCompleteMe)P :lprevious<CR>
