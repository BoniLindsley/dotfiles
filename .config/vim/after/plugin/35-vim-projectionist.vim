" # vim-projectionist

" Upstream: https://github.com/tpope/vim-projectionist
"
" Defines properties for buffers, for use by other plugins.
" For example, an 'alternate' for tests, or a 'dispatch' test command.

if !exists("g:loaded_projectionist")
  finish
endif

function s:OnProjectionistDetect()
  if getbufvar(g:projectionist_file, '&filetype') == 'python'
    py3 boni.python.on_projectionist_detect()
  endif
endfunction

autocmd User ProjectionistDetect call s:OnProjectionistDetect()

nnoremap <Plug>(Boni.Find)t :A<CR>
