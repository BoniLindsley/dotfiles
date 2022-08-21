if exists('loaded_boni_speech_map')
  finish
endif
let loaded_boni_speech_map=1

function g:boni#speech#map#init()
  :
endfunction

if !has('python3')
  echomsg 'speech requires Python support. Not found.'
  finish
endif

command -count BoniSpeechSetRate :py3 boni.speech.client.set_rate(<count>)

nmap <Plug>(Boni)s <Plug>(Boni.Speech)
nnoremap <Plug>(Boni.Speech)<F1> :echo
  \ 'speech: (c)ancel (l)ine (p)unc (r)ate
  \<CR>
nnoremap <Plug>(Boni.Speech)c :py3 boni.speech.client.cancel()<CR>
nnoremap <Plug>(Boni.Speech)l :py3do boni.speech.client.speak(line)<CR>
nnoremap <Plug>(Boni.Speech)p :py3 boni.speech.cycle_punctuation()<CR>
nnoremap <Plug>(Boni.Speech)r :BoniSpeechSetRate<CR>
