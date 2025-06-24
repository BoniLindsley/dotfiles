if exists('loaded_autoload_bonivim_taskmd')
  finish
endif
let loaded_autoload_bonivim_taskmd=1

if !has('python3')
  echomsg 'taskmd requires Python support. Not found.'
  finish
endif

try
  py3 import bonivim.taskmd
catch /^Vim(py3):ModuleNotFoundError:/
  echomsg 'taskmd requires Python taskmd library. Not found.'
  finish
endtry

function g:bonivim#taskmd#end_clock()
  py3 bonivim.taskmd.end_clock()
endfunction

function g:bonivim#taskmd#fix_clocks()
  py3 bonivim.taskmd.fix_clocks()
endfunction

function g:bonivim#taskmd#jump_to_started_clock()
  py3 bonivim.taskmd.jump_to_started_clock()
endfunction

function g:bonivim#taskmd#set_timezone()
  py3 bonivim.taskmd.set_timezone()
endfunction

function g:bonivim#taskmd#write_day_report_to_qlist()
  py3 bonivim.taskmd.write_day_report_to_qlist()
endfunction

function g:bonivim#taskmd#write_month_report_to_qlist()
  py3 bonivim.taskmd.write_month_report_to_qlist()
endfunction

function g:bonivim#taskmd#write_summary_to_qlist()
  py3 bonivim.taskmd.write_summary_to_qlist()
endfunction

function g:bonivim#taskmd#write_timesheet_to_qlist()
  py3 bonivim.taskmd.write_timesheet_to_qlist()
endfunction

function g:bonivim#taskmd#start_clock()
  py3 bonivim.taskmd.start_clock()
endfunction

function g:bonivim#taskmd#remap()
  nunmap <Plug>(Boni.Calendar)
  nnoremap <Plug>(Boni.Calendar)<F1> :echo
    \ 'calendar: (F)ix (I)n (O)ut (s)ummary'
    \<CR>
  nnoremap <Plug>(Boni.Calendar)<Tab>
    \ :call BoniMapWait("\<Plug>(Boni.Calendar)")<CR>
  nmap <Plug>(Boni.Calendar)<Space> <Plug>(Boni.Calendar)S
  nnoremap <Plug>(Boni.Calendar)F :call g:bonivim#taskmd#fix_clocks()<CR>
  nnoremap <Plug>(Boni.Calendar)I :call g:bonivim#taskmd#start_clock()<CR>
  nnoremap <Plug>(Boni.Calendar)J :call g:bonivim#taskmd#jump_to_started_clock()<CR>
  nnoremap <Plug>(Boni.Calendar)O :call g:bonivim#taskmd#end_clock()<CR>
  nnoremap <Plug>(Boni.Calendar)D :call g:bonivim#taskmd#write_day_report_to_qlist()<CR>
  nnoremap <Plug>(Boni.Calendar)M :call g:bonivim#taskmd#write_month_report_to_qlist()<CR>
  nnoremap <Plug>(Boni.Calendar)S :call g:bonivim#taskmd#write_summary_to_qlist()<CR>
  nnoremap <Plug>(Boni.Calendar)T :call g:bonivim#taskmd#write_timesheet_to_qlist()<CR>
  nnoremap <Plug>(Boni.Calendar), :call g:bonivim#taskmd#set_timezone()<CR>
  call BoniMapWait("\<Plug>(Boni.Calendar)")
endfunction
