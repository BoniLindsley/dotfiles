#!/usr/bin/env python3

# Standard library.
# TODO[python 3.10]: Annotations are built-in in 3.10.
from __future__ import annotations
import importlib.machinery

# External dependencies.
import speechd.client  # type: ignore[import]
import vim


_module_spec: importlib.machinery.ModuleSpec = (
    # TODO[mypy issue 4145: Module variable `__spec__` not in type hint.
    #
    # If fixed
    #
    # -   Replace all use of `_module_spec` with `__spec__`.
    # -   Remove import of `importlib.machinery`.
    #
    __spec__  # type: ignore[name-defined]
)
_package_name = (
    getattr(_module_spec, "parent", None) or _module_spec.name
)

try:
    client = speechd.client.SSIPClient(_package_name)
except AttributeError:
    pass


def echo(text: str) -> None:
    client.set_priority(speechd.client.Priority.NOTIFICATION)
    client.speak(text)
    print(text)
    client.set_priority(speechd.client.Priority.MESSAGE)


punctuation_cycle_map = {"all": "none", "none": "all"}


def cycle_punctuation() -> None:
    current_mode = client.get_punctuation()
    next_mode = punctuation_cycle_map.get(
        current_mode, speechd.client.PunctuationMode.NONE
    )
    client.set_punctuation(next_mode)
    echo(f"{next_mode} punctuation mode is active.")


def current_word() -> str:
    row, column = vim.current.window.cursor
    line: str = vim.current.line
    line.find(" ", column)


last_cursor = (0, 0)


def on_cursor_moved() -> None:
    global last_cursor
    client.set_priority(speechd.client.Priority.TEXT)
    cursor = vim.current.window.cursor
    row = cursor[0]
    last_row = last_cursor[0]
    if row != last_row:
        client.speak(vim.current.line)
    else:
        column = cursor[1]
        try:
            character = vim.current.line[column]
        except IndexError:
            client.sound_icon("empty-text")
        else:
            client.char(character)
    last_cursor = cursor
    print(cursor)
    client.set_priority(speechd.client.Priority.MESSAGE)

def on_cursor_moved_insert() -> None:
    global last_cursor
    client.set_priority(speechd.client.Priority.TEXT)
    cursor = vim.current.window.cursor
    row = cursor[0]
    last_row = last_cursor[0]
    if row != last_row:
        client.speak(vim.current.line)
    else:
        column = max(cursor[1] - 1, 0)
        try:
            character = vim.current.line[column]
        except IndexError:
            client.sound_icon("empty-text")
        else:
            client.char(character)
    last_cursor = cursor
    client.set_priority(speechd.client.Priority.MESSAGE)
