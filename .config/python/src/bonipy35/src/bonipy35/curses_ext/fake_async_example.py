#!/usr/bin/env python3

# Standard libraries.
import argparse
import collections
import curses
import curses.panel
import curses.textpad
import datetime
import json
import logging
import pathlib
import sys
import typing

# Internal dependencies.
from .. import contextlib_ext
from .. import logging_ext

from . import fake_async

NullaryCallback = typing.Callable[[], typing.Any]

_logger = logging.getLogger(__name__)


class Data:
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self.red_herb = 0
        self.red_potion = 0
        self.updated_at = datetime.datetime.now()
        self.zenny = 0

    @classmethod
    def load(cls, path: pathlib.Path) -> "typing.Self":
        with path.open(encoding="utf-8") as file:
            json_data = json.load(file)
        data = cls()
        data_members = data.__dict__
        for key, value in json_data.items():
            try:
                value = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
            except (TypeError, ValueError):
                pass
            data_members[key] = value
        return data

    def save(self, path: pathlib.Path) -> None:
        json_data = {}  # type: dict[str, typing.Any]
        for key, value in vars(self).items():
            if isinstance(value, datetime.datetime):
                json_data[key] = value.strftime("%Y-%m-%dT%H:%M:%S")
            else:
                json_data[key] = value
        with path.open("w", encoding="utf-8") as file:
            json.dump(json_data, file)


