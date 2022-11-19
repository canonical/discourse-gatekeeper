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
        pytest.param(
            (), (("file1.MD",),), (("file1.MD",),), id="single file upper case extension"
        ),
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
        pytest.param(
            (("dir1",), ("dir2",)),
            (
                ("file1.md",),
                ("dir1", "dir1file1.md"),
                ("dir1", "dir1file2.md"),
                ("dir2", "dir2file1.md"),
                ("dir2", "dir2file2.md"),
            ),
            (
                ("dir1",),
                ("dir1", "dir1file1.md"),
                ("dir1", "dir1file2.md"),
                ("dir2",),
                ("dir2", "dir2file1.md"),
                ("dir2", "dir2file2.md"),
                ("file1.md",),
            ),
            id="multiple files in multiple directories",
        ),
    ],
)
def test__get_directories_files(
    directories: tuple[tuple[str, ...], ...],
    files: tuple[tuple[str, ...], ...],
    expected_paths: tuple[tuple[str, ...], ...],
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

    assert [path.relative_to(tmp_path) for path in returned_paths] == [
        Path(*expected_path) for expected_path in expected_paths
    ]


@pytest.mark.parametrize(
    "directories, expected_level",
    [
        pytest.param(("dir1",), 1, id="single"),
        pytest.param(("dir1", "dir2"), 2, id="multiple"),
        pytest.param(("dir1", "dir2", "dir3"), 3, id="many"),
    ],
)
def test__calculate_level_directory(
    directories: tuple[str, ...], expected_level: int, tmp_path: Path
):
    """
    arrange: directories to create
    act: when _calculate_level is called with the docs folder and the created directory
    assert: then the expected level is returned.
    """
    path = tmp_path
    for directory in directories:
        path /= directory
        path.mkdir()

    returned_level = docs_folder._calculate_level(path=path, docs_path=tmp_path)

    assert returned_level == expected_level


@pytest.mark.parametrize(
    "directories, expected_level",
    [
        pytest.param((), 1, id="in docs"),
        pytest.param(("dir1",), 2, id="single directory"),
        pytest.param(("dir1", "dir2"), 3, id="multiple directories"),
        pytest.param(("dir1", "dir2", "dir3"), 4, id="many directories"),
    ],
)
def test__calculate_level_file(directories: tuple[str, ...], expected_level: int, tmp_path: Path):
    """
    arrange: directories to create
    act: when _calculate_level is called with the docs folder and the created directory
    assert: then the expected level is returned.
    """
    path = tmp_path
    for directory in directories:
        path /= directory
        path.mkdir()
    path /= "file1.md"
    path.touch()

    returned_level = docs_folder._calculate_level(path=path, docs_path=tmp_path)

    assert returned_level == expected_level
