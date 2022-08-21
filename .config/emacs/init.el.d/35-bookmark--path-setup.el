(eval-after-load 'bookmark
  (custom-set-variables
    ;(SYMBOL EXP [NOW [REQUEST [COMMENT]]])

    ;'(bookmark-default-file "~/.emacs.bmk")
    '(bookmark-default-file
       (expand-file-name ".emacs.bmk" user-emacs-directory)
    )
  )
)
