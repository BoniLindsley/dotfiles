(use-package warnings
  :custom
    ; Focus warnings buffer for messages as least as severe as given.
    ; Messages still logged according `warning-minimum-log-level`.
    ;(warning-minimum-level :warning)
    (warning-minimum-level :emergency)
)
