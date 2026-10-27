#!/usr/bin/env python3

# Standard libraries.
import asyncio
import curses
import datetime
import itertools

from typing import Any, Awaitable, Callable, Generator, List, Union
from unittest.mock import Mock, call

# External dependencies.
import pytest

# Internal modules.
from bonipy35 import asyncio_ext
from bonipy35.curses_ext.selector_loop import use_event_loop_policy
from bonipy35.syncpick.compare import Entry, Side, State
from bonipy35.syncpick.rc import RcError
from bonipy35.syncpick.screen import Screen, Style
from bonipy35.syncpick.transfer import Direction, Result
from bonipy35.syncpick.tree import Model
from bonipy35.syncpick.tui import App, attributes, draw, run

SIDE = Side(size=1, modified=datetime.datetime(2026, 1, 1))

ENTRIES = [
    Entry(path="new", state=State.LEFT_ONLY, left=SIDE, right=None),
    Entry(path="old", state=State.LEFT_ONLY, left=SIDE, right=None),
    Entry(path="same", state=State.SAME, left=SIDE, right=SIDE),
]

ESCAPE = 27


@pytest.fixture(name="window")
def fixture_window(
    monkeypatch: pytest.MonkeyPatch, selectable_stdin: None
) -> Mock:
    del selectable_stdin
    window = Mock()
    window.getmaxyx.return_value = (6, 41)
    monkeypatch.setattr(curses, "doupdate", Mock())
    return window


class Keys:
    """Feed keys to ``App.run``, each once it waits for one."""

    def __init__(self) -> None:
        self.queue = asyncio.Queue()  # type: asyncio.Queue[int]
        self.waiting = asyncio.Event()

    async def getch(self) -> int:
        self.waiting.set()
        return await self.queue.get()

    async def press(self, key: Union[int, str]) -> None:
        """Press a key and wait until the app waits for the next one."""
        await self.waiting.wait()
        self.waiting.clear()
        self.queue.put_nowait(ord(key) if isinstance(key, str) else key)
        if key != "q":
            await self.waiting.wait()


class Fakes:
    """Comparisons and copies recorded instead of run."""

    def __init__(self) -> None:
        self.entries = list(ENTRIES)
        self.compared = 0
        self.copied = []  # type: List[Any]
        self.errors = {}  # type: dict[str, str]
        self.on_copy = lambda path: None  # type: Callable[[str], None]

    def compare_files(self, left: str, right: str) -> List[Entry]:
        assert (left, right) == ("a", "b")
        self.compared += 1
        return self.entries

    def copy_files(
        self, left: str, right: str, paths: List[str], *, direction: Direction
    ) -> Generator[Result, None, None]:
        assert (left, right) == ("a", "b")
        self.copied.append((paths, direction))
        for path in paths:
            self.on_copy(path)
            yield Result(path=path, error=self.errors.get(path))


def make_app(window: Mock, fakes: Fakes) -> App:
    return App(
        view=Screen(Model(), left="a", right="b"),
        window=window,
        compare_files=fakes.compare_files,
        copy_files=fakes.copy_files,
    )


def play(
    window: Mock,
    fakes: Fakes,
    scenario: Callable[[App, Keys], Awaitable[None]],
) -> App:
    """Run the app with a scenario pressing keys, which must end with q."""
    app = make_app(window, fakes)

    async def main() -> None:
        keys = Keys()
        running = asyncio.ensure_future(app.run(keys.getch))
        await keys.waiting.wait()
        await scenario(app, keys)
        await running

    asyncio_ext.run(main())
    return app


