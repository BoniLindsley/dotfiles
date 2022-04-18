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
  )
)
;(eval-after-load 'org
;    '(let
;      (
;       (boni/org/agenda/directory
;         (expand-file-name "agenda" org-directory)
;       )
;      )
;      (make-directory boni/org/agenda/directory t)
;      (add-to-list 'org-agenda-files boni/org/agenda/directory)
;    )
;    ;(add-to-list 'org-agenda-files org-directory)
;)
