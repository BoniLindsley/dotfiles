#!/usr/bin/env python3

# Standard libraries.
import sys

from typing import List, Union

# Internal modules.
from . import runpy_ext


def main(argv: Union[None, List[str]] = None) -> int:
    """Parse command line arguments and forward to a submodule."""
    return runpy_ext.subcommand_main(
        argv=argv,
        choices=[
            "alarm",
            "bapt",
            "curses_ext",
            "logging_ext",
            "taskmd",
        ],
        package=__package__,
    )


if __name__ == "__main__":
    sys.exit(main())
