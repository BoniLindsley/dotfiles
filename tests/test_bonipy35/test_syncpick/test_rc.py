#!/usr/bin/env python3

# Standard libraries.
import pathlib
import shutil
import sys
import typing
import urllib.error
import urllib.request

from typing import Dict, Iterator, List

# External dependencies.
import pytest

# Internal modules.
from bonipy35.syncpick.rc import Daemon, RcError
from bonipy35.syncpick.runner import RcloneError, Runner

RCLONE = shutil.which("rclone")

# A fake rcd. The daemon runs `<executable> rcd --rc-addr ...`,
# so with the interpreter as executable and this saved as `rcd`
# in the working directory, the interpreter runs it as a script.
_FAKE_RCD = """
import base64
import http.server
import json
import os
import sys

expected = "Basic " + base64.b64encode(
    "{}:{}".format(
        os.environ["RCLONE_RC_USER"], os.environ["RCLONE_RC_PASS"]
    ).encode("ascii")
).decode("ascii")


class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        if self.headers["Authorization"] != expected:
            self.reply(401, b"Unauthorized")
        elif self.path == "/echo":
            self.reply(200, json.dumps({
                "config": os.environ.get("RCLONE_CONFIG"),
                "input": json.loads(body.decode("utf-8")),
            }).encode("utf-8"))
        elif self.path == "/fail":
            self.reply(500, b'{"error": "boom", "status": 500}')
        elif self.path == "/fail-other":
            self.reply(500, b'["boom"]')
        elif self.path == "/list":
            self.reply(200, b"[]")
        elif self.path == "/quit":
            self.reply(200, b"{}")
            self.server.shutdown_request(self.request)
            os._exit(0)
        else:
            self.reply(404, b"not found")

    def reply(self, status, content):
        self.send_response(status)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, *args):
        pass


server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
sys.stderr.write("NOTICE: starting\\n")
sys.stderr.write(
    "NOTICE: Serving remote control on http://127.0.0.1:{}/\\n".format(
        server.server_address[1]
    )
)
sys.stderr.write("NOTICE: served\\n")
sys.stderr.flush()
server.serve_forever()
"""

_FAILING_RCD = """
import sys
sys.stderr.write("ERROR: bad flag\\n")
sys.exit(3)
"""


def write_fake(directory: pathlib.Path, content: str) -> None:
    (directory / "rcd").write_text(content)


@pytest.fixture(name="runner")
def fixture_runner(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> Runner:
    monkeypatch.chdir(tmp_path)
    write_fake(tmp_path, _FAKE_RCD)
    return Runner(executable=sys.executable, config=tmp_path / "rclone.conf")


@pytest.fixture(name="daemon")
def fixture_daemon(runner: Runner) -> Iterator[Daemon]:
    with Daemon(runner) as daemon:
        yield daemon


class TestStart:
    def test_reads_address(self, daemon: Daemon) -> None:
        assert daemon.url.startswith("http://127.0.0.1:")
        assert not daemon.url.endswith("/")

    def test_exposes_credentials(self, runner: Runner) -> None:
        with Daemon(runner) as first, Daemon(runner) as second:
            assert len(first.user) == len(first.password) == 32
            assert first.user != first.password
            assert (first.user, first.password) != (
                second.user,
                second.password,
            )

    def test_keeps_reading_stderr(self, runner: Runner) -> None:
        daemon = Daemon(runner)
        daemon.start()
        daemon.stop()
        assert daemon.stderr.splitlines()[0] == "NOTICE: starting"
        assert daemon.stderr.splitlines()[-1] == "NOTICE: served"

    def test_exits_early(
        self, runner: Runner, tmp_path: pathlib.Path
    ) -> None:
        write_fake(tmp_path, _FAILING_RCD)
        with pytest.raises(RcloneError, match="code 3") as raised:
            Daemon(runner).start()
        assert raised.value.returncode == 3
        assert raised.value.stderr == "ERROR: bad flag"

    def test_unrunnable_executable(self, tmp_path: pathlib.Path) -> None:
        runner = Runner(executable=str(tmp_path / "missing"))
        with pytest.raises(RcloneError) as raised:
            Daemon(runner).start()
        assert raised.value.returncode is None


class TestCall:
    def test_sends_parameters(
        self, daemon: Daemon, runner: Runner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A proxy that does not exist; requests must bypass it.
        monkeypatch.setenv("http_proxy", "http://127.0.0.1:9")
        assert daemon.call("echo", {"fs": "ü"}) == {
            "config": str(runner.config),
            "input": {"fs": "ü"},
        }
        assert daemon.call("echo")["input"] == {}

    def test_requires_credentials(self, daemon: Daemon) -> None:
        request = urllib.request.Request(daemon.url + "/echo", data=b"{}")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with pytest.raises(urllib.error.HTTPError) as raised:
            opener.open(request)
        raised.value.close()
        assert raised.value.code == 401

    @pytest.mark.parametrize(
        ("path", "message", "status"),
        [
            ("fail", "boom", 500),
            ("fail-other", '["boom"]', 500),
            ("missing", "not found", 404),
            ("list", "Unexpected response: []", 200),
        ],
    )
    def test_errors(
        self, daemon: Daemon, path: str, message: str, status: int
    ) -> None:
        with pytest.raises(RcError) as raised:
            daemon.call(path)
        assert str(raised.value) == message
        assert raised.value.path == path
        assert raised.value.status == status

    def test_unreachable(self, daemon: Daemon) -> None:
        daemon.call("quit")
        with pytest.raises(RcError) as raised:
            daemon.call("echo")
        assert raised.value.status == 0

    def test_not_running(self, runner: Runner) -> None:
        daemon = Daemon(runner)
        with pytest.raises(RcError, match="not running"):
            daemon.call("echo")
        daemon.start()
        daemon.stop()
        with pytest.raises(RcError, match="not running"):
            daemon.call("echo")


class TestWait:
    def test_returns_exit_code(self, daemon: Daemon) -> None:
        daemon.call("quit")
        assert daemon.wait() == 0

    def test_not_running(self, runner: Runner) -> None:
        with pytest.raises(RuntimeError, match="not running"):
            Daemon(runner).wait()


class TestStop:
    def test_idempotent(self, runner: Runner) -> None:
        daemon = Daemon(runner)
        daemon.stop()
        daemon.start()
        daemon.stop()
        daemon.stop()
        assert daemon.stderr


@pytest.mark.integration
@pytest.mark.skipif(RCLONE is None, reason="Executable not found: rclone")
class TestRealRcd:
    def test_list_and_errors(self, tmp_path: pathlib.Path) -> None:
        config = tmp_path / "rclone.conf"
        config.write_text("")
        tree = tmp_path / "tree"
        (tree / "d").mkdir(parents=True)
        (tree / "d" / "file").write_text("content")
        with Daemon(Runner(config=config)) as daemon:
            result = daemon.call(
                "operations/list",
                {
                    "fs": str(tree),
                    "remote": "",
                    "opt": {"recurse": True, "filesOnly": True},
                },
            )
            listed = typing.cast(List[Dict[str, object]], result["list"])
            assert [(item["Path"], item["Size"]) for item in listed] == [
                ("d/file", 7)
            ]
            with pytest.raises(RcError) as raised:
                daemon.call(
                    "operations/copyfile",
                    {
                        "srcFs": str(tree),
                        "srcRemote": "missing",
                        "dstFs": str(tree),
                        "dstRemote": "copy",
                    },
                )
            assert raised.value.status == 404
