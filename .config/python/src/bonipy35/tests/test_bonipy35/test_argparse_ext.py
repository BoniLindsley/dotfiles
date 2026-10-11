#!/usr/bin/env python3

# Standard libraries.
import argparse
import inspect
import typing

from typing import List, Union

# External dependencies.
import pytest

# Internal modules.
from bonipy35.argparse_ext import (
    SimpleBooleanOptionalAction,
    add_function_argument,
)


class TestSimpleBooleanOptionalAction:
    def test_formats_both_options(self) -> None:
        action = SimpleBooleanOptionalAction(["--feature"], dest="feature")
        assert action.format_usage() == "--feature | --no-feature"

    @pytest.mark.parametrize("option", [None, "--unknown"])
    def test_ignores_unrelated_calls(self, option: Union[None, str]) -> None:
        action = SimpleBooleanOptionalAction(["--feature"], dest="feature")
        namespace = argparse.Namespace(feature="unchanged")
        action(argparse.ArgumentParser(), namespace, None, option)
        assert namespace.feature == "unchanged"

    @pytest.mark.parametrize(
        "arguments, expected",
        [
            ([], None),
            (["--feature"], True),
            (["--no-feature"], False),
            (["--feature", "--no-feature"], False),
            (["--no-feature", "--feature"], True),
        ],
    )
    def test_parses_boolean_options(
        self, arguments: List[str], expected: Union[None, bool]
    ) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument("--feature", action=SimpleBooleanOptionalAction)
        assert parser.parse_args(arguments).feature is expected

    @pytest.mark.parametrize(
        "options", [[], ["--one", "--two"], ["-f"], ["feature"]]
    )
    def test_rejects_invalid_options(self, options: List[str]) -> None:
        with pytest.raises(ValueError, match="SimpleBooleanOptionalAction"):
            SimpleBooleanOptionalAction(options, dest="feature")


