#!/usr/bin/env python3

# Standard libraries.
import pathlib
import tarfile

from typing import Union

# External dependencies.
import pytest

# Internal modules.
from bonipy35.tarfile_ext import create, extract


@pytest.fixture(name="source_dir")
def archive_source(tmp_path: pathlib.Path) -> pathlib.Path:
    source = tmp_path / "source"
    (source / "nested").mkdir(parents=True)
    (source / "empty").mkdir()
    (source / "first.txt").write_text("first content")
    (source / "nested" / "second.txt").write_bytes(b"second content")
    return source


class TestCreate:
    @pytest.mark.parametrize("arcname", [None, "custom/root"])
    def test_archives_contents(
        self,
        arcname: Union[None, str],
        source_dir: pathlib.Path,
        tmp_path: pathlib.Path,
    ) -> None:
        dest = tmp_path / "output" / "archive.tar.gz"
        create(source_dir, dest, arcname=arcname)
        root = source_dir.name if arcname is None else arcname
        with tarfile.open(str(dest), "r:gz") as archive:
            assert set(archive.getnames()) == {
                root,
                root + "/empty",
                root + "/first.txt",
                root + "/nested",
                root + "/nested/second.txt",
            }
            first = archive.extractfile(root + "/first.txt")
            assert first is not None
            with first:
                assert first.read() == b"first content"
            second = archive.extractfile(root + "/nested/second.txt")
            assert second is not None
            with second:
                assert second.read() == b"second content"
        assert (source_dir / "first.txt").read_text() == "first content"

    def test_errors_if_source_missing(self, tmp_path: pathlib.Path) -> None:
        with pytest.raises(FileNotFoundError):
            create(tmp_path / "missing", tmp_path / "archive.tar.gz")

    def test_errors_if_destination_parent_is_file(
        self, source_dir: pathlib.Path, tmp_path: pathlib.Path
    ) -> None:
        parent = tmp_path / "file"
        parent.write_text("keep")
        with pytest.raises(FileExistsError):
            create(source_dir, parent / "archive.tar.gz")
        assert parent.read_text() == "keep"


class TestExtract:
    def test_creates_original_content(
        self, source_dir: pathlib.Path, tmp_path: pathlib.Path
    ) -> None:
        tarball = tmp_path / "archive.tar.gz"
        create(source_dir, tarball)
        dest = tmp_path / "extracted"
        extract(tarball, dest)
        assert (dest / "source" / "first.txt").read_text() == "first content"
        assert (
            dest / "source" / "nested" / "second.txt"
        ).read_bytes() == b"second content"
        assert (dest / "source" / "empty").is_dir()

    def test_errors_if_destination_is_file(
        self, source_dir: pathlib.Path, tmp_path: pathlib.Path
    ) -> None:
        tarball = tmp_path / "archive.tar.gz"
        create(source_dir, tarball)
        dest = tmp_path / "existing.txt"
        dest.write_text("keep")
        with pytest.raises(FileExistsError):
            extract(tarball, dest)
        assert dest.read_text() == "keep"

    def test_errors_if_archive_invalid(self, tmp_path: pathlib.Path) -> None:
        tarball = tmp_path / "invalid.tar.gz"
        tarball.write_text("not an archive")
        with pytest.raises(tarfile.ReadError):
            extract(tarball, tmp_path / "extracted")

    def test_errors_if_archive_missing(self, tmp_path: pathlib.Path) -> None:
        with pytest.raises(FileNotFoundError):
            extract(tmp_path / "missing.tar.gz", tmp_path / "extracted")

    def test_strips_leading_component(
        self, source_dir: pathlib.Path, tmp_path: pathlib.Path
    ) -> None:
        tarball = tmp_path / "archive.tar.gz"
        create(source_dir, tarball)
        dest = tmp_path / "extracted"
        extract(tarball, dest, strip_components=1)
        assert (dest / "first.txt").read_text() == "first content"
        assert (
            dest / "nested" / "second.txt"
        ).read_bytes() == b"second content"
        assert (dest / "empty").is_dir()
        assert not (dest / "source").exists()

    def test_strips_multiple_components(
        self, source_dir: pathlib.Path, tmp_path: pathlib.Path
    ) -> None:
        tarball = tmp_path / "archive.tar.gz"
        create(source_dir, tarball)
        dest = tmp_path / "extracted"
        extract(tarball, dest, strip_components=2)
        assert list(dest.iterdir()) == [dest / "second.txt"]
        assert (dest / "second.txt").read_bytes() == b"second content"

    def test_skips_members_with_too_few_components(
        self, source_dir: pathlib.Path, tmp_path: pathlib.Path
    ) -> None:
        tarball = tmp_path / "archive.tar.gz"
        create(source_dir, tarball)
        dest = tmp_path / "extracted"
        extract(tarball, dest, strip_components=3)
        assert dest.is_dir()
        assert not list(dest.iterdir())
