#!/usr/bin/env python3

# Standard libraries.
import errno

from unittest.mock import Mock

# External dependencies.
import pytest

# Internal modules.
from bonipy35.alarm.clock import DeadlineClock


class TestClockErrors:
    def test_creation_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        library = Mock()
        library.timerfd_create.return_value = -1
        monkeypatch.setattr(
            "bonipy35.alarm.clock.ctypes.CDLL", Mock(return_value=library)
        )
        monkeypatch.setattr(
            "bonipy35.alarm.clock.ctypes.get_errno",
            Mock(return_value=errno.EMFILE),
        )
        with pytest.raises(OSError) as caught:
            DeadlineClock()
        assert caught.value.errno == errno.EMFILE

    def test_arm_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        timer = DeadlineClock()
        try:
            library = Mock()
            library.timerfd_settime.return_value = -1
            monkeypatch.setattr(timer, "_libc", library)
            monkeypatch.setattr(
                "bonipy35.alarm.clock.ctypes.get_errno",
                Mock(return_value=errno.EINVAL),
            )
            with pytest.raises(OSError) as caught:
                timer.arm(None)
            assert caught.value.errno == errno.EINVAL
        finally:
            timer.close()

    @pytest.mark.parametrize("code", [errno.ECANCELED, errno.EAGAIN])
    def test_clock_change_or_spurious_readiness_is_recoverable(
        self, code: int, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        timer = DeadlineClock()
        try:
            monkeypatch.setattr(
                "bonipy35.alarm.clock.os.read",
                Mock(side_effect=OSError(code, "clock event")),
            )
            timer.consume()
        finally:
            timer.close()

    def test_unexpected_read_error_propagates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        timer = DeadlineClock()
        try:
            monkeypatch.setattr(
                "bonipy35.alarm.clock.os.read",
                Mock(side_effect=OSError(errno.EIO, "broken")),
            )
            with pytest.raises(OSError) as caught:
                timer.consume()
            assert caught.value.errno == errno.EIO
        finally:
            timer.close()
