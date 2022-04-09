(defun boni/env-set-default (name default)
  "Set environment variable if not defined."
  (cond
    ((getenv name))
    ((setenv name default))
  )
)

(boni/env-set-default "HOME" default-directory)
(boni/env-set-default "XDG_LOCAL_HOME"
  (expand-file-name ".local" (getenv "HOME"))
)
(boni/env-set-default "XDG_LIB_HOME"
  (expand-file-name "lib" (getenv "XDG_LOCAL_HOME"))
)
(boni/env-set-default "XDG_CACHE_HOME"
  (expand-file-name ".cache" (getenv "HOME"))
)
(boni/env-set-default "XDG_CONFIG_HOME"
  (expand-file-name ".config" (getenv "HOME"))
)
(boni/env-set-default "XDG_DATA_HOME"
  (expand-file-name "share" (getenv "XDG_LOCAL_HOME"))
)
(boni/env-set-default "XDG_STATE_HOME"
  (expand-file-name "state" (getenv "XDG_LOCAL_HOME"))
)
