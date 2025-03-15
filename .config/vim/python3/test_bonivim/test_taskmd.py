#!/usr/bin/env python3

# Standard libraries.
import inspect
import io
import pathlib

# External dependencies.
import pytest

# Internal modules.
from bonivim.taskmd import run


def get_module_path() -> pathlib.Path:
    module_path_value = inspect.getsourcefile(lambda: None)
    if not module_path_value:
        raise RuntimeError("Unable to determine module path.")
    return pathlib.Path(module_path_value)


def get_input_paths() -> list[pathlib.Path]:
    module_path = get_module_path()
    module_directory = module_path.parent
    module_name = module_path.stem.removeprefix("test_")
    input_directory = module_directory / ("input_" + module_name)
    return sorted(input_path for input_path in input_directory.iterdir())


@pytest.fixture(
    ids=lambda path: path.name,
    name="input_path",
    params=get_input_paths(),
    scope="package",
)
def fixture_input_path(request: pytest.FixtureRequest) -> pathlib.Path:
    return request.param  # type: ignore[no-any-return]


@pytest.fixture(name="reference_path")
def fixture_reference_path(
    input_path: pathlib.Path, request: pytest.FixtureRequest
) -> pathlib.Path:
    module_path = get_module_path()
    module_directory = module_path.parent
    module_name = module_path.stem.removeprefix("test_")
    test_name = request.node.originalname  # type: str
    reference_directory = module_directory / ("reference_" + module_name) / test_name
    reference_directory.mkdir(exist_ok=True, parents=True)
    return reference_directory / (input_path.name + ".txt")


def test_run(input_path: pathlib.Path, reference_path: pathlib.Path) -> None:
    stdout = io.StringIO()
    with input_path.open() as stdin:
        assert run(stdin=stdin, stdout=stdout) == 0

    try:
        reference = reference_path.read_text()
    except FileNotFoundError:
        reference_path.write_text(stdout.getvalue())
    else:
        assert stdout.getvalue() == reference
