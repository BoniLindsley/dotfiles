#!/usr/bin/env python3

# Standard libraries.
import logging
import pathlib

# External dependencies.
import pytest

_logger = logging.getLogger(__name__)


@pytest.fixture(name="is_generating_reference")
def fixture_is_generating_reference(reference_path: pathlib.Path) -> bool:
    exists = reference_path.exists()
    if not exists:
        _logger.warning("Missing reference will be generated: %s", reference_path)
    return not exists


@pytest.fixture(name="reference_path")
def fixture_reference_path(request: pytest.FixtureRequest) -> pathlib.Path:
    node = request.node
    module_directory = node.path or pathlib.Path()

    module_name = module_directory.stem
    prefix = "test_"
    if module_name.startswith(prefix):
        module_name = module_name[len(prefix) :]
    module_name = "reference_" + module_name

    subdirectory_name = ".".join(node.nodeid.split("::")[1:])
    reference_path = module_directory.parent / module_name / subdirectory_name
    return reference_path


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    param_name = "input_path"
    if param_name in metafunc.fixturenames:
        node = metafunc.definition
        module_directory = node.path or pathlib.Path()

        module_name = module_directory.stem
        prefix = "test_"
        if module_name.startswith(prefix):
            module_name = module_name[len(prefix) :]
        module_name = "input_" + module_name

        subdirectory_name = ".".join(node.nodeid.split("::")[1:])
        input_directory = module_directory.parent / module_name / subdirectory_name
        assert input_directory.is_dir()
        metafunc.parametrize(param_name, input_directory.iterdir())
