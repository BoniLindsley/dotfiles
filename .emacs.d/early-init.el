; Emacs searches for configuration from `${XDG_CONFIG_HOME}`
; starting Emacs 27.1 in 2020-08.
; This is wrapper for that behaviour.
(let*
  (
    (home (cond
      ((getenv "HOME"))
      (default-directory)
    ))
    (xdg-config-home (cond
      ((getenv "XDG_CONFIG_HOME"))
      (expand-file-name ".config" home)
    ))
  )
  (setq user-emacs-directory
    (expand-file-name "emacs" xdg-config-home)
  )
  (setq user-init-file
    (expand-file-name "init.el" user-emacs-directory)
  )
  (setq early-init-file
    (expand-file-name "early-init.el" user-emacs-directory)
  )
  (load early-init-file "NOERROR")
)