class TestAttributes:
    def test_without_colours(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(curses, "has_colors", Mock(return_value=False))
        styles = attributes()
        assert styles[Style.MUTED] == curses.A_DIM
        assert set(styles) == set(Style)

    @pytest.mark.parametrize(
        "default_colours, background", [(True, -1), (False, 0)]
    )
    def test_with_colours(
        self,
        monkeypatch: pytest.MonkeyPatch,
        default_colours: bool,
        background: int,
    ) -> None:
        monkeypatch.setattr(curses, "has_colors", Mock(return_value=True))
        use_default_colors = Mock(
            side_effect=None if default_colours else curses.error
        )
        monkeypatch.setattr(curses, "use_default_colors", use_default_colors)
        init_pair = Mock()
        monkeypatch.setattr(curses, "init_pair", init_pair)
        monkeypatch.setattr(curses, "color_pair", lambda number: number << 8)
        monkeypatch.setattr(curses, "COLOR_BLACK", 0, raising=False)
        styles = attributes()
        assert init_pair.call_args_list == [
            call(1, curses.COLOR_YELLOW, background),
            call(2, curses.COLOR_GREEN, background),
            call(3, curses.COLOR_RED, background),
        ]
        assert styles[Style.BAD] == curses.A_BOLD | 3 << 8


class TestDraw:
    def test_lines(self, window: Mock) -> None:
        view = Screen(Model(ENTRIES), left="a", right="b", height=24)
        styles = {style: 0 for style in Style}
        styles[Style.HEADER] = curses.A_BOLD
        draw(window, view, styles)
        # Fitted to the window, leaving the last column free.
        assert view.height == 6
        window.erase.assert_called_once_with()
        calls = window.addnstr.call_args_list
        assert calls[0] == call(0, 0, "a  <->  b", 40, curses.A_BOLD)
        cursor = [c for c in calls if c[0][0] == 1]
        assert all(c[0][4] == curses.A_REVERSE for c in cursor)
        # The cursor row is filled to the edge.
        assert cursor[-1][0][1] + cursor[-1][0][3] == 40
        assert all(c[0][4] == 0 for c in calls if c[0][0] == 2)
        window.noutrefresh.assert_called_once_with()

    def test_fills_cursor_row(self, window: Mock) -> None:
        window.getmaxyx.return_value = (6, 121)
        # Directory rows are shorter than the window; file rows fill it.
        nested = [entry._replace(path="d/" + entry.path) for entry in ENTRIES]
        view = Screen(Model(nested), left="a", right="b")
        draw(window, view, {style: 0 for style in Style})
        cursor = [c[0] for c in window.addnstr.call_args_list if c[0][0] == 1]
        assert cursor[-1][2].strip() == ""
        assert cursor[-1][1] + cursor[-1][3] == 120

    def test_clips_to_width(self, window: Mock) -> None:
        window.getmaxyx.return_value = (6, 12)
        view = Screen(Model(ENTRIES), left="a", right="b")
        draw(window, view, {style: 0 for style in Style})
        for args in (c[0] for c in window.addnstr.call_args_list):
            assert args[1] < 11 and args[1] + args[3] == 11

    def test_without_rows(self, window: Mock) -> None:
        draw(window, Screen(Model()), {style: 0 for style in Style})
        assert all(c[0][4] == 0 for c in window.addnstr.call_args_list)


class TestApp:
    def test_compares_first(self, window: Mock) -> None:
        fakes = Fakes()

        async def scenario(app: App, keys: Keys) -> None:
            assert app.task is not None
            await app.task
            assert app.view.message == "3 files, 1 the same."
            assert not app.view.busy
            await keys.press("q")

        app = play(window, fakes, scenario)
        assert fakes.compared == 1
        assert app.stopping.is_set()

    def test_compare_fails(self, window: Mock) -> None:
        fakes = Fakes()

        def fail(left: str, right: str) -> List[Entry]:
            raise RcError("no remote", path="operations/list", status=500)

        async def scenario(app: App, keys: Keys) -> None:
            assert app.task is not None
            await app.task
            app.compare_files = fail
            await keys.press("r")
            assert app.task is not None
            await app.task
            assert app.view.message.startswith("Comparing failed: ")
            assert "no remote" in app.view.message
            await keys.press("q")

        play(window, fakes, scenario)

    def test_copies(self, window: Mock) -> None:
        fakes = Fakes()
        fakes.errors = {"old": "denied"}

        async def scenario(app: App, keys: Keys) -> None:
            assert app.task is not None
            await app.task
            for key in (" ", " ", ">"):
                await keys.press(key)
            assert app.view.busy
            await app.task
            assert not app.view.busy
            await keys.press("q")

        app = play(window, fakes, scenario)
        assert fakes.copied == [(["new", "old"], Direction.LEFT_TO_RIGHT)]
        assert fakes.compared == 2
        assert app.view.results == {"new": None, "old": "denied"}
        assert app.view.message == (
            "Copied 1 of 2, 1 failed. 3 files, 1 the same."
        )
        # Failed files stay picked.
        assert app.view.model.picked == {"old"}

    def test_copies_right_to_left(self, window: Mock) -> None:
        fakes = Fakes()
        fakes.entries = [
            Entry(
                path="theirs", state=State.RIGHT_ONLY, left=None, right=SIDE
            )
        ]

        async def scenario(app: App, keys: Keys) -> None:
            assert app.task is not None
            await app.task
            await keys.press(" ")
            await keys.press("<")
            await app.task
            await keys.press("q")

        app = play(window, fakes, scenario)
        assert fakes.copied == [(["theirs"], Direction.RIGHT_TO_LEFT)]
        assert app.view.message.startswith("Copied 1 of 1. ")

    def test_stops_between_files(self, window: Mock) -> None:
        fakes = Fakes()

        async def scenario(app: App, keys: Keys) -> None:
            # Escape arrives while the first file copies.
            fakes.on_copy = lambda path: app.stopping.set()
            assert app.task is not None
            await app.task
            await keys.press(curses.KEY_HOME)
            for key in (" ", " ", ">"):
                await keys.press(key)
            await app.task
            await keys.press("q")

        app = play(window, fakes, scenario)
        assert app.view.results == {"new": None}
        assert app.view.message.startswith("Stopped after 1 of 2. ")

    def test_escape_sets_stopping(self, window: Mock) -> None:
        fakes = Fakes()

        async def scenario(app: App, keys: Keys) -> None:
            await keys.press(ESCAPE)
            # The comparison may or may not have finished by now.
            assert app.task is not None
            await app.task
            app.view.busy = True
            app.stopping.clear()
            await keys.press(ESCAPE)
            assert app.stopping.is_set()
            assert app.view.message.startswith("Stopping")
            app.view.busy = False
            await keys.press("q")

        play(window, fakes, scenario)

    def test_quit_while_copying(
        self, window: Mock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fakes = Fakes()

        async def scenario(app: App, keys: Keys) -> None:
            assert app.task is not None
            await app.task
            loop = asyncio.get_event_loop()
            original = loop.call_soon_threadsafe

            def closed(callback: Any, *args: Any) -> Any:
                if getattr(callback, "__name__", "") == "report":
                    raise RuntimeError("Event loop is closed")
                return original(callback, *args)

            monkeypatch.setattr(loop, "call_soon_threadsafe", closed)
            await keys.press(" ")
            await keys.press(">")
            await app.task
            await keys.press("q")

        app = play(window, fakes, scenario)
        # The worker stopped at the first unreported result.
        assert app.view.results == {}
        assert fakes.copied == [(["new"], Direction.LEFT_TO_RIGHT)]


class TestRun:
    def test_quits(
        self, window: Mock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(curses, "has_colors", Mock(return_value=False))
        # Then no key, as when the wait times out.
        window.getch.side_effect = itertools.chain(
            [ord("q")], itertools.repeat(-1)
        )
        daemon = Mock()
        daemon.call.return_value = {"list": [], "combined": []}
        with use_event_loop_policy(window):
            asyncio_ext.run(run(daemon, "a", "b"))
        assert window.addnstr.call_args_list[0][0][2] == "a  <->  b"
