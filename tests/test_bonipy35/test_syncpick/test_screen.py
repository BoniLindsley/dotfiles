#!/usr/bin/env python3

# Standard libraries.
import curses
import datetime

from typing import List, Union

# External dependencies.
import pytest

# Internal modules.
from bonipy35.syncpick.compare import Entry, Side, State
from bonipy35.syncpick.screen import Action, Line, Screen, Style
from bonipy35.syncpick.tree import Model

OLD = datetime.datetime(2001, 9, 9, 1, 46, tzinfo=datetime.timezone.utc)
NEW = datetime.datetime(2026, 10, 26, 19, 40, tzinfo=datetime.timezone.utc)


def entry(
    path: str,
    state: State,
    left: Union[None, Side] = Side(size=1, modified=NEW),
    right: Union[None, Side] = Side(size=1, modified=NEW),
) -> Entry:
    return Entry(path=path, state=state, left=left, right=right)


ENTRIES = [
    entry("same/a", State.SAME),
    entry("same/b", State.SAME),
    entry(
        "sub/deep/changed",
        State.DIFFERENT,
        left=Side(size=2048, modified=NEW),
        right=Side(size=3, modified=OLD),
    ),
    entry("sub/deep/new", State.LEFT_ONLY, right=None),
    entry("sub/theirs", State.RIGHT_ONLY, left=None),
    entry("top", State.SAME),
]


@pytest.fixture(name="screen")
def fixture_screen() -> Screen:
    return Screen(Model(ENTRIES), left="a", right="b:c", height=6)


def text(line: Line) -> str:
    return "".join(segment[0] for segment in line)


def names(screen: Screen) -> List[str]:
    """Shown rows without their columns, as drawn."""
    return [line[0][0].rstrip() for line in screen.lines(80)[1:-1] if line]


def press(screen: Screen, *keys: Union[int, str]) -> List[Action]:
    return [
        screen.key(ord(key) if isinstance(key, str) else key) for key in keys
    ]


