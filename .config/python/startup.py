#!/usr/bin/env python3

# Wrapper to import custom startup script.
# Import only if version requirements are satisfied.
# Conditional import allows REPL startup to not error
# even if requirement not satisfied by not importing.

# NOTE: Make sure not minimise local variables which are exposed to REPL.

import platform

# Required Python 3.6 for explicit type hints on variables.
# Required Python 3.6 `open` support for `pathlib.Path`.
# Required Python 3.9 built-in templates such as `list[str]`.
# Required Python 3.10 union type support written with pipes.
required_version = (3, 6)
if tuple(map(int, platform.python_version_tuple()[:2])) < required_version:
    import logging

    logging.getLogger(__name__).warning(
        "Not loading startup script. Python version %s required.",
        required_version,
    )
    del logging
else:
    # Figure out where the python config directory is.
    import inspect
    import os.path
    import sys

    startup_path = inspect.getsourcefile(lambda: None) or "."
    startup_dir = os.path.dirname(os.path.abspath(startup_path))
    sys.path.insert(0, startup_dir)
    del startup_dir
    del startup_path

    del inspect
    del os
    del sys

    # Make exported variables available in REPL.
    from startup_loader import *  # pylint: disable=unused-wildcard-import,wildcard-import
del required_version

del platform
