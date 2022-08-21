call ale#Set('fortran_fprettify_executable', 'fprettify')
call ale#Set('fortran_fprettify_options', '')
call ale#Set('fortran_fprettify_change_directory', 1)

function! ale#fixers#fprettify#Fix(buffer) abort
  let l:executable = ale#Var(a:buffer, 'fortran_fprettify_executable')
  let l:cmd = [ale#Escape(l:executable)]

  let l:options = ale#Var(a:buffer, 'fortran_fprettify_options')
  if !empty(l:options)
    call add(l:cmd, l:options)
  endif

  let l:result = {'command': join(l:cmd, ' ')}

  if ale#Var(a:buffer, 'fortran_fprettify_change_directory')
    let l:result.cwd = '%s:h'
  endif

  return l:result
endfunction
