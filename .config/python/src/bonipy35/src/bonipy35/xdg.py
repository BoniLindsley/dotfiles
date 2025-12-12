#!/usr/bin/env python3

# Standard libraries.
import functools
import logging
import os
import pathlib
import typing

from typing import Union

_T = typing.TypeVar("_T")

_logger = logging.getLogger(__name__)


def ensure_directory_exists(directory: pathlib.Path) -> None:
    if directory.is_dir():
        return
    directory.mkdir(parents=True, exist_ok=True)


def get_environ_path(name: str) -> Union[None, pathlib.Path]:
    source = os.environ.get(name)
    if source is None:
        return source
    return pathlib.Path(source)


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


@nullary_cache
def home() -> pathlib.Path:
    path = get_environ_path("HOME")
    if path is None:
        path = pathlib.Path()
    return path


@nullary_cache
def config_home() -> pathlib.Path:
    path = get_environ_path("XDG_CONFIG_HOME")
    if path is None:
        path = home() / ".config"
    return path


@nullary_cache
def data_home() -> pathlib.Path:
    path = get_environ_path("XDG_DATA_HOME")
    if path is None:
        path = home() / ".local" / "share"
    return path


@nullary_cache
def state_home() -> pathlib.Path:
    path = get_environ_path("XDG_STATE_HOME")
    if path is None:
        path = home() / ".local" / "state"
    return path


class AppDirectories:
    def __init__(self, *args: typing.Any, app_name: str, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self.app_name = app_name

    @property
    def config_home(self) -> pathlib.Path:
        path = config_home() / self.app_name
        ensure_directory_exists(path)
        return path

    @property
    def data_home(self) -> pathlib.Path:
        path = data_home() / self.app_name
        ensure_directory_exists(path)
        return path

    @property
    def state_home(self) -> pathlib.Path:
        path = state_home() / self.app_name
        ensure_directory_exists(path)
        return path
