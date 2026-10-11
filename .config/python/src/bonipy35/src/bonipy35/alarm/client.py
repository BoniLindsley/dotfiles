#!/usr/bin/env python3
"""Local client, automatic startup and framed request/event handling."""

# Standard libraries.
import argparse
import contextlib
import errno
import fcntl
import pathlib
import socket
import subprocess
import sys
import typing

from typing import Callable, Dict, List, Union

# Internal modules.
from . import paths, protocol

Snapshot = Dict[str, typing.Any]


def connect_socket(directory: pathlib.Path) -> socket.socket:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(10)
    try:
        sock.connect(str(directory / "socket"))
    except BaseException:
        sock.close()
        raise
    return sock


def ensure_server(directory: pathlib.Path) -> socket.socket:
    directory = paths.prepare_directory(directory)
    with (directory / "startup.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            return connect_socket(directory)
        except OSError as error:
            if error.errno not in (errno.ENOENT, errno.ECONNREFUSED):
                raise
        # A shutdown may have closed its endpoint before releasing ownership.
        # Wait for cleanup before spawning a replacement, without polling.
        with (directory / "server.lock").open("a+") as lifetime_lock:
            fcntl.flock(lifetime_lock, fcntl.LOCK_EX)
        parent, child = socket.socketpair()
        with parent, child:
            parent.settimeout(10)
            # The detached service intentionally outlives the spawning client;
            # using Popen as a context manager would wait for server shutdown.
            process = subprocess.Popen(  # pylint: disable=consider-using-with
                [
                    sys.executable,
                    "-m",
                    "bonipy35.alarm.server",
                    "--directory",
                    str(directory),
                    "--ready-fd",
                    str(child.fileno()),
                ],
                pass_fds=(child.fileno(),),
                start_new_session=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            child.close()
            decoder = protocol.Decoder()
            try:
                messages = []  # type: List[Dict[str, typing.Any]]
                while not messages:
                    chunk = parent.recv(65536)
                    if not chunk:
                        raise RuntimeError(
                            "Server exited before becoming ready"
                        )
                    messages = decoder.feed(chunk)
                if not messages[0].get("ready"):
                    raise RuntimeError(
                        messages[0].get("error", "Startup failed")
                    )
            except BaseException:
                process.terminate()
                process.wait()
                raise
        # The server remains independent of this client after readiness.
        return connect_socket(directory)


class Client:
    def __init__(self, *, directory: pathlib.Path) -> None:
        self._request_id = 0
        self.snapshot = {"items": [], "notifications": []}  # type: Snapshot
        self._pending = []  # type: List[Dict[str, typing.Any]]
        for attempt in range(2):
            self.sock = ensure_server(directory)
            self.decoder = protocol.Decoder()
            self._pending.clear()
            try:
                # Only this read-only handshake can be retried safely. A lost
                # mutation response never implies that its command was not applied.
                self.request("status")
                break
            except (EOFError, ConnectionError):
                self.close()
                if attempt:
                    raise
            except BaseException:
                self.close()
                raise

    def __enter__(self) -> "typing.Self":
        return self

    def __exit__(self, *args: typing.Any) -> None:
        self.close()

    def close(self) -> None:
        self.sock.close()

    def receive(self) -> Dict[str, typing.Any]:
        while not self._pending:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise EOFError("Alarm server disconnected")
            self._pending.extend(self.decoder.feed(chunk))
        message = self._pending.pop(0)
        if "snapshot" in message:
            self.snapshot = message["snapshot"]
        return message

    @property
    def buffered(self) -> bool:
        return bool(self._pending)

    def request(self, command: str, **fields: typing.Any) -> Snapshot:
        self._request_id += 1
        request_id = self._request_id
        fields.update(command=command, request_id=request_id)
        previous = self.sock.gettimeout()
        self.sock.settimeout(10)
        try:
            self.sock.sendall(protocol.encode(fields))
            while True:
                message = self.receive()
                if message.get("request_id") != request_id:
                    continue
                if "error" in message:
                    raise ValueError(message["error"])
                return self.snapshot
        finally:
            self.sock.settimeout(previous)

    @contextlib.contextmanager
    def events(self) -> typing.Iterator["typing.Self"]:
        previous = self.sock.gettimeout()
        self.sock.settimeout(None)
        try:
            yield self
        finally:
            self.sock.settimeout(previous)


def interface_main(
    run: Callable[[pathlib.Path], int],
    argv: Union[None, List[str]],
    description: Union[None, str],
) -> int:
    if argv is None:
        argv = sys.argv
    parser = argparse.ArgumentParser(description=description)
    paths.add_directory_argument(parser)
    arguments = parser.parse_args(argv[1:])
    try:
        return run(arguments.directory)
    except KeyboardInterrupt:
        return 0
    except (OSError, ValueError, RuntimeError, EOFError) as error:
        print(str(error), file=sys.stderr)
        return 1
