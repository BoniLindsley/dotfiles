if exists('loaded_bonivim_taskmd')
  finish
endif
let loaded_bonivim_taskmd=1

if !has('python3')
  echomsg 'taskmd requires Python support. Not found.'
  finish
endif

nmap <Plug>(Boni.Calendar) :call g:bonivim#taskmd#remap()<CR>
