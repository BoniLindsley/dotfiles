" Plugin options
" ==============

" vim-latex
" =========
" Disable folding on file open.
let g:Tex_AutoFolding = 0
" Disabling auto folding does not seem to be working.
" Disable LaTeX file folding altogether.
let g:Tex_Folding = 0
" Compile as pdf.
let g:Tex_DefaultTargetFormat = 'pdf'
" Use okular as viewer for pdf output.
let g:Tex_ViewRule_pdf = 'mupdf'
" Use latexmk to compile by using hotkey '\m'.
autocmd FileType tex setlocal makeprg=latexmk
" Use custom bash script via vim-latex using '\ll'.
let g:Tex_CompileRule_pdf = 'boni-pdflatex.sh --latexmain --refresh'
"" " Run custom bash script via vim-dispatch using '\d';
"" autocmd FileType tex
""     \ let b:dispatch = 'boni-pdflatex.sh --latexmain --refresh'
"" nnoremap <leader>LL F\i[<Esc>wdwiref<Esc>f}a]<Esc>
"" nnoremap <leader>LF :wincmd w<CR>/!<CR>:wincmd w<CR>
"" nnoremap <leader>LQ :wincmd w<CR>:q<CR>
"" nnoremap <leader>HL :h ls_3_2_3<CR>


" vim-magma
" =========
if has('win32')
  autocmd FileType magma let b:dispatch = 'magma -s %'
  autocmd FileType magma
      \ let b:start = 'pscp -load emmy ' . expand('%:p')
      \ . ' emmy:base/documents/magma/src/'
  autocmd FileType magma
      \ let b:dispatch = 'pscp -load emmy ' . expand('%:p')
      \ . ' emmy:base/documents/magma/src/'
      \ . ' && plink emmy "cd base/documents/magma/src && ./'
      \ . expand('%:t')
      \ .'"'
else
  autocmd FileType magma
      \ let b:start = 'rsync'
      \ . ' -Clprtv --exclude=\*.swp'
      \ . ' $HOME/base/documents/magma/'
      \ . ' sshgw-emmy:base/documents/magma'
  autocmd FileType magma
      \ let b:dispatch = 'rsync'
      \ . ' -Clprtv --exclude=\*.swp'
      \ . ' $HOME/base/documents/magma/'
      \ . ' sshgw-emmy:base/documents/magma'
      \ . ' && ssh sshgw-emmy "cd base/documents/magma && ' . expand('%:~')
      \ . '"'
endif
" " Use .m extension for MAGMA as well.
" autocmd BufRead,BufNewFile *.m set filetype=magma omnifunc=CompleteMagma

" vim-markdown
" ============
"" " Do not require .md extensions for Markdown links.
"" let g:vim_markdown_no_extensions_in_markdown = 1

" vim-json
" ========
" Enable folding for json files.
autocmd FileType json :setlocal foldmethod=syntax
" Disable double quote hiding,
"   so that the file content is displayed as is.
let g:vim_json_syntax_conceal = 0
" Disable vim-json specific warnings.
let g:vim_json_warnings=0

" UltiSnips
" =========
"" " Default hotkeys.
"" let g:UltiSnipsExpandTrigger       = '<tab>'
"" let g:UltiSnipsListSnippets        = '<c-tab>'
"" let g:UltiSnipsJumpForwardTrigger  = '<c-j>'
"" let g:UltiSnipsJumpBackwardTrigger = '<c-k>'

"" " Conque GDB
"" " ==========
"" let g:ConqueGdb_Leader = '<leader>g'

"" " vim-taskwarrior
"" " ===============
"" if !exists("*ChangeVimTimeWarriorDir")
""   function ChangeVimTimeWarriorDir()
""     " Makes sure the rc file exists.
""     " Otherise the plugin will complain.
""     silent !touch .taskrc
""     let $TASKRC = getcwd() . '/.taskrc'
""     " FIXME: This ovewrites the settings from the $TASKRC file.
""     "        Ideally, this should not be used
""     "          and the touch command above should fill in the default
""     "          data file as `./task` instead.
""     let $TASKDATA = getcwd() . '/.task'
""     " This seems to get reset if it is initialised on start up.
""     " And the plugin ends up trying to write
""     " to root `/.vim_tw.history`.
""     let g:task_log_directory = g:boni_vimfiles
""                                \ . '/var/vim-taskwarrior'
""   endfunction
"" endif
"" nnoremap <leader>t :call ChangeVimTimeWarriorDir()<CR>:TW<CR>
"" " FIXME: Need to change it to be called when entering a taskreport.
"" "        But that requires two autocmd type matching.
"" "        See: https://stackoverflow.com/1313171
"" "        Otherwise, opening multiple taskreport
"" "          will overwrite environment variable
"" "          in a different taskreport.
"" autocmd FileType taskreport call ChangeVimTimeWarriorDir()

" ## vimspeak

" It overrides the default behavior of the `s` and `S` keybindings.
" The former, when combined with a motion,
"   will read the implicated text aloud - for example
"
"   * `s}` will read the next paragraph;
"   * `sw`  will read the next word; and
"   * `ss` will read the current line.
"
" The `S` key is a prefix which can be combined with other keys
"   to do more specific actions:

"   * `St`: toggle vimspeak off or on (default: on)
"   * `Sc`: cancel the current reading
"   * `Sl`: read out the current line number
"   * `Ss`: adjust the speed of speech (default: 300)
"   * `Sp`: toggle punctuation (default: on)
"   * `Sb`: read the name of the current buffer

"let g:vimspeak_enabled = 1
let g:vimspeak_enabled = 0
" Arguments passed to eSpeak.
"let g:vimspeak_args  = ""
"let g:vimspeak_capital_pitch = "30"
"let g:vimspeak_speed = "200"
"let g:vimspeak_use_punct = 1
