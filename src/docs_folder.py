# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Class for reading the docs directory."""

from pathlib import Path
import typing


class File(typing.NamedTuple):
    """Represents a file or directory in the docs directory.

    Attrs:
        disk_path: The path to the file on the local disk.
        level: The number of parent directories to the docs folder including the docs folder.
        table_path: The compyuted table path based on the disk path relative to the docs folder.
        navlink_title: The title of the navlink.
    """

    disk_path: Path
    level: int
    table_path: str
    navlink_title: str


def read(docs_path: Path) -> list[File]:
    """Read the docs directory and return information about each directory and documentation file.

    Algorithm:
        1.  Get a list of all sub directories and .md files in the docs folder.
        2.  For each directory/ file:
            2.1. Calculate the level based on the number of sub-directories to the docs directory
                including the docs directory.
            2.2. Calculate the table path using the relative path to the docs directory, replacing
                / with -, removing the extension and converting to lower case.
            2.3. Calculate the navlink title based on the first heading, first line if there is no
                heading or the file/ directory name excluding the extension with - replaced by space
                and titlelized if the file is empty or it is a directory.

    Args:
        docs_path: The path to the docs folder containing all the documentation.

    Returns:
        Information about each directory and documentation file in the docs folder.
    """
