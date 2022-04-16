; This makes backspace and `C-h` both `DEL`
; which is backspace instead of both being `C-h`.
; Use `F1` as an alternative to `C-h` help functionalities.
;
; Might be possible to split the keys in .Xresources instead.
; But tmux might merge them again
; because of incompatible termcap / terminfo detection.
(let
  (
    (term (getenv-internal "TERM" initial-environment))
  )
  (cond
    (
      (string-equal term "screen-256color")
      (normal-erase-is-backspace-mode 0)
    )
    (
      (string-equal term "xterm")
      (normal-erase-is-backspace-mode 1)
    )
  )
)
