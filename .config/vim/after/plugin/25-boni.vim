" Need to know how to preview the output.
" Windows usually needs an explicit path.
if has('win32')
  let g:boni_browser = 'explorer'
else
  let g:boni_browser = 'firefox'
endif

" Windows has a different binary name for Python3.
if has('win32')
  let g:boni_python = 'py'
else
  let g:boni_python = 'python3'
endif

let g:boni_path = $PATH
