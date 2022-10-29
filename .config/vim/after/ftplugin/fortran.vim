set tabstop=3

if exists("g:loaded_dispatch")
  if executable('fpm')
    let b:dispatch = 'fpm build'
    let b:start = 'fpm run'
  endif
endif