class Menu:
    def __init__(
        self,
        *args: typing.Any,
        items: "list[tuple[str, NullaryCallback]]",
        parent: "curses.window",
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.window = parent.subwin(0, 0)

        self.position = 0
        self.items = items
        self.items.append(("exit", exit))

    def navigate(self, n: int) -> None:
        self.position += n
        if self.position < 0:
            self.position = 0
        elif self.position >= len(self.items):
            self.position = len(self.items) - 1

    def print(self) -> None:
        for index, item in enumerate(self.items):
            if index == self.position:
                mode = curses.A_REVERSE
            else:
                mode = curses.A_NORMAL

            msg = str(index) + ". " + item[0]
            self.window.addstr(1 + index, 1, msg, mode)

        # key = self.window.getch()

        # if key in [curses.KEY_ENTER, ord("\n")]:
        #     if self.position == len(self.items) - 1:
        #         return
        #     self.items[self.position][1]()

        # elif key == curses.KEY_UP:
        #     self.navigate(-1)

        # elif key == curses.KEY_DOWN:
        #     self.navigate(1)


class MessageArea:
    def __init__(
        self, *args: typing.Any, parent: "curses.window", **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        height, width = parent.getmaxyx()
        self.window = window = parent.derwin(1, width, height - 1, 0)
        self.panel = curses.panel.new_panel(window)
        self.textbox = curses.textpad.Textbox(window)


class State:
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self.data = Data()
        self.is_stopping = False
        self.frame = 0

    def print(self, window: "curses.window") -> None:
        data = self.data
        last_now_string = data.updated_at.strftime("%Y-%m-%d %H:%M:%S")

        window.addstr(0, 0, "Time: " + last_now_string)
        window.addstr(1, 0, "Frame: " + str(self.frame))
        window.addstr(2, 0, "Zenny: " + str(data.zenny))
        window.addstr(3, 0, "Red Herb: " + str(data.red_herb))
        window.addstr(4, 0, "Red Potion: " + str(data.red_potion))

    def update(self) -> None:
        self.frame += 1
        data = self.data

        last_updated_at = datetime.datetime(
            year=data.updated_at.year,
            month=data.updated_at.month,
            day=data.updated_at.day,
            hour=data.updated_at.hour,
            minute=data.updated_at.minute,
            second=data.updated_at.second,
            microsecond=0,
        )
        now = datetime.datetime.now()
        now = datetime.datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=now.hour,
            minute=now.minute,
            second=now.second,
            microsecond=0,
        )
        self.data.updated_at = now

        time_passed = now.replace(microsecond=0) - last_updated_at
        steps = int(time_passed.total_seconds())
        data.zenny += steps


Command = typing.Callable[[State], State]


def edit(state: State) -> State:
    state.data = Data.load(pathlib.Path("data.json"))
    state.update()
    return state


def new(state: State) -> State:
    state.data = Data()
    return state


def noop(state: State) -> State:
    return state


def quit_(state: State) -> State:
    state = write(state)
    state.is_stopping = True
    return state


def write(state: State) -> State:
    state.update()
    state.data.save(pathlib.Path("data.json"))
    return state


command_map = {
    "edit": edit,
    "new": new,
    "quit": quit_,
    "redraw": noop,
    "write": write,
}  # type: dict[str, Command]

key_map = {
    "ZZ": ":q\n",
    "\x0c": ":redraw\n",
}


class Typeahead:
    def __init__(
        self,
        *args: typing.Any,
        getch: typing.Callable[[], fake_async.Coroutine[int]],
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self._cache = collections.deque()  # type: collections.deque[int | str]
        self._cache_repeat_count = 0
        self._getch = getch

    def getch(self) -> fake_async.Coroutine[int]:
        """
        :return: Cached input character or retrieve from ``curses``.
        :raise RecursionError: See ``popleft``.
        """
        try:
            return self.popleft()
        except IndexError:
            pass
        self._cache_repeat_count = 0
        curses.doupdate()
        return (yield from self._getch())

    def popleft(self) -> int:
        """
        :return: Next cached input character.
        :raise IndexError: If cache is empty.
        :raise RecursionError:
            If popleft is used a certain number of times
            without getch redirecting to user input.
            This is to prevent map recursion causing infinite loops.
            The limit is currently set as ``sys.getrecursionlimit()``.
        """
        self._cache_repeat_count += 1
        if self._cache_repeat_count > sys.getrecursionlimit():
            raise RecursionError(
                "Too many uses of Typeahead cache without user input.",
            )
        next_entry = self._cache.popleft()
        if isinstance(next_entry, int):
            return next_entry
        first, remaining = next_entry[0], next_entry[1:]
        if remaining:
            self.appendleft(remaining)
        return ord(first)

    def appendleft(self, next_entry: "int | str") -> None:
        self._cache.appendleft(next_entry)


def get_command_in_command_line_mode(
    *, message_area: MessageArea, typeahead: Typeahead
) -> fake_async.Coroutine[str]:
    textbox = message_area.textbox
    window = message_area.window
    window.clear()
    empty_check_keys = {
        0x04,  # Ctrl+D for deleting current character.
        0x08,  # Ctrl+H for deleting last character.
        0x0B,  # Ctrl+K for deleting line.
        curses.KEY_BACKSPACE,  # Physical key input.
    }
    while True:
        next_key = yield from typeahead.getch()
        if next_key == 7:  # Ctrl+G to cacnel.
            window.clear()
            break
        if next_key == 10:  # Ctrl+J to also act as return.
            break
        textbox.do_command(next_key)
        # Early exit if textbox empty. Only check on using backspace.
        if next_key in empty_check_keys:
            if not textbox.gather():
                break
        window.noutrefresh()
    window.noutrefresh()
    return textbox.gather()


def process_command_in_command_mode(*, command: str, state: State) -> State:
    if command:
        potential_sequences = {key for key in command_map if key.startswith(command)}
        if len(potential_sequences) == 1:
            state = command_map[potential_sequences.pop()](state)
        else:
            curses.beep()
    return state


def process_command_in_normal_mode(
    *, typeahead: Typeahead
) -> fake_async.Coroutine[None]:
    potential_sequences = list(key_map.keys())
    buffer = ""
    while potential_sequences:
        next_ch = yield from typeahead.getch()
        try:
            next_char = chr(next_ch)
        except ValueError:
            potential_sequences.clear()
            continue
        buffer += next_char
        new_typeahead_entry = key_map.get(buffer)
        if new_typeahead_entry is not None:
            typeahead.appendleft(new_typeahead_entry)
            break
        potential_sequences = [
            seq for seq in potential_sequences if seq.startswith(buffer)
        ]
    else:
        curses.beep()


def refresh(*, window: "curses.window") -> typing.Generator[None, None, None]:
    window.clear()
    while True:
        window.noutrefresh()
        yield


def async_run() -> fake_async.Coroutine[int]:
    loop = fake_async.get_running_loop()
    stdscr = loop.open()
    message_area = MessageArea(parent=stdscr)
    typeahead = Typeahead(getch=loop.getch)

    state = State()
    state = edit(state)
    while not state.is_stopping:
        stdscr.clear()
        state.print(stdscr)
        stdscr.noutrefresh()

        next_char = yield from typeahead.getch()
        if next_char == curses.KEY_RESIZE:
            message_area = MessageArea(parent=stdscr)
        else:
            typeahead.appendleft(next_char)
        if next_char == ord(":"):
            command = yield from get_command_in_command_line_mode(
                message_area=message_area,
                typeahead=typeahead,
            )
            state = process_command_in_command_mode(command=command[1:-1], state=state)
        else:
            yield from process_command_in_normal_mode(typeahead=typeahead)

        state.update()
    return 0


def run() -> int:
    return_value = fake_async.run(async_run())
    return return_value or 0


def main(argv: "None | list[str]" = None) -> int:
    """Parse command line arguments and call `run`."""

    if argv is None:
        argv = sys.argv

    logging_ext.set_up_logging(logger=_logger)

    parser = argparse.ArgumentParser()
    logging_ext.add_verbose_flag(parser)
    arguments = parser.parse_args(argv[1:])

    logging_ext.set_logger_verbosity(logger=_logger, verbosity=arguments.verbosity)

    with contextlib_ext.suppress_keyboard_interrupt():
        return run()

    return 2


if __name__ == "__main__":
    sys.exit(main())
