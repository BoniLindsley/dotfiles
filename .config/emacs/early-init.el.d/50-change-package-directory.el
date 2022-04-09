(require 'package)

; Change Base installation directory for packages before activation.
;(setq package-user-dir (expand-file-name "elpa" user-emacs-directory))
(setq package-user-dir
  (expand-file-name "package"
    (expand-file-name "emacs"
        (getenv "XDG_LIB_HOME")
    )
  )
)

; Change GnuPG keyring directory path.
; TODO(BoniLindsley): This should not need to be changed.
; Something in initialisation is changing it, if `nil`,
; to `(expand-file-name "elpa/gnupg" user-emacs-directory)`
;(setq package-gnupghome-dir (expand-file-name "gnupg" package-user-dir))
(setq package-gnupghome-dir (expand-file-name "gnupg" package-user-dir))
