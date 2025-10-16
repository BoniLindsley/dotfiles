if exists('loaded_autoload_bonipy35_taskmd')
  finish
endif
let loaded_autoload_bonipy35_taskmd=1

if !has('python3')
  echomsg 'taskmd requires Python support. Not found.'
  finish
endif

try
  py3 import bonipy35.taskmd.vim
catch /^Vim(py3):ModuleNotFoundError:/
  echomsg 'taskmd requires Python taskmd library. Not found.'
  finish
endtry

function g:bonipy35#taskmd#remap()
  nunmap <Plug>(Boni.Calendar)
  nnoremap <Plug>(Boni.Calendar)<F1> :echo
    \ 'calendar: (F)ix (I)n (O)ut (s)ummary'
    \<CR>
  nnoremap <Plug>(Boni.Calendar)<Tab>
    \ :call BoniMapWait("\<Plug>(Boni.Calendar)")<CR>
  nmap <Plug>(Boni.Calendar)<Space> <Plug>(Boni.Calendar)S
  nnoremap <Plug>(Boni.Calendar)A :py3 bonipy35.taskmd.vim.write_agenda_to_qlist()<CR>
  nnoremap <Plug>(Boni.Calendar)F :py3 bonipy35.taskmd.vim.fix_clocks()<CR>
  nnoremap <Plug>(Boni.Calendar)I :py3 bonipy35.taskmd.vim.start_clock()<CR>
  nnoremap <Plug>(Boni.Calendar)J :py3 bonipy35.taskmd.vim.jump_to_started_clock()<CR>
  nnoremap <Plug>(Boni.Calendar)O :py3 bonipy35.taskmd.vim.end_clock()<CR>
  nnoremap <Plug>(Boni.Calendar)D :py3 bonipy35.taskmd.vim.write_day_report_to_qlist()<CR>
  nnoremap <Plug>(Boni.Calendar)M :py3 bonipy35.taskmd.vim.write_month_report_to_qlist()<CR>
  nnoremap <Plug>(Boni.Calendar)S :py3 bonipy35.taskmd.vim.write_summary_to_qlist()<CR>
  nnoremap <Plug>(Boni.Calendar)T :py3 bonipy35.taskmd.vim.write_timesheet_to_qlist()<CR>
  nnoremap <Plug>(Boni.Calendar), :py3 bonipy35.taskmd.vim.set_timezone()<CR>
  call BoniMapWait("\<Plug>(Boni.Calendar)")
endfunction
