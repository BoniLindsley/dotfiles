" # ALE

" Upstream: https://github.com/dense-analysis/ale

if v:version < 800
  finish
endif

" Language server protocol client
"let g:ale_completion_enabled = 0
let g:ale_completion_enabled = 1

" Do not send requests too frequently.
"let g:ale_completion_delay = 100
let g:ale_completion_delay = 1000

"let g:ale_lint_on_enter = 1
let g:ale_lint_on_enter = 0
"let g:ale_lint_on_filetype_changed = 1
let g:ale_lint_on_filetype_changed = 0
"let g:ale_lint_on_insert_leave = 1
let g:ale_lint_on_insert_leave = 0
"let g:ale_lint_on_save = 1
let g:ale_lint_on_save = 0
"let g:ale_lint_on_text_changed = 'normal'
let g:ale_lint_on_text_changed = 0

Plug 'https://github.com/dense-analysis/ale.git'
