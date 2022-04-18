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
  )
)
