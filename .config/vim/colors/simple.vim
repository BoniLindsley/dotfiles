" Change all colours back to default before adding settings.
highlight clear
syntax reset

let g:colors_name = 'simple'

" Use a 'dark background' in GUI mode.
"highlight clear Normal
if &background == 'dark'
  highlight Normal guifg=White guibg=Black
endif

"highlight Comment term=bold ctermfg=4 guifg=Blue

"highlight Constant term=underline ctermfg=1 guifg=Magenta
"highlight link String         Constant
"highlight link Character      Constant
"highlight link Number         Constant
"highlight link Boolean        Constant
"highlight link Float          Number

"highlight Identifier term=underline ctermfg=6 guifg=DarkCyan
"highlight link Function Identifier

"highlight Statement term=bold                  gui=bold
"                            \ ctermfg=130    guifg=Brown
"highlight link Conditional Statement
"highlight link Repeat      Statement
"highlight link Label       Statement
"highlight link Operator    Statement
"highlight link Keyword     Statement
"highlight link Exception   Statement
"
"highlight PreProc term=underline ctermfg=5 guifg=#6a0dad
"highlight link Include        PreProc
"highlight link Define         PreProc
"highlight link Macro          PreProc
"highlight link PreCondit      PreProc

"highlight Type term=underline             gui=bold
"                            \ ctermfg=2 guifg=SeaGreen
"highlight link StorageClass Type
"highlight link Structure    Type
"highlight link Typedef      Type

"highlight Special term=bold ctermfg=5 guifg=#6a5acd
"highlight link Tag            Special
"highlight link SpecialChar    Special
"highlight link Delimiter      Special
"highlight link SpecialComment Special
"highlight link Debug          Special

"highlight Underlined term=underline   cterm=underline   gui=underline
"                                  \ ctermfg=5         guifg=SlateBlue
"highlight Ignore ctermfg=White guifg=bg
"highlight Error term=reverse ctermfg=White guifg=White
"                             ctermbg=Blue  guibg=Red
"highlight Todo term=standout ctermfg=Black guifg=Blue
"                           \ ctermbg=Cyan  guibg=Yellow