class TestScreen:
    class TestKey:
        def test_moves(self, screen: Screen) -> None:
            assert screen.page == 4
            press(screen, curses.KEY_DOWN, "j")
            assert screen.cursor == 2
            press(screen, curses.KEY_UP, "k", "k")
            assert screen.cursor == 0

        def test_scrolls(self, screen: Screen) -> None:
            # same/, sub/, deep/, changed, new, theirs, top.
            press(screen, curses.KEY_NPAGE)
            assert (screen.cursor, screen.top) == (4, 1)
            press(screen, curses.KEY_END)
            assert (screen.cursor, screen.top) == (6, 3)
            press(screen, curses.KEY_PPAGE)
            assert (screen.cursor, screen.top) == (2, 2)
            press(screen, curses.KEY_HOME)
            assert (screen.cursor, screen.top) == (0, 0)

        def test_expands_and_collapses(self, screen: Screen) -> None:
            press(screen, curses.KEY_RIGHT)
            assert names(screen)[:3] == [
                "[ ] v same/",
                "[ ]     a",
                "[ ]     b",
            ]
            press(screen, curses.KEY_LEFT)
            assert names(screen)[:2] == ["[ ] > same/", "[ ] v sub/"]
            # Expanding twice leaves it expanded.
            press(screen, "\n", curses.KEY_ENTER)
            assert names(screen)[1] == "[ ]     a"

        def test_left_goes_to_parent(self, screen: Screen) -> None:
            press(screen, curses.KEY_DOWN, curses.KEY_DOWN, curses.KEY_DOWN)
            assert names(screen)[3].endswith("changed")
            press(screen, curses.KEY_LEFT)
            assert screen.cursor == 2
            press(screen, curses.KEY_LEFT)
            assert names(screen)[2] == "[ ]   > deep/"
            press(screen, curses.KEY_LEFT)
            assert screen.cursor == 1
            press(screen, curses.KEY_END, curses.KEY_LEFT)
            # Top-level rows have no parent row.
            assert names(screen)[-1].endswith("top")

        def test_expand_ignores_files(self, screen: Screen) -> None:
            press(screen, curses.KEY_END, curses.KEY_RIGHT)
            assert screen.cursor == 6

        def test_picks_and_moves_down(self, screen: Screen) -> None:
            press(screen, curses.KEY_DOWN, " ")
            assert screen.cursor == 2
            assert names(screen)[1] == "[x] v sub/"
            assert names(screen)[2] == "[x]   v deep/"
            press(screen, " ")
            assert names(screen)[1] == "[-] v sub/"

        def test_hides_identical(self, screen: Screen) -> None:
            press(screen, curses.KEY_END, "=")
            assert screen.message == "Identical files hidden."
            # The cursor stays on the last row, now "theirs".
            assert (screen.cursor, len(screen.rows)) == (4, 5)
            assert names(screen)[-1] == "[ ]     theirs"
            press(screen, "=")
            assert screen.message == "Identical files shown."

        def test_actions(self, screen: Screen) -> None:
            assert press(screen, "q", "r", 27, "x") == [
                Action.QUIT,
                Action.COMPARE,
                Action.NONE,
                Action.NONE,
            ]

        def test_copies_picked(self, screen: Screen) -> None:
            assert press(screen, ">") == [Action.NONE]
            assert screen.message == "No picked files on the left."
            press(screen, curses.KEY_END, " ")
            assert press(screen, ">", "<") == [
                Action.COPY_LEFT_TO_RIGHT,
                Action.COPY_RIGHT_TO_LEFT,
            ]
            screen.model.picked = {"sub/theirs"}
            assert press(screen, ">", "<") == [
                Action.NONE,
                Action.COPY_RIGHT_TO_LEFT,
            ]

        def test_busy(self, screen: Screen) -> None:
            screen.busy = True
            press(screen, curses.KEY_END)
            assert (
                press(screen, " ", "=", "r", ">", "<", "x")
                == [Action.NONE] * 6
            )
            assert screen.message == "Busy; Esc stops copying."
            assert not screen.model.picked
            assert press(screen, 27, "q", curses.KEY_HOME) == [
                Action.STOP,
                Action.QUIT,
                Action.NONE,
            ]
            assert screen.cursor == 0

    class TestUpdate:
        def test_keeps_row(self, screen: Screen) -> None:
            press(screen, curses.KEY_DOWN, curses.KEY_DOWN)
            screen.refresh(ENTRIES[2:])
            assert names(screen)[screen.cursor - screen.top].endswith("deep/")

        def test_clamps_removed_row(self, screen: Screen) -> None:
            press(screen, curses.KEY_END)
            screen.refresh(ENTRIES[:2])
            assert (screen.cursor, screen.top) == (0, 0)

        def test_empty(self, screen: Screen) -> None:
            screen.refresh([])
            assert screen.current() is None
            assert (
                press(screen, curses.KEY_DOWN, " ", curses.KEY_LEFT)
                == [Action.NONE] * 3
            )
            assert screen.lines(40)[-1][0][0].startswith("No files shown.")

    class TestLines:
        @pytest.fixture(name="screen")
        def fixture_screen(self, screen: Screen) -> Screen:
            screen.height = 10
            return screen

        def test_layout(self, screen: Screen) -> None:
            lines = screen.lines(30)
            assert len(lines) == 10
            assert lines[0] == [("a  <->  b:c", Style.HEADER)]
            assert text(lines[-1]).startswith("1/7  Space pick")
            assert len(text(lines[-1])) == 30
            screen.message = "Hello"
            assert text(screen.lines(30)[-1]) == "Hello"

        def test_pads_short_pages(self) -> None:
            screen = Screen(Model(ENTRIES[:1]), height=5)
            assert screen.lines(30)[2:4] == [[], []]

        def test_directory(self, screen: Screen) -> None:
            line = screen.lines(80)[2]
            assert line[0][1] is Style.DIRECTORY
            assert line[1] == (" *1 +1 -1", Style.MUTED)

        def test_wide_file(self, screen: Screen) -> None:
            line = screen.lines(80)[4]
            assert text(line).startswith("[ ]       changed")
            assert line[1:] == [
                (" * ", Style.NORMAL),
                ("    2.0K", Style.NORMAL),
                (" 2026-10-26 19:40", Style.NEWER),
                ("       3", Style.NORMAL),
                (" 2001-09-09 01:46", Style.NORMAL),
            ]

        def test_same_values(self, screen: Screen) -> None:
            press(screen, curses.KEY_END)
            line = screen.lines(80)[7]
            assert line[0][0].strip() == "[ ]   top"
            assert line[4:] == [
                ("    same", Style.MUTED),
                (" same            ", Style.MUTED),
            ]

        def test_narrow_file(self, screen: Screen) -> None:
            # Too narrow for times, so only sizes follow the name.
            line = screen.lines(40)[5]
            assert [segment[0] for segment in line[1:]] == [
                " + ",
                "       1",
                "       -",
            ]

        def test_cuts_long_names(self, screen: Screen) -> None:
            assert screen.lines(28)[1][0][0] == "[ ] > sa~"

        def test_results(self, screen: Screen) -> None:
            screen.results = {
                "sub/deep/changed": None,
                "sub/deep/new": "denied",
            }
            lines = screen.lines(80)
            assert lines[4][-1] == (" copied", Style.GOOD)
            assert lines[5][-1] == (" failed: denied", Style.BAD)

        @pytest.mark.parametrize(
            "size, shown",
            [
                (-1, "?"),
                (1023, "1023"),
                (1536, "1.5K"),
                (5 * 1024**2, "5.0M"),
                (2048 * 1024**4, "2048.0T"),
            ],
        )
        def test_sizes(self, size: int, shown: str) -> None:
            screen = Screen(
                Model([entry("f", State.LEFT_ONLY, Side(size, NEW), None)])
            )
            assert screen.lines(80)[1][2][0].strip() == shown
