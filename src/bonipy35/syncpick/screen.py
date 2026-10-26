#!/usr/bin/env python3
"""Screen state of the curses frontend, driven by key codes.

Drawing and running rclone are left to the caller,
so that this can be tested without a terminal.
"""

# Standard libraries.
import curses
import datetime
import enum

from typing import Dict, List, Tuple, Union

# Internal modules.
from . import compare
from . import transfer
from . import tree


class Action(enum.Enum):
    """What the caller should do after a key."""

    NONE = "none"
    QUIT = "quit"
    COMPARE = "compare"
    COPY_LEFT_TO_RIGHT = "copy-left-to-right"
    COPY_RIGHT_TO_LEFT = "copy-right-to-left"
    STOP = "stop"


class Style(enum.Enum):
    """How to draw a segment; the caller maps these to attributes."""

    NORMAL = "normal"
    HEADER = "header"
    DIRECTORY = "directory"
    MUTED = "muted"
    NEWER = "newer"
    GOOD = "good"
    BAD = "bad"


Segment = Tuple[str, Style]
Line = List[Segment]

HELP = (
    "Space pick  > copy to right  < copy to left"
    "  = identical  r compare  Esc stop  q quit"
)

# Width of the state, sizes and times after the name column.
_SIZE_WIDTH = 7
_TIME_WIDTH = 16
_WIDE_COLUMNS = 3 + 2 * (1 + _SIZE_WIDTH + 1 + _TIME_WIDTH)
_NARROW_COLUMNS = 3 + 2 * (1 + _SIZE_WIDTH)
# Narrower names than this leave out the times.
_MIN_NAME_WIDTH = 20

_DOWN = (curses.KEY_DOWN, ord("j"))
_UP = (curses.KEY_UP, ord("k"))
_EXPAND = (curses.KEY_RIGHT, curses.KEY_ENTER, ord("\n"), ord("\r"))
_ESCAPE = 27
# Keys blocked while comparing or copying.
_COMMANDS = tuple(ord(key) for key in " =r><")


class Screen:
    """The comparison of ``left`` and ``right`` as a scrollable tree.

    ``height`` is the number of terminal rows; one is the header and one
    the status line. ``busy`` is set by the caller while comparing or
    copying, which blocks keys that would start or change those.
    ``results`` holds copy results by path, ``None`` for success.
    """

    def __init__(
        self,
        model: tree.Model,
        *,
        left: str = "",
        right: str = "",
        height: int = 24
    ) -> None:
        self.model = model
        self.left = left
        self.right = right
        self.height = height
        self.busy = False
        self.message = ""
        self.results = {}  # type: Dict[str, Union[None, str]]
        self.cursor = 0
        self.top = 0
        self.rows = model.rows()

    @property
    def page(self) -> int:
        """Number of rows shown at once."""
        return max(1, self.height - 2)

    def current(self) -> Union[None, tree.Row]:
        return self.rows[self.cursor] if self.rows else None

    def update(self) -> None:
        """Rebuild rows after the model changed, keeping the cursor's row."""
        current = self.current()
        key = None if current is None else _key(current)
        self.rows = self.model.rows()
        keys = [_key(row) for row in self.rows]
        if key in keys:
            self.cursor = keys.index(key)
        self._move(0)

    def refresh(self, entries: List[compare.Entry]) -> None:
        """Show a new comparison of the same locations."""
        self.model.refresh(entries)
        self.update()

    def key(self, key: int) -> Action:
        """Handle a key code, returning what the caller should do."""
        offset = self._offsets().get(key)
        if offset is not None:
            self._move(offset)
        elif key in _EXPAND:
            self._expand()
        elif key == curses.KEY_LEFT:
            self._collapse()
        elif key == ord("q"):
            return Action.QUIT
        elif key == _ESCAPE:
            return Action.STOP if self.busy else Action.NONE
        elif key in _COMMANDS:
            if not self.busy:
                return self._command(key)
            self.message = "Busy; Esc stops copying."
        return Action.NONE

    def _offsets(self) -> Dict[int, int]:
        """Cursor movement by key."""
        offsets = {
            curses.KEY_NPAGE: self.page,
            curses.KEY_PPAGE: -self.page,
            curses.KEY_HOME: -len(self.rows),
            curses.KEY_END: len(self.rows),
        }
        offsets.update((key, 1) for key in _DOWN)
        offsets.update((key, -1) for key in _UP)
        return offsets

    def _command(self, key: int) -> Action:
        """Handle a key that changes picks, entries or files."""
        if key == ord(" "):
            current = self.current()
            if current is not None:
                self.model.toggle_pick(current)
                self._move(1)
        elif key == ord("="):
            self.model.toggle_state(compare.State.SAME)
            self.update()
            self.message = (
                "Identical files shown."
                if compare.State.SAME in self.model.shown
                else "Identical files hidden."
            )
        elif key == ord("r"):
            return Action.COMPARE
        elif key == ord(">"):
            return self._copy(transfer.Direction.LEFT_TO_RIGHT, "left")
        else:
            return self._copy(transfer.Direction.RIGHT_TO_LEFT, "right")
        return Action.NONE

    def _copy(self, direction: transfer.Direction, source: str) -> Action:
        if not self.model.picked_paths(direction):
            self.message = "No picked files on the {}.".format(source)
            return Action.NONE
        if direction is transfer.Direction.LEFT_TO_RIGHT:
            return Action.COPY_LEFT_TO_RIGHT
        return Action.COPY_RIGHT_TO_LEFT

    def _move(self, offset: int) -> None:
        if not self.rows:
            self.cursor = self.top = 0
            return
        self.cursor = min(max(self.cursor + offset, 0), len(self.rows) - 1)
        if self.cursor < self.top:
            self.top = self.cursor
        elif self.cursor >= self.top + self.page:
            self.top = self.cursor - self.page + 1
        # Fill the page when rows were removed below it.
        self.top = max(0, min(self.top, len(self.rows) - self.page))

    def _expand(self) -> None:
        current = self.current()
        if isinstance(current, tree.Directory) and not self.model.is_expanded(
            current
        ):
            self.model.toggle(current)
            self.update()

    def _collapse(self) -> None:
        current = self.current()
        if isinstance(current, tree.Directory) and self.model.is_expanded(
            current
        ):
            self.model.toggle(current)
            self.update()
            return
        if current is None:
            return
        parent = _parent(_key(current))
        for index, row in enumerate(self.rows):
            if isinstance(row, tree.Directory) and row.path == parent:
                self._move(index - self.cursor)
                return

    def lines(self, width: int) -> List[Line]:
        """Lines to draw for ``height`` rows of ``width`` columns."""
        header = "{}  <->  {}".format(self.left, self.right)
        lines = [[(_fit(header, width), Style.HEADER)]]  # type: List[Line]
        wide = width - _WIDE_COLUMNS >= _MIN_NAME_WIDTH
        name_width = max(
            1, width - (_WIDE_COLUMNS if wide else _NARROW_COLUMNS)
        )
        shown = self.rows[self.top : self.top + self.page]
        for row in shown:
            lines.append(self._row_line(row, name_width, wide))
        lines.extend([] for _ in range(self.page - len(shown)))
        lines.append([(_fit(self._status(), width), Style.NORMAL)])
        return lines

    def _status(self) -> str:
        if self.message:
            return self.message
        if not self.rows:
            return "No files shown.  " + HELP
        return "{}/{}  {}".format(self.cursor + 1, len(self.rows), HELP)

    def _row_line(self, row: tree.Row, name_width: int, wide: bool) -> Line:
        mark = {
            tree.Pick.NONE: "[ ] ",
            tree.Pick.SOME: "[-] ",
            tree.Pick.ALL: "[x] ",
        }[self.model.pick_state(row)]
        indent = "  " * row.depth
        if isinstance(row, tree.Directory):
            toggle = "v " if self.model.is_expanded(row) else "> "
            name = _fit(mark + indent + toggle + row.name + "/", name_width)
            counts = row.counts()
            summary = " ".join(
                state.value + str(counts[state])
                for state in compare.State
                if state in counts
            )
            return [
                (name.ljust(name_width), Style.DIRECTORY),
                (" " + summary, Style.MUTED),
            ]
        entry = row.entry
        name = _fit(mark + indent + "  " + row.name, name_width)
        line = [
            (name.ljust(name_width), Style.NORMAL),
            (" " + entry.state.value + " ", Style.NORMAL),
        ]  # type: Line
        line.extend(_sides(entry, wide))
        if entry.path in self.results:
            error = self.results[entry.path]
            line.append(
                (" copied", Style.GOOD)
                if error is None
                else (" failed: " + error, Style.BAD)
            )
        return line


