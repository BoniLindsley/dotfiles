(eval-after-load 'org
  '(progn
    (custom-set-variables
      ;(SYMBOL EXP [NOW [REQUEST [COMMENT]]])

      ;'(org-directory "~/org")
      '(org-directory (expand-file-name "org/" user-emacs-directory))

      ;'(org-agenda-files nil)
      '(org-agenda-files (list org-directory))

      ;'(org-default-notes-file "~/.notes")
      '(org-default-notes-file
        (expand-file-name "notes.org" org-directory)
      )
    )
    (make-directory org-directory t)
  )
)
