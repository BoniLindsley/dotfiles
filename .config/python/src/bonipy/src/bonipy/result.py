#!/usr/bin/env python3

# Standard libraries.
import typing as _t


_T = _t.TypeVar("_T")
_U = _t.TypeVar("_U")


class Err(_t.Generic[_T]):
    def __init__(self, value: _T) -> None:
        self._value = value

    def is_err(self) -> bool:
        return True

    def is_ok(self) -> bool:
        return False

    def unwrap(self) -> _t.NoReturn:
        raise RuntimeError("Unable to unwrap error as ok result.")

    def unwrap_err(self) -> _T:
        return self._value


class Ok(_t.Generic[_T]):
    def __init__(self, value: _T) -> None:
        self._value = value

    def is_err(self) -> bool:
        return False

    def is_ok(self) -> bool:
        return True

    def unwrap(self) -> _T:
        return self._value

    def unwrap_err(self) -> _t.NoReturn:
        raise RuntimeError("Unable to unwrap ok result as an error.")


Result = Ok[_T] | Err[_U]
