#!/usr/bin/env python3

# Standard libraries.
import importlib
import inspect
import logging
import pathlib
import sys


__all__ = []
_logger = logging.getLogger(__name__)

startup_path = pathlib.Path(inspect.getsourcefile(lambda: None) or ".")

site_path = startup_path.with_name("packages")
_logger.debug("Using packages in %s", site_path)
sys.path.insert(0, str(site_path))

for package_path in sorted((startup_path.parent / "src").iterdir()):
    if package_path.name.startswith("."):
        continue
    for sys_path in (package_path / "src", package_path):
        if sys_path.is_dir():
            _logger.debug("Using packages in %s", sys_path)
            sys.path.insert(0, str(sys_path))
            break

recurse_directory = startup_path.parent / "startup.py.d"
sys.path.insert(0, str(recurse_directory))
for script_path in sorted(recurse_directory.glob("*.py")):
    imported_module = importlib.import_module(script_path.stem)
    try:
        module_variables = getattr(imported_module, "__all__")
    except AttributeError:
        module_variables = [
            attribute
            for attribute in dir(imported_module)
            if attribute and attribute[0] != "_"
        ]
    globals().update(
        {
            attribute: getattr(imported_module, attribute)
            for attribute in module_variables
        }
    )
    __all__.extend(module_variables)