def _sides(entry: compare.Entry, wide: bool) -> List[Segment]:
    """Sizes and times, with right values equal to the left's as "same"."""
    left = entry.left
    right = entry.right
    # Times compare as shown, since backends keep different precisions.
    same_time = bool(left and right and _time(left) == _time(right))
    newer = ""
    if (
        entry.state is compare.State.DIFFERENT
        and left
        and right
        and not same_time
    ):
        newer = "left" if left.modified > right.modified else "right"
    segments = [
        (" " + _size(left).rjust(_SIZE_WIDTH), Style.NORMAL)
    ]  # type: List[Segment]
    if wide:
        segments.append(
            (
                " " + _time(left).ljust(_TIME_WIDTH),
                Style.NEWER if newer == "left" else Style.NORMAL,
            )
        )
    if left and right and left.size == right.size:
        segments.append((" " + "same".rjust(_SIZE_WIDTH), Style.MUTED))
    else:
        segments.append((" " + _size(right).rjust(_SIZE_WIDTH), Style.NORMAL))
    if wide:
        if same_time:
            segments.append((" " + "same".ljust(_TIME_WIDTH), Style.MUTED))
        else:
            segments.append(
                (
                    " " + _time(right).ljust(_TIME_WIDTH),
                    Style.NEWER if newer == "right" else Style.NORMAL,
                )
            )
    return segments


def _size(side: Union[None, compare.Side]) -> str:
    """A size in bytes, or with a binary unit prefix if long."""
    if side is None:
        return "-"
    if side.size < 0:
        return "?"
    if side.size < 1024:
        return str(side.size)
    units = "KMGT"
    size = side.size / 1024
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    return "{:.1f}{}".format(size, units[index])


def _time(side: Union[None, compare.Side]) -> str:
    """A time in UTC to the minute, or ``-`` for a missing side."""
    if side is None:
        return "-"
    modified = side.modified.astimezone(datetime.timezone.utc)
    return modified.strftime("%Y-%m-%d %H:%M")


def _fit(text: str, width: int) -> str:
    """Cut ``text`` to ``width``, marking a cut with ``~``."""
    if len(text) <= width:
        return text
    return text[: max(0, width - 1)] + "~"


def _key(row: tree.Row) -> str:
    """A path naming a row: directories end with ``/``."""
    if isinstance(row, tree.Directory):
        return row.path
    return row.entry.path


def _parent(key: str) -> str:
    """The directory path containing a row, empty at the top."""
    head, separator, _ = key.rstrip("/").rpartition("/")
    return head + separator
