" Automatically fitting a quickfix window height between two sizes.
" Reference: http://vim.wikia.com/wiki/
function! AdjustWindowHeight(minheight, maxheight)
  execute max([min([line("$"), a:maxheight]), a:minheight]) . "wincmd _"
endfunction
call AdjustWindowHeight(8, 16)
