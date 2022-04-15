; Emacs 27+ initialises as follows:
;
; -   Load `early-init.el`.
; -   Activate installed packages so that their functions can be called.
; -   Load `init.el`.
;
; Before version 27, there were no `early-init.el`
; and there were no automatic package activation.
; So they need to be done manually.
(cond
  (
    (< emacs-major-version 27)
    (let
      (
        (early-init-file
          (expand-file-name "early-init.el"
            (file-name-directory user-init-file)
          )
        )
      )
      (if (file-readable-p early-init-file)
        (load-file early-init-file)
      )
    )
    (if (require 'package nil 'noerror)
      (package-initialize)
    )
  )
)
