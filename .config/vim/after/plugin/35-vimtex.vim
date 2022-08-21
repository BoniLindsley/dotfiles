" # vimtex
"
" Upstream: https://github.com/lervag/vimtex

if empty(v:servername) && has('serverclient')
  call remote_startserver('VIM')
endif

"let g:vimtex_compiler_latexmk = {
"    \ 'backend' : DEPENDS ON SYSTEM (SEE BELOW),
"    \ 'background' : 1,
"    \ 'build_dir' : '',
"    \ 'callback' : 1,
"    \ 'continuous' : 1,
"    \ 'executable' : 'latexmk',
"    \ 'options' : [
"    \   '-verbose',
"    \   '-file-line-error',
"    \   '-synctex=1',
"    \   '-interaction=nonstopmode',
"    \ ],
"    \}
let g:vimtex_compiler_latexmk = {
  \ 'continuous' : 0,
  \ 'build_dir' : 'build-latexmk',
  \}
"
" Use this option to disable/enable the vimtex view interface.
"let g:vimtex_view_enabled = 1
" If enabled,
"   the view will open automatically
"   when compilation has started in `continuous` mode
"   and if `callback` is enabled,
"   or if `continuous` mode is disabled
"   and one uses either the `jobs` or the `nvim` backend.
"let g:vimtex_view_automatic = 1
"let g:vimtex_view_method = 'general'
if has('win32') || has('win32unix')
  let g:vimtex_view_method = 'general'
else
  let g:vimtex_view_method = 'mupdf'
endif

" If enabled, allows browsing current output while recompiling.
"let g:vimtex_view_use_temp_files = 0
" "" File copying after compiling seems to be broken.
" if has('win32') || has('win32unix')
"   "Reload does not seem to work well for temp files on Windows.
"   let g:vimtex_view_use_temp_files = 0
" else
"   let g:vimtex_view_use_temp_files = 1
" endif

"let g:vimtex_view_forward_search_on_start = 1

"let g:vimtex_view_general_viewer = 'xdg-open'
"let g:vimtex_view_general_options = '@pdf'
"let g:vimtex_view_general_options_latexmk = ''
"let g:vimtex_view_general_callback = ''
if has('win32') || has('win32unix')
  let g:vimtex_view_general_viewer = 'SumatraPDF'
  let g:vimtex_view_general_options
      \ = '-reuse-instance -forward-search @tex @line @pdf'
      \ . ' -inverse-search "gvim --servername ' . v:servername
      \ . ' --remote-send \"^<C-\^>^<C-n^>'
      \ . ':drop \%f^<CR^>:\%l^<CR^>:normal\! zzzv^<CR^>'
      \ . ':execute ''drop '' . fnameescape(''\%f'')^<CR^>'
      \ . ':\%l^<CR^>:normal\! zzzv^<CR^>'
      \ . ':call remote_foreground('''.v:servername.''')^<CR^>^<CR^>\""'
else
  let g:vimtex_view_general_viewer = 'okular'
  let g:vimtex_view_general_options = '--unique file:@pdf\#src:@line@tex'
  let g:vimtex_view_general_options_latexmk = '--unique'
  " Backward search must be set up from the viewer through
  "   `Settings > Editor > Custom Text Editor`.
  " The following settings should work for Vim:
  "
  "     vim --remote-silent +%l "%f"
  "
  " Or with arguably more convenient reverse goto function:
  "
  "     vim --remote-expr "vimtex#view#reverse_goto(%l, '%f')"
  "
  " Note: To perform a backward (or inverse) search in Okular,
  "   you do "shift + click",
  "   not "ctrl + click" as in most other viewers.
endif

"let g:vimtex_view_mupdf_options = ''
"let g:vimtex_view_mupdf_send_keys = ''
"let g:vimtex_view_skim_activate = 0
"let g:vimtex_view_skim_reading_bar = 1
"let g:vimtex_view_skim_zathura_options = ''

autocmd FileType tex
  \ nnoremap <buffer> <Plug>(Boni.Dispatch.Dispatch)
  \ :w<CR>:call vimtex#compiler#compile()<CR>
