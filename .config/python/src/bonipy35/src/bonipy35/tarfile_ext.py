#!/usr/bin/env python3

# Standard libraries.
import logging
import pathlib
import tarfile

from typing import Union

# Internal modules.
from . import pathlib_ext

_logger = logging.getLogger(__name__)


def create(
    source_dir: pathlib.Path,
    dest: pathlib.Path,
    arcname: Union[None, str] = None,
) -> None:
    if arcname is None:
        arcname = source_dir.name
    _logger.info("Creating tarball at   : %s", dest)
    _logger.info("Creating tarball using: %s", source_dir)
    pathlib_ext.ensure_is_dir(dest.parent)
    with tarfile.open(str(dest), "w:gz") as tf:
        tf.add(str(source_dir), arcname=arcname)


def extract(
    tarball: pathlib.Path, dest: pathlib.Path, strip_components: int = 0
) -> None:
    _logger.info("Extracting from: %s", tarball)
    _logger.info("Extracting into: %s", dest)
    pathlib_ext.ensure_is_dir(dest)
    with tarfile.open(str(tarball), "r:gz") as tf:
        members = tf.getmembers()
        for member in members:
            if strip_components:
                parts = pathlib.Path(member.name).parts
                if len(parts) <= strip_components:
                    continue
                parts = parts[strip_components:]
                member.name = str(pathlib.Path(*parts))
            tf.extract(member, str(dest))
