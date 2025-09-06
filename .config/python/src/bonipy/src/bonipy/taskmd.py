#!/usr/bin/env python3

# This is a wrapper package.
# pylint: disable=unused-wildcard-import
# pylint: disable=wildcard-import
# pylint: disable=wrong-import-position

import platform

required_version = (3, 5)
if tuple(map(int, platform.python_version_tuple()[:2])) < required_version:
    raise ImportError(__name__ + " requires Python " + str(required_version))

from bonipy35.taskmd import *
