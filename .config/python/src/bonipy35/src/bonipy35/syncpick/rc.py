#!/usr/bin/env python3
"""Run ``rclone rcd`` and send requests to its remote control API."""

# Standard libraries.
import base64
import binascii
import collections
import json
import os
import re
import subprocess
import sys
import threading
import typing
import urllib.error
import urllib.request

from typing import BinaryIO, Dict, List, Tuple, Union

# Internal modules.
from .runner import (
    RcloneError,
    Runner,
    argument_parser,
    runner_from_arguments,
)

_SERVING = re.compile(r"Serving remote control on (http://\S+?)/?$")


class RcError(Exception):
    """The remote control API could not be reached or rejected a request.

    ``status`` is the HTTP status, or 0 if no response was received.
    """

    def __init__(self, message: str, *, path: str, status: int) -> None:
        super().__init__(message)
        self.path = path
        self.status = status


class Daemon:
    """One ``rclone rcd`` process listening on localhost.

    Credentials are generated for each start and passed in the environment,
    so that they do not appear in process listings.
    Other clients may use them from ``user`` and ``password``.
    Requests may be sent from several threads,
    and each blocks until rclone responds.
    """

    def __init__(self, runner: Runner) -> None:
        self.runner = runner
        self.url = ""
        self.user = ""
        self.password = ""
        self._authorization = ""
        # The process and the thread reading its standard error.
        self._running = (
            None
        )  # type: Union[None, Tuple[subprocess.Popen[bytes], threading.Thread]]
        self._stderr = collections.deque(maxlen=50)  # type: typing.Deque[str]

    def __enter__(self) -> "Daemon":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()

    @property
    def stderr(self) -> str:
        """The last lines rclone wrote to its standard error."""
        return "\n".join(self._stderr)

    def start(self) -> None:
        """Start rclone and wait until it accepts requests."""
        user = binascii.hexlify(os.urandom(16)).decode("ascii")
        password = binascii.hexlify(os.urandom(16)).decode("ascii")
        environment = self.runner.environment()
        environment["RCLONE_RC_USER"] = user
        environment["RCLONE_RC_PASS"] = password
        command = [self.runner.executable, "rcd", "--rc-addr", "127.0.0.1:0"]
        try:
            # Outlives this method; stop() waits for it.
            process = subprocess.Popen(  # pylint: disable=consider-using-with
                command,
                env=environment,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
            )
        except OSError as error:
            raise RcloneError(str(error), command=command) from error
        stream = typing.cast(BinaryIO, process.stderr)
        # Blocks until rclone announces its address or exits.
        url = ""
        for line in stream:
            self._stderr.append(
                line.decode("utf-8", errors="replace").rstrip()
            )
            match = _SERVING.search(self._stderr[-1])
            if match is not None:
                url = match.group(1)
                break
        if not url:
            stream.close()
            returncode = process.wait()
            raise RcloneError(
                "rclone rcd exited with code {}".format(returncode),
                command=command,
                returncode=returncode,
                stderr=self.stderr,
            )
        credentials = "{}:{}".format(user, password).encode("ascii")
        self._authorization = "Basic " + base64.b64encode(credentials).decode(
            "ascii"
        )
        self.url = url
        self.user = user
        self.password = password
        # Keep reading so that rclone never blocks on a full pipe.
        reader = threading.Thread(
            target=self._read_stderr, args=(stream,), daemon=True
        )
        reader.start()
        self._running = (process, reader)

    def _read_stderr(self, stream: BinaryIO) -> None:
        for line in stream:
            self._stderr.append(
                line.decode("utf-8", errors="replace").rstrip()
            )

    def call(
        self, path: str, parameters: Union[None, Dict[str, object]] = None
    ) -> Dict[str, object]:
        """Send a request, such as ``operations/list``; return its result."""
        if self._running is None:
            raise RcError("rclone rcd is not running", path=path, status=0)
        request = urllib.request.Request(
            self.url + "/" + path,
            data=json.dumps(parameters or {}).encode("utf-8"),
            headers={
                "Authorization": self._authorization,
                "Content-Type": "application/json",
            },
        )
        # Proxies from the environment must not see local requests.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(request) as response:
                content = response.read()  # type: bytes
        except urllib.error.HTTPError as error:
            try:
                message = _error_message(error.read())
            finally:
                error.close()
            raise RcError(message, path=path, status=error.code) from error
        except urllib.error.URLError as error:
            raise RcError(str(error.reason), path=path, status=0) from error
        result = json.loads(content.decode("utf-8"))
        if not isinstance(result, dict):
            raise RcError(
                "Unexpected response: {!r}".format(result),
                path=path,
                status=200,
            )
        return result

    def wait(self) -> int:
        """Wait until rclone exits, such as after ``core/quit``.

        Returns its exit code. Call ``stop()`` afterwards to clean up.
        """
        if self._running is None:
            raise RuntimeError("rclone rcd is not running")
        return self._running[0].wait()

    def stop(self) -> None:
        """Stop rclone, interrupting any request in progress."""
        if self._running is None:
            return
        process, reader = self._running
        self._running = None
        process.terminate()
        process.wait()
        reader.join()
        typing.cast(BinaryIO, process.stderr).close()


def _error_message(content: bytes) -> str:
    """Extract the message from an error response body."""
    text = content.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(text)
    except ValueError:
        return text.strip()
    if isinstance(parsed, dict) and "error" in parsed:
        return str(parsed["error"])
    return text.strip()


def main(argv: Union[None, List[str]] = None) -> int:
    """Start ``rclone rcd`` and send one request, or serve until Ctrl+C."""
    parser = argument_parser(description=typing.cast(str, main.__doc__))
    parser.add_argument(
        "path", nargs="?", help="request path, such as operations/list"
    )
    parser.add_argument(
        "parameters",
        nargs="?",
        default="{}",
        help="request parameters as a JSON object (default: {})",
    )
    arguments = parser.parse_args((sys.argv if argv is None else argv)[1:])
    parameters = json.loads(arguments.parameters)
    try:
        with Daemon(runner_from_arguments(arguments)) as daemon:
            if arguments.path is None:
                print("Serving on", daemon.url)
                print(
                    "Try: rclone rc --url {} --user {} --pass {} "
                    "core/version".format(
                        daemon.url, daemon.user, daemon.password
                    )
                )
                print("Press Ctrl+C to stop.", flush=True)
                try:
                    return daemon.wait()
                except KeyboardInterrupt:
                    return 0
            result = daemon.call(arguments.path, parameters)
    except (RcError, RcloneError) as error:
        print(error, file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
