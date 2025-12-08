#!/usr/bin/env python3

# Standard libraries.
import importlib
import re
import sys

sys.modules[__name__] = importlib.import_module(
    re.sub("^bonipy.", "bonipy35.", __name__)
)

del importlib
del re
del sys
