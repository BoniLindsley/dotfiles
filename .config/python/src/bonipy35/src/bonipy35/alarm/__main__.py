#!/usr/bin/env python3

# Standard libraries.
import sys

from typing import List, Union

# Internal modules.
from .. import runpy_ext


def main(argv: Union[None, List[str]] = None) -> int:
    return runpy_ext.subcommand_main(
        argv,
        package=__package__,
        choices=("cli", "cmd", "server", "gui", "tui"),
    )


if __name__ == "__main__":
    sys.exit(main())
