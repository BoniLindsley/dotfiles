" # vim-dispatch
" Upstream: https://github.com/tpope/vim-dispatch

" Disable default hotkey maps.
"let g:dispatch_no_maps = 0
let g:dispatch_no_maps = 1

" How to run jobs.
"let g:dispatch_handlers = [
"  \ 'tmux', 'job', 'screen', 'windows', 'iterm', 'x11', 'headless']
let g:dispatch_handlers = [
  \ 'job', 'tmux', 'screen', 'windows', 'iterm', 'x11', 'headless']

let g:boni_markdown_html_output = $VIM_TMPDIR_HOME . '/%:t:r.html'
autocmd FileType markdown let b:dispatch =
  \ g:boni_python . ' -m markdown'
  \ . ' -x fenced_code'
  \ . ' -x tables'
  \ . ' --output_format=html'
  \ . ' --file=' . g:boni_markdown_html_output . ' "%:p"'
autocmd FileType markdown let b:start =
  \ g:boni_browser . ' "file:///' . g:boni_markdown_html_output . '"'

if executable('fpm')
  autocmd FileType fortran let b:dispatch = 'fpm build'
  autocmd FileType fortran let b:start = 'fpm run'
endif

" autocmd FileType cpp let b:dispatch = 'boni-cmake'
"                                       \ . ' --command cmake'
"                                       \ . ' --command build'
"                                       \ . ' --command install'
" autocmd FileType cpp let b:start = 'boni-cmake --command run'

let g:boni_cmake_script_path = $HOME . '\base\bin\boni-cmake.cmake'
let g:boni_cmake_script_command = 'cmake -P ' . g:boni_cmake_script_path
let g:boni_msvc_path = 'C:\Program Files (x86)\Microsoft Visual Studio'
  \ . '\2019\Community\VC\Tools\MSVC\14.24.28314\bin\Hostx64\x64'
let g:boni_vs_env_path = 'C:\Program Files (x86)\Microsoft Visual Studio'
  \ . '\2019\Community\Common7\Tools\VsDevCmd.bat'

nnoremap <Plug>(Boni.Dispatch)<F1> :echo
\ 'vim-dispatch: (space) Dispatch! (c) Copen (f) Dispatch (m) Make'
\<CR>
nnoremap <Plug>(Boni.Dispatch)<Tab>
\ :call BoniMapWait("\<Plug>(Boni.Dispatch)")<CR>
nmap <Plug>(Boni.Dispatch)<Space> <Plug>(Boni.Dispatch.Dispatch)
nnoremap <Plug>(Boni.Dispatch.Dispatch) :w<CR>:Dispatch<CR>
nnoremap <Plug>(Boni.Dispatch)c :w<CR>:Dispatch!<CR>
nmap <Plug>(Boni.Dispatch)F <Plug>(Boni.Dispatch.Config)
nnoremap <Plug>(Boni.Dispatch)l :Copen<CR>
nnoremap <Plug>(Boni.Dispatch)m :w<CR>:Make<CR>
nnoremap <Plug>(Boni.Dispatch)S :w<CR>:Start!<CR>
nnoremap <Plug>(Boni.Dispatch)? :let b:dispatch<CR>

nnoremap <Plug>(Boni.Dispatch.Config)<F1>
\ :echo 'Set b:dispatch:'
\ . ' ( ) custom (c) CMake (m)ake (r) file (t)est'<CR>
nnoremap <Plug>(Boni.Dispatch.Config)<Tab>
\ :call BoniMapWait("\<Plug>(Boni.Dispatch.Config)")<CR>
nnoremap <Plug>(Boni.Dispatch.Config)<Space> :let b:dispatch = ''<Left>
nnoremap <Plug>(Boni.Dispatch.Config)c
\ :let b:dispatch = g:boni_cmake_script_command<CR>
\:echo 'Set b:dispatch: (c) CMake'<CR>
nmap <Plug>(Boni.Dispatch.Config)C <Plug>(Boni.Dispatch.Config.CMake)
nnoremap <Plug>(Boni.Dispatch.Config)m :let b:dispatch = 'make'<CR>
nnoremap <Plug>(Boni.Dispatch.Config)r :let b:dispatch = '%:p'<CR>
nnoremap <Plug>(Boni.Dispatch.Config.CMake)<F1> :echo
\ 'Set b:dispatch CMake: Set target to (m) MinGW64 (v) MSVC'<CR>
nnoremap <Plug>(Boni.Dispatch.Config.CMake)<Tab>
\ :call BoniMapWait("\<Plug>(Boni.Dispatch.Config.CMake)")<CR>
nnoremap <Plug>(Boni.Dispatch.Config.CMake)m
\ :let b:dispatch = g:boni_vs_env_path
\ . " && " . g:boni_cmake_script_command<CR>
\:echo 'Set b:dispatch CMake: Target set to (m) MinGW64'<CR>
nnoremap <Plug>(Boni.Dispatch.Config.CMake)v
\ :let $PATH = g:boni_msvc_path . ";" . g:boni_path<CR>
\:let b:dispatch = g:boni_cmake_script_command<CR>
\:echo 'Set b:dispatch CMake: Target set to (v) MSVC'<CR>
