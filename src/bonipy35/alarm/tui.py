#!/usr/bin/env python3
"""Readiness-driven curses interface; countdowns are snapshot values."""

# Standard libraries.
import curses
import pathlib
import selectors
import sys

from typing import List, Union

# Internal modules.
from . import cli, client, data


class TUIClient:
    def __init__(
        self, connection: client.Client, window: "curses.window"
    ) -> None:
        self.connection = connection
        self.window = window
        self.selected = 0
        self.message = ""

    def draw(self) -> None:
        self.window.erase()
        lines = [
            "q quit | j/k select | a alarm | t timer | p pause/resume | s stop | r restart | d delete | x dismiss",
            self.message,
        ]
        lines.extend(cli.format_snapshot(self.connection.snapshot))
        height, width = self.window.getmaxyx()
        for row, line in enumerate(lines[: max(0, height - 1)]):
            attribute = (
                curses.A_REVERSE
                if row == self.selected + 2
                else curses.A_NORMAL
            )
            self.window.addnstr(row, 0, line, max(0, width - 1), attribute)
        self.window.refresh()

    def ask(self, prompt: str) -> str:
        self.window.nodelay(False)
        curses.echo()
        try:
            self.window.move(self.window.getmaxyx()[0] - 1, 0)
            self.window.clrtoeol()
            self.window.addstr(prompt)
            return self.window.getstr().decode("utf-8")
        finally:
            curses.noecho()
            self.window.nodelay(True)

    def handle(self, key: int) -> bool:
        if key == ord("q"):
            return False
        items = self.connection.snapshot["items"]
        if key in (ord("j"), ord("k")):
            self.selected = max(
                0,
                min(
                    len(items) - 1,
                    self.selected + (1 if key == ord("j") else -1),
                ),
            )
            return True
        try:
            if key == ord("a"):
                value = self.ask("Alarm time: ")
                self.connection.request(
                    "alarm",
                    end_time=data.Datetime.model_dump(
                        cli.parse_alarm_time(value, data.utc_now())
                    ),
                )
            elif key == ord("t"):
                value = self.ask("Duration: ")
                self.connection.request(
                    "timer",
                    duration=cli.parse_duration(value).total_seconds(),
                )
            elif items and key in (
                ord("p"),
                ord("s"),
                ord("r"),
                ord("d"),
                ord("x"),
            ):
                item = items[min(self.selected, len(items) - 1)]
                action = {
                    ord("s"): "stop",
                    ord("r"): "restart",
                    ord("d"): "delete",
                    ord("x"): "dismiss",
                }.get(key, "resume" if item["state"] == "paused" else "pause")
                self.connection.request(action, id_=item["id_"])
            self.message = ""
        except (ValueError, OverflowError) as error:
            self.message = str(error)
        return True

    def run(self) -> None:
        self.window.nodelay(True)
        with self.connection.events(), selectors.DefaultSelector() as selector:
            selector.register(sys.stdin, selectors.EVENT_READ, "input")
            selector.register(
                self.connection.sock, selectors.EVENT_READ, "event"
            )
            while True:
                self.selected = min(
                    self.selected,
                    max(0, len(self.connection.snapshot["items"]) - 1),
                )
                self.draw()
                if self.connection.buffered:
                    self.connection.receive()
                    continue
                for event, _mask in selector.select():
                    if event.data == "event":
                        self.connection.receive()
                    else:
                        # Drain ncurses' decoded input queue after stdin becomes
                        # ready; it can contain more than one key per OS read.
                        while True:
                            key = self.window.getch()
                            if key == -1:
                                break
                            if not self.handle(key):
                                return


def run(directory: pathlib.Path) -> int:
    try:
        with client.Client(directory=directory) as connection:
            curses.wrapper(lambda window: TUIClient(connection, window).run())
    except curses.error as error:
        raise RuntimeError(str(error)) from error
    return 0


def main(argv: Union[None, List[str]] = None) -> int:
    return client.interface_main(run, argv, __doc__)


if __name__ == "__main__":
    sys.exit(main())
