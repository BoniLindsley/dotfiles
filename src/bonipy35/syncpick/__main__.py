#!/usr/bin/env python3

# Standard libraries.
import sys

from typing import List, Union

# Internal modules.
from .. import runpy_ext


def main(argv: Union[None, List[str]] = None) -> int:
    """Forward command arguments to the corresponding syncpick module."""
    return runpy_ext.subcommand_main(
        argv=argv,
        choices=("rc", "runner"),
        package=__package__,
        description="Compare and copy files with rclone.",
    )


if __name__ == "__main__":
    sys.exit(main())
