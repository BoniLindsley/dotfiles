(setq
  ; Just disable auto-save. It is more annoying than helpful.
  ; I save frequently anyway.
  ; If I do not save, that is usually on purpose.
  ;auto-save-default t
  auto-save-default nil
  ; Move backup files to a fixed location.
  ; Default saves to the same place as the original file.
  ;setq backup-directory-alist nil
  backup-directory-alist `(
    ("." .  ,(expand-file-name "backup" user-emacs-directory))
  )
  ;backup-by-copying-when-linked nil
  backup-by-copying-when-linked t
  ; Disable lock files too. They are for multi-session situations.
  ; Have to be mindful of these situations regardless of editor used.
  ; Since I use Vim as well, no point in using a Emacs-only mechanism.
  ;create-lockfiles t
  create-lockfiles nil
)
