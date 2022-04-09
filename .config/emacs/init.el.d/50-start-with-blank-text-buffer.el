; Changes initial blank window to be for text instead of lisp code.
(setq initial-major-mode 'text-mode)
; The messages for the blank window is set independently,
;   so we change that as well.
(setq initial-scratch-message "")
; Disable Emacs splash screen.
(setq inhibit-startup-screen t)
