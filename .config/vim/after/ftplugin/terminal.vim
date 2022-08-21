if exists("b:did_ftplugin")
  finish
endif
let b:did_ftplugin = 1

let b:undo_ftplugin = "setlocal wrap<"
\ . "| unlet b:match_ignorecase b:match_words b:match_skip"

setlocal nowrap
