;
; In XTerm,
; Delete sends `<deletechar>` which maps to `delete-forward-char`.
; `C-d` sends `C-d` which maps to `delete-char` (forward).
;
; And by default,
; Backsapce sends `C-d`
; `C-h` sends `DEL` which maps to `delete-backward-char`.

; After setting the mode,
; Backspace sends `DEL`
; `C-h` sends C-h`.

(let
  (
    (term (getenv-internal "TERM" initial-environment))
  )
  (cond
    (
      (string-equal term "xterm")
      (normal-erase-is-backspace-mode 0)
    )
    (
      (string-equal term "xterm-256color")
      (normal-erase-is-backspace-mode 0)
    )
  )
)
