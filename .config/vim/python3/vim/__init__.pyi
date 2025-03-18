#!/usr/bin/env python3

# pylint: disable=unused-argument

# Standard libraries.
import typing

Buffer = typing.Any
Range = typing.Any
String = typing.Any
TabPage = typing.Any

class Window:
    cursor: tuple[int, int]
    height: int
    options: dict[str, typing.Any]  # Fixed keys.
    valid: bool
    vars: dict[str, typing.Any]  # Fixed keys.
    width: int

    @property
    def buffer(self) -> Buffer: ...
    @property
    def col(self) -> int: ...
    @property
    def number(self) -> int: ...
    @property
    def row(self) -> int: ...
    @property
    def tabpage(self) -> TabPage: ...

class Current:
    buffer: Buffer
    line: String
    tabpage: TabPage
    window: Window

    @property
    def range(self) -> Range: ...

current: Current

def eval(  # pylint: disable=redefined-builtin
    argument: str,
) -> dict[str, typing.Any] | list[str] | str: ...
