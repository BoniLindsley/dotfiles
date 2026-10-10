#!/usr/bin/env python3

# Standard libraries.
import pathlib


def ensure_is_dir(path: pathlib.Path) -> None:
    path.mkdir(mode=0o755, parents=True, exist_ok=True)
