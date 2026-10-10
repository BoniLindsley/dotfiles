#!/usr/bin/env python3

# Standard libraries.
import datetime
import re
import sys
import typing

from typing import Union


class Builder:
    def __init__(  # pylint: disable=keyword-arg-before-vararg,too-many-arguments,too-many-positional-arguments
        self,
        year: int,
        month: int,
        day: int,
        hour: Union[None, int] = None,
        minute: Union[None, int] = None,
        second: Union[None, int] = None,
        microsecond: Union[None, int] = None,
        tzinfo: Union[None, datetime.tzinfo] = None,
        fold: Union[None, int] = None,
        *args: typing.Any,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        if hour is None:
            hour = 0
        if minute is None:
            minute = 0
        if second is None:
            second = 0
        if microsecond is None:
            microsecond = 0
        if fold is None:
            fold = 0
        self._year = year
        self._month = month
        self._day = day
        self._hour = hour
        self._minute = minute
        self._second = second
        self._microsecond = microsecond
        self._tzinfo = tzinfo
        self._fold = fold

    def build(self) -> datetime.datetime:
        result = datetime.datetime(
            self._year,
            self._month,
            self._day,
            self._hour,
            self._minute,
            self._second,
            self._microsecond,
            self._tzinfo,
        )

        # Python 3.5 has no fold flag; ordinary datetimes still work.
        if sys.version_info >= (3, 6):
            result = result.replace(fold=self._fold)
        elif self._fold:
            raise ValueError("fold requires Python 3.6 or later")
        return result

    @classmethod
    def copy(
        cls: "type[typing.Self]", source: datetime.datetime
    ) -> "typing.Self":
        self = cls(
            year=source.year,
            month=source.month,
            day=source.day,
            hour=source.hour,
            minute=source.minute,
            second=source.second,
            microsecond=source.microsecond,
            tzinfo=source.tzinfo,
            fold=getattr(source, "fold", 0),
        )
        return self

    def day(self, value: int) -> "typing.Self":
        self._day = value
        return self

    def fold(self, value: int) -> "typing.Self":
        self._fold = value
        return self

    def hour(self, value: int) -> "typing.Self":
        self._hour = value
        return self

    def microsecond(self, value: int) -> "typing.Self":
        self._microsecond = value
        return self

    def minute(self, value: int) -> "typing.Self":
        self._minute = value
        return self

    def month(self, value: int) -> "typing.Self":
        self._month = value
        return self

    def second(self, value: int) -> "typing.Self":
        self._second = value
        return self

    def tzinfo(self, value: Union[None, datetime.tzinfo]) -> "typing.Self":
        self._tzinfo = value
        return self

    def utc(self) -> "typing.Self":
        self._tzinfo = datetime.timezone.utc
        return self

    def year(self, value: int) -> "typing.Self":
        self._year = value
        return self


def parse_date(value: str) -> datetime.date:
    """Parse a calendar date without Python 3.7's fromisoformat."""
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("expected YYYY-MM-DD")
    return datetime.datetime.strptime(value, "%Y-%m-%d").date()


def format_datetime(
    value: datetime.datetime, *, minutes: bool = False
) -> str:
    """Format at minute/second precision without the newer timespec API."""
    text = value.replace(microsecond=0).isoformat()
    if minutes:
        return text[:16] + text[19:]
    return text
