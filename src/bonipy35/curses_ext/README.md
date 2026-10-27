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

To check a terminal, run `python -m bonipy35.curses_ext.selector_loop`:
it shows keys, a clock, the size and thread wakeups.

## Usage

```python
import asyncio
import curses
import typing
from bonipy35.curses_ext import EventLoop, run


async def async_run():
    loop = typing.cast(EventLoop, asyncio.get_event_loop())
    window = loop.window
    window.addstr(0, 0, "Press a key")
    window.noutrefresh()
    curses.doupdate()
    key = await loop.getch()
    await asyncio.sleep(0.1)  # Normal asyncio operations work here.
    return key


key = run(async_run())
print("Key:", key)  # The terminal has been restored.
```

The `run()` function restores the terminal on exit
and cancels unfinished tasks.
The loop waits outside curses and reads keys when input is ready,
so socket, pipe and subprocess readiness work as usual on Unix.
On Windows it waits on the console and the loop's sockets,
the only readiness Windows selector loops support.

`getch()` returns `KEY_RESIZE` when the terminal is resized.
On Unix the loop handles `SIGWINCH`;
`run()` keeps ncurses from installing its own handler.
Applications that initialise curses themselves
should do so inside `keep_resize_handler()`.

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
