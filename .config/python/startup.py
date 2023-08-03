#!/usr/bin/env python3

# Standard libraries.
import inspect
import logging
import os.path
import platform
import sys


_logger = logging.getLogger(__name__)

# Required Python 3.6 for explicit type hints on variables.
# Required Python 3.6 `open` support for `pathlib.Path`.
# Required Python 3.9 built-in templates such as `list[str]`.
# Required Python 3.10 union type support written with pipes.
if tuple(map(int, platform.python_version_tuple())) < (3, 6, 0):
    _logger.warning(
        "Not loading startup script. Python version 3.5 required."
    )
else:
    # Figure out where the python config directory is.
    startup_path = inspect.getsourcefile(lambda: None) or "."
    startup_dir = os.path.dirname(os.path.abspath(startup_path))
    sys.path.insert(0, startup_dir)
    # Do not expose local variables to REPL.
    del startup_dir
    del startup_path

    # Make exported variables available in REPL.
    from startup_loader import *  # pylint: disable=unused-import
