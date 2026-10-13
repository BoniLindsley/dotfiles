#!/usr/bin/env python3

# Standard libraries.
import argparse
import os
import pathlib

# Internal modules.
from .. import xdg


def default_directory() -> pathlib.Path:
    return xdg.state_home() / "bonipy35" / "alarm"


def prepare_directory(directory: pathlib.Path) -> pathlib.Path:
    directory = directory.resolve()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    stat = directory.stat()
    if stat.st_uid != os.getuid() or stat.st_mode & 0o077:
        raise ValueError(
            "Alarm directory must be owned by you with mode 0700"
        )
    return directory


def add_directory_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--directory", type=pathlib.Path, default=default_directory()
    )
