(eval-after-load 'org
  (custom-set-variables
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

    ; Use fractions (1.5h) instead of minutes (1:30).
    '(org-time-clocksum-use-fractional t)
  )
)
