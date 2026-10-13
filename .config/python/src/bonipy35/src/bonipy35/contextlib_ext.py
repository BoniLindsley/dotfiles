#!/usr/bin/env python3

# Standard libraries.
import contextlib
import typing


@contextlib.contextmanager
def suppress_keyboard_interrupt() -> typing.Generator[None, None, None]:
    try:
        yield
    except KeyboardInterrupt:
        # Clear line echo-ing "^C".
        print()
