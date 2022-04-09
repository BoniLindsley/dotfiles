; Open URLs externally in Firefox.
(setq browse-url-generic-program "boni-url-open.py")
; Use EWW as default browser.
(setq browse-url-browser-function 'eww-browse-url)
; Open all new buffers in the same window.
(setq same-window-regexps '(".*"))
; Indent settings.
(setq-default indent-tabs-mode nil)
(setq-default tab-width 2)
