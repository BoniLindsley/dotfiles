#!/usr/bin/env python3

# Standard libraries.
import bz2
import gzip
import io
import json
import lzma
import pathlib
import tarfile
import typing

from unittest import mock

# External dependencies.
import pytest

# Internal modules.
from bonipy35.log_viewer import (
    LogRequestHandler,
    generate_highlights,
    read_file_contents,
    run,
)


class TestGenerateHighlights:
    def test_empty(self) -> None:
        result = generate_highlights(b"")
        assert set(result) == {
            "all",
            "datetime",
            "error",
            "warning",
            "info",
            "debug",
            "stderr",
            "fatal",
        }
        assert all(not spans for spans in result.values())

    def test_datetime(self) -> None:
        assert generate_highlights(b"2026-10-11T12:30:00")["datetime"] == [
            {"start": 0, "end": 19}
        ]

    def test_error(self) -> None:
        result = generate_highlights(b"Error is here\nWhat is error?")
        assert result["error"] == [
            {"end": 5, "start": 0},
            {"end": 27, "start": 22},
        ]
        assert all(
            not spans for name, spans in result.items() if name != "error"
        )


@pytest.fixture(name="handler")
def fixture_handler(tmp_path: pathlib.Path) -> LogRequestHandler:
    instance = object.__new__(LogRequestHandler)
    instance.log_directory = tmp_path / "logs"
    instance.log_directory.mkdir()
    instance.static_directory = tmp_path / "assets"
    instance.static_directory.mkdir()
    instance.extension_map = instance.default_extension_map.copy()
    instance.wfile = io.BytesIO()
    instance.rfile = io.BytesIO()
    instance.request_version = "HTTP/1.0"
    instance.requestline = "GET / HTTP/1.0"
    instance.command = "GET"
    instance.client_address = ("127.0.0.1", 1234)
    instance.server = typing.cast(typing.Any, None)
    return instance


class TestCheckRequestPath:
    def test_relative_and_absolute(self, handler: LogRequestHandler) -> None:
        log = handler.log_directory / "sample.log"
        log.write_text("hello")
        assert handler.check_request_path(pathlib.Path("sample.log")) == log
        assert handler.check_request_path(log) == log

    def test_outside_and_symlink(self, handler: LogRequestHandler) -> None:
        outside = handler.static_directory / "secret"
        outside.write_text("secret")
        link = handler.log_directory / "link"
        link.symlink_to(outside)
        for path in (outside, link, pathlib.Path("../assets/secret")):
            assert handler.check_request_path(path) is None

    def test_resolution_error(self, handler: LogRequestHandler) -> None:
        with mock.patch.object(pathlib.Path, "resolve", side_effect=OSError):
            assert (
                handler.check_request_path(pathlib.Path("sample.log")) is None
            )

    def test_missing_and_directory(self, handler: LogRequestHandler) -> None:
        assert handler.check_request_path(pathlib.Path("missing")) is None
        assert handler.check_request_path(pathlib.Path(".")) is None


