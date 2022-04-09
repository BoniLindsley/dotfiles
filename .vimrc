let $VIM_PWD = getcwd()

if !has_key(environ(), 'HOME')
  if index(keys(environ()), 'UserProfile', 0, 1) != -1
    let $HOME = escape($UserProfile, ' ')
  endif
endif

if !has_key(environ(), 'XDG_CONFIG_HOME')
  let $XDG_CONFIG_HOME = $HOME . '/.config'
endif

if !has_key(environ(), 'XDG_LOCAL_HOME')
  if has('win32')
    let $XDG_LOCAL_HOME = escape($LocalAppData, ' ') . '/xdg.local'
  else
    let $XDG_LOCAL_HOME = $HOME
  endif
endif
if !has_key(environ(), 'XDG_CACHE_HOME')
  if has('win32')
    let $XDG_CACHE_HOME = $XDG_LOCAL_HOME . '/cache'
  else
    let $XDG_CACHE_HOME = $HOME . '/.cache'
  endif
endif
if !has_key(environ(), 'XDG_DATA_HOME')
  let $XDG_DATA_HOME = $XDG_LOCAL_HOME . '/share'
endif
if !has_key(environ(), 'XDG_LIB_HOME')
  let $XDG_LIB_HOME = $XDG_LOCAL_HOME . '/lib'
endif
if !has_key(environ(), 'XDG_STATE_HOME')
  let $XDG_STATE_HOME = $XDG_LOCAL_HOME . '/state'
endif

" For files that may be deleted to 'factory reset' an application.
let $VIM_CONFIG_HOME = $XDG_CONFIG_HOME . '/vim'

" For files that may be deleted
" to pretend the application was not used before...
let $VIM_DATA_HOME = $XDG_DATA_HOME . '/vim'

" Files that should be removed when uninstalling.
let $VIM_LIB_HOME = $XDG_LIB_HOME . '/vim'

" Stores runtime customisation and information.
let $VIM_STATE_HOME = $XDG_STATE_HOME . '/vim'

let $VIM_TMPDIR_HOME = $XDG_LOCAL_HOME . '/tmp/vim'

" The first path given in option `&runtimepath` is used as default
" for creating directories.
" Prepends path for priority, and escapes in case there is spaces.
execute 'set runtimepath ^=' . fnameescape($VIM_STATE_HOME)

" Every path in option `&runtimepath` is used
" when searching for `autoload`, ftdetect`, `plugin`, etc.
" Append config files to be searched by Vim.
" In particular, note that `*.vim` files recursively searched
" in the `plugin` subdirectory of each directory listed in `&runtimepath`
" will be sourced by Vim after `vimrc` is searched.
execute 'set runtimepath +=' . fnameescape($VIM_CONFIG_HOME)

" Source every file in a `vimrc.d` directory.
" External plugins, such as those managed by `vim-plug`
" may rely on having their `plugin` directories sourced.
" If the paths to those plugins are only added
" inside other `plugin` " files,
" then the files inside the `plugin` directory of those plugins
" would not be ran.
" So some scripts must be loaded here,
" instead of relying on the `plugin` directory.
for filepath in split(glob($VIM_CONFIG_HOME . '/rc.d/*.vim'), '\n')
  execute 'source ' . fnameescape(filepath)
endfor
