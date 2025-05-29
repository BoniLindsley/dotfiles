#!/usr/bin/env python3

# External dependencies.
import pytest

# Internal modules.
from bonipy35.result import Err, Ok, Result


class TestErr:
    def test_construct_with_value_type(self) -> None:
        instance = Err("E")  # type: Err[str]
        del instance

    def test_state_check(self) -> None:
        instance = Err("E")
        assert instance.is_err()
        assert not instance.is_ok()

    def test_unwrap_raises(self) -> None:
        instance = Err("E")
        with pytest.raises(RuntimeError):
            instance.unwrap()

    def test_unwrap_err_returns_value(self) -> None:
        instance = Err("No")
        assert instance.unwrap_err() == "No"


class TestOk:
    def test_construct_with_value_type(self) -> None:
        instance = Ok(1)
        del instance

    def test_state_check(self) -> None:
        instance = Ok(1)
        assert not instance.is_err()
        assert instance.is_ok()

    def test_unwrap_returns_value(self) -> None:
        instance = Ok(1010)
        assert instance.unwrap() == 1010

    def test_unwrap_err_raises(self) -> None:
        instance = Ok(1010)
        with pytest.raises(RuntimeError):
            instance.unwrap_err()


class TestResult:
    def test_can_be_err(self) -> None:
        result = Err(" ")  # type: Result[int, str]
        del result

    def test_can_be_ok(self) -> None:
        result = Ok(1)  # type: Result[int, str]
        del result
