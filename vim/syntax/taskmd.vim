" syntax/taskmd.vim
"
" `taskmd` files are valid Markdown (see SPEC.md, section 1: the format is
" designed so files degrade gracefully to plain Markdown in editors
" that don't know about `taskmd`). Rather than reimplementing
" highlighting, just source Markdown's syntax file directly and mark
" ourselves as having consumed it.

if exists('b:current_syntax')
  finish
endif

runtime! syntax/markdown.vim
unlet! b:current_syntax

let b:current_syntax = 'taskmd'
