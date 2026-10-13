#!/usr/bin/env python3

# Standard libraries.
import ast

from pathlib import Path


class TestPython35Compatibility:
    def test_syntax(self) -> None:
        for path in Path("src/bonipy35/curses_ext").glob("*.py"):
            tree = ast.parse(
                path.read_text(encoding="utf-8"), feature_version=(3, 5)
            )
            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef):
                    assert not any(
                        isinstance(child, ast.Yield)
                        for child in ast.walk(node)
                    )
