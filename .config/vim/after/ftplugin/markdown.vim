if exists("g:loaded_dispatch")
  let b:boni_markdown_html_output = $VIM_TMPDIR_HOME . '/%:t:r.html'
  let b:dispatch =
    \ g:boni_python . ' -m markdown'
    \ . ' -x fenced_code'
    \ . ' -x tables'
    \ . ' --output_format=html'
    \ . ' --file="' . b:boni_markdown_html_output . '" "%:p"'
  let b:start = g:boni_browser . ' "file:///' . b:boni_markdown_html_output . '"'
endif
