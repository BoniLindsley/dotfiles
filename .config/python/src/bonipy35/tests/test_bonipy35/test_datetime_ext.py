#!/usr/bin/env python3

# Standard libraries.
import datetime

from typing import Union

# External dependencies.
import pytest

# Internal modules.
from bonipy35.datetime_ext import Builder, format_datetime, parse_date


class TestBuilder:
    def test_build(self) -> None:
        builder = Builder(1970, 1, 2)
        result = builder.build()
        reference = datetime.datetime(1970, 1, 2)
        assert result == reference

    def test_copy(self) -> None:
        source = datetime.datetime(1970, 1, 2, 3, 4, 5)
        result = Builder.copy(source).build()
        reference = source
        assert result == reference

    def test_date(self) -> None:
        builder = Builder(1970, 1, 2, 3, 4, 5)
        builder = builder.year(2000).month(7).day(8)
        result = builder.build()
        reference = datetime.datetime(2000, 7, 8, 3, 4, 5)
        assert result == reference

    def test_fold(self) -> None:
        builder = Builder(1970, 1, 2, fold=0)
        builder = builder.fold(1)
        result = builder.build()
        reference = datetime.datetime(1970, 1, 2, fold=1)
        assert result == reference

    def test_time(self) -> None:
        builder = Builder(1970, 1, 2, 3, 4, 5)
        builder = builder.hour(6).minute(7).second(8).microsecond(9)
        result = builder.build()
        reference = datetime.datetime(1970, 1, 2, 6, 7, 8, 9)
        assert result == reference

    def test_tzinfo(self) -> None:
        tzinfo = datetime.timezone(datetime.timedelta(hours=2))
        builder = Builder(1970, 1, 2, 3, 4, 5, tzinfo=tzinfo)
        new_tzinfo = datetime.timezone(datetime.timedelta(hours=3))
        builder = builder.tzinfo(new_tzinfo)
        result = builder.build()
        reference = datetime.datetime(1970, 1, 2, 3, 4, 5, tzinfo=new_tzinfo)
        assert result == reference

    def test_utc(self) -> None:
        tzinfo = datetime.timezone(datetime.timedelta(hours=1))
        builder = Builder(1970, 1, 2, 3, 4, 5, tzinfo=tzinfo)
        builder = builder.utc()
        result = builder.build()
        reference = datetime.datetime(
            1970, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc
        )
        assert result == reference


class TestParseDate:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("2025-06-01", datetime.date(2025, 6, 1)),
            ("2024-02-29", datetime.date(2024, 2, 29)),
            ("2000-02-29", datetime.date(2000, 2, 29)),
            ("0001-01-01", datetime.date.min),
            ("9999-12-31", datetime.date.max),
        ],
    )
    def test_accepts_valid_dates(
        self, value: str, expected: datetime.date
    ) -> None:
        assert parse_date(value) == expected

    @pytest.mark.parametrize(
        "value",
        [
            "2025-02-29",
            "1900-02-29",
            "2025-04-31",
            "2025-00-01",
            "2025-13-01",
            "2025-01-00",
            "2025-01-32",
            "0000-01-01",
        ],
    )
    def test_rejects_invalid_calendar_dates(self, value: str) -> None:
        with pytest.raises(ValueError):
            parse_date(value)

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "garbage",
            "2025-1-01",
            "2025-01-1",
            "25-01-01",
            "20250101",
            "2025/01/01",
            " 2025-01-01",
            "2025-01-01 ",
            "2025-01-01\n",
            "2025-01-01T00:00:00",
            "２０２５-01-01",
        ],
    )
    def test_rejects_non_iso_format(self, value: str) -> None:
        with pytest.raises(ValueError, match="expected YYYY-MM-DD"):
            parse_date(value)


class TestFormatDatetime:
    @pytest.mark.parametrize("minutes", [False, True])
    @pytest.mark.parametrize(
        "offset,suffix",
        [(None, ""), (0, "+00:00"), (330, "+05:30"), (-210, "-03:30")],
    )
    def test_precision_and_timezone(
        self, minutes: bool, offset: Union[None, int], suffix: str
    ) -> None:
        timezone = (
            None
            if offset is None
            else datetime.timezone(datetime.timedelta(minutes=offset))
        )
        value = datetime.datetime(
            2025, 6, 1, 9, 30, 45, 987654, tzinfo=timezone
        )
        expected = "2025-06-01T09:30" + ("" if minutes else ":45") + suffix
        assert format_datetime(value, minutes=minutes) == expected
        assert value.second == 45
        assert value.microsecond == 987654
        assert value.tzinfo is timezone

    def test_default_precision_includes_zero_seconds(self) -> None:
        assert format_datetime(datetime.datetime(2025, 6, 1, 9, 30)) == (
            "2025-06-01T09:30:00"
        )

    @pytest.mark.parametrize("minutes", [False, True])
    def test_year_is_zero_padded(self, minutes: bool) -> None:
        value = datetime.datetime(1, 1, 1, tzinfo=datetime.timezone.utc)
        expected = "0001-01-01T00:00" + ("" if minutes else ":00") + "+00:00"
        assert format_datetime(value, minutes=minutes) == expected
