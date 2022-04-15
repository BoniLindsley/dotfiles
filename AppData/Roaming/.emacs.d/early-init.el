; Emacs scaffolding for Windows to user config in `%UserProfile%`.
(setenv "Home" (getenv "UserProfile"))
(setq default-directory (getenv "Home"))

; Old config has support for XDG_CONFIG_HOME searching.
(load
  (expand-file-name "early-init.el"
    (expand-file-name ".emacs.d"
      (getenv "Home")
    )
  )
)
