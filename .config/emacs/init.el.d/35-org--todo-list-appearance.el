(eval-after-load 'org
  (progn
    (custom-set-variables
      ; Only show top-level items in todo view.
      '(org-agenda-todo-list-sublevels nil)

      ; Show schedule using "future" to mean "after current second".
      ; Default is "after today".
      ;'(org-agenda-todo-ignore-time-comparison-use-seconds nil)
      '(org-agenda-todo-ignore-time-comparison-use-seconds t)

      ; Hide item scheduled in the future.
      ; Default shows all scheduled items in the todo list.
      ;'(org-agenda-todo-ignore-scheduled nil)
      '(org-agenda-todo-ignore-scheduled 'future)

      ; Use only hours (25h) instead of days (1d 1h).
      '(org-time-clocksum-format '(
        :hours "%d"
        :require-hours t
        :minutes ":%02d"
        :require-minutes t
      ))
    )
    ; Use fractions (1.5h) instead of minutes (1:30).
    (cond
      (
        (or
          (> emacs-major-version 26)
          (and
            (= emacs-major-version 26)
            (> emacs-minor-version 0)
          )
        )
        (custom-set-variables
          '(org-duration-format '(("h") (special . 2)))
        )
      )
      ; Old variable for pre-26.1.
      (t
        (custom-set-variables
          '(org-time-clocksum-use-fractional t)
        )
      )
    )
  )
)
