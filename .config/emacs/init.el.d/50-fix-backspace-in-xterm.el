; Default of `normal-erase-is-backsapce` is `maybe`.
;
; In XTerm,
; Backsapce sends `C-d` which maps to `delete-char` (forward).
; Delete sends `<deletechar>` which maps to `delete-forward-char`.
; `C-h` sends `DEL` which maps to `delete-backward-char`.

; After setting the mode
; `C-d` sends `C-d`
; Delete sends `<deletechar>`
; Backspace sends `DEL`
; `C-h` sends C-h`.

(let
  (
    (term (getenv-internal "TERM" initial-environment))
  )
  (cond
    (
      (string-equal term "xterm")
      (normal-erase-is-backspace-mode 1)
    )
    (
      (string-equal term "xterm-256color")
      (normal-erase-is-backspace-mode 1)
    )
  )
)
