" Ultisnips
"
" Upstream: https://github.com/SirVer/ultisnips

" Implemented in Python3.
if !has('python3')
  finish
endif

" Requires Python 3.6 for f-strings.
python3 import platform
if py3eval('int(platform.python_version_tuple()[1]) < 6')
  finish
endif

"" Group dependencies, vim-snippets depends on ultisnips
"Plug 'SirVer/ultisnips' | Plug 'honza/vim-snippets'
