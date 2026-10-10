#!/usr/bin/env python3

# Standard libraries.
import datetime

# External dependencies.
import pytest

# Internal modules.
from bonipy35.taskmd import errors
from bonipy35.taskmd import recur


def _dt(
    year: int, month: int, day: int, hour: int = 0, minute: int = 0
) -> datetime.datetime:
    return datetime.datetime(
        year, month, day, hour, minute, tzinfo=datetime.timezone.utc
    )


class TestParseRule:
    def test_daily(self) -> None:
        rule = recur.parse_rule("+1d")
        assert rule.prefix == "+"
        assert rule.interval == 1
        assert rule.unit == "d"
        assert rule.weekdays == []
        assert rule.until is None
        assert rule.raw == "+1d"

    def test_fixed_cadence_weekly_with_weekdays(self) -> None:
        rule = recur.parse_rule("++1w MON,WED")
        assert rule.prefix == "++"
        assert rule.unit == "w"
        assert rule.weekdays == ["MON", "WED"]

    def test_catch_up_prefix(self) -> None:
        rule = recur.parse_rule(".+1d")
        assert rule.prefix == ".+"

    def test_nth_weekday_of_month(self) -> None:
        rule = recur.parse_rule("++1m 2MON")
        assert rule.unit == "m"
        assert rule.weekdays == ["2MON"]

    def test_last_weekday_of_month_with_until(self) -> None:
        rule = recur.parse_rule("+1m -1FRI @2026-12-31")
        assert rule.weekdays == ["-1FRI"]
        assert rule.until == datetime.date(2026, 12, 31)

    def test_annual(self) -> None:
        rule = recur.parse_rule("++1y")
        assert rule.unit == "y"

    def test_multi_digit_interval(self) -> None:
        rule = recur.parse_rule("+12d")
        assert rule.interval == 12

    def test_bare_weekday_valid_for_weekly(self) -> None:
        rule = recur.parse_rule("+2w FRI")
        assert rule.weekdays == ["FRI"]

    def test_malformed_rule_raises(self) -> None:
        with pytest.raises(errors.RecurParseError):
            recur.parse_rule("bogus")

    def test_zero_interval_raises(self) -> None:
        with pytest.raises(errors.RecurParseError):
            recur.parse_rule("+0d")

    def test_comma_list_requires_weekly_unit(self) -> None:
        with pytest.raises(errors.RecurParseError):
            recur.parse_rule("+1m MON,WED")

    def test_nth_weekday_requires_monthly_unit(self) -> None:
        with pytest.raises(errors.RecurParseError):
            recur.parse_rule("+1w 2MON")

    def test_bare_weekday_requires_weekly_unit(self) -> None:
        with pytest.raises(errors.RecurParseError):
            recur.parse_rule("+1m MON")

    def test_invalid_weekday_name_raises(self) -> None:
        with pytest.raises(errors.RecurParseError):
            recur.parse_rule("+1w XYZ")

    def test_invalid_comma_weekday_name_raises(self) -> None:
        with pytest.raises(errors.RecurParseError):
            recur.parse_rule("+1w MON,XYZ")

    def test_error_includes_line_number(self) -> None:
        with pytest.raises(errors.RecurParseError) as excinfo:
            recur.parse_rule("bogus", line_number=7)
        assert excinfo.value.line_number == 7


class TestExpand:
    def test_no_weekdays_daily(self) -> None:
        rule = recur.parse_rule("+1d")
        anchor = _dt(2025, 1, 1, 10)
        result = recur.expand(
            rule, anchor, _dt(2025, 1, 1, 0), _dt(2025, 1, 4, 23)
        )
        assert result == [
            _dt(2025, 1, 1, 10),
            _dt(2025, 1, 2, 10),
            _dt(2025, 1, 3, 10),
            _dt(2025, 1, 4, 10),
        ]

    def test_weekly_with_weekday_list(self) -> None:
        # 2025-09-01 is a Monday.
        rule = recur.parse_rule("+1w MON,WED")
        anchor = _dt(2025, 9, 1, 10)
        result = recur.expand(rule, anchor, _dt(2025, 9, 1), _dt(2025, 9, 14))
        assert result == [
            _dt(2025, 9, 1, 10),
            _dt(2025, 9, 3, 10),
            _dt(2025, 9, 8, 10),
            _dt(2025, 9, 10, 10),
        ]

    def test_monthly_nth_weekday(self) -> None:
        rule = recur.parse_rule("++1m 2MON")
        anchor = _dt(2025, 9, 8, 10)  # second Monday of September 2025.
        result = recur.expand(
            rule, anchor, _dt(2025, 9, 1), _dt(2025, 11, 30)
        )
        assert result == [
            _dt(2025, 9, 8, 10),
            _dt(2025, 10, 13, 10),
            _dt(2025, 11, 10, 10),
        ]

    def test_monthly_last_friday_with_until(self) -> None:
        rule = recur.parse_rule("+1m -1FRI @2025-11-01")
        anchor = _dt(2025, 9, 26, 10)  # last Friday of September 2025.
        result = recur.expand(
            rule, anchor, _dt(2025, 9, 1), _dt(2025, 12, 31)
        )
        assert result == [
            _dt(2025, 9, 26, 10),
            _dt(2025, 10, 31, 10),
        ]

    def test_monthly_without_weekday_uses_day_of_month(self) -> None:
        rule = recur.parse_rule("++1m")
        anchor = _dt(2025, 1, 15, 9)
        result = recur.expand(rule, anchor, _dt(2025, 1, 1), _dt(2025, 3, 31))
        assert result == [
            _dt(2025, 1, 15, 9),
            _dt(2025, 2, 15, 9),
            _dt(2025, 3, 15, 9),
        ]

    def test_yearly(self) -> None:
        rule = recur.parse_rule("++1y")
        anchor = _dt(2024, 6, 9, 9)
        result = recur.expand(
            rule, anchor, _dt(2024, 1, 1), _dt(2026, 12, 31)
        )
        assert result == [
            _dt(2024, 6, 9, 9),
            _dt(2025, 6, 9, 9),
            _dt(2026, 6, 9, 9),
        ]

    def test_window_excludes_out_of_range_occurrences(self) -> None:
        rule = recur.parse_rule("+1d")
        anchor = _dt(2025, 1, 10, 10)
        result = recur.expand(rule, anchor, _dt(2025, 1, 1), _dt(2025, 1, 5))
        assert not result
