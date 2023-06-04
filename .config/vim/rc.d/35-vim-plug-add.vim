" Make sure you use single quotes

" " Format code with one button press.
" Plug 'Chiel92/vim-autoformat'

"" " NERD tree will be loaded on the first invocation
"" "   of NERDTreeToggle command
"" Plug 'scrooloose/nerdtree', { 'on': 'NERDTreeToggle' }

"" " Reference: http://vim-latex.sourceforge.net/
"" Plug 'vim-latex/vim-latex'

" Force `.tex` file type to be loaded as`latex` instead of `plaintex`.
" This allows small `\include` files to be detected as `latex` files.
let g:tex_flavor = "latex"
" A modern vim plugin for editing LaTeX files.
Plug 'lervag/vimtex'

"" " Macros for making Markdown documents.
"" Plug 'vimwiki/vimwiki'

" Asynchronous build and test dispatcher.
Plug 'tpope/vim-dispatch'

" Shows a git diff in the 'gutter'
Plug 'airblade/vim-gitgutter'

" Git wrapper
Plug 'tpope/vim-fugitive'

"" " Conque GDB
"" Plug 'vim-scripts/Conque-GDB'

"" " TaskWarrior TUI
"" Plug 'blindFS/vim-taskwarrior'

"" EditorConfig Plugin for vim
"" The config files are not really used much.
"" There might be an ALE plugin for it, which is better
"" as an explicit way of triggering formatting.
"Plug 'editorconfig/editorconfig-vim'

" Commands for working with CMake projects.
Plug 'https://github.com/vhdirk/vim-cmake.git'

" CMake Integration with CtrlP, vim-dispatch and Vimspector.
Plug 'https://github.com/ilyachur/cmake4vim.git'

" Vim fuzzy finder.
Plug 'ctrlpvim/ctrlp.vim'

" Vimscript testing.
Plug 'junegunn/vader.vim'

" Run tests depending on context.
Plug 'vim-test/vim-test'

" Project management.
Plug 'tpope/vim-projectionist'

"" netrw extension.
"Plug 'https://github.com/tpope/vim-vinegar.git'

"" Run static checker.
"" Syntastic is blocking.
"" Disabled in favour of ALE which is an asynchronous LSP linter.
"Plug 'https://github.com/vim-syntastic/syntastic.git'

""" Pass texts to eSpeak.
""" Using a local copy since upstream is buggy.
""Plug 'ddevault/vimspeak'

" " Easier keymap and some speech-dispatcher support.
"
" " The speak package sort of works.
" " Uses `spd-say` to call separately.
" " No insert mode character or word echo.
" " Some default keymaps do not work in terminal.
" Plug 'https://github.com/luffah/vim-accessibility.git'

" Using git URL
" Plug 'https://github.com/junegunn/vim-github-dashboard.git'

" Plugin options
" Plug 'nsf/gocode', { 'tag': 'v.20150303', 'rtp': 'vim' }

" Plugin outside ~/.vim/plugged with post-update hook
" Plug 'junegunn/fzf', { 'dir': '~/.fzf', 'do': 'yes \| ./install' }

" Unmanaged plugin (manually installed and updated)
" Plug '~/my-prototype-plugin'

" Walyand support. Requires wl-clipboard.
Plug 'https://github.com/jasonccox/vim-wayland-clipboard.git'

" Visual undo tree.
Plug 'sjl/gundo.vim'

" GPG file extension.
Plug 'jamessan/vim-gnupg'

" Todo.txt
Plug 'https://github.com/freitass/todo.txt-vim.git'

" Interactive scratchpad
Plug 'https://github.com/metakirby5/codi.vim.git'

" Interactve with Jupyter.
Plug 'https://github.com/jupyter-vim/jupyter-vim.git'

" Word substitutions.
Plug 'https://github.com/tpope/vim-abolish.git'

" Base16 colour themes.
Plug 'https://github.com/chriskempson/base16-vim.git'
