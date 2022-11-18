# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Class for reading the docs directory."""

from pathlib import Path
import typing


class PathInfo(typing.NamedTuple):
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


def _get_directories_files(docs_path: Path) -> typing.Iterator[Path]:
    """Get all the directories and documentation files recursively in the docs folder.

    Args:
        docs_path: The path to the docs folder containing all the documentation.

    Returns:
        Iterator with all the directories and documentation files in the docs folder.
    """
    return (path for path in docs_path.rglob("*") if path.is_dir() or path.suffix.lower() == ".md")


def _calculate_level(path: Path, docs_path: Path) -> int:
    """Calculate the level of a path.

    Args:
        path: The path to calculate the level for.
        docs_path: The path to the docs folder.

    Returns:
        The number of sub-directories from the path to the docs directory including the docs
        directory.
    """


def _calculate_table_path(path: Path, docs_path: Path) -> int:
    """Calculate the table path of a path.

    Args:
        path: The path to calculate the table path for.
        docs_path: The path to the docs folder.

    Returns:
        The relative path to the docs directory, replacing / with -, removing the extension and
        converting to lower case.
    """


def _calculate_navlink_title(path: Path, docs_path: Path) -> int:
    """Calculate the navlink title of a path.

    Args:
        path: The path to calculate the navlink title for.
        docs_path: The path to the docs folder.

    Returns:
        The first heading, first line if there is no heading or the file/ directory name excluding
        the extension with - replaced by space and titlelized if the file is empty or it is a
        directory.
    """


def _get_path_info(path: Path, docs_path: Path) -> PathInfo:
    """Get the information for a path.

    Args:
        path: The path to calculate the information for.
        docs_path: The path to the docs folder.

    Returns:
        The information for the path.
    """


def read(docs_path: Path) -> list[PathInfo]:
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
