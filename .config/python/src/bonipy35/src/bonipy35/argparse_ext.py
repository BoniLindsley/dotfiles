#!/usr/bin/env python3

# Standard libraries.
import argparse
import inspect
import typing

from typing import List, Union


class SimpleBooleanOptionalAction(argparse.Action):
    def __init__(
        self,
        option_strings: List[str],
        *args: typing.Any,
        **kwargs: typing.Any
    ) -> None:
        if len(option_strings) != 1:
            raise ValueError(
                "SimpleBooleanOptionalAction only accepts one option."
            )
        option = option_strings[0]
        if not option.startswith("--"):
            raise ValueError(
                "SimpleBooleanOptionalAction only option starting with --"
            )
        kwargs["option_strings"] = [option, "--no" + option[1:]]
        kwargs["nargs"] = 0
        super().__init__(*args, **kwargs)

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: typing.Any,
        option_string: Union[None, str] = None,
    ) -> None:
        del parser
        del values

        if option_string is None:
            return
        if option_string in self.option_strings:
            setattr(
                namespace, self.dest, not option_string.startswith("--no-")
            )

    def format_usage(self) -> str:
        return " | ".join(self.option_strings)


def _parse_boolean(value: str) -> bool:
    normalized = value.lower()
    if normalized in {"yes", "y", "true", "t", "1", "on"}:
        return True
    if normalized in {"no", "n", "false", "f", "0", "off"}:
        return False
    raise argparse.ArgumentTypeError(
        "Expected yes/y/true/t/1/on or no/n/false/f/0/off for a boolean"
    )


def add_function_argument(
    parser: argparse.ArgumentParser, handler: typing.Callable[..., typing.Any]
) -> None:
    signature = inspect.signature(handler)
    for parameter in signature.parameters.values():
        if parameter.kind in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            continue

        help_text = []
        annotation = parameter.annotation
        is_boolean = annotation is bool
        if is_boolean:
            help_text.append("Type: " + annotation.__name__)

        is_option = parameter.kind == inspect.Parameter.KEYWORD_ONLY
        if is_option and is_boolean:
            action = (
                SimpleBooleanOptionalAction
            )  # type: str | type[argparse.Action]
        else:
            action = "store"

        if not is_option and is_boolean:
            argument_type = _parse_boolean
        else:
            argument_type = annotation

        default = parameter.default
        has_default = default is not inspect.Parameter.empty
        if has_default:
            help_text.append("Default: " + str(default))
        else:
            default = None

        name = parameter.name
        if is_option:
            name = "--" + name

        argument = parser.add_argument(
            name,
            type=argument_type,
            help=". ".join(help_text),
            default=default,
            action=action,
            nargs="?" if has_default and not is_option else None,
        )
        if is_option:
            argument.required = not has_default
    parser.set_defaults(handler=handler)
