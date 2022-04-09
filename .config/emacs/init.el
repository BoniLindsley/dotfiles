;(require 'ob-tangle)
;(require 'org)
;
;(defun boni/load-file (file)
;  "Load `.el` files or compile `.org` before loading."
;  (pcase (file-name-extension file)
;    ("org"
;      (let*
;        (
;          (compiled-file-path
;            (expand-file-name (concat (file-name-base file) ".el")
;              (expand-file-name "org-babel-tangled"
;                (expand-file-name "emacs"
;                  (cond
;                    ((getenv "XDG_CACHE_HOME"))
;                    ((expand-file-name ".cache"
;                      (cond
;                        ((getenv "HOME"))
;                        (default-directory)
;                      )
;                    ))
;                  )
;                )
;              )
;            )
;          )
;        )
;        (make-directory compiled-init-directory t)
;        (org-babel-tangle-file
;          file
;          compiled-file-path
;        )
;        (load-file compiled-file-path)
;      )
;    )
;    (_ (load-file file))
;  )
;)
;
;; Configurations are placed in `init.el.d` directory to reduce clutter.
;; Search in it for files.
;(mapc 'boni/load-file
;  (directory-files (concat user-init-file ".d") t "\\.\\(el\\|org\\)$")
;)

(mapc 'load-file
  (directory-files
    (concat user-init-file ".d") t "\\.el$"
  )
)
