# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for docs folder module."""

# Need access to protected functions for testing
# pylint: disable=protected-access

from pathlib import Path

import pytest

from src import docs_folder


@pytest.mark.parametrize(
    "directories, files, expected_paths",
    [
        pytest.param((), (), (), id="empty"),
        pytest.param((("dir1",),), (), (("dir1",),), id="single directory"),
        pytest.param((("dir1",), ("dir2",)), (), (("dir1",), ("dir2",)), id="multiple directory"),
        pytest.param(
            (("dir1",), ("dir1", "subdir1")),
            (),
            (("dir1",), ("dir1", "subdir1")),
            id="nested directory",
        ),
        pytest.param((), (("file1.md",),), (("file1.md",),), id="single file"),
        pytest.param((), (("file1.txt",),), (), id="single file not documentation"),
        pytest.param(
            (("dir1",),),
            (("dir1", "file1.md"),),
            (("dir1",), ("dir1", "file1.md")),
            id="single file in directory",
        ),
        pytest.param(
            (), (("file1.md",), ("file2.md",)), (("file1.md",), ("file2.md",)), id="multiple files"
        ),
        pytest.param(
            (("dir1",),),
            (("file1.md",),),
            (("dir1",), ("file1.md",)),
            id="single directory and single file",
        ),
        pytest.param(
            (("dir1",),),
            (("dir1", "file1.md"),),
            (("dir1",), ("dir1", "file1.md")),
            id="file in directory",
        ),
    ],
)
def test__get_directories_files(
    directories: tuple[tuple[str], ...],
    files: tuple[tuple[str], ...],
    expected_paths: tuple[str, ...],
    tmp_path: Path,
):
    """
    arrange: given docs folder and paths to create
    act: when _get_directories_files is called with the docs folder
    assert: then the expected paths are returned.
    """
    for directory in directories:
        (tmp_path / Path(*directory)).mkdir()
    for file in files:
        (tmp_path / Path(*file)).touch()

    returned_paths = docs_folder._get_directories_files(docs_path=tmp_path)

    assert {path.relative_to(tmp_path) for path in returned_paths} == {
        Path(*expected_path) for expected_path in expected_paths
    }
