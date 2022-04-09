; Packages write to the user directory
; which defaults to the config directory.
; This should keep the config directory clean.
(setq user-emacs-directory
  (expand-file-name "emacs" (getenv "XDG_DATA_HOME"))
)

; Remember where the init file is stored.
(setq user-init-directory
  (file-name-directory user-init-file)
)
