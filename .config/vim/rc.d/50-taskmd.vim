if exists('loaded_bonivim_taskmd')
  finish
endif
let loaded_bonivim_taskmd=1

if !has('python3')
  echomsg 'taskmd requires Python support. Not found.'
  finish
endif

nnoremap <Plug>(Boni.Calendar)<F1> :echo
  \ 'calendar: (F)ix (I)n (O)ut (s)ummary'
  \<CR>
nnoremap <Plug>(Boni.Calendar)<Tab>
  \ :call BoniMapWait("\<Plug>(Boni.Calendar)")<CR>
nmap <Plug>(Boni.Calendar)<Space> <Plug>(Boni.Calendar)S
nnoremap <Plug>(Boni.Calendar)F :call g:bonivim#taskmd#fix_clocks()<CR>
nnoremap <Plug>(Boni.Calendar)I :call g:bonivim#taskmd#start_clock()<CR>
nnoremap <Plug>(Boni.Calendar)O :call g:bonivim#taskmd#end_clock()<CR>
nnoremap <Plug>(Boni.Calendar)D :call g:bonivim#taskmd#write_day_report_to_qlist()<CR>
nnoremap <Plug>(Boni.Calendar)M :call g:bonivim#taskmd#write_month_report_to_qlist()<CR>
nnoremap <Plug>(Boni.Calendar)S :call g:bonivim#taskmd#write_summary_to_qlist()<CR>
nnoremap <Plug>(Boni.Calendar)T :call g:bonivim#taskmd#write_timesheet_to_qlist()<CR>
nnoremap <Plug>(Boni.Calendar), :call g:bonivim#taskmd#set_timezone()<CR>
