#!/usr/bin/env python3

# Standard libraries.
import collections
import pathlib
import shutil
import typing
import urllib.request

from typing import Dict, Union

# External dependencies.
import pytest

# Internal modules.
from bonipy35.bapt.packaging import Configuration, Control, Package, download
from bonipy35.tarfile_ext import create


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
    def test_build_directory(self, tmp_path: pathlib.Path) -> None:
        configuration = Configuration(prefix=tmp_path)
        assert configuration.build_directory == tmp_path / "build"
        configuration = Configuration(build_directory=tmp_path / "custom")
        assert configuration.build_directory == tmp_path / "custom"

    def test_default_component(self, tmp_path: pathlib.Path) -> None:
        control = Control(package="example", tag="1.0")
        assert control.get_package_directory() == pathlib.Path(
            "pool/main/e/example"
        )
        assert control.get_package_directory(
            component="extra"
        ) == pathlib.Path("pool/extra/e/example")
        configuration = Configuration(prefix=tmp_path)
        assert configuration.get_install_directory(control) == (
            tmp_path / "opt" / "example_1.0_all"
        )

    def test_prefix_setter(self, tmp_path: pathlib.Path) -> None:
        configuration = Configuration()
        configuration.prefix = tmp_path
        assert configuration.prefix == tmp_path
        configuration.prefix = None
        assert configuration.prefix == pathlib.Path.home()

    def test_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def home() -> pathlib.Path:
            return pathlib.Path("/home/username")

        with monkeypatch.context() as m:
            m.setattr(pathlib.Path, "home", home)
            configuration = Configuration()
            assert configuration.prefix == pathlib.Path("/home/username")
            assert configuration.repository == pathlib.Path(
                "/home/username/srv/bapt"
            )

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
            configuration = Configuration(
                prefix=pathlib.Path("/home/username")
            )
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
            prefix=pathlib.Path("/home/me"),
            repository=pathlib.Path("/tmp/repository"),
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
    @pytest.mark.parametrize(
        "package,tag,architecture",
        [("", "1.0", None), ("example", "", None), ("example", "1.0", "")],
    )
    def test_invalid(
        self, package: str, tag: str, architecture: Union[None, str]
    ) -> None:
        with pytest.raises(ValueError):
            Control(package=package, tag=tag, architecture=architecture)

    def test_other_type(self) -> None:
        assert Control(package="example", tag="1.0") != "example"

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
        assert control.version == "3.2-5"
        assert control.stem == "water_3.2-5_all"

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


@pytest.fixture(name="package")
def fixture_package(tmp_path: pathlib.Path) -> Package:
    return Package(
        configuration=Configuration(prefix=tmp_path),
        package="example",
        tag="1.0",
    )


class TestPackage:
    def test_defaults(self) -> None:
        package = Package(package="example", tag="1.0")
        assert package.configuration.prefix == pathlib.Path.home()
        assert package.orig_suffix == ".tar.gz"
        assert package.orig_filename == "example_1.0.orig.tar.gz"

    def test_custom_suffix(self) -> None:
        package = Package(package="example", tag="1.0", orig_suffix=".tgz")
        assert package.orig_filename == "example_1.0.orig.tgz"

    def test_unimplemented(self, package: Package) -> None:
        with pytest.raises(NotImplementedError):
            package.build()
        with pytest.raises(NotImplementedError):
            _ = package.orig_url

    class TestDownloadOrig:
        def test_download(self, tmp_path: pathlib.Path) -> None:
            source = tmp_path / "source.tar.gz"
            source.write_bytes(b"archive")

            # Only the source URL is needed for this download test.
            class LocalPackage(Package):  # pylint: disable=abstract-method
                @property
                def orig_url(self) -> str:
                    return source.as_uri()

            package = LocalPackage(
                configuration=Configuration(prefix=tmp_path),
                package="example",
                tag="1.0",
            )
            package.download_orig()
            assert package.orig_local_path.read_bytes() == b"archive"

    class TestTransfers:
        @pytest.mark.parametrize("orig", [False, True])
        def test_round_trip(
            self,
            package: Package,
            monkeypatch: pytest.MonkeyPatch,
            orig: bool,
        ) -> None:
            # Enforce the string-path interface required by Python 3.5.
            copyfile = shutil.copyfile

            def copy_with_strings(source: str, destination: str) -> str:
                assert isinstance(source, str)
                assert isinstance(destination, str)
                return copyfile(source, destination)

            monkeypatch.setattr(shutil, "copyfile", copy_with_strings)
            local_path = (
                package.orig_local_path if orig else package.local_path
            )
            repository_path = (
                package.orig_package_path if orig else package.package_path
            )
            local_path.parent.mkdir(parents=True)
            local_path.write_bytes(b"archive")
            if orig:
                package.push_orig()
            else:
                package.push()
            assert repository_path.read_bytes() == b"archive"
            local_path.unlink()
            local_path.parent.rmdir()
            if orig:
                package.pull_orig()
            else:
                package.pull()
            assert local_path.read_bytes() == b"archive"

    class TestPackageAndInstall:
        def test_round_trip(self, package: Package) -> None:
            (package.destdir / "bin").mkdir(parents=True)
            (package.destdir / "bin" / "example").write_bytes(b"program")
            package.package()
            package.install()
            installation = package.configuration.get_install_directory(
                package.control
            )
            assert (
                installation / "bin" / "example"
            ).read_bytes() == b"program"

    class TestExtract:
        def test_strip_root(
            self, package: Package, tmp_path: pathlib.Path
        ) -> None:
            source = tmp_path / "source"
            source.mkdir()
            (source / "README").write_text("source")
            create(source, package.orig_local_path)
            package.extract()
            assert (
                package.build_directory / "README"
            ).read_text() == "source"

    class TestStatus:
        def test_missing_and_present(
            self, package: Package, capsys: pytest.CaptureFixture[str]
        ) -> None:
            package.status()
            output = capsys.readouterr().out
            assert "Package example" in output
            assert "Version 1.0" in output
            for state in (
                "downloaded",
                "archived",
                "built",
                "packaged",
                "installed",
            ):
                assert "Not " + state in output
            for path in (
                package.orig_local_path,
                package.orig_package_path,
                package.local_path,
                package.package_path,
            ):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            package.configuration.get_install_directory(
                package.control
            ).mkdir(parents=True)
            package.status()
            assert "Not " not in capsys.readouterr().out
