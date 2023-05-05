#!/usr/bin/env python3

# Standard libraries.
import inspect
import logging
import pathlib
import sys

_logger = logging.getLogger(__name__)


startup_path = pathlib.Path(inspect.getsourcefile(lambda: None) or ".")

site_path = startup_path.with_name("packages")
_logger.debug("Using packages in %s", site_path)
sys.path.insert(0, str(site_path))
del site_path

for package_path in sorted((startup_path.parent / "src").iterdir()):
    for sys_path in (package_path / "src", package_path):
        if sys_path.is_dir():
            _logger.debug("Using packages in %s", sys_path)
            sys.path.insert(0, str(sys_path))
            break
    del sys_path
    del package_path

recurse_directory = startup_path.parent / (startup_path.name + ".d")
for script_path in sorted(recurse_directory.glob("*.py")):
    with open(script_path, encoding="utf-8") as script:
        _logger.debug("Loading source at %s", script_path)
        # Mimicking bash source.
        exec(script.read())  # pylint: disable=exec-used
    del script
    del script_path
del recurse_directory

del startup_path
