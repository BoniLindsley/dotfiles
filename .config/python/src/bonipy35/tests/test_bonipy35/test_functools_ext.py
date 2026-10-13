#!/usr/bin/env python3

# Standard libraries.
import typing

# External dependencies.
import pytest

# Internal modules.
from bonipy35.functools_ext import cached_property, nullary_cache


class _CachedValue:
    def __init__(self) -> None:
        self.calls = 0

    @cached_property
    def value(self) -> object:
        self.calls += 1
        return object()


class TestCachedProperty:
    def test_allows_override(self) -> None:
        instance = _CachedValue()
        replacement = object()
        instance.value = replacement
        assert instance.value is replacement
        assert instance.calls == 0

    def test_caches_independently(self) -> None:
        first = _CachedValue()
        second = _CachedValue()
        assert first.value is not second.value
        assert first.calls == second.calls == 1

    def test_caches_on_instance(self) -> None:
        instance = _CachedValue()
        value = instance.value
        assert instance.value is value
        assert instance.calls == 1
        assert instance.__dict__["value"] is value

    def test_recomputes_after_deletion(self) -> None:
        instance = _CachedValue()
        original = instance.value
        del instance.value
        assert instance.value is not original
        assert instance.calls == 2

    def test_retries_after_error(self) -> None:
        class FailingOnce:
            def __init__(self) -> None:
                self.calls = 0

            @cached_property
            def value(self) -> int:
                self.calls += 1
                if self.calls == 1:
                    raise ValueError("failure")
                return 42

        instance = FailingOnce()
        with pytest.raises(ValueError, match="failure"):
            _ = instance.value
        assert instance.value == 42
        assert instance.value == 42
        assert instance.calls == 2


class TestNullaryCache:
    @pytest.mark.parametrize("value", [None, False, 0, "", object()])
    def test_caches_result(self, value: typing.Any) -> None:
        calls = []  # type: typing.List[None]

        @nullary_cache
        def compute() -> typing.Any:
            calls.append(None)
            return value

        assert compute() is value
        assert compute() is value
        assert len(calls) == 1

    def test_preserves_function_metadata(self) -> None:
        def compute() -> int:
            """Compute a value."""
            return 42

        cached = nullary_cache(compute)
        assert cached.__name__ == compute.__name__
        assert cached.__doc__ == compute.__doc__
        assert cached.__module__ == compute.__module__

    def test_retries_after_error(self) -> None:
        calls = []  # type: typing.List[None]

        @nullary_cache
        def compute() -> int:
            calls.append(None)
            if len(calls) == 1:
                raise ValueError("failure")
            return 42

        with pytest.raises(ValueError, match="failure"):
            compute()
        assert compute() == 42
        assert compute() == 42
        assert len(calls) == 2

    def test_caches_each_function_independently(self) -> None:
        @nullary_cache
        def first() -> object:
            return object()

        @nullary_cache
        def second() -> object:
            return object()

        assert first() is not second()
