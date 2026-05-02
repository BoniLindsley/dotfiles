#!/usr/bin/env python3

# Standard libraries.
import collections
import pathlib
import typing
import urllib.request

from typing import Dict, Union

# External dependencies.
import pytest

# Internal modules.
from bonipy35.bapt.packaging import Configuration, Control, download


@pytest.fixture(name="override_download")
def fixture_override_download(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> Dict[str, Union[None, pathlib.Path, str]]:
    source_path = tmp_path / "test_data.txt"
    override_download = {
        "source": source_path,
        "url": None,
    }  # type: Dict[str, Union[None, pathlib.Path, str]]

    def mock_urlopen(url: str) -> typing.BinaryIO:
        override_download["url"] = url
        return open(str(source_path), "rb")

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    return override_download


class TestDownload:
    def test_copy_url(
        self,
        override_download: Dict[str, Union[None, pathlib.Path, str]],
        tmp_path: pathlib.Path,
    ) -> None:
        source_path = override_download["source"]
        assert isinstance(source_path, pathlib.Path)
        source_path.write_bytes(b"Hello, World!")

        download("http://example.com", tmp_path / "downloaded_file.txt")
        output = (tmp_path / "downloaded_file.txt").read_bytes()
        assert output == b"Hello, World!"


class TestConfiguration:
    def test_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def home() -> pathlib.Path:
            return pathlib.Path("/home/username")

        with monkeypatch.context() as m:
            m.setattr(pathlib.Path, "home", home)
            configuration = Configuration()
            assert configuration.prefix == pathlib.Path("/home/username")
            assert configuration.repository == pathlib.Path("/home/username/srv/bapt")

    class TestGetPackageDirectory:
        def test_component(self) -> None:
            configuration = Configuration(prefix=pathlib.Path("/tmp/home/m"))
            control = Control(package="query", tag="9.8")
            package_directory = configuration.get_package_directory(
                control, component="extra"
            )
            assert package_directory == pathlib.Path(
                "/tmp/home/m/srv/bapt/pool/extra/q/query"
            )

        def test_default(self) -> None:
            configuration = Configuration(prefix=pathlib.Path("/home/username"))
            control = Control(package="power", tag="1.2")
            package_directory = configuration.get_package_directory(control)
            assert package_directory == pathlib.Path(
                "/home/username/srv/bapt/pool/main/p/power"
            )

    def test_init(self) -> None:
        configuration = Configuration(
            prefix=pathlib.Path("/home/me/home"),
            repository=pathlib.Path("/my/repo"),
        )
        assert configuration.prefix == pathlib.Path("/home/me/home")
        assert configuration.repository == pathlib.Path("/my/repo")

    def test_reset(self) -> None:
        configuration = Configuration(
            prefix=pathlib.Path("/home/me"), repository=pathlib.Path("/tmp/repository")
        )
        assert configuration.prefix == pathlib.Path("/home/me")
        assert configuration.repository == pathlib.Path("/tmp/repository")

        configuration.repository = None
        assert configuration.prefix == pathlib.Path("/home/me")
        assert configuration.repository == pathlib.Path("/home/me/srv/bapt")

    def test_setter(self) -> None:
        configuration = Configuration(prefix=pathlib.Path("/tmp/my"))
        assert configuration.repository == pathlib.Path("/tmp/my/srv/bapt")

        configuration.repository = pathlib.Path("/tmp/repository")
        assert configuration.repository == pathlib.Path("/tmp/repository")


class TestControl:
    def test_default(self) -> None:
        control = Control(package="power", tag="1.2")
        assert control.architecture == "all"
        assert control.package == "power"
        assert control.revision is None
        assert control.stem == "power_1.2_all"
        assert control.tag == "1.2"
        assert control.version == "1.2"
        assert control.to_dict() == collections.OrderedDict(
            Package="power",
            Version="1.2",
            Architecture="all",
        )

    def test_parse_architecture(self) -> None:
        control = Control.parse("zebra_1.1_x64")
        reference = Control(architecture="x64", package="zebra", tag="1.1")
        assert control == reference

    def test_parse_package_only(self) -> None:
        control = Control.parse("power")
        reference = Control(package="power", tag="0.0.1")
        assert control == reference

    def test_parse_revision(self) -> None:
        control = Control.parse("water_3.2-5")
        reference = Control(package="water", revision=5, tag="3.2")
        assert control == reference

    def test_parse_revision_and_architecture(self) -> None:
        control = Control.parse("fire_3.2-5_amd64")
        reference = Control(
            architecture="amd64", package="fire", revision="5", tag="3.2"
        )
        assert control == reference

    def test_parse_tag(self) -> None:
        control = Control.parse("purple_3.2")
        reference = Control(package="purple", tag="3.2")
        assert control == reference
