#!/usr/bin/env python3
"""Python 3.5 compatible asyncio integration for ncurses."""

from .asyncio_loop import (
    EventLoop,
    EventLoopPolicy,
    run,
    use_event_loop_policy,
)

__all__ = ["EventLoop", "EventLoopPolicy", "run", "use_event_loop_policy"]
