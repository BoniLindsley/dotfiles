#!/usr/bin/env python3

# Standard libraries.
import functools
import typing

from typing import Union

_T = typing.TypeVar("_T")
_U = typing.TypeVar("_U")


class cached_property(typing.Generic[_T, _U]):  # pylint: disable=invalid-name
    def __init__(self, function: typing.Callable[[_T], _U]) -> None:
        self.__function = function

    def __get__(self, instance: _T, owner: Union[None, typing.Type[_T]] = None) -> _U:
        del owner
        function = self.__function
        value = function(instance)
        setattr(instance, function.__name__, value)
        return value


def nullary_cache(function: typing.Callable[[], _T]) -> typing.Callable[[], _T]:
    lookup = {}  # type: dict[None, _T]

    @functools.wraps(function)
    def wrapper() -> _T:
        try:
            return lookup[None]
        except KeyError:
            pass
        result = lookup[None] = function()
        return result

    return wrapper
