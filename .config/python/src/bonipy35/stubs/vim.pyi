#!/usr/bin/env python3

# Standard libraries.
import typing

class Buffer:
    vars: object
    options: object
    name: str
    number: int
    valid: bool

    def __getitem__(self, key: int) -> str: ...
    def __iter__(self) -> typing.Self: ...
    def __len__(self) -> int: ...
    def __next__(self) -> str: ...
    def __setitem__(self, key: int, value: str) -> None: ...
    def append(self, _str: str, _nr: int) -> None: ...

class Window:
    buffer: Buffer
    col: int
    cursor: tuple[int, int]
    height: int
    number: int
    options: object
    row: int
    tabpage: object
    valid: bool
    vars: object
    width: int

class _Current:
    buffer: Buffer
    line: str
    range: object
    tabpage: object
    window: Window

current: _Current

def command(_: str) -> None: ...
def eval(_: str) -> object: ...  # pylint: disable=redefined-builtin
