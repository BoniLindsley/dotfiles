# Asyncio and ncurses

Await terminal input while asyncio tasks and timers continue running,
without periodic polling.
Applications decide when to refresh the screen.
Requires Python 3.5 or newer and Python's `curses` module,
which on Windows comes from the `windows-curses` package,
installed with the `curses` extra.

```sh
python -m bonipy35.curses_ext clock
python -m bonipy35.curses_ext counter
python -m bonipy35.curses_ext editor
python -m bonipy35.curses_ext tower
```

The clock quits with `q`.
In the counter, `+` increments, `s` saves to `data.json`,
and `q` saves and quits.

To check a terminal, run `python -m bonipy35.curses_ext.input_loop`:
it shows keys, mouse events, a clock, the size and thread wakeups.

## Usage

```python
import asyncio
from bonipy35.curses_ext import WindowInput, run


async def main(window):
    window.addstr(0, 0, "Press a key")
    window.refresh()
    key = await WindowInput(window).getch()
    await asyncio.sleep(0.1)  # Normal asyncio operations work here.
    return key


key = run(main)
print("Key:", key)  # The terminal has been restored.
```

`run(main)` initialises curses with `stdscr` in nodelay mode,
runs `main(stdscr)` on an `EventLoop`,
and restores the terminal on exit, cancelling unfinished tasks.
To do the steps separately, enter `initialise()`,
then run the coroutine with `loop_factory=EventLoop`,
for example with `bonipy35.asyncio_ext.run`.

`WindowInput(window).getch()` returns the next key,
waiting on the loop while curses has none,
so other tasks keep running.
Keys pushed back with `curses.ungetch` from any task are returned too.
Waiting peeks with `getch`, which refreshes the window,
so draw each screen in one synchronous step.
The loop waits outside curses, so socket, pipe and subprocess
readiness work as usual on Unix.
On Windows it waits on the console and the loop's sockets,
the only readiness Windows selector loops support.

`getch()` returns `KEY_RESIZE` when the terminal is resized.
On Unix the loop handles `SIGWINCH`;
`initialise()` keeps ncurses from installing its own handler.
Applications that initialise curses themselves
should do so inside `keep_resize_handler()`,
and create the loop inside it.
On Windows, windows-curses resizes curses itself
before returning `KEY_RESIZE`.

## Mini-editor

The editor focuses on modes and commands, with placeholder text editing.
Press `i` to insert, Escape for normal mode, and `:` to enter a command:
`quit` (`q`), `new` (`n`), `edit <path>` (`e`),
`write [path]` (`w`), or `redraw` (`r`).
Enter executes; Escape cancels.
Append `!` to discard unsaved changes.
Quote paths containing spaces.
Ctrl+L redraws.

Files must be ASCII, at most 4 KiB, and fit the initial editing area.
There is no scrolling or line splitting/joining,
and saving normalizes whitespace.
See [`Editor`](editor.py) for editing and file-format limitations.

## Tower defence

The tower example animates at five frames per second while awaiting input.
Use WASD or arrow keys to move, 1/2/3 to select a plant, Space to plant,
and q to quit. It needs at least 44 columns and 28 rows; resizing to a
smaller terminal pauses the simulation.
