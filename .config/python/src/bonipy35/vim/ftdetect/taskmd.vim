" Filetype detection for taskmd files.
"
" A file is a taskmd file if either:
"   1. its name ends in `.task.md`, or
"   2. it's a `.md` file whose first line is exactly `<!-- taskmd -->`.
"
" Both forms are valid Markdown, so any editor that doesn't source
" this file still renders them as plain Markdown (see SPEC.md, section 1).
"
" The `taskmd` filetype itself is set up (in ftplugin/taskmd.vim) to
" inherit standard Markdown syntax highlighting, so this only affects
" which buffer-local commands/keybindings are available -- it does
" not change how the file looks.

augroup taskmd_filetype
  autocmd!
  autocmd BufRead,BufNewFile *.task.md set filetype=taskmd
  autocmd BufRead,BufNewFile *.md
    \ if getline(1) =~# '^<!-- taskmd -->' | set filetype=taskmd | endif
augroup END
