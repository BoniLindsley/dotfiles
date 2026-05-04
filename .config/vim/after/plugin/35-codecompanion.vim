if !has('nvim')
  finish
endif

try
  lua require('codecompanion')
catch /^Vim\%((\a\+)\)\=:E5108:/
  finish
endtry

lua << EOF
codecompanion_setup = {
  opts = {
    log_level = "DEBUG", -- or "TRACE"
  }
}
EOF
