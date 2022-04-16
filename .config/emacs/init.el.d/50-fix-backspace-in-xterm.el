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
      ; Emacs tries to do the right thing
      ; and sends them to C-d in this term mode?
      ; Turn that off first.
      (string-equal term "screen-256color")
      (normal-erase-is-backspace-mode 0)
    )
  )
)
(keyboard-translate ?\C-h ?\C-?)
