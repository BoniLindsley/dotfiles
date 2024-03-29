if !executable('p4')
  nnoremap <Plug>(Boni.Perforce) :echo 'Error: p4 not found'<CR>
  finish
endif

" Create a new buffer to view diff from Perforce.
nnoremap <Plug>(Boni.Perforce)d
  \ :diffthis<CR>
  \:new<CR>
  \:r !env P4DIFF= p4 diff -du #:.<CR>
  \:%!patch --output=- --quiet --reverse #:.<CR>
  \:diffthis<CR>
  \:set buftype=nofile<CR>
nnoremap <Plug>(Boni.Perforce)e :!p4 edit %:.<CR>
nnoremap <Plug>(Boni.Perforce)r :!p4 revert %:.<CR>
