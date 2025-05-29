#!/usr/bin/env python3

# Standard libraries.
import typing

_T = typing.TypeVar("_T")
_U = typing.TypeVar("_U")


class Err(typing.Generic[_T]):
    def __init__(self, value: _T) -> None:
        self._value = value

    def is_err(self) -> bool:
        return True

    def is_ok(self) -> bool:
        return False

    # TODO(Python 3.5.10): Use NoReturn without quote.
    def unwrap(self) -> "typing.NoReturn":
        raise RuntimeError("Unable to unwrap error as ok result.")

    def unwrap_err(self) -> _T:
        return self._value


class Ok(typing.Generic[_T]):
    def __init__(self, value: _T) -> None:
        self._value = value

    def is_err(self) -> bool:
        return False

    def is_ok(self) -> bool:
        return True

    def unwrap(self) -> _T:
        return self._value

    # TODO(Python 3.5.10): Use NoReturn without quote.
    def unwrap_err(self) -> "typing.NoReturn":
        raise RuntimeError("Unable to unwrap ok result as an error.")


# TODO(Python 3.9): Use pipe instead of typing.Union.
Result = typing.Union[Ok[_T], Err[_U]]
