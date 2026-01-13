#!/usr/bin/env python3

# Standard libraries.
import os
import pathlib

from typing import Union


def get_environ_path(name: str) -> Union[None, pathlib.Path]:
    source = os.environ.get(name)
    if source is None:
        return source
    return pathlib.Path(source)
