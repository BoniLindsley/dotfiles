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

function g:bonivim#taskmd#run()
  py3 bonivim.taskmd.write_summary_to_qlist()
  copen
  wincmd p
endfunction

function g:bonivim#taskmd#start_clock()
  py3 bonivim.taskmd.start_clock()
endfunction
