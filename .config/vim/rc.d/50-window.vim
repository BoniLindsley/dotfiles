" Window
" ======
"
" Mapping for opening windows.
"
" -   `CTRL-W s`: Horizontal split window (top-down). Show same file.
"     `CTRL-W S` as alternative.
"     `CTRL-W CTRL-S` as alternative, terminal might steal `CTRL-S`.
" -   `CTRL-W v`: Vertical split window (left-right). Show same file.
"     `CTRL-W V` as alternative.
"     `CTRL-W CTRL-V` as alternative.
" -   `CTRL-W n`: Horizontal split. Show a new empty buffer on top.
"     `CTRL-W CTRL-N` as alternative.
" -   `CTRL-W ^`: Horizonta split. Show alternative file on top.
"     `CTRL-W CTRL-^` as alternative.
" -   `CTRL-W :`: Start entering a command. Same as `:`.
"
" Mapping for closing a window.
"
" -   `CTRL-W c`: Close current window (or hide if `&hidden`)
" -   `CTRL-W o`: Close all other windows (or hide if `&hidden`)
"     `CTRL-W CTRL-O` as alternative.
" -   `CTRL-W q`: Quit current window (close if not last window).
"     `CTRL-W CTRL-Q` as alternative, terminal might steal `CTRL-Q`.
"
" Mapping for moving cursor to another window:
"
" -   `CTRL-W {hjkl}`: To the left, etc, with wrapping.
"     `CTRL-W CTRL-{HJKL}` as alternative.
" -   `CTRL-W w`: Below or right, or wrapping to top-most.
"     Prefix to go to a specific window number.
"     `CTRL-W CTRL-W` as alternative
"     `CTRL-W W`: To reverse
" -   `CTRL-W t` and `CTRL-W b`: top-left and bottom-right.
"     `CTRL-W CTRL-T` and `CTRL-W CTRL-B` as alternatives.
" -   `CTRL-W p`: last accessed (alt-tab-like).
"     `CTRL-W CTRL-P` as alternative.
" -   `CTRL-W P`: preview window.
"
" Move mapping:
"
" -   `CTRL-W r` to rotate windows down and right
"     `CTRL-W CTRL-R` as alternative.
"     `CTRL-W R` to reverse.
" -   `CTRL-W x` to swap with the next window.
"     `CTRL-W CTRL-X` as alternative.
" -   `CTRL-W {HJKL}` to move window to left-most, etc.
" -   `CTRL-W T` to move window to a new tab.
"
" Resize mapping:
"
" -   `CTRL-W -` and `CTRL-W +` to change height by one.
"     `CTRL-W <` and `CTRL-W >` to change width by one.
" -   `CTRL-W _` and `CTRL-W |` to change to maximum height and width.
"     Prefix by a number to change to specific height and width.
" -   `CTRL-W =` to try to equally spread out height and width.

set splitbelow
