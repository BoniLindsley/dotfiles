#!/usr/bin/env python3

# Standard libraries.
import logging
import pathlib
import typing

# Internal modules.
from . import functools_ext
from . import os_ext


_logger = logging.getLogger(__name__)


def ensure_directory_exists(directory: pathlib.Path) -> None:
    if directory.is_dir():
        return
    directory.mkdir(parents=True, exist_ok=True)



@functools_ext.nullary_cache
def home() -> pathlib.Path:
    path = os_ext.get_environ_path("HOME")
    if path is None:
        path = pathlib.Path()
    return path


@functools_ext.nullary_cache
def config_home() -> pathlib.Path:
    path = os_ext.get_environ_path("XDG_CONFIG_HOME")
    if path is None:
        path = home() / ".config"
    return path


@functools_ext.nullary_cache
def data_home() -> pathlib.Path:
    path = os_ext.get_environ_path("XDG_DATA_HOME")
    if path is None:
        path = home() / ".local" / "share"
    return path


@functools_ext.nullary_cache
def state_home() -> pathlib.Path:
    path = os_ext.get_environ_path("XDG_STATE_HOME")
    if path is None:
        path = home() / ".local" / "state"
    return path


class AppDirectories:
    def __init__(self, *args: typing.Any, app_name: str, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self.app_name = app_name

    @functools_ext.cached_property
    def config_home(self) -> pathlib.Path:
        path = config_home() / self.app_name
        ensure_directory_exists(path)
        return path

    @functools_ext.cached_property
    def data_home(self) -> pathlib.Path:
        path = data_home() / self.app_name
        ensure_directory_exists(path)
        return path

    @functools_ext.cached_property
    def state_home(self) -> pathlib.Path:
        path = state_home() / self.app_name
        ensure_directory_exists(path)
        return path
