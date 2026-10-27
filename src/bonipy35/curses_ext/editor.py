#!/usr/bin/env python3
"""Small modal editor demonstrating Textbox and asyncio input."""

# Standard libraries.
import argparse
import asyncio
import curses
import curses.textpad
import pathlib
import shlex
import sys
import typing

from typing import List, Union

# Internal modules.
from . import selector_loop

MAX_FILE_SIZE = 4096


class Editor:
    """A fixed-size ASCII buffer; Textbox supplies placeholder editing.

    Supports typing, arrows, Backspace, Delete, Home and End.
    Enter moves to the next row without splitting a line;
    Backspace does not join lines.
    There is no scrolling.
    Resizing crops the view without losing contents.

    Files may contain printable ASCII, tabs and line endings,
    up to 4 KiB,
    and must fit the initial area (at most 32 rows and 120 columns).
    Loaded lines must leave one column free.
    Tabs expand to four-column stops and CRLF becomes LF.
    Saving trims trailing spaces and final blank rows,
    preserves interior blank lines
    and adds a final newline to nonempty text.
    Writing without a path uses the current filename.
    Quit, new and edit require `!` to discard unsaved changes.
    """

    def __init__(self, window: "curses.window") -> None:
        height, width = window.getmaxyx()
        if height < 3 or width < 4:
            raise ValueError(
                "Editor needs a terminal of at least 3 rows and 4 columns"
            )
        self.window = window
        # The independent pad keeps its contents when the terminal shrinks.
        self.buffer = curses.newpad(min(height - 2, 32), min(width - 1, 120))
        self.textbox = curses.textpad.Textbox(self.buffer, insert_mode=True)
        self.mode = "normal"
        self.command = ""
        self.message = "i: insert, Esc: normal, : command"
        self.path = None  # type: Union[None, pathlib.Path]
        self.saved_text = ""

    def text(self) -> str:
        """Read window contents, preserving interior blank lines and cursor."""
        height, width = self.buffer.getmaxyx()
        position = self.buffer.getyx()
        try:
            lines = [
                self.buffer.instr(row, 0, width).decode("ascii").rstrip(" ")
                for row in range(height)
            ]
        finally:
            self.buffer.move(*position)
        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines) + "\n" if lines else ""

    def load(self, path: pathlib.Path) -> None:
        with path.open("rb") as file:
            raw = file.read(MAX_FILE_SIZE + 1)
        if len(raw) > MAX_FILE_SIZE:
            raise ValueError("File exceeds 4 KiB")
        text = raw.decode("ascii").replace("\r\n", "\n")
        if any(
            char not in "\n\t" and not 32 <= ord(char) <= 126 for char in text
        ):
            raise ValueError(
                "Only printable ASCII, tabs and newlines are supported"
            )
        text = text.expandtabs(4)
        height, width = self.buffer.getmaxyx()
        lines = text.split("\n")
        if lines[-1] == "":
            lines.pop()
        if (
            len(text) > MAX_FILE_SIZE
            or len(lines) > height
            or any(len(line) >= width for line in lines)
        ):
            raise ValueError("File does not fit the fixed editing buffer")
        # Validate first, so a failed edit command leaves the current buffer.
        self.buffer.erase()
        for row, line in enumerate(lines):
            self.buffer.addstr(row, 0, line)
        self.buffer.move(0, 0)
        self.path = path
        self.saved_text = self.text()

    def execute(self, command: str) -> bool:
        """Execute a colon command; return True only when quitting."""
        parts = shlex.split(command)
        if not parts:
            return False
        name = parts[0].rstrip("!")
        force = parts[0].endswith("!")
        name = {
            "q": "quit",
            "n": "new",
            "e": "edit",
            "w": "write",
            "r": "redraw",
        }.get(name, name)
        arguments = parts[1:]
        counts = {
            "quit": (0,),
            "new": (0,),
            "edit": (1,),
            "write": (0, 1),
            "redraw": (0,),
        }
        if name not in counts or len(arguments) not in counts[name]:
            raise ValueError(
                "Use quit, new, edit <path>, write [path], or redraw"
            )
        text = self.text()
        if (
            name in ("quit", "new", "edit")
            and text != self.saved_text
            and not force
        ):
            raise ValueError(
                "Unsaved changes; write first or append ! to discard"
            )
        if name == "quit":
            return True
        if name == "new":
            self.buffer.erase()
            self.buffer.move(0, 0)
            self.path = None
            self.saved_text = ""
        elif name == "edit":
            self.load(pathlib.Path(arguments[0]))
        elif name == "write":
            path = pathlib.Path(arguments[0]) if arguments else self.path
            if path is None:
                raise ValueError("Specify a filename: write <path>")
            if len(text) > MAX_FILE_SIZE:
                raise ValueError("Buffer exceeds 4 KiB")
            path.write_text(text, encoding="ascii")
            self.path = path
            self.saved_text = text
        else:
            self.window.clearok(True)
            self.buffer.touchwin()
        self.message = name + " complete"
        return False

    def handle_key(self, key: int) -> bool:
        if key == curses.KEY_RESIZE:
            self.window.clearok(True)
            self.buffer.touchwin()
        elif key == 27:
            self.mode = "normal"
            self.command = ""
        elif key == 12 and self.mode != "command":
            self.execute("redraw")
        elif self.mode == "insert":
            key = {
                curses.KEY_DC: 4,
                curses.KEY_HOME: 1,
                curses.KEY_END: 5,
                curses.KEY_ENTER: 10,
                13: 10,
            }.get(key, key)
            self.textbox.do_command(key)
        elif self.mode == "command":
            if key in (10, 13, curses.KEY_ENTER):
                command = self.command
                self.mode = "normal"
                self.command = ""
                try:
                    return self.execute(command)
                except (OSError, ValueError) as error:
                    self.message = str(error)
            elif key in (8, 127, curses.KEY_BACKSPACE):
                self.command = self.command[:-1]
            elif 32 <= key <= 126 and len(self.command) < 1024:
                self.command += chr(key)
        elif key == ord("i"):
            self.mode = "insert"
        elif key == ord(":"):
            self.mode = "command"
            self.command = ""
        return False

    def render(self) -> None:
        height, width = self.window.getmaxyx()
        dirty = " *" if self.text() != self.saved_text else ""
        status = (
            self.mode.upper() + " " + str(self.path or "[No name]") + dirty
        )
        prompt = (
            ":" + self.command if self.mode == "command" else self.message
        )
        for row, line in ((max(0, height - 2), status), (height - 1, prompt)):
            self.window.move(row, 0)
            self.window.clrtoeol()
            self.window.addnstr(row, 0, line, max(0, width - 1))
        self.window.noutrefresh()
        rows, columns = self.buffer.getmaxyx()
        if height >= 3 and width >= 2:
            self.buffer.leaveok(self.mode != "insert")
            self.buffer.noutrefresh(
                0,
                0,
                0,
                0,
                min(rows, height - 2) - 1,
                min(columns, width - 1) - 1,
            )
        curses.doupdate()


async def async_run() -> int:
    loop = typing.cast(selector_loop.EventLoop, asyncio.get_event_loop())
    editor = Editor(loop.window)
    while True:
        editor.render()
        if editor.handle_key(await loop.getch()):
            return 0


def main(argv: Union[None, List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Modal ASCII editor using asyncio and ncurses"
    )
    parser.parse_args(None if argv is None else argv[1:])
    return selector_loop.run(async_run())


if __name__ == "__main__":
    sys.exit(main())
