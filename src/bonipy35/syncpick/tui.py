#!/usr/bin/env python3
"""Pick and copy files of two rclone locations in a terminal."""

# Standard libraries.
import asyncio
import curses
import functools
import os
import sys
import threading
import typing

from typing import Awaitable, Callable, Dict, Generator, List, Union

# Internal modules.
from ..curses_ext import selector_loop
from . import compare
from . import rc
from . import runner
from . import screen
from . import transfer
from . import tree

CompareFiles = Callable[[str, str], List[compare.Entry]]
"""Compares two locations, like ``compare.compare`` given a daemon."""

CopyFiles = Callable[..., Generator[transfer.Result, None, None]]
"""Copies paths, like ``transfer.copy_files`` given a daemon."""


def attributes() -> Dict[screen.Style, int]:
    """Curses attributes by style, with colours if the terminal has them.

    Call after curses is initialised.
    """
    result = {
        screen.Style.NORMAL: curses.A_NORMAL,
        screen.Style.HEADER: curses.A_BOLD,
        screen.Style.DIRECTORY: curses.A_BOLD,
        screen.Style.MUTED: curses.A_DIM,
        screen.Style.NEWER: curses.A_BOLD,
        screen.Style.GOOD: curses.A_NORMAL,
        screen.Style.BAD: curses.A_BOLD,
    }
    if curses.has_colors():
        try:
            curses.use_default_colors()
            background = -1
        except curses.error:
            background = curses.COLOR_BLACK
        colours = (
            (screen.Style.NEWER, curses.COLOR_YELLOW),
            (screen.Style.GOOD, curses.COLOR_GREEN),
            (screen.Style.BAD, curses.COLOR_RED),
        )
        for number, (style, colour) in enumerate(colours, start=1):
            curses.init_pair(number, colour, background)
            result[style] |= curses.color_pair(number)
    return result


def draw(
    window: "curses.window",
    view: screen.Screen,
    styles: Dict[screen.Style, int],
) -> None:
    """Draw the screen, fitting it to the window first."""
    height, width = window.getmaxyx()
    view.resize(height)
    # Leave the final column free to avoid the bottom-right error.
    width = max(0, width - 1)
    window.erase()
    cursor = view.cursor - view.top + 1 if view.rows else -1
    for row, line in enumerate(view.lines(width)[:height]):
        extra = curses.A_REVERSE if row == cursor else 0
        column = 0
        for text, style in line:
            if column >= width:
                break
            window.addnstr(
                row, column, text, width - column, styles[style] | extra
            )
            column += len(text)
        if extra and column < width:
            fill = width - column
            window.addnstr(row, column, " " * fill, fill, extra)
    window.noutrefresh()
    curses.doupdate()


