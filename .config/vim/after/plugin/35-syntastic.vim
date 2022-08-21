" # syntastic

" Upstream: https://github.com/vim-syntastic/syntastic

if !exists('g:loaded_syntastic_plugin')
  finish
endif

set statusline+=%#warningmsg#
set statusline+=%{SyntasticStatuslineFlag()}
set statusline+=%*

" Disable check on save. Prefer manual check.
"let g:syntastic_mode_map = {
"  \ 'mode': 'active',
"  \ 'active_filetypes': [],
"  \ 'passive_filetypes': []
"  \ }
let g:syntastic_mode_map = {
  \ 'mode': 'passive',
  \ 'active_filetypes': [],
  \ 'passive_filetypes': []
  \ }

" Write errors to location list to allow jumping to them.
"let g:syntastic_always_populate_loc_list = 0
let g:syntastic_always_populate_loc_list = 1
" Close location list when there are no errors.
"let g:syntastic_auto_loc_list = 2
" Check when opening, if in active mode, which checks when saving.
"let g:syntastic_check_on_open = 0
" Do not check when writing just before quitting.
"let g:syntastic_check_on_wq = 1
let g:syntastic_check_on_wq = 0

" I use mypy by default.
"unlet g:syntastic_python_checkers
let g:syntastic_python_checkers = ['mypy', 'pylint']

nnoremap <Plug>(Boni.Syntastic)<Space> :w<CR>:SyntasticCheck<CR>
