" vim-dispatch
"
" Upstream: https://github.com/tpope/vim-dispatch

if !exists("g:loaded_dispatch")
  finish
endif

" Disable default hotkey maps.
"let g:dispatch_no_maps = 0
let g:dispatch_no_maps = 1

" How to run jobs.
"let g:dispatch_handlers = [
"  \ 'tmux', 'job', 'screen', 'windows', 'iterm', 'x11', 'headless']
let g:dispatch_handlers = [
  \ 'job', 'tmux', 'screen', 'windows', 'iterm', 'x11', 'headless']

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
\ 'vim-dispatch: (space) Dispatch (s)tart
\<CR>
nnoremap <Plug>(Boni.Dispatch)<Tab>
\ :call BoniMapWait("\<Plug>(Boni.Dispatch)")<CR>
nmap <Plug>(Boni.Dispatch)<Space> <Plug>(Boni.Dispatch.Dispatch)
nnoremap <Plug>(Boni.Dispatch.Dispatch) :Dispatch<CR>
" The :Start command can only be started once.
nnoremap <Plug>(Boni.Dispatch)s :Dispatch <C-R>=b:start<CR><CR>
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
