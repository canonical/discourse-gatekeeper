# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for handling interactions with git commit."""

import re
from collections.abc import Iterator
from itertools import takewhile
from pathlib import Path
from typing import NamedTuple


class FileAdded(NamedTuple):
    """File that was added or copied in a commit.

    Attributes:
        path: The location of the file on disk.
        content: The content of the file.
    """

    path: Path
    content: str


class FileModified(NamedTuple):
    """File that was modified in a commit.

    Attributes:
        path: The location of the file on disk.
        content: The content of the file.
    """

    path: Path
    content: str


class FileDeleted(NamedTuple):
    """File that was deleted in a commit.

    Attributes:
        path: The location of the file on disk.
    """

    path: Path


# Copied will be mapped to added and renamed will be mapped to be a delete and add
FileAction = FileAdded | FileModified | FileDeleted
_ADDED_PATTERN = re.compile(r"A\s*(\S*)")
_MODIFIED_PATTERN = re.compile(r"M\s*(\S*)")
_DELETED_PATTERN = re.compile(r"D\s*(\S*)")
_RENAMED_PATTERN = re.compile(r"R\d+\s*(\S*)\s*(\S*)")
_COPIED_PATTERN = re.compile(r"C\d+\s*(\S*)\s*(\S*)")


def parse_git_show(output: str, repository_path: Path) -> Iterator[FileAction]:
    """Parse the output of a git show with --name-status intmanageable files.

    Args:
        output: The output of the git show command.
        repository_path: The path to the git repository.

    Yields:
        Information about each of the files that changed in the commit.
    """
    # Processing in reverse up to empty line to detect end of file changes as an empty line.
    # Example output:
    #     git show --name-status <commit sha>
    #     commit <commit sha> (HEAD -> <branch name>)
    #     Author: <author>
    #     Date:   <date>

    #         <commit message>

    #     A       add-file.text
    #     M       change-file.text
    #     D       delete-file.txt
    #     R100    renamed-file.text       is-renamed-file.text
    #     C100    to-be-copied-file.text  copied-file.text
    lines = takewhile(bool, reversed(output.splitlines()))
    for line in lines:
        if (added_match := _ADDED_PATTERN.match(line)) is not None:
            path = Path(added_match.group(1))
            yield FileAdded(path, (repository_path / path).read_text(encoding="utf-8"))
            continue

        if (copied_match := _COPIED_PATTERN.match(line)) is not None:
            path = Path(copied_match.group(2))
            yield FileAdded(path, (repository_path / path).read_text(encoding="utf-8"))
            continue

        if (modified_match := _MODIFIED_PATTERN.match(line)) is not None:
            path = Path(modified_match.group(1))
            yield FileModified(path, (repository_path / path).read_text(encoding="utf-8"))
            continue

        if (delete_match := _DELETED_PATTERN.match(line)) is not None:
            path = Path(delete_match.group(1))
            yield FileDeleted(path)
            continue

        if (renamed_match := _RENAMED_PATTERN.match(line)) is not None:
            old_path = Path(renamed_match.group(1))
            path = Path(renamed_match.group(2))
            yield FileDeleted(old_path)
            yield FileAdded(path, (repository_path / path).read_text(encoding="utf-8"))
            continue
