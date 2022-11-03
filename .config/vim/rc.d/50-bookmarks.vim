if exists('g:loaded_boni_bookmarks') || &compatible
  finish
endif
let g:loaded_boni_bookmarks = 1

if !exists('g:boni_bookmarks_default')
  let g:boni_bookmarks_default
    \ = $VIM_DATA_HOME . '/boni/bookmarks/default.txt'
endif

nnoremap <Plug>(Boni.Bookmarks)<F1>
  \ :echo 'bookmark: (d)elete (l)ist (m)ark'<CR>
nnoremap <Plug>(Boni.Bookmarks)<Tab>
  \ :call BoniMapWait("\<Plug>(Boni.Bookmarks)")<CR>

nnoremap <Plug>(Boni.Bookmarks)d :call <SID>BoniBookmarksDelete()<CR>
nnoremap <Plug>(Boni.Bookmarks)l :call <SID>BoniBookmarksOpen()<CR>
nnoremap <Plug>(Boni.Bookmarks)m :call <SID>BoniBookmarksAppend()<CR>

function s:BoniBookmarksMkdir()
  let l:directory = fnamemodify(g:boni_bookmarks_default, ":p:h")
  if !isdirectory(l:directory)
    call mkdir(l:directory, 'p')
  endif
endfunction

function s:BoniBookmarksAppend()
  if &filetype ==# 'netrw'
    let l:file_path = b:netrw_curdir
  else
    let l:file_path = fnameescape(expand('%:p'))
  endif

  if l:file_path == ""
    echo 'Buffer has no path.'
    return
  endif

  call s:BoniBookmarksMkdir()
  call writefile([l:file_path], g:boni_bookmarks_default, 'a')

  echo printf("Added bookmark: %s", l:file_path)
endfunction

function s:BoniBookmarksOpen()
  if !filereadable(g:boni_bookmarks_default)
    call s:BoniBookmarksCreate()
  endif
  call s:BoniBookmarksMkdir()
  execute 'edit' fnameescape(g:boni_bookmarks_default)
endfunction

function s:BoniBookmarksCreate()
  let l:new_entries = []
  for l:file_path in [
  \ expand($HOME . '/base'),
  \ expand($HOME . '/base/downloads'),
  \ expand($HOME . '/base/src'),
  \ expand($HOME . '/case'),
  \ expand($HOME . '/case/music'),
  \ expand($XDG_CONFIG_HOME),
  \ expand($VIM_CONFIG_HOME . '/rc.d'),
  \ expand($XDG_CONFIG_HOME . '/emacs/init.el.d'),
  \ expand($XDG_CONFIG_HOME . '/password-store'),
  \ expand($XDG_LOCAL_HOME)
  \]
    if !empty(glob(l:file_path))
      call add(l:new_entries, l:file_path)
    endif
  endfor

  call s:BoniBookmarksMkdir()
  call writefile(l:new_entries, g:boni_bookmarks_default, 'a')
endfunction
