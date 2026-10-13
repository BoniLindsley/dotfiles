#!/usr/bin/env python3

# Standard libraries.
import os
import pathlib

# Internal modules.
from .. import xdg


def default_directory() -> pathlib.Path:
    """Resolve the task directory without creating it."""
    directory = os.environ.get("TASKMD_DIR")
    if directory:
        return pathlib.Path(directory).expanduser()
    return xdg.data_home() / "bonipy35" / "taskmd"


def default_document() -> pathlib.Path:
    return default_directory() / "main.task.md"
