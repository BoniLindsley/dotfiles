if !executable('p4')
  nnoremap <Plug>(Boni.Perforce) :echo 'Error: p4 not found'<CR>
  finish
endif

nnoremap <Plug>(Boni.Perforce)e :!p4 edit %:p<CR>
nnoremap <Plug>(Boni.Perforce)r :!p4 revert %:p<CR>
