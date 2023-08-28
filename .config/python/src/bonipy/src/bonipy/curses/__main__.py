# /usr/bin/env python3

# Standard libraries.
import collections
import curses
import curses.textpad
import datetime
import json
import logging
import sys
import typing as t

# Internal dependencies.
import bonipy.curses as curses_async

# In Windows native, need windows-curses

# In MSYS2, might need
# export TERMINFO=$MSYSTEM_PREFIX/share/terminfo

_P = t.ParamSpec("_P")

JsonData = t.Any
NullaryCallable = t.Callable[[], t.Any]

_logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def stop_running_loop() -> None:
    curses_async.get_running_loop().stop()


class Data(t.TypedDict):
    red_herb: int
    red_potion: int
    updated_at: datetime.datetime
    zenny: int


def new_data() -> Data:
    data: Data = {
        "red_herb": 0,
        "red_potion": 0,
        "zenny": 0,
        "updated_at": datetime.datetime.now(),
    }
    return data


class MessageArea:
    def __init__(self, *args: t.Any, parent: curses.window, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)
        height, width = parent.getmaxyx()
        self.window = parent.derwin(1, width, height - 1, 0)
        self.textbox = curses.textpad.Textbox(self.window)


class State:
    def __init__(self, *args: _P.args, **kwargs: _P.kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.frame = 0
        self.data = new_data()

    def print(self, window: curses.window) -> None:
        data = self.data
        last_now_string = data["updated_at"].strftime("%y-%m-%d %H:%M:%S")

        window.addstr(0, 0, f"Time: {last_now_string}")
        window.addstr(1, 0, f"Frame: {self.frame}")

        window.addstr(2, 0, f"Zenny: {data['zenny']}")
        window.addstr(3, 0, f"Red Herb: {data['red_herb']}")
        window.addstr(4, 0, f"Red Potion: {data['red_potion']}")

    def update(self) -> None:
        self.frame += 1
        data = self.data

        last_updated_at = data["updated_at"].replace(microsecond=0)
        now = datetime.datetime.now()
        data["updated_at"] = now

        time_passed = now.replace(microsecond=0) - last_updated_at
        steps = int(time_passed.total_seconds())
        data["zenny"] += steps


Command = t.Callable[[State], State]


def edit(state: State) -> State:
    with open("data.json", encoding="utf-8") as file:
        data = json.load(file)
    data["updated_at"] = datetime.datetime.fromisoformat(data["updated_at"])
    state.data = t.cast(Data, data)
    state.update()
    return state


def new(state: State) -> State:
    state.data = new_data()
    return state


def noop(state: State) -> State:
    return state


def quit_(state: State) -> State:
    state = write(state)
    stop_running_loop()
    return state


def write(state: State) -> State:
    state.update()

    data = state.data
    json_data: JsonData = data.copy()
    json_data["updated_at"] = data["updated_at"].isoformat()
    with open("data.json", "w", encoding="utf-8") as file:
        json.dump(json_data, file)
    return state


command_map: dict[str, Command] = {
    "edit": edit,
    "new": new,
    "quit": quit_,
    "redraw": noop,
    "write": write,
}

key_map: dict[str, str] = {
    "ZZ": ":q\n",
    "\x0c": ":redraw\n",
}


class Typeahead:
    def __init__(
        self,
        *args: t.Any,
        getch: t.Callable[[], curses_async.Coroutine[int]],
        **kwargs: t.Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._cache = collections.deque[int | str]()
        self._cache_repeat_count = 0
        self._getch = getch

    def getch(self) -> curses_async.Coroutine[int]:
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

    def appendleft(self, next_entry: int | str) -> None:
        self._cache.appendleft(next_entry)


def get_command_in_command_line_mode(
    *, message_area: MessageArea, typeahead: Typeahead
) -> curses_async.Coroutine[str]:
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
) -> curses_async.Coroutine[None]:
    potential_sequences = list(key_map.keys())
    buffer = ""
    while potential_sequences:
        next_ch = yield from typeahead.getch()
        buffer += chr(next_ch)
        new_typeahead_entry = key_map.get(buffer)
        if new_typeahead_entry is not None:
            typeahead.appendleft(new_typeahead_entry)
            break
        potential_sequences = [
            seq for seq in potential_sequences if seq.startswith(buffer)
        ]
    else:
        curses.beep()


def refresh(*, window: curses.window) -> collections.abc.Generator[None, None, None]:
    window.clear()
    while True:
        window.noutrefresh()
        yield


def async_main() -> curses_async.Coroutine[int]:
    loop = curses_async.get_running_loop()
    stdscr = loop.open()
    message_area = MessageArea(parent=stdscr)
    typeahead = Typeahead(getch=loop.getch)

    state = State()
    state = edit(state)
    while True:
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


def main() -> int:
    return_value = curses_async.run(async_main())
    return return_value if return_value is not None else 1


if __name__ == "__main__":
    sys.exit(main())
