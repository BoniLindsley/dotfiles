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

nnoremap <Plug>(Boni.Bookmarks)<F1>
  \ :echo 'bookmark: (l)ist (m)ark'<CR>
nnoremap <Plug>(Boni.Bookmarks)<Tab>
  \ :call BoniMapWait("\<Plug>(Boni.Bookmarks)")<CR>

nnoremap <Plug>(Boni.Bookmarks)d :call <SID>BoniBookmarksDelete()<CR>
nnoremap <Plug>(Boni.Bookmarks)l :call <SID>BoniBookmarksOpen()<CR>
nnoremap <Plug>(Boni.Bookmarks)m :call <SID>BoniBookmarksAppend()<CR>

function s:BoniBookmarksAppend()
  if -1 == s:BoniBookmarksInitialiseNetrw()
    return -1
  endif

  if &filetype ==# 'netrw'
    let l:file_path = b:netrw_curdir
  else
    let l:file_path = fnameescape(expand('%:p'))
  endif

  if l:file_path == ""
    echo 'Buffer has no path.'
    return
  endif

  let l:index = index(g:netrw_bookmarklist, l:file_path)
  if l:index == -1
    let l:index = len(g:netrw_bookmarklist)
    call add(g:netrw_bookmarklist, l:file_path)
  endif

  echo printf("%d: %s", l:index + 1, l:file_path)
endfunction

function s:BoniBookmarksDelete()
  let l:index = s:BoniBookmarksInputIndex("Delete: " )
  if l:index != -1
    call remove(g:netrw_bookmarklist, l:index)
  endif

  let l:netrwbook_path = g:netrw_home . '/.netrwbook'
  if filereadable(l:netrwbook_path)
    call delete(l:netrwbook_path)
  endif
endfunction

function s:BoniBookmarksInitialiseNetrw()
  if !exists('g:loaded_netrw')
    " Try to load bookmarks.
    " Also initialise Netrw so that bookmarks are saved on exit.
    echo 'Netrw not loaded.'
    if 'y' != input('Load with :Vexplore :q? ', 'y')
      return -1
    endif
    Vexplore
    quit
  endif
endfunction

function s:BoniBookmarksInputIndex(prompt)
  if -1 == s:BoniBookmarksInitialiseNetrw()
    return -1
  endif

  if !exists("g:netrw_bookmarklist") || len(g:netrw_bookmarklist) <= 0
    echo 'Bookmark list is empty.'
    if 'y' != input('Prepoulate? ', 'y')
      return -1
    endif
    let g:netrw_bookmarklist = [
    \ fnameescape($HOME . '/base/'),
    \ fnameescape($HOME . '/base/downloads/'),
    \ fnameescape($HOME . '/base/src/'),
    \ fnameescape($HOME . '/case/'),
    \ fnameescape($HOME . '/case/music/'),
    \ fnameescape($XDG_CONFIG_HOME),
    \ fnameescape($VIM_CONFIG_HOME . '/rc.d/'),
    \ fnameescape($XDG_CONFIG_HOME . '/emacs/init.el.d/'),
    \ fnameescape($XDG_CONFIG_HOME . '/password-store/'),
    \ fnameescape($XDG_LOCAL_HOME)
    \]
    echo ' '
  endif

  let l:input = 1
  for l:file_path in g:netrw_bookmarklist
    echo printf("%d: %s", l:input, l:file_path)
    let l:input += 1
  endfor

  let l:input = input(a:prompt, "",
    \ "customlist,g:BoniBookmarksCustomComplete")
  " Make sure to have a new line after input for other messages.
  echo ' '

  if l:input ==# ''
    let l:index = -1
  elseif l:input =~# '^\d\+$'
    let l:index = l:input - 1
    if l:index >= len(g:netrw_bookmarklist)
      echomsg 'Bookmark number not found.'
      let l:index = -1
    endif
  else
    let l:index = index(g:netrw_bookmarklist, l:input)
    if l:index == -1
      echo 'Bookmark not found.'
    endif
  endif

  return l:index
endfunction

function s:BoniBookmarksOpen()
  let l:index = s:BoniBookmarksInputIndex("Open: ")
  if l:index != -1
    execute 'edit' fnameescape(g:netrw_bookmarklist[l:index])
  endif
endfunction

function g:BoniBookmarksCustomComplete(ArgLead, CmdLine, CursorPos)
  return matchfuzzy(g:netrw_bookmarklist, a:CmdLine)
endfunction
