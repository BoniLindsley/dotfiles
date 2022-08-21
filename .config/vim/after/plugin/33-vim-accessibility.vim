" # vim-accessibility

" Upstream: https://github.com/luffah/vim-accessibility

" KeyMap package works pretty well. GPL3 licensed.

" The speak package sort of works.
" Uses `spd-say` to call separately.
" No insert mode character or word echo.
" Some default keymaps do not work in terminal.

if !exists('g:loaded_accessibility_keymap')
  finish
endif

let g:enable_accessibility_speak = 1

"call KeyMap#Map('Description', keys, action, modes)
call KeyMap#Map(
\  'Boni.Application' ,
\  ['<Plug>(Boni)a'],
\ '<Layer><Plug>(Boni.Application)' ,
\  ['~n']
\)

call KeyMap#Map(
\  'Boni.Application:Speak' ,
\  ['s'],
\  '<ExitLayer>'
\  . ':call speak#enable(1)<CR>'
\  . ":call KeyMap#ToggleLayer('~Speak')<CR>",
\  ['n']
\)

call KeyMap#Map(
\  '~Speak' ,
\  ['<Plug>(Boni.Speak.Layer)'],
\ "<Layer>",
\  ['n']
\)

call KeyMap#Map(
\  '~Speak:Refresh' ,
\  ['<C-l>'],
\ '<C-o>:SpeakLine<CR>'
\  . '<C-o>:redraw!<CR>',
\  ['i']
\)

call KeyMap#Map(
\  '~Speak:Refresh' ,
\  ['<C-l>'],
\ ':SpeakLine<CR>'
\  . ':redraw!<CR>',
\  ['n']
\)
