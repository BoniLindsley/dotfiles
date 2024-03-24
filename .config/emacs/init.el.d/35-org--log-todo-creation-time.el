(eval-after-load 'org
  (custom-set-variables

    ; Consistency with old version.
    ;'(org-clock-into-drawer ; New from Emacs 26.1.
    ;  t ; Log state changes into "LOGBOOK".
    ;  ; "TODOSTATE ; Log state changes into "TODOSTATE".
    ;  ; nil ; Do not use a drawer.
    ;)

    ; Record a note when clocking out of an item.
    ;org-log-note-clock-out nil
    '(org-log-note-clock-out t)

    ;'(org-todo-keywords '((sequence "TODO" "DONE")))
    '(org-todo-keywords
      '(
        ; (aX/Y) for state hotkey a, enter state action X and leave Y.
        ; Hotkey is entered after `C-c C-t`.
        ; Use ! to store a timestamp for state change.
        ; Use @ to store a timestamp and a note.
        (sequence
          "TODO(t!)"  ; Store creation time via `C-c C-x M`.
          "|" ; Terminal states after this.
          "DONE(d!)"  ; Store completion time.
          "DROP(D@/!)"
          "WAIT(w@/!)"
        )
      )
    )

    ; Store creation time via `C-c C-x M`.
    ;'(org-treat-insert-todo-heading-as-state-change nil)
    '(org-treat-insert-todo-heading-as-state-change t)
  )
)
