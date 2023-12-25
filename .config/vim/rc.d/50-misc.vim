" Copy indentation to new lines.
"set noautoindent
set autoindent

" BAckspace over indent, new lines, and start of insert.
"set backspace=''
set backspace=eol,indent,start

" Move `.swp` files.
let s:backup_directory = $VIM_DATA_HOME . '/backup'
let &backupdir = fnameescape(s:backup_directory) . '//'
if !isdirectory(s:backup_directory)
  call mkdir(s:backup_directory, 'p')
endif

" Highlight wrapped column.
set colorcolumn=+1
"highlight CursorColumn term=reverse ctermbg=242 guibg=Grey40
highlight ColorColumn cterm=reverse gui=reverse

" Move `.swp` files.
let s:swap_directory = $VIM_DATA_HOME . '/swp'
let &directory = s:swap_directory . '//'
if !isdirectory(s:swap_directory)
  call mkdir(s:swap_directory, 'p')
endif

" End the last line with @@@ if it is too long.
"set display=''
set display=lastline

" Default encoding for display.
"set encoding=utf-8 or $LANG or latin1
set encoding=utf-8

" Insert space instead when tab is inserted.
"set noexpandtab
set expandtab

" Default encoding written to file.
"set fileencoding=""
set fileencoding=utf-8

" Remove comment leader with joining comment lines.
"set formatoptions=tcq
set formatoptions+=j

" Jump to and highlight searches as they are typed.
"set noincsearch
set incsearch

" Do not force insert EOL before EOF.
"set fixendofline
silent! set nofixendofline

" Disable folding by default.
" It increases loading time and not necessarily used.
"set foldenable
set nofoldenable

" Additional flags for grep.
if !has('win32')
  "set grepprg='grep -n '
  let &grepprg = 'grep '
  let &grepprg .= '--color=auto '
  let &grepprg .= '--exclude-dir=.git '
  let &grepprg .= '--exclude-dir=.mypy_cache '
  let &grepprg .= '--exclude-dir=.pytest_cache '
  let &grepprg .= '--exclude-dir=.vscode '
  let &grepprg .= '--exclude-dir=\*.egg-info '
  let &grepprg .= '--exclude-dir=__pycache__ '
  let &grepprg .= '--exclude=tags '
  let &grepprg .= '--ignore-case '
  let &grepprg .= '--line-number '
  let &grepprg .= '--recursive '
  let &grepprg .= '-I '
endif

" Allow unsaved buffers to be hidden.
"set nohidden
set hidden

" Highlight matched search groups by default.
"set nohlsearch
set hlsearch

" Always show status line isntead of only for multiple windows.
"set laststatus=1
set laststatus=2

" Determine how space characters are shown if shown.
"set lcs=eol:$
set listchars=tab:>\ ,trail:-,extends:>,precedes:<,nbsp:+,eol:$

" Show some control characters.
"set nolist
set list

" Disable modeline -- comments in file seen as commands to execute.
"set modeline
set nomodeline

" Show relative line number. Useful for motions.
" set norelativenumber
set relativenumber

" Minimum Number of buffer lines to display between the top and bottom of a window.
"set ncrolloff=0
set scrolloff=1

" Width of indentation. Uses tabstop value if 0.
" Older versions did not have the zero behaviour.
"set shiftwidth=8
try
  set shiftwidth=0
catch /^Vim\%((\a\+)\)\=:E487:/
  set shiftwidth=2
endtry

" Minimum Number of buffer lines to display between the top and bottom of a window.
"set sidescroll=0

" Number of spaces for a tab character. Affects view and expand.
"set tabstop=8
set tabstop=2

" Recursively search parent directories for tags files.
"set tags=./tags,tags
setglobal tags-=./tags
setglobal tags-=tags
setglobal tags-=./TAGS
setglobal tags-=TAGS
setglobal tags^=TAGS;/
setglobal tags^=tags;/


" Word wrapping at column 74.
"set textwidth=0
set textwidth=73

" Timeout duration when waiting for the next key in mappings.
"set timeoutlen=100

" Allow timeout on terminal key codes to process `Esc` key.
"set nottimeout
set ttimeout

" Small timeout on terminal key codes to process `Esc` key.
" Negative means to use `timeoutlen` which is for mapping.
"set ttimeoutlen=-1
set ttimeoutlen=100

" Allow tab completion in macros and maps.
"set wildcharm=0
set wildcharm=<C-I>

" Use completion in command line.
"set nowildmenu
set wildmenu

" No visual wrapping of lines longer than the window is wide.
"set wrap
set nowrap

" Make sure the font supports unicode.
if has('win32')
  set guifont=Lucida\ Console:h9
endif

" Set encryption method used when saving.
" Use `:X` to enter a key, which then enables encryption.
" Use `:set key=` to reset the key, which disables encryption.
" Changing the `key` does not change
" whether a stored file is encrypted or decrypted.
" Save (for example with `:w`) to apply the new setting
silent! set cryptmethod=blowfish2


" Text insertion
" ==============
nnoremap <leader>PTT :put =strftime('%Y-%m-%d %H:%M:%S')<CR>
" ISO-8601 format current time
nnoremap <leader>PTI :put =strftime('%FT%T%z')<CR>
nnoremap <leader>PTi :put =strftime('%Y%m%dT%H%M%SZ')<CR>

" Remembering runtime data such as history between sessions
" =======
" Move viminfo file, that is usually in `$HOME/.viminfo`
" into the run directory.
" The `n` flag is followed by the path of viminfo file to use.
" Use a subdirectory to contain the files.
" It can litter copies if there is a race condition to save data.
let s:viminfo_path = $VIM_DATA_HOME . '/viminfo.d/viminfo'
execute "set viminfo +=" . 'n' . escape(s:viminfo_path, '\ ')
let s:viminfo_directory = fnamemodify(s:viminfo_path, ':p:h')
if !isdirectory(s:viminfo_directory)
  call mkdir(s:viminfo_directory, 'p')
endif
