; Emacs searches for configuration from `${XDG_CONFIG_HOME}`
; starting Emacs 27.1 in 2020-08.
; This is wrapper for that behaviour.
(defun boni/load-xdg-config ()
  "Load `init.el` from `${XDG_CONFIG_HOME}`."
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
    (load user-init-file "NOERROR")
  )
)
(boni/load-xdg-config)
