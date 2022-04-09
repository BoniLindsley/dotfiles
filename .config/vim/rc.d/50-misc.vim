" Copy indentation to new lines.
"set noautoindent
set autoindent

" Move `.swp` files.
let s:backup_directory = $VIM_DATA_HOME . '/backup'
let &backupdir = s:backup_directory . '//'
call mkdir(s:backup_directory, 'p')

" Highlight wrapped column.
set colorcolumn=+1
highlight ColorColumn ctermbg=darkgray

" Move `.swp` files.
let s:swap_directory = $VIM_DATA_HOME . '/swp'
let &directory = s:swap_directory . '//'
call mkdir(s:swap_directory, 'p')

" Default encoding for display.
"set encoding=utf-8 or $LANG or latin1
set encoding=utf-8

" Insert space instead when tab is inserted.
"set noexpandtab
set expandtab

" Default encoding written to file.
"set fileencoding=""
set fileencoding=utf-8

" Do not force insert EOL before EOF.
"set fixendofline
set nofixendofline

" Disable folding by default.
" It increases loading time and not necessarily used.
"set foldenable
set nofoldenable

" Additional flags for grep.
"set grepprg='grep -n '
let &grepprg = 'grep '
let &grepprg .= '--color=auto '
let &grepprg .= '--ignore-case '
let &grepprg .= '--line-number '
let &grepprg .= '--recursive '
let &grepprg .= '-I '

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

" Size of an indent
"set shiftwidth=8
set shiftwidth=2

" Number of spaces for a tab character. Affects view and expand.
"set tabstop=8
set tabstop=2

" Word wrapping at column 74.
"set textwidth=0
set textwidth=73

" Allow tab completion in macros and maps.
"set wildcharm=0
set wildcharm=<C-I>

" No visual wrapping of lines longer than the window is wide.
"set wrap
set nowrap

" Make sure the font supports unicode.
if has('win32')
  set guifont=Lucida_Console:h9
endif

" Set encryption method used when saving.
" Use `:X` to enter a key, which then enables encryption.
" Use `:set key=` to reset the key, which disables encryption.
" Changing the `key` does not change
"   whether a stored file is encrypted or decrypted.
" Save (for example with `:w`) to apply the new setting
set cryptmethod=blowfish2


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
call mkdir(fnamemodify(s:viminfo_path, ':p:h'), 'p')