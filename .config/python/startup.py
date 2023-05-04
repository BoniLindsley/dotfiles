#!/usr/bin/env python3

# Standard libraries.
import inspect
import pathlib
import sys


startup_path = pathlib.Path(inspect.getsourcefile(lambda: None))

site_path = startup_path.with_name("packages")
sys.path.insert(0, str(site_path))
del site_path

recurse_directory = startup_path.parent / (startup_path.name + ".d")
for script_path in sorted(recurse_directory.glob("*.py")):
    with open(script_path) as script:
        exec(script.read())
    del script
    del script_path
del recurse_directory

del startup_path
