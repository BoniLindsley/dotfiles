if !has('nvim')
  finish
endif

try
  lua require('codecompanion')
catch /^Vim\%((\a\+)\)\=:E5108:/
  finish
endtry

" Use `ga` to select adapter and model.
lua require('codecompanion').setup(codecompanion_setup)

nnoremap <Plug>(Boni.CodeCompanion)<F1>
  \ :echo 'CodeCompanion: ( ) ChatToggle'<CR>
nnoremap <Plug>(Boni.CodeCompanion)<Tab>
  \ :call BoniMapWait("\<Plug>(Boni.CodeCompanion)")<CR>
nmap <Plug>(Boni.CodeCompanion)<Space> :CodeCompanionChat Toggle<CR>
