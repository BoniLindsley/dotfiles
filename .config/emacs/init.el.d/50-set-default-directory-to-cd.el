; Always try to use the $PWD as the default directory for new files.
(defun boni/get-current-directory ()
  (cond
    ((eq system-type 'windows-nt) (getenv "CD"))
    (t (getenv "PWD"))
  )
)
(defun boni/change-default-directory-to-pwd ()
  (cd (boni/get-current-directory))
)
; (add-hook 'find-file-hook 'boni/change-default-directory-to-pwd)
; (setq-default default-directory (boni/get-current-directory))
