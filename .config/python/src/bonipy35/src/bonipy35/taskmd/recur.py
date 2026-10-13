#!/usr/bin/env python3

"""`RECUR` rule string parsing and recurrence expansion.

This module is deliberately free of file I/O: it only knows how to
turn a rule string (the bit after the `RECUR` sentinel on an `EVENT`
heading, e.g. `"+1w MON,WED"`) into a `RecurRule`, and how to
expand a `RecurRule` anchored at a given datetime into concrete
occurrence datetimes within a window. See `SPEC.md` section 7.3.

Prefix semantics (`+`, `++`, `.+`) mirror org-mode's repeat cookies
and describe how a *single* next occurrence should be rescheduled
relative to when a recurring item was last completed. This data
model has no notion of "last completed occurrence" separate from an
event's own `CLOCK:` history, so `expand` treats all three prefixes
identically: a fixed-cadence sequence anchored at `anchor`. The
prefix is still parsed and stored on `RecurRule.prefix` so that it
round-trips through `RecurRule.raw` and is available to any future
feature that wants to distinguish them.
"""

# Standard libraries.
import calendar
import datetime
import re
import typing

from typing import List, Union

# Internal modules.
from .. import datetime_ext

from . import errors

WEEKDAY_NAMES = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")

_RULE_RE = re.compile(
    r"^(?P<prefix>\+\+|\.\+|\+)"
    r"(?P<interval>\d+)"
    r"(?P<unit>[dwmy])"
    r"(?:\s+(?P<weekdays>[A-Za-z0-9,-]+))?"
    r"(?:\s+@(?P<until>\d{4}-\d{2}-\d{2}))?"
    r"\s*$",
)

_NTH_WEEKDAY_RE = re.compile(
    r"^(?P<nth>-?\d+)(?P<day>{0})$".format("|".join(WEEKDAY_NAMES)),
)


