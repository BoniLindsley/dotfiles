if exists('loaded_bonivim_taskmd')
  finish
endif
let loaded_bonivim_taskmd=1

if !has('python3')
  echomsg 'taskmd requires Python support. Not found.'
  finish
endif

nnoremap <Plug>(Boni.Calendar)<F1> :echo
  \ 'calendar: (I)n (s)ummary
  \<CR>
nnoremap <Plug>(Boni.Calendar)<Tab>
  \ :call BoniMapWait("\<Plug>(Boni.Calendar)")<CR>
nmap <Plug>(Boni.Calendar)<Space> <Plug>(Boni.Calendar)s
nnoremap <Plug>(Boni.Calendar)I :py3 bonivim.taskmd.start_clock()<CR>
nnoremap <Plug>(Boni.Calendar)O :py3 bonivim.taskmd.end_clock()<CR>
nnoremap <Plug>(Boni.Calendar)I :call g:bonivim#taskmd#start_clock()<CR>
nnoremap <Plug>(Boni.Calendar)O :call g:bonivim#taskmd#end_clock()<CR>
nnoremap <Plug>(Boni.Calendar)s :call g:bonivim#taskmd#run()<CR>
