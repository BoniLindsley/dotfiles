if empty($HOME)
  if !empty($UserProfile)
    let $HOME = fnameescape($UserProfile)
  endif
endif

if empty($XDG_CONFIG_HOME)
  let $XDG_CONFIG_HOME = $HOME . '/.config'
endif

execute 'source ' . fnameescape($XDG_CONFIG_HOME . '/vim/vimrc')
