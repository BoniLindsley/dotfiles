" This file is only sourced by Vim if it is running with `gui_running`.
" It occurs after sourcing `.vimrc` and plugins.
"
" Source every file in a `gvimrc.d` directory.
for s:filepath in split(glob($VIM_CONFIG_HOME. '/gvimrc.d/*.vim'), '\n')
  execute 'source ' . s:filepath
endfor
