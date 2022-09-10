(eval-after-load 'bookmark
  (custom-set-variables
    ;(SYMBOL EXP [NOW [REQUEST [COMMENT]]])

    ;'(bookmark-default-file "~/.emacs.bmk")
    ;'(bookmark-default-file ; As early as Emacs v27.1.
    ;   (expand-file-name "bookmarks" user-emacs-directory)
    ;)
    '(bookmark-default-file
       (expand-file-name "bookmarks" user-emacs-directory)
    )
  )
)