class TestReadFileContents:
    @pytest.mark.parametrize(
        "suffix", [".log", ".gz", ".bz2", ".xz", ".tar.gz"]
    )
    def test_formats(self, tmp_path: pathlib.Path, suffix: str) -> None:
        path = tmp_path / ("sample" + suffix)
        content = b"Error here\n"
        if suffix == ".tar.gz":
            with tarfile.open(str(path), "w:gz") as archive:
                member = tarfile.TarInfo("sample.log")
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
        else:
            compressors: typing.Dict[str, typing.Callable[[bytes], bytes]] = {
                ".gz": gzip.compress,
                ".bz2": bz2.compress,
                ".xz": lzma.compress,
            }
            path.write_bytes(
                compressors[suffix](content)
                if suffix in compressors
                else content
            )
        assert read_file_contents(path) == content

    def test_empty_archive(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "empty.tar.gz"
        with tarfile.open(str(path), "w:gz"):
            pass
        with pytest.raises(ValueError, match="exactly one"):
            read_file_contents(path)

    def test_directory_archive(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "directory.tar.gz"
        with tarfile.open(str(path), "w:gz") as archive:
            member = tarfile.TarInfo("directory")
            member.type = tarfile.DIRTYPE
            archive.addfile(member)
        with pytest.raises(ValueError, match="Could not extract"):
            read_file_contents(path)


class TestDoGet:
    @pytest.mark.parametrize(
        "route",
        [
            "/",
            "/index.html",
            "/log_viewer.html",
            "/log_viewer.js",
            "/log_viewer.css",
        ],
    )
    def test_static(self, handler: LogRequestHandler, route: str) -> None:
        name = (
            "log_viewer.html" if route in {"/", "/index.html"} else route[1:]
        )
        (handler.static_directory / name).write_bytes(b"asset")
        handler.path = route
        handler.do_GET()
        assert (
            typing.cast(io.BytesIO, handler.wfile)
            .getvalue()
            .endswith(b"\r\n\r\nasset")
        )

    @pytest.mark.parametrize(
        "route", ["/unknown", "/api/logs", "/log_viewer.html", "/../secret"]
    )
    def test_missing(self, handler: LogRequestHandler, route: str) -> None:
        handler.path = route
        handler.do_GET()
        assert (
            b"404"
            in typing.cast(io.BytesIO, handler.wfile)
            .getvalue()
            .split(b"\r\n")[0]
        )

    def test_log(self, handler: LogRequestHandler) -> None:
        (handler.log_directory / "sample.log").write_text("Error")
        handler.path = "/api/log?path=sample.log"
        handler.do_GET()
        response = json.loads(
            typing.cast(io.BytesIO, handler.wfile)
            .getvalue()
            .split(b"\r\n\r\n")[1]
        )
        assert response["content"] == "Error"

    def test_missing_path(self, handler: LogRequestHandler) -> None:
        handler.path = "/api/log"
        handler.do_GET()
        assert (
            b"400"
            in typing.cast(io.BytesIO, handler.wfile)
            .getvalue()
            .split(b"\r\n")[0]
        )


class TestDoPost:
    @pytest.mark.parametrize(
        "body,code",
        [
            (b'{"path":"sample.log"}', 200),
            (b"{}", 400),
            (b"[]", 400),
            (b"{", 400),
            (b"\xff", 400),
            (b'{"path":1}', 400),
            (b'{"path":""}', 400),
            (b'{"path":"missing"}', 404),
            (b'{"path":"a\\u0000b"}', 400),
        ],
    )
    def test_body(
        self, handler: LogRequestHandler, body: bytes, code: int
    ) -> None:
        (handler.log_directory / "sample.log").write_text("hello")
        handler.path = "/api/log"
        handler.headers = typing.cast(
            typing.Any, {"Content-Length": str(len(body))}
        )
        handler.rfile = io.BytesIO(body)
        handler.do_POST()
        assert (
            str(code).encode()
            in typing.cast(io.BytesIO, handler.wfile)
            .getvalue()
            .split(b"\r\n")[0]
        )

    @pytest.mark.parametrize("length", [None, "bad", "-1"])
    def test_length(
        self, handler: LogRequestHandler, length: typing.Union[None, str]
    ) -> None:
        handler.path = "/api/log"
        handler.headers = typing.cast(
            typing.Any, {} if length is None else {"Content-Length": length}
        )
        handler.do_POST()
        assert (
            b"400"
            in typing.cast(io.BytesIO, handler.wfile)
            .getvalue()
            .split(b"\r\n")[0]
        )

    def test_unknown_route_returns(self, handler: LogRequestHandler) -> None:
        handler.path = "/unknown"
        handler.do_POST()
        assert (
            typing.cast(io.BytesIO, handler.wfile)
            .getvalue()
            .count(b"HTTP/1.0")
            == 1
        )
        assert (
            b"404"
            in typing.cast(io.BytesIO, handler.wfile)
            .getvalue()
            .split(b"\r\n")[0]
        )


class TestSendLogResponse:
    @pytest.mark.parametrize(
        "name,content",
        [
            ("missing", None),
            ("bad.log", b"\xff"),
            ("bad.gz", b"bad"),
            ("bad.xz", b"bad"),
            ("bad.tar.gz", b"bad"),
        ],
    )
    def test_errors(
        self,
        handler: LogRequestHandler,
        name: str,
        content: typing.Union[None, bytes],
    ) -> None:
        path = handler.log_directory / name
        if content is not None:
            path.write_bytes(content)
        handler.send_log_response(path)
        response = typing.cast(io.BytesIO, handler.wfile).getvalue()
        assert b"500" in response.split(b"\r\n")[0]
        assert json.loads(response.split(b"\r\n\r\n")[1]) == {
            "error": "Error reading file"
        }


class TestRun:
    @pytest.mark.parametrize(
        "failure", [None, KeyboardInterrupt, RuntimeError]
    )
    def test_server_lifecycle(
        self, tmp_path: pathlib.Path, failure: typing.Any
    ) -> None:
        cwd = pathlib.Path.cwd()
        with mock.patch(
            "bonipy35.log_viewer.socketserver.TCPServer"
        ) as server_type:
            server = server_type.return_value
            server.serve_forever.side_effect = failure
            if failure is RuntimeError:
                with pytest.raises(RuntimeError):
                    run(log_directory=tmp_path, port=8000)
            else:
                assert run(log_directory=tmp_path, port=8000) == 0
            assert pathlib.Path.cwd() == cwd
            server.server_close.assert_called_once_with()
            address, factory = server_type.call_args.args
            assert address == ("127.0.0.1", 8000)
            assert factory.keywords["log_directory"] == tmp_path.resolve()
            assert (
                factory.keywords["static_directory"] / "log_viewer.html"
            ).is_file()


class TestLogRequestHandler:
    def test_initialization(self, handler: LogRequestHandler) -> None:
        with mock.patch(
            "http.server.BaseHTTPRequestHandler.__init__"
        ) as initialize:
            instance = LogRequestHandler(
                log_directory=handler.log_directory,
                static_directory=handler.static_directory,
            )
        initialize.assert_called_once_with()
        assert instance.path == ""
        assert instance.extension_map == instance.default_extension_map
        assert instance.extension_map is not instance.default_extension_map
        assert instance.log_directory == handler.log_directory
        assert instance.static_directory == handler.static_directory
