# /usr/bin/env python3

# Standard libraries.
import argparse
import asyncio
import curses
import curses.textpad
import datetime
import json
import sys
import typing as t

# Internal modules.
import bonipy.asyncio_ext
import bonipy.logging_ext
from . import raii

JsonData = t.Any


async def getch_from_window(window: curses.window) -> int:
    window.timeout(0)
    curses.doupdate()

    next_ch = window.getch()
    if next_ch == -1:
        # Timed out waiting for input.
        await bonipy.asyncio_ext.stdin_ready()
        next_ch = window.getch()
    assert next_ch != -1

    return next_ch


def getch_from_cache(cache: list[int | str]) -> int:
    try:
        next_entry = cache.pop()
    except IndexError:
        return -1
    if isinstance(next_entry, int):
        return next_entry
    first, remaining = next_entry[0], next_entry[1:]
    if remaining:
        cache.append(remaining)
    return ord(first)


class Typeahead:
    def __init__(self, *args: t.Any, window: curses.window, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)

        self._cache: list[int | str] = []
        self._cache_repeat_count = 0
        self._cache_repeat_limit = sys.getrecursionlimit()
        self._window = window

    async def getch(self) -> int:
        """
        :return: Cached input character or retrieve from ``curses``.
        :raise RecursionError:
            If pop is used a certain number of times
            without getch redirecting to user input.
            This is to prevent map recursion causing infinite loops.
            The limit is currently set as ``sys.getrecursionlimit()``.
        """
        if self._cache:
            self._cache_repeat_count += 1
            if self._cache_repeat_count > self._cache_repeat_limit:
                raise RecursionError(
                    "Too many uses of Typeahead cache without user input.",
                )
            next_ch = getch_from_cache(self._cache)
            if next_ch != -1:
                return next_ch

        self._cache_repeat_count = 0
        return await getch_from_window(self._window)

    def append(self, next_entry: int | str) -> None:
        if not next_entry and isinstance(next_entry, str):
            return
        self._cache.append(next_entry)


class MessageArea:
    def __init__(self, *args: t.Any, parent: curses.window, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)
        height, width = parent.getmaxyx()
        self.window = parent.derwin(1, width, height - 1, 0)
        self.textbox = curses.textpad.Textbox(self.window)


async def get_command_in_command_line_mode(
    *, message_area: MessageArea, typeahead: Typeahead
) -> str:
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
        next_key = await typeahead.getch()
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


class State:
    command_map: dict[str, "Command"]
    data: Data
    frame: int
    message_area: MessageArea
    normal_map: dict[str, str]
    window: curses.window
    typeahead: Typeahead


Command = t.Callable[[State], None]


def edit(state: State) -> None:
    try:
        with open("data.json", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        new(state)
        return
    data["updated_at"] = datetime.datetime.fromisoformat(data["updated_at"])
    state.data = t.cast(Data, data)
    update(state)


def new(state: State) -> None:
    state.data = new_data()


def noop(state: State) -> None:
    del state


def quit_(state: State) -> None:
    del state
    raise asyncio.CancelledError()


def redraw(state: State) -> None:
    data = state.data
    window = state.window

    last_now_string = data["updated_at"].strftime("%y-%m-%d %H:%M:%S")

    window.erase()

    window.addstr(0, 0, f"Time: {last_now_string}")
    window.addstr(1, 0, f"Frame: {state.frame}")

    window.addstr(2, 0, f"Zenny: {data['zenny']}")
    window.addstr(3, 0, f"Red Herb: {data['red_herb']}")
    window.addstr(4, 0, f"Red Potion: {data['red_potion']}")

    window.noutrefresh()


def update(state: State) -> None:
    state.frame += 1
    data = state.data

    last_updated_at = data["updated_at"].replace(microsecond=0)
    now = datetime.datetime.now()
    data["updated_at"] = now

    time_passed = now.replace(microsecond=0) - last_updated_at
    steps = int(time_passed.total_seconds())
    data["zenny"] += steps


def write(state: State) -> None:
    update(state)

    data = state.data
    json_data: JsonData = data.copy()
    json_data["updated_at"] = data["updated_at"].isoformat()
    with open("data.json", "w", encoding="utf-8") as file:
        json.dump(json_data, file)


DEFAULT_COMMAND_MAP: dict[str, Command] = {
    "edit": edit,
    "new": new,
    "noop": noop,
    "quit": quit_,
    "redraw": redraw,
    "write": write,
}

DEFAULT_NORMAL_MAP: dict[str, str] = {
    "ZZ": ":q\n",
    "\x0c": ":redraw\n",
}


def new_state(*, window: curses.window) -> State:
    state = State()
    state.command_map = DEFAULT_COMMAND_MAP.copy()
    state.frame = 0
    state.message_area = MessageArea(parent=window)
    state.normal_map = DEFAULT_NORMAL_MAP.copy()
    state.typeahead = Typeahead(window=window)
    state.window = window
    edit(state)
    return state


def process_command_in_command_mode(*, command: str, state: State) -> None:
    if not command:
        return

    command_map = state.command_map
    potential_sequences = {key for key in command_map if key.startswith(command)}
    if len(potential_sequences) == 1:
        command_map[potential_sequences.pop()](state)
    else:
        curses.beep()


async def process_command_in_normal_mode(
    *, normal_map: dict[str, str], typeahead: Typeahead
) -> None:
    potential_sequences = list(normal_map.keys())
    buffer = ""
    while potential_sequences:
        next_ch = await typeahead.getch()
        buffer += chr(next_ch)
        new_typeahead_entry = normal_map.get(buffer)
        if new_typeahead_entry is not None:
            typeahead.append(new_typeahead_entry)
            break
        potential_sequences = [
            seq for seq in potential_sequences if seq.startswith(buffer)
        ]
    else:
        curses.beep()


async def amain() -> int:
    with raii.initialise() as window:
        state = new_state(window=window)

        while True:
            redraw(state)

            next_char = await state.typeahead.getch()
            if next_char == curses.KEY_RESIZE:
                state.message_area = MessageArea(parent=window)
            else:
                state.typeahead.append(next_char)
            if next_char == ord(":"):
                command = await get_command_in_command_line_mode(
                    message_area=state.message_area,
                    typeahead=state.typeahead,
                )
                process_command_in_command_mode(command=command[1:-1], state=state)
            else:
                await process_command_in_normal_mode(
                    normal_map=state.normal_map, typeahead=state.typeahead
                )

            update(state)

    return 0


def parse_arguments(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    bonipy.logging_ext.add_verbose_flag(parser)
    return parser.parse_args(args)


def main(argv: None | list[str] = None) -> int:
    if argv is None:
        argv = sys.argv
    arguments = parse_arguments(argv[1:])

    bonipy.logging_ext.set_up_logging(verbosity=arguments.verbosity)

    try:
        return asyncio.run(amain())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
