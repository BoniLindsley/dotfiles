" orgmode
"
" Upstream: https://github.com/nvim-orgmode/orgmode
"

if !has('nvim')
  finish
endif

try
  lua require('orgmode')
catch /^Vim\%((\a\+)\)\=:E5108:/
  finish
endtry

lua << EOF

-- Load custom treesitter grammar for org filetype
require('orgmode').setup_ts_grammar()

-- Treesitter configuration
require('nvim-treesitter.configs').setup {
  -- If TS highlights are not enabled at all, or disabled via `disable` prop,
  -- highlighting will fallback to default Vim syntax highlighting
  highlight = {
    enable = true,
    -- -- Required for spellcheck, some LaTex highlights and
    -- -- code block highlights that do not have ts grammar
    -- additional_vim_regex_highlighting = {'org'},
  },
  ensure_installed = {'org'}, -- Or run :TSUpdate org
}

require('orgmode').setup({
  org_agenda_files = {'~/.local/share/emacs/org/notes.org'},
  org_default_notes_file = '~/.local/share/emacs/org/notes.org',
  -- org_log_done = 'time',
  -- org_log_into_drawer = nil,
  -- org_log_into_drawer = 'LOGBOOK',
  -- org_todo_keywords = {'TODO', '|', 'DONE'},
  org_todo_keywords = {'TODO(t!)', '|', 'DONE(d!)', 'DROP(D!)'},
})

EOF
