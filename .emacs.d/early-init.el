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
      ((expand-file-name ".config" home))
    ))
    (user-init-directory
      (expand-file-name "emacs" xdg-config-home)
    )
  )
  (setq early-init-file
    (expand-file-name "early-init.el" user-init-directory)
  )
  (load early-init-file "NOERROR")
)
