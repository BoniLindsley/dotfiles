#!/usr/bin/env python3

# Standard libraries.
import importlib
import re
import sys
import typing


# Overriding this module at the import level is not recognised by linters.
if typing.TYPE_CHECKING:
    from bonipy35.result import *  # pylint: disable=unused-wildcard-import,wildcard-import

# Wildcard import does not allow submodule imports.
# Override this module completely with another at the import level.
sys.modules[__name__] = importlib.import_module(
    re.sub(r"^bonipy\.", "bonipy35.", __name__)
)


del importlib
del re
del sys
del typing
