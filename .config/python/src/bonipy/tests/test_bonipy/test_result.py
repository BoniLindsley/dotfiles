#!/usr/bin/env python3

# External dependencies.
import pytest

# Internal modules.
from bonipy.result import Err, Ok, Result


class TestErr:
    def test_construct_with_value_type(self) -> None:
        instance: Err[str] = Err("E")
        del instance

    def test_state_check(self) -> None:
        instance: Err[str] = Err("E")
        assert instance.is_err()
        assert not instance.is_ok()

    def test_unwrap_raises(self) -> None:
        instance: Err[str] = Err("E")
        with pytest.raises(RuntimeError):
            instance.unwrap()

    def test_unwrap_err_returns_value(self) -> None:
        instance: Err[str] = Err("No")
        assert instance.unwrap_err() == "No"


class TestOk:
    def test_construct_with_value_type(self) -> None:
        instance: Ok[int] = Ok(1)
        del instance

    def test_state_check(self) -> None:
        instance: Ok[int] = Ok(1)
        assert not instance.is_err()
        assert instance.is_ok()

    def test_unwrap_returns_value(self) -> None:
        instance: Ok[int] = Ok(1010)
        assert instance.unwrap() == 1010

    def test_unwrap_err_raises(self) -> None:
        instance: Ok[int] = Ok(1010)
        with pytest.raises(RuntimeError):
            instance.unwrap_err()


class TestResult:
    def test_can_be_err(self) -> None:
        result: Result[int, str] = Err(" ")
        del result

    def test_can_be_ok(self) -> None:
        result: Result[int, str] = Ok(1)
        del result
