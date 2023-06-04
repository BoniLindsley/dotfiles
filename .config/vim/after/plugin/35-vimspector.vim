" # vimspector

" Upstream: https://github.com/puremourning/vimspector
" Introduction: `:help vimspector`
" Reference: `:help vimspector-ref`

if !exists( 'g:loaded_vimpector' )
  finish
endif

" This check should not be necessary
" since Vimspector checks for it too.
" But do it anyway just to be safe.
if !has('python3')
  finish
endif

" Use `:VimspectorUpdate` to install debug adapters.
" To see available adapters, use `:VimspectorInstall`
" and then `C-d` or tab completion.
let g:vimspector_install_gadgets = [ 'debugpy' ]

nnoremap <Plug>(Boni.Vimspector)<F1> :echo
\ 'vimspector: ( ) launch (q)uit (r)eset (s)tack (v)ar (w)atch (c-h)elp'
\<CR>
nnoremap <Plug>(Boni.Vimspector)<Tab>
\ :call BoniMapWait("\<Plug>(Boni.Vimspector)")<CR>
" Start last known launch settings.
nmap <Plug>(Boni.Vimspector)<Space> <Plug>VimspectorRestart<CR>
" Stop current launch.
nnoremap <Plug>(Boni.Vimspector)q :VimspectorReset<CR>
" Start and ask for new launch settings.
nmap <Plug>(Boni.Vimspector)r <Plug>VimspectorLaunch<CR>

nnoremap <Plug>(Boni.Vimspector)b :VimspectorBreakpoints<CR><Plug>(Boni.Vimspector)
nnoremap <Plug>(Boni.Vimspector)s
  \ :sbuffer vimspector.StackTrace<CR><Plug>(Boni.Vimspector)
nnoremap <Plug>(Boni.Vimspector)v
  \ :sbuffer vimspector.Variables<CR><Plug>(Boni.Vimspector)
nnoremap <Plug>(Boni.Vimspector)w
  \ :sbuffer vimspector.Watches<CR><Plug>(Boni.Vimspector)
nnoremap <Plug>(Boni.Vimspector)<C-h> :echo
\ 'F5:Cont F6:Pause F9:Break F10:Over F11:Into'
\<CR>

nmap <Plug>(Boni.Vimspector)3           <F3><Plug>(Boni.Vimspector)
nmap <Plug>(Boni.Vimspector)4           <F4><Plug>(Boni.Vimspector)
nmap <Plug>(Boni.Vimspector)5           <F5><Plug>(Boni.Vimspector)
nmap <Plug>(Boni.Vimspector)55        <S-F5><Plug>(Boni.Vimspector)
nmap <Plug>(Boni.Vimspector)555      <C-S-5><Plug>(Boni.Vimspector)
nmap <Plug>(Boni.Vimspector)25  <Leader><F5><Plug>(Boni.Vimspector)
nmap <Plug>(Boni.Vimspector)6           <F6><Plug>(Boni.Vimspector)
nmap <Plug>(Boni.Vimspector)7           <F7><Plug>(Boni.Vimspector)
nmap <Plug>(Boni.Vimspector)8           <F8><Plug>(Boni.Vimspector)
nmap <Plug>(Boni.Vimspector)28  <Leader><F8><Plug>(Boni.Vimspector)
nmap <Plug>(Boni.Vimspector)9           <F9><Plug>(Boni.Vimspector)
nmap <Plug>(Boni.Vimspector)99        <S-F9><Plug>(Boni.Vimspector)
nmap <Plug>(Boni.Vimspector)29  <Leader><F9><Plug>(Boni.Vimspector)
nmap <Plug>(Boni.Vimspector)0          <F10><Plug>(Boni.Vimspector)
nmap <Plug>(Boni.Vimspector)-          <F11><Plug>(Boni.Vimspector)
nmap <Plug>(Boni.Vimspector)--       <S-F11><Plug>(Boni.Vimspector)
nmap <Plug>(Boni.Vimspector)+          <F12><Plug>(Boni.Vimspector)

function! BoniTestStrategyVimspector(cmd) abort
  let settings = {}
  let settings['args'] = split(a:cmd)[-1]
  let settings['configuration'] = 'debugpy - module'
  let position = g:test#last_position
  let runner = test#determine_runner(position['file'])
  let runner_modules = {
  \ 'python#pytest': 'pytest',
  \ 'python#pyunit': 'unittest',
  \}
  let settings['module'] = runner_modules[runner]
  call vimspector#LaunchWithSettings(settings)
endfunction

" Customise vim-test if that is installed.
if exists('g:loaded_test')
  let g:test#custom_strategies['vimspector'] = function(
  \ 'BoniTestStrategyVimspector'
  \)
endif

function! s:CustomiseUI()
  call win_gotoid(g:vimspector_session_windows.code)
  only
endfunction

augroup MyVimspectorUICustomistaion
  autocmd!
  autocmd User VimspectorUICreated call s:CustomiseUI()
  "autocmd User VimspectorTerminalOpened call s:SetUpTerminal()
augroup END
