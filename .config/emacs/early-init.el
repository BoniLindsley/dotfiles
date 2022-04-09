(mapc 'load-file
  (directory-files
    (concat early-init-file ".d") t "\\.el$"
  )
)
