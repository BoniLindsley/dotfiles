" autoload/taskmd.vim
"
" Thin Vimscript wrappers around the `taskmd_vim.py` Python shim.
" All of the actual logic -- building the `taskmd` CLI argv, running
" it, parsing its output, and handling the ambiguous-stop menu --
" lives in `vim/taskmd_vim.py`, which is fully unit-tested outside of
" Vim (see tests/test_bonipy35/test_taskmd/test_vim_shim.py). This
" file's only job is to point Vim's embedded Python3 interpreter at
" that module and dispatch each `:Taskmd*` command to the matching
" `taskmd_vim.vim_*` function, which itself reads the current buffer
" path/cursor line and updates the buffer/quickfix list/echo area.

if !has('python3')
  finish
endif

let s:plugin_root = expand('<sfile>:p:h:h')

function! s:EnsureShimLoaded() abort
  if exists('s:shim_loaded')
    return
  endif
  python3 << EOF
import sys
import vim

_plugin_root = vim.eval('s:plugin_root')
if _plugin_root not in sys.path:
    sys.path.insert(0, _plugin_root)

import taskmd_vim  # noqa: E402  (import must follow the sys.path fix-up)
EOF
  let s:shim_loaded = 1
endfunction

" Start a clock session for the task at the cursor line in the
" current buffer.
function! taskmd#ClockStart() abort
  call s:EnsureShimLoaded()
  python3 taskmd_vim.vim_clock_start()
endfunction

" Stop the open clock session for the task at the cursor. If there
" are multiple open sessions in the file, prompts with `inputlist()`.
function! taskmd#ClockStop() abort
  call s:EnsureShimLoaded()
  python3 taskmd_vim.vim_clock_stop()
endfunction

" Echo whether the task at the cursor has an open clock session.
function! taskmd#ClockStatus() abort
  call s:EnsureShimLoaded()
  python3 taskmd_vim.vim_clock_status()
endfunction

" Open a scratch buffer with the report for the current file.
function! taskmd#Report() abort
  call s:EnsureShimLoaded()
  python3 taskmd_vim.vim_report()
endfunction

" Open a scratch buffer with the report for the current file's
" directory.
function! taskmd#ReportDir() abort
  call s:EnsureShimLoaded()
  python3 taskmd_vim.vim_report_dir()
endfunction

" Populate and open the quickfix list with every unclosed CLOCK:
" session in the current file.
function! taskmd#ListOpen() abort
  call s:EnsureShimLoaded()
  python3 taskmd_vim.vim_list_open()
endfunction

" Open a scratch buffer with the agenda for the next 14 days.
function! taskmd#ScheduleShow() abort
  call s:EnsureShimLoaded()
  python3 taskmd_vim.vim_schedule_show()
endfunction

" Open a quickfix list of scheduling conflicts in the current file.
function! taskmd#ScheduleConflicts() abort
  call s:EnsureShimLoaded()
  python3 taskmd_vim.vim_schedule_conflicts()
endfunction

" Open a scratch buffer with the schedule summary for the current file.
function! taskmd#ScheduleSummary() abort
  call s:EnsureShimLoaded()
  python3 taskmd_vim.vim_schedule_summary()
endfunction