class TestAddFunctionArgument:
    def test_accepts_boolean_default(self) -> None:
        def handler(feature: bool = True) -> bool:
            return feature

        parser = argparse.ArgumentParser()
        add_function_argument(parser, handler)
        assert parser.parse_args([]).feature is True
        assert parser.parse_args(["off"]).feature is False

    def test_accepts_numeric_default(self) -> None:
        def handler(count: int = 3) -> int:
            return count

        parser = argparse.ArgumentParser()
        add_function_argument(parser, handler)
        assert parser.parse_args([]).count == 3
        assert parser.parse_args(["7"]).count == 7
        with pytest.raises(SystemExit):
            parser.parse_args(["--count", "7"])

    def test_adds_boolean_options(self) -> None:
        def handler(*, feature: bool) -> bool:
            return feature

        parser = argparse.ArgumentParser()
        add_function_argument(parser, handler)
        assert parser.parse_args(["--feature"]).feature is True
        assert parser.parse_args(["--no-feature"]).feature is False
        assert "Type: bool" in parser.format_help()

    def test_parses_mixed_parameter_kinds(self) -> None:
        def handler(
            enabled: bool, count: int = 3, *, verbose: bool = False
        ) -> None:
            del enabled, count, verbose

        parser = argparse.ArgumentParser()
        add_function_argument(parser, handler)
        arguments = parser.parse_args(["YES"])
        assert arguments.enabled is True
        assert arguments.count == 3
        assert arguments.verbose is False
        arguments = parser.parse_args(["off", "5", "--verbose"])
        assert arguments.enabled is False
        assert arguments.count == 5
        assert arguments.verbose is True
        assert arguments.handler is handler

    @pytest.mark.parametrize("default", [True, False])
    def test_parses_optional_keyword_only_boolean(
        self, default: bool
    ) -> None:
        def handler(*, feature: bool = default) -> bool:
            return feature

        parser = argparse.ArgumentParser()
        add_function_argument(parser, handler)
        assert parser.parse_args([]).feature is default
        assert parser.parse_args(["--feature"]).feature is True
        assert parser.parse_args(["--no-feature"]).feature is False

    def test_parses_optional_keyword_only_value(self) -> None:
        def handler(*, count: int = 3) -> int:
            return count

        parser = argparse.ArgumentParser()
        add_function_argument(parser, handler)
        assert parser.parse_args([]).count == 3
        assert parser.parse_args(["--count", "7"]).count == 7
        with pytest.raises(SystemExit):
            parser.parse_args(["7"])

    def test_parses_optional_string_argument(self) -> None:
        def handler(name: str = "default") -> str:
            return name

        parser = argparse.ArgumentParser()
        add_function_argument(parser, handler)
        assert parser.parse_args([]).name == "default"
        assert parser.parse_args(["custom"]).name == "custom"
        assert "Default: default" in parser.format_help()

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("yes", True),
            ("y", True),
            ("true", True),
            ("t", True),
            ("1", True),
            ("on", True),
            ("no", False),
            ("n", False),
            ("false", False),
            ("f", False),
            ("0", False),
            ("off", False),
        ],
    )
    @pytest.mark.parametrize("case", ["lower", "upper", "title"])
    def test_parses_positional_boolean(
        self, value: str, expected: bool, case: str
    ) -> None:
        def handler(feature: bool) -> bool:
            return feature

        parser = argparse.ArgumentParser()
        add_function_argument(parser, handler)
        token = getattr(value, case)()
        assert parser.parse_args([token]).feature is expected

    def test_parses_positional_only_parameter(self) -> None:
        def handler(count: int) -> int:
            return count

        # Signature metadata avoids Python 3.8-only slash syntax in tests.
        setattr(
            handler,
            "__signature__",
            inspect.Signature(
                [
                    inspect.Parameter(
                        "count",
                        inspect.Parameter.POSITIONAL_ONLY,
                        annotation=int,
                    )
                ]
            ),
        )
        parser = argparse.ArgumentParser()
        add_function_argument(parser, handler)
        assert parser.parse_args(["12"]).count == 12
        with pytest.raises(SystemExit):
            parser.parse_args(["--count", "12"])

    def test_parses_required_keyword_only_value(self) -> None:
        def handler(*, count: int) -> int:
            return count

        parser = argparse.ArgumentParser()
        add_function_argument(parser, handler)
        assert parser.parse_args(["--count", "12"]).count == 12
        with pytest.raises(SystemExit) as error:
            parser.parse_args([])
        assert error.value.code == 2
        with pytest.raises(SystemExit):
            parser.parse_args(["12"])

    def test_parses_required_typed_argument(self) -> None:
        def handler(count: int) -> int:
            return count

        parser = argparse.ArgumentParser()
        add_function_argument(parser, handler)
        arguments = parser.parse_args(["12"])
        assert arguments.count == 12
        assert arguments.handler is handler

    @pytest.mark.parametrize("value", ["maybe", "2", "", "enabled", " true "])
    def test_rejects_invalid_positional_boolean(
        self, value: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def handler(feature: bool) -> bool:
            return feature

        parser = argparse.ArgumentParser()
        add_function_argument(parser, handler)
        with pytest.raises(SystemExit) as error:
            parser.parse_args([value])
        assert error.value.code == 2
        assert "boolean" in capsys.readouterr().err

    def test_rejects_missing_required_boolean(self) -> None:
        def handler(*, feature: bool) -> bool:
            return feature

        parser = argparse.ArgumentParser()
        add_function_argument(parser, handler)

        with pytest.raises(SystemExit) as error:
            parser.parse_args([])

        assert error.value.code == 2

    def test_requires_positional_boolean(self) -> None:
        def handler(feature: bool) -> bool:
            return feature

        parser = argparse.ArgumentParser()
        add_function_argument(parser, handler)
        with pytest.raises(SystemExit) as error:
            parser.parse_args([])
        assert error.value.code == 2

    def test_retains_regular_parameters_named_args_and_kwargs(self) -> None:
        def handler(args: int, kwargs: int) -> None:
            del args, kwargs

        parser = argparse.ArgumentParser()
        add_function_argument(parser, handler)
        arguments = parser.parse_args(["1", "2"])
        assert arguments.args == 1
        assert arguments.kwargs == 2

    def test_skips_args_and_kwargs(self) -> None:
        def handler(*args: typing.Any, **kwargs: typing.Any) -> None:
            del args, kwargs

        parser = argparse.ArgumentParser()
        add_function_argument(parser, handler)
        assert vars(parser.parse_args([])) == {"handler": handler}

    def test_skips_variadic_parameters_regardless_of_name(self) -> None:
        def handler(*values: int, **options: int) -> None:
            del values, options

        parser = argparse.ArgumentParser()
        add_function_argument(parser, handler)
        assert vars(parser.parse_args([])) == {"handler": handler}
