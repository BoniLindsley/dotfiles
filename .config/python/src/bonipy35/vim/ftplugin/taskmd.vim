" ftplugin/taskmd.vim
"
" Buffer-local commands (and, unless disabled, keybindings) for
" `taskmd` files. Sourced once per buffer whenever `filetype=taskmd`
" is set (see ftdetect/taskmd.vim).

if exists('b:did_ftplugin')
  finish
endif
let b:did_ftplugin = 1

" `taskmd` files are valid Markdown (see SPEC.md, section 1), so inherit
" Markdown's syntax highlighting, indent, and other ftplugin settings
" rather than reimplementing them.
runtime! ftplugin/markdown.vim ftplugin/markdown_*.vim ftplugin/markdown/*.vim

command! -buffer TaskmdClockStart call taskmd#ClockStart()
command! -buffer TaskmdClockStop call taskmd#ClockStop()
command! -buffer TaskmdClockStatus call taskmd#ClockStatus()
command! -buffer TaskmdReport call taskmd#Report()
command! -buffer TaskmdReportDir call taskmd#ReportDir()
command! -buffer TaskmdListOpen call taskmd#ListOpen()
command! -buffer TaskmdScheduleShow call taskmd#ScheduleShow()
command! -buffer TaskmdScheduleConflicts call taskmd#ScheduleConflicts()
command! -buffer TaskmdScheduleSummary call taskmd#ScheduleSummary()

" Set g:taskmd_no_mappings = 1 (before this file loads) to skip the
" default keybindings and define your own.
if !exists('g:taskmd_no_mappings') || !g:taskmd_no_mappings
  nnoremap <buffer> <silent> <LocalLeader>ts :TaskmdClockStart<CR>
  nnoremap <buffer> <silent> <LocalLeader>tS :TaskmdClockStop<CR>
  nnoremap <buffer> <silent> <LocalLeader>t? :TaskmdClockStatus<CR>
  nnoremap <buffer> <silent> <LocalLeader>tr :TaskmdReport<CR>
  nnoremap <buffer> <silent> <LocalLeader>tR :TaskmdReportDir<CR>
  nnoremap <buffer> <silent> <LocalLeader>tl :TaskmdListOpen<CR>
  nnoremap <buffer> <silent> <LocalLeader>tas :TaskmdScheduleShow<CR>
  nnoremap <buffer> <silent> <LocalLeader>tac :TaskmdScheduleConflicts<CR>
  nnoremap <buffer> <silent> <LocalLeader>tau :TaskmdScheduleSummary<CR>
endif

let b:undo_ftplugin = ''
  \ . 'silent! delcommand TaskmdClockStart | '
  \ . 'silent! delcommand TaskmdClockStop | '
  \ . 'silent! delcommand TaskmdClockStatus | '
  \ . 'silent! delcommand TaskmdReport | '
  \ . 'silent! delcommand TaskmdReportDir | '
  \ . 'silent! delcommand TaskmdListOpen | '
  \ . 'silent! delcommand TaskmdScheduleShow | '
  \ . 'silent! delcommand TaskmdScheduleConflicts | '
  \ . 'silent! delcommand TaskmdScheduleSummary'
