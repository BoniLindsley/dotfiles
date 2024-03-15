call ale#Set('markdown_mdformat_executable', 'mdformat')
call ale#Set('markdown_mdformat_options', '')
call ale#Set('markdown_mdformat_change_directory', 1)

function! ale#fixers#mdformat#Fix(buffer) abort
  let l:executable = ale#Var(a:buffer, 'markdown_mdformat_executable')
  let l:cmd = [ale#Escape(l:executable)]

  let l:options = ale#Var(a:buffer, 'markdown_mdformat_options')
  if !empty(l:options)
    call add(l:cmd, l:options)
  endif
    call add(l:cmd, '-')

  let l:result = {'command': join(l:cmd, ' ')}

  if ale#Var(a:buffer, 'markdown_mdformat_change_directory')
    let l:result.cwd = '%s:h'
  endif

  return l:result
endfunction
