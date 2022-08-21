#!/usr/bin/env python3

# Standard libraries.
from __future__ import annotations
import contextlib
import functools
import pathlib
import typing

# External dependencies.
import vim  # type: ignore[import]  # pylint: disable=import-error


def removesuffix(source: str, suffix: str) -> str:
    return source[: -len(suffix)] if source.endswith(suffix) else source


def has(feature: str) -> bool:
    return typing.cast(str, vim.eval("has('" + feature + "')")) == "1"


if has("win32"):
    _EXECUTABLE_NAME = "py"
else:
    _EXECUTABLE_NAME = "python3"

vim.vars["boni_python"] = _EXECUTABLE_NAME

possible_project_path_files = (
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    "tox.ini",
)


def get_project_path(source_path: pathlib.Path) -> pathlib.Path:
    for parent in source_path.parents:
        if any(
            (parent / filename).is_file()
            for filename in possible_project_path_files
        ):
            return parent
    return source_path.parent


def get_source_filename(test_filename: str) -> str:
    if test_filename == "tests":
        return "src"
    if test_filename == "test_init.py":
        return "__init__.py"
    if test_filename.startswith("test_"):
        return test_filename[5:]
    return test_filename


def get_test_filename(source_filename: str) -> str:
    if source_filename == "src":
        return "tests"
    if source_filename == "__init__.py":
        return "test_init.py"
    if source_filename.startswith(("__", "test_")):
        return source_filename
    return "test_" + source_filename


def get_test_path(
    source_path: pathlib.Path,
    project_path: pathlib.Path | None = None,
) -> pathlib.Path:
    if project_path is None:
        project_path = get_project_path(source_path)
    assert project_path is not None
    with contextlib.suppress(ValueError):
        source_path = source_path.relative_to(project_path)
    # '{project}/a/b/c/d' -> '{project}/test_a/test_b/test_c/test_d'
    return functools.reduce(
        lambda total, value: total / get_test_filename(value),
        list(source_path.parts),
        project_path,
    )


def get_source_path(
    source_path: pathlib.Path,
    project_path: pathlib.Path | None = None,
) -> pathlib.Path:
    if project_path is None:
        project_path = get_project_path(source_path)
    assert project_path is not None
    with contextlib.suppress(ValueError):
        source_path = source_path.relative_to(project_path)
    return functools.reduce(
        lambda total, value: total / get_source_filename(value),
        list(source_path.parts),
        project_path,
    )


def on_projectionist_detect() -> None:
    source_path = pathlib.Path(vim.vars["projectionist_file"].decode())
    project_path = get_project_path(source_path)
    is_test = source_path.name.startswith("test_")
    if is_test:
        alternate_path = get_source_path(source_path, project_path)
    else:
        alternate_path = get_test_path(source_path, project_path)
    projection = {
        "*": {
            "alternate": str(alternate_path),
            "type": "test" if is_test else "source",
        }
    }
    append = vim.Function("projectionist#append", self={})
    append(str(project_path), projection)


def do_ftplugin() -> None:
    source_path = pathlib.Path(vim.current.buffer.name)
    test_path = get_test_path(source_path)
    vim.current.buffer.vars["boni_test_path"] = str(test_path)

    if source_path.anchor:
        vim.current.buffer.vars["boni_dispatch_test"] = (
            _EXECUTABLE_NAME + " " + str(test_path)
        )
    else:
        module_name = ".".join(list(test_path.parts))
        module_name = removesuffix(module_name, ".py")
        vim.current.buffer.vars["boni_dispatch_test"] = (
            _EXECUTABLE_NAME + " -m " + module_name
        )
