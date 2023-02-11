(require 'custom)

; Move customisation from Emacs interface out of init file.
(setq custom-file (expand-file-name "custom.el" user-init-directory))
(if (file-readable-p custom-file)
  (load-file custom-file)
)
