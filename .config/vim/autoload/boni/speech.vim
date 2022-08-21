if exists('loaded_boni_speech')
  finish
endif
let loaded_boni_speech=1

function g:boni#speech#init()
  if !has('python3')
    echomsg 'speech requires Python support. Not found.'
    return
  endif
  try
    py3 import boni.speech
  catch /^Vim(py3):ModuleNotFoundError:/
    echomsg 'speech requires Python speechd library. Not found.'
    return
  endtry
  call g:boni#speech#map#init()
  py3 boni.speech.client.speak("Vimspeak is ready.")
endfunction

autocmd CursorMoved * py3 boni.speech.on_cursor_moved()
autocmd CursorMovedI * py3 boni.speech.on_cursor_moved_insert()
