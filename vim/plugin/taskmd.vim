" Make the default document accessible before opening a taskmd buffer.
if exists('g:loaded_taskmd') || !has('python3')
  finish
endif
let g:loaded_taskmd = 1

command! TaskmdOpen call taskmd#Open()
