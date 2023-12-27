# /usr/bin/env python3

# Standard libraries.
import argparse
import asyncio
import collections.abc as cabc
import contextlib
import curses
import logging
import os
import selectors
import signal
import sys
import typing as t

# Internal modules.
from . import logging_ext


_logger = logging.getLogger(__name__)

SelectorEvent = t.Literal[0, 1, 2, 3]


class Selector:
    def __init__(self, *args: t.Any, stdscr: curses.window, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)
        self._stdscr = stdscr

    def select(
        self, timeout: None | float = None
    ) -> list[tuple[selectors.SelectorKey, SelectorEvent]]:
        if timeout is None:
            timeout = -1
        timeout *= 1000
        self._stdscr.timeout(int(timeout))

        try:
            next_ch = self._stdscr.getch()
            del next_ch
        except KeyboardInterrupt:
            pass

        event_list: list[tuple[selectors.SelectorKey, SelectorEvent]] = []
        return event_list


class EventLoop(asyncio.BaseEventLoop):
    _unpause_signal = (
        signal.SIGINT
        if os.name != "nt"
        else (
            signal.CTRL_C_EVENT  # type: ignore[attr-defined]  # pylint: disable=no-member
        )
    )

    def __init__(self, *args: t.Any, stdscr: curses.window, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)
        self._pid = os.getpid()
        self._selector = Selector(stdscr=stdscr)

    def _make_datagram_transport(  # type: ignore[no-untyped-def]  # pylint: disable=too-many-arguments
        self, sock, protocol, address=None, waiter=None, extra=None
    ):
        raise NotImplementedError

    def _make_read_pipe_transport(self, pipe, protocol, waiter=None, extra=None):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    def _make_socket_transport(  # type: ignore[no-untyped-def]  # pylint: disable=too-many-arguments
        self, sock, protocol, waiter=None, *, extra=None, server=None
    ):
        raise NotImplementedError

    def _make_ssl_transport(  # type: ignore[no-untyped-def]  # pylint: disable=too-many-arguments
        self,
        rawsock,
        protocol,
        sslcontext,
        waiter=None,
        *,
        server_side=False,
        server_hostname=None,
        extra=None,
        server=None,
        ssl_handshake_timeout=None,
        ssl_shutdown_timeout=None,
        call_connection_made=True
    ):
        raise NotImplementedError

    async def _make_subprocess_transport(  # type: ignore[no-untyped-def]  # pylint: disable=too-many-arguments
        self,
        protocol,
        args,
        shell,
        stdin,
        stdout,
        stderr,
        bufsize,
        extra=None,
        **kwargs
    ):
        raise NotImplementedError

    def _make_write_pipe_transport(self, pipe, protocol, waiter=None, extra=None):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    def _process_events(
        self, event_list: list[tuple[selectors.SelectorKey, SelectorEvent]]
    ) -> None:
        pass

    def _write_to_self(self) -> None:
        os.kill(self._pid, self._unpause_signal)


class EventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    def __init__(self, *args: t.Any, stdscr: curses.window, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)
        self._stdscr = stdscr

    def new_event_loop(self) -> EventLoop:
        return EventLoop(stdscr=self._stdscr)


@contextlib.contextmanager
def initialise(
    initscr: None | cabc.Callable[[], curses.window] = None
) -> cabc.Iterator[curses.window]:
    with contextlib.ExitStack() as stack:
        if initscr is None:
            initscr = curses.initscr

        stdscr = initscr()
        stack.callback(curses.endwin)

        curses.noecho()
        stack.callback(curses.echo)

        curses.cbreak()
        stack.callback(curses.nocbreak)

        stdscr.keypad(True)
        stack.callback(stdscr.keypad, False)

        curses.start_color()

        stack.callback(asyncio.set_event_loop_policy, asyncio.get_event_loop_policy())
        asyncio.set_event_loop_policy(EventLoopPolicy(stdscr=stdscr))

        yield stdscr


async def amain(stdscr: curses.window) -> int:
    stdscr.timeout(-1)
    stdscr.getch()
    await asyncio.sleep(2)
    return 0


def parse_arguments(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    logging_ext.add_verbose_flag(parser)
    return parser.parse_args(args)


def main(argv: None | list[str] = None) -> int:
    if argv is None:
        argv = sys.argv
    arguments = parse_arguments(argv[1:])

    logging_ext.set_up_logging(verbosity=arguments.verbosity)

    with initialise() as stdscr:
        return asyncio.run(amain(stdscr))


if __name__ == "__main__":
    sys.exit(main())
