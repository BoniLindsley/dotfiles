#!/usr/bin/env python3

# Standard libraries.
from typing import Union


class TaskmdError(Exception):
    pass


class ParseError(TaskmdError):
    def __init__(
        self, message: str, line_number: Union[None, int] = None
    ) -> None:
        super().__init__(message)
        self.line_number = line_number
        self.message = message

    def __str__(self) -> str:
        if self.line_number is None:
            return self.message
        return "line {0}: {1}".format(self.line_number, self.message)


class ParseWarning(TaskmdError):
    def __init__(
        self, message: str, line_number: Union[None, int] = None
    ) -> None:
        super().__init__(message)
        self.line_number = line_number
        self.message = message

    def __str__(self) -> str:
        if self.line_number is None:
            return self.message
        return "line {0}: {1}".format(self.line_number, self.message)


class ClockFormatError(ParseError):
    pass


class RecurParseError(ParseError):
    pass


class StatusError(ParseError):
    pass


class TimezoneError(ParseError):
    pass


class UnknownHeadingError(ParseError):
    pass
