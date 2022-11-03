" # Built-in Netrw
"
" Netrw is the default directory explorer in Vim.
" Netrw is necessary to open files via scp in Vim.
"
" The default netrw buffer mapping is in `:h netrw-browse-maps`
" The following is a copy.
"
" | Mapping | Description                             | Help            |
" | ------- | --------------------------------------- | --------------- |
" | <F1>    | Show help                               | netrw-quickhelp |
" | <cr>    | Read file or enter directory            | netrw-cr        |
" | <del>   | Remove the file or directory            | netrw-del       |
" | <c-h>   | Edit file hiding list                   | netrw-ctrl-h    |
" | <c-l>   | Refresh                                 | netrw-ctrl-l    |
" | <c-r>   | Browse using a gvim server              | netrw-ctrl-r    |
" | <c-tab> | Shrink or expand window                 | netrw-c-tab     |
" | -       | Go up one directory                     | netrw--         |
" | a       | Show all, filtered or hidden files      | netrw-a         |
" | cd      | Change $CD to browsing directory        | netrw-cd        |
" | C       | Setting the editing window              | netrw-C         |
" | d       | Make directory                          | netrw-d         |
" | D       | Remove file(s) and directory(ies)       | netrw-D         |
" | gb      | Go to previous bookmarked directory     | netrw-gb        |
" | gd      | Force treatment as directory            | netrw-gd        |
" | gf      | Force treatment as file                 | netrw-gf        |
" | gh      | Quick hide/unhide of dot-files          | netrw-gh        |
" | gn      | Browse from directory below the cursor  | netrw-gn        |
" | i       | Use thin, long, wide or tree listings   | netrw-i         |
" | I       | Toggle the displaying of the banner     | netrw-I         |
" | mb      | Bookmark current directory              | netrw-mb        |
" | mc      | Copy `mf` file to `mt` directory        | netrw-mc        |
" | md      | Apply diff to marked files (up to 3)    | netrw-md        |
" | me      | Place `mf` on arg list and edit them    | netrw-me        |
" | mf      | Mark file; add to `mf`                  | netrw-mf        |
" | mF      | Umark file; remove from `mf`            | netrw-mF        |
" | mg      | Apply vimgrep to marked files           | netrw-mg        |
" | mh      | Hide or show files with `mf` suffices   | netrw-mh        |
" | mm      | Move `mf` file to `mt` directory        | netrw-mm        |
" | mp      | Print marked files                      | netrw-mp        |
" | mr      | Set `mf` using shell-style regexp       | netrw-mr        |
" | mt      | Use browsing directory as `mt`          | netrw-mt        |
" | mT      | Apply ctags to marked files             | netrw-mT        |
" | mu      | Unmark all marked files                 | netrw-mu        |
" | mv      | Run vim command to `mf` files           | netrw-mv        |
" | mx      | Run `command mf` in shell for each `mf` | netrw-mx        |
" | mX      | Run `command mf1 mf2 ...` in shell      | netrw-mX        |
" | mz      | Compress or decompress marked files     | netrw-mz        |
" | o       | Enter in new horizontal-split window.   | netrw-o         |
" | O       | Obtain a file specified by cursor       | netrw-O         |
" | p       | Preview the file                        | netrw-p         |
" | P       | Browse in the previously used window    | netrw-P         |
" | qb      | List bookmark and history               | netrw-qb        |
" | qf      | Display information on file             | netrw-qf        |
" | qF      | Mark files using a quickfix list        | netrw-qF        |
" | qL      | Mark files using a location-list        | netrw-qL        |
" | r       | Reverse sorting order                   | netrw-r         |
" | R       | Rename prompted files                   | netrw-R         |
" | s       | Sort by name, time, or file size        | netrw-s         |
" | S       | Change suffix sorting priority          | netrw-S         |
" | t       | Enter in a new tab                      | netrw-t         |
" | u       | Browse last-visited directory           | netrw-u         |
" | U       | Browse next-visited directory           | netrw-U         |
" | v       | Enter in new vertical split.            | netrw-v         |
" | x       | Open file with special handler          | netrw-x         |
" | X       | Execute file via system()               | netrw-X         |
" | %       | Open a prompted file                    | netrw-%         |

" Netrw is built-in.
" So there are no official options to disable it.
" One way to to disable the plugin entirely is pretend it is loaded,
" so that it will not be loaded after `vimrc` is read.
"" let g:loaded_netrw = 1
"" let g:loaded_netrwPlugin = 1

if &compatible
  throw 'Boni(Netrw):Netrw requires &nocompatible'
endif

if version >= 600
  filetype plugin indent on
endif

" Whether to disable scp file transfer confirmations.
if has('win32')
  let g:netrw_silent = 1
endif

" Disable status list on top.
"let g:netrw_banner = 1
let g:netrw_banner = 0

" Settings netrw buffers have.
"let g:netrw_bufsettings = 'noma nomod nonu nowrap ro nobl'
" Preserve default / user numbering setting.
let g:netrw_bufsettings = ''
let g:netrw_bufsettings .= ' nobuflisted'
let g:netrw_bufsettings .= ' nomodifiable'
let g:netrw_bufsettings .= ' nomodified'
let g:netrw_bufsettings .= ' nowrap'
let g:netrw_bufsettings .= ' readonly'

" Do not cache directory listing.
"let g:netrw_fastbrowse = 1
let g:netrw_fastbrowse = 0

" Directory containing the `.netrwbook` bookmark file,
" and the `.netrwhist` history list.
"unlet! g:netrw_home
let g:netrw_home = $VIM_DATA_HOME . '/netrw'

" 0: Change current directory to browsing directory while browsing.
" 1: Default. Current directory does not change.
" Picking 0 makes moving and copying files much easier.
" However, that can get bothersome for linting
" that requires a correct current directory.
"let g:netrw_keepdir = 1

" One file per line.
"let g:netrw_liststyle = 0

" Hit enter in the file browser
" to open the selected file with :vsplit
" to the right of the browser.
" Reference: https://stackoverflow.com/a/5636941
"" let g:netrw_browse_split = 4
"" let g:netrw_altv = 1

" Show error message in a separate window
" instead of a popup that may not disappear by itself.
" If any commands shows a popup window,
" use `:call popup_clear(1)` to remove it.
"let g:netrw_use_errorwindow = 2
let g:netrw_use_errorwindow = 1

" Do not list netrw in :bn etc.
autocmd FileType netrw setlocal buflisted

" Netrw can be 'buggy'.
" In particular, if `set hidden` is used,
" its directory buffers remains in the buffer list (:ls)
" even after being closed.
" This gets in the way of toggling between buffers.
" One way to mitigate it is to enable `hidden`
" for all other file types instead in autocommand.
" However, it also seems to stop quickfix windows from closing.
" Reference: https://github.com/tpope/vim-vinegar/issues/13
"" autocmd FileType netrw setl bufhidden=unload
"" augroup netrw_buf_hidden_fix
""   autocmd!
""   " Set all non-netrw buffers to bufhidden=hide
""   autocmd BufWinEnter *
""           \  if &ft != 'netrw'
""           \|     set bufhidden=hide
""           \| endif
"" augroup end
