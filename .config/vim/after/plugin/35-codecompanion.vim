" orgmode
"
" Upstream: https://github.com/nvim-orgmode/orgmode
"

if !has('nvim')
  finish
endif

try
  lua require('codecompanion')
catch /^Vim\%((\a\+)\)\=:E5108:/
  finish
endtry

lua << EOF

require('codecompanion').setup()
