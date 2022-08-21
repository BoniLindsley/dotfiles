if !has('python3')
  finish
endif

" Debugger building on top of Visual Studio Code adapter.
Plug 'puremourning/vimspector'

let g:vimspector_enable_mappings = 'VISUAL_STUDIO'
