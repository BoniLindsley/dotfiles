(eval-after-load 'org
  (custom-set-variables
    ; Archive all to a fixed file in the same directory.
    '(org-archive-location "archive.org::")

    ; Allow subtrees to be refiled to as top-level of another file.
    '(org-refile-use-outline-path 'file)
  )
)
