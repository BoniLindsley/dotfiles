#!/usr/bin/env python3

# Standard libraries.
import pathlib

from unittest import mock

# External dependencies.
import pytest

# Internal modules.
from bonipy35.inspect_ext import get_module_directory


class TestGetModuleDirectory:
    def test_propagates_unsupported_source_error(self) -> None:
        with pytest.raises(TypeError):
            get_module_directory(len)

    def test_returns_current_directory_without_source(self) -> None:
        with mock.patch(
            "bonipy35.inspect_ext.inspect.getsourcefile", return_value=None
        ):
            assert get_module_directory(lambda: None) == pathlib.Path()

    def test_returns_source_directory(self) -> None:
        assert (
            get_module_directory(lambda: None)
            == pathlib.Path(__file__).parent
        )