class App:
    """Run comparisons and copies for a screen, redrawing as they go.

    rclone requests run in executor threads; copy results come back
    with ``call_soon_threadsafe``, so the loop never polls.
    """

    def __init__(
        self,
        *,
        view: screen.Screen,
        window: "curses.window",
        compare_files: CompareFiles,
        copy_files: CopyFiles,
        styles: Union[None, Dict[screen.Style, int]] = None
    ) -> None:
        self.view = view
        self.window = window
        self.compare_files = compare_files
        self.copy_files = copy_files
        self.styles = styles or {style: 0 for style in screen.Style}
        self.task = None  # type: Union[None, asyncio.Future[None]]
        self.stopping = threading.Event()

    def draw(self) -> None:
        draw(self.window, self.view, self.styles)

    async def run(self, getch: Callable[[], Awaitable[int]]) -> None:
        """Compare, then handle keys until ``q``."""
        self.start(self.compare())
        try:
            while True:
                self.draw()
                action = self.view.key(await getch())
                if action is screen.Action.QUIT:
                    return
                if action is screen.Action.COMPARE:
                    self.start(self.compare())
                elif action is screen.Action.COPY_LEFT_TO_RIGHT:
                    self.start(self.copy(transfer.Direction.LEFT_TO_RIGHT))
                elif action is screen.Action.COPY_RIGHT_TO_LEFT:
                    self.start(self.copy(transfer.Direction.RIGHT_TO_LEFT))
                elif action is screen.Action.STOP:
                    self.stopping.set()
                    self.view.message = "Stopping after the current file..."
        finally:
            # Copying stops between files; rclone stops with its daemon.
            self.stopping.set()
            if self.task is not None:
                self.task.cancel()

    def start(self, coroutine: "typing.Coroutine[None, None, None]") -> None:
        self.view.busy = True
        self.stopping.clear()
        self.task = asyncio.ensure_future(coroutine)

    async def compare(self) -> None:
        self.view.message = "Comparing..."
        self.draw()
        try:
            await self._compare()
        finally:
            self.view.busy = False
            self.draw()

    async def _compare(self) -> None:
        loop = asyncio.get_event_loop()
        try:
            entries = await loop.run_in_executor(
                None, self.compare_files, self.view.left, self.view.right
            )
        except rc.RcError as error:
            self.view.message = "Comparing failed: {}".format(error)
            return
        self.view.refresh(entries)
        same = sum(
            1 for entry in entries if entry.state is compare.State.SAME
        )
        self.view.message = "{} files, {} the same.".format(
            len(entries), same
        )

    async def copy(self, direction: transfer.Direction) -> None:
        paths = self.view.model.picked_paths(direction)
        self.view.results.clear()
        self.view.message = "Copying 0 of {}...".format(len(paths))
        self.draw()
        try:
            await self._copy(paths, direction)
        finally:
            self.view.busy = False
            self.draw()

    async def _copy(
        self, paths: List[str], direction: transfer.Direction
    ) -> None:
        loop = asyncio.get_event_loop()
        results = self.view.results

        def report(result: transfer.Result) -> None:
            results[result.path] = result.error
            self.view.message = "Copying {} of {}...".format(
                len(results), len(paths)
            )
            self.draw()

        def work() -> None:
            copies = self.copy_files(
                self.view.left, self.view.right, paths, direction=direction
            )
            try:
                for result in copies:
                    try:
                        loop.call_soon_threadsafe(report, result)
                    except RuntimeError:
                        return  # The loop closed: the app quit.
                    if self.stopping.is_set():
                        return
            finally:
                copies.close()

        await loop.run_in_executor(None, work)
        stopped = self.stopping.is_set()
        failed = sum(1 for error in results.values() if error is not None)
        self.view.model.picked.difference_update(
            path for path, error in results.items() if error is None
        )
        await self._compare()
        summary = "{} {} of {}{}.".format(
            "Stopped after" if stopped else "Copied",
            len(results) - failed,
            len(paths),
            ", {} failed".format(failed) if failed else "",
        )
        self.view.message = summary + " " + self.view.message


async def run(daemon: rc.Daemon, left: str, right: str) -> None:
    """Run the app in the curses event loop of ``curses_ext.run``."""
    loop = typing.cast(selector_loop.EventLoop, asyncio.get_event_loop())
    app = App(
        view=screen.Screen(tree.Model(), left=left, right=right),
        window=loop.window,
        compare_files=functools.partial(compare.compare, daemon),
        copy_files=functools.partial(transfer.copy_files, daemon),
        styles=attributes(),
    )
    await app.run(loop.getch)


def main(argv: Union[None, List[str]] = None) -> int:
    """Compare two rclone paths in the terminal and copy picked files."""
    parser = runner.argument_parser(
        description=typing.cast(str, main.__doc__)
    )
    parser.add_argument("left", help="rclone path, such as remote:dir")
    parser.add_argument("right", help="rclone path, such as some/directory")
    arguments = parser.parse_args((sys.argv if argv is None else argv)[1:])
    # Ncurses waits this long after Escape for the rest of a key sequence.
    os.environ.setdefault("ESCDELAY", "25")
    try:
        with rc.Daemon(runner.runner_from_arguments(arguments)) as daemon:
            selector_loop.run(run(daemon, arguments.left, arguments.right))
            return 0
    except (OSError, rc.RcError, runner.RcloneError) as error:
        print(error, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