class RecurRule:
    def __init__(  # pylint: disable=too-many-arguments
        self,
        *args: typing.Any,
        interval: int,
        prefix: 'typing.Literal["+", "++", ".+"]',
        raw: str,
        unit: 'typing.Literal["d", "w", "m", "y"]',
        until: Union[None, datetime.date] = None,
        weekdays: Union[None, List[str]] = None,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.interval = interval
        self.prefix = prefix
        self.raw = raw
        self.unit = unit
        self.until = until
        self.weekdays = weekdays


def parse_rule(
    raw: str, *, line_number: Union[None, int] = None
) -> RecurRule:
    """Parse a `RECUR` rule string (e.g. `"++1m 2MON @2026-12-31"`).

    Raises `errors.RecurParseError` if `raw` does not match the
    grammar in `SPEC.md` section 7.3. Never raises anything else.
    """
    match = _RULE_RE.match(raw.strip())
    if not match:
        raise errors.RecurParseError(
            "malformed RECUR rule: {0!r}".format(raw), line_number
        )

    prefix = typing.cast(
        'typing.Literal["+", "++", ".+"]', match.group("prefix")
    )
    interval = int(match.group("interval"))
    if interval < 1:
        raise errors.RecurParseError(
            "RECUR interval must be >= 1: {0!r}".format(raw), line_number
        )
    unit = typing.cast(
        'typing.Literal["d", "w", "m", "y"]', match.group("unit")
    )

    weekdays_raw = match.group("weekdays")
    weekdays = (
        parse_weekdays(
            weekdays_raw, unit, raw_rule=raw, line_number=line_number
        )
        if weekdays_raw
        else []
    )  # type: List[str]

    until_raw = match.group("until")
    try:
        until = datetime_ext.parse_date(until_raw) if until_raw else None
    except ValueError as error:
        raise errors.RecurParseError(
            "invalid UNTIL date: {0!r}".format(until_raw), line_number
        ) from error

    return RecurRule(
        raw=raw,
        prefix=prefix,
        interval=interval,
        unit=unit,
        weekdays=weekdays,
        until=until,
    )


def parse_weekdays(
    selector: str,
    unit: str,
    *,
    raw_rule: str,
    line_number: Union[None, int] = None
) -> List[str]:
    """Parse the `WEEKDAYS` component of a `RECUR` rule.

    `selector` is one of: a comma-separated list of named days
    (`"MON,WED"`, only valid with `unit == "w"`), a single nth-weekday
    selector (`"2MON"`, `"-1FRI"`, only valid with `unit == "m"`), or
    a single bare named day (`"MON"`, only valid with `unit == "w"`).
    """
    if "," in selector:
        if unit != "w":
            raise errors.RecurParseError(
                "comma-separated weekday list is only valid with unit "
                "'w': {0!r}".format(raw_rule),
                line_number,
            )
        parts = selector.split(",")
        for part in parts:
            if part not in WEEKDAY_NAMES:
                raise errors.RecurParseError(
                    "invalid weekday {0!r} in RECUR rule: {1!r}".format(
                        part, raw_rule
                    ),
                    line_number,
                )
        return list(parts)

    nth_match = _NTH_WEEKDAY_RE.match(selector)
    if nth_match:
        if unit != "m":
            raise errors.RecurParseError(
                "nth-weekday selector is only valid with unit "
                "'m': {0!r}".format(raw_rule),
                line_number,
            )
        if int(nth_match.group("nth")) == 0:
            raise errors.RecurParseError(
                "nth weekday cannot be zero: {0!r}".format(raw_rule),
                line_number,
            )
        return [selector]

    if selector in WEEKDAY_NAMES:
        if unit != "w":
            raise errors.RecurParseError(
                "bare weekday selector is only valid with unit "
                "'w': {0!r}".format(raw_rule),
                line_number,
            )
        return [selector]

    raise errors.RecurParseError(
        "invalid weekday selector {0!r} in RECUR rule: {1!r}".format(
            selector, raw_rule
        ),
        line_number,
    )


def _matches_date(
    rule: RecurRule, anchor: datetime.date, day: datetime.date
) -> bool:
    if rule.unit == "d":
        return (day - anchor).days % rule.interval == 0
    if rule.unit == "w":
        # Cadence is measured in Monday-based calendar weeks, including
        # the partial week containing the anchor.
        weeks = ((day - anchor).days + anchor.weekday()) // 7
        weekdays = rule.weekdays or [WEEKDAY_NAMES[anchor.weekday()]]
        return (
            weeks % rule.interval == 0
            and WEEKDAY_NAMES[day.weekday()] in weekdays
        )
    if rule.unit == "y":
        return (
            (day.year - anchor.year) % rule.interval == 0
            and day.month == anchor.month
            and day.day == anchor.day
        )
    months = (day.year - anchor.year) * 12 + day.month - anchor.month
    if months % rule.interval:
        return False
    if not rule.weekdays:
        return day.day == anchor.day
    token = rule.weekdays[0]
    match = _NTH_WEEKDAY_RE.match(token)
    assert match
    nth = int(match.group("nth"))
    if nth > 0:
        position = (day.day - 1) // 7 + 1
    else:
        position = -(
            (calendar.monthrange(day.year, day.month)[1] - day.day) // 7 + 1
        )
    return position == nth and WEEKDAY_NAMES[day.weekday()] == match.group(
        "day"
    )


def expand(
    rule: RecurRule,
    anchor: datetime.datetime,
    from_date: datetime.datetime,
    to_date: datetime.datetime,
) -> List[datetime.datetime]:
    """Expand a fixed cadence within the inclusive window using only stdlib.

    Invalid calendar dates (January 31 in February, or February 29 in
    non-leap years) are skipped rather than shifted. Only the requested
    window is traversed, so old anchors do not require replaying history.
    """
    if from_date > to_date or to_date < anchor:
        return []
    first = max(from_date, anchor)
    last = to_date
    if anchor.tzinfo is not None:
        first = first.astimezone(anchor.tzinfo)
        last = last.astimezone(anchor.tzinfo)
    last_day = last.date()
    if rule.until is not None:
        last_day = min(last_day, rule.until)
    result = []
    for ordinal in range(first.date().toordinal(), last_day.toordinal() + 1):
        day = datetime.date.fromordinal(ordinal)
        if not _matches_date(rule, anchor.date(), day):
            continue
        occurrence = anchor.replace(
            year=day.year, month=day.month, day=day.day
        )
        if first <= occurrence <= last:
            result.append(occurrence)
    return result
