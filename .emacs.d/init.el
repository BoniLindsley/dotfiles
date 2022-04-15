; Emacs does early config load starting Emacs 27.1 in 2020-08.
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
  (setq user-init-file
    (expand-file-name "init.el" user-init-directory)
  )
  (load user-init-file "NOERROR")
)
