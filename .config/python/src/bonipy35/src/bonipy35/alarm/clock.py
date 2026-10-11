#!/usr/bin/env python3
"""Linux wall-clock deadline readiness, including suspend and clock changes."""

# Standard libraries.
import ctypes
import datetime
import errno
import os

from typing import Union


class _Timespec(ctypes.Structure):
    _fields_ = [("seconds", ctypes.c_long), ("nanoseconds", ctypes.c_long)]


class _TimerSpec(ctypes.Structure):
    _fields_ = [("interval", _Timespec), ("value", _Timespec)]


class DeadlineClock:
    def __init__(self) -> None:
        self._libc = ctypes.CDLL(None, use_errno=True)
        create = self._libc.timerfd_create
        create.argtypes = [ctypes.c_int, ctypes.c_int]
        create.restype = ctypes.c_int
        settime = self._libc.timerfd_settime
        settime.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(_TimerSpec),
            ctypes.POINTER(_TimerSpec),
        ]
        settime.restype = ctypes.c_int
        # CLOCK_REALTIME=0; O_* flags also serve as TFD_* flags on Linux.
        self.fd = create(0, os.O_NONBLOCK | os.O_CLOEXEC)
        if self.fd < 0:
            code = ctypes.get_errno()
            raise OSError(code, os.strerror(code))

    def arm(self, deadline: Union[None, datetime.datetime]) -> None:
        seconds = 0
        nanoseconds = 0
        if deadline is not None:
            timestamp = deadline.timestamp()
            seconds = int(timestamp)
            nanoseconds = int((timestamp - seconds) * 1000000000)
            # An all-zero value disarms timerfd rather than expiring it.
            if seconds <= 0:
                seconds, nanoseconds = 0, 1
        spec = _TimerSpec(_Timespec(0, 0), _Timespec(seconds, nanoseconds))
        # TFD_TIMER_ABSTIME | TFD_TIMER_CANCEL_ON_SET.
        if (
            self._libc.timerfd_settime(self.fd, 3, ctypes.byref(spec), None)
            < 0
        ):
            code = ctypes.get_errno()
            raise OSError(code, os.strerror(code))

    def consume(self) -> None:
        try:
            os.read(self.fd, 8)
        except OSError as error:
            if error.errno not in (errno.ECANCELED, errno.EAGAIN):
                raise

    def close(self) -> None:
        os.close(self.fd)
