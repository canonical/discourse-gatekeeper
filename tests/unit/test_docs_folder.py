# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for docs folder module."""

# Need access to protected functions for testing
# pylint: disable=protected-access

from pathlib import Path

import pytest

from src import docs_folder


def create_directories_file(
    base_path: Path, directories: tuple[str, ...], file: str | None
) -> Path:
    """Create directories and file.

    Args:
        base_path: The path to start with.
        directories: The directories to be created.
        file: The file to be created. If None, only creates directories.

    Returns:
        The deepest nested directory or file.
    """
    path = base_path
    for directory in directories:
        path /= directory
        path.mkdir()
    if file is not None:
        path /= file
        path.touch()
    return path


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
    "directories, file, expected_level",
    [
        pytest.param((), "file1.md", 1, id="file in docs"),
        pytest.param(("dir1",), None, 1, id="directory in docs"),
        pytest.param(("dir1",), "file1.md", 2, id="directory file in docs"),
        pytest.param(("dir1", "dir2"), None, 2, id="multiple directory in docs"),
        pytest.param(("dir1", "dir2"), "file1.md", 3, id="multiple directory file in docs"),
        pytest.param(("dir1", "dir2", "dir3"), None, 3, id="many directory in docs"),
        pytest.param(("dir1", "dir2", "dir3"), "file1.md", 4, id="many directory file in docs"),
    ],
)
def test__calculate_level(
    directories: tuple[str, ...], file: str | None, expected_level: int, tmp_path: Path
):
    """
    arrange: given directories and file to create
    act: when _calculate_level is called with the docs folder and the created directory and file
    assert: then the expected level is returned.
    """
    path = create_directories_file(base_path=tmp_path, directories=directories, file=file)

    returned_level = docs_folder._calculate_level(path=path, docs_path=tmp_path)

    assert returned_level == expected_level


@pytest.mark.parametrize(
    "directories, file, expected_table_path",
    [
        pytest.param((), "file1.md", "file1", id="file in docs"),
        pytest.param((), "FILE1.md", "file1", id="file upper case in docs"),
        pytest.param(("dir1",), None, "dir1", id="directory in docs"),
        pytest.param(("dir1",), "file1.md", "dir1-file1", id="directory file in docs"),
        pytest.param(("dir1", "dir2"), None, "dir1-dir2", id="multiple directory in docs"),
        pytest.param(
            ("dir1", "dir2"), "file1.md", "dir1-dir2-file1", id="multiple directory file in docs"
        ),
        pytest.param(
            ("dir1", "dir2", "dir3"), None, "dir1-dir2-dir3", id="many directory in docs"
        ),
        pytest.param(
            ("dir1", "dir2", "dir3"),
            "file1.md",
            "dir1-dir2-dir3-file1",
            id="many directory file in docs",
        ),
    ],
)
def test__calculate_table_path(
    directories: tuple[str, ...], file: str | None, expected_table_path: str, tmp_path: Path
):
    """
    arrange: given directories and file to create
    act: when _calculate_table_path is called with the docs folder and the created directory and file
    assert: then the expected table path is returned.
    """
    path = create_directories_file(base_path=tmp_path, directories=directories, file=file)

    returned_level = docs_folder._calculate_table_path(path=path, docs_path=tmp_path)

    assert returned_level == expected_table_path


@pytest.mark.parametrize(
    "directories, file, content, expected_navlink_title",
    [
        pytest.param(("dir1",), None, None, "Dir1", id="directory in docs"),
        pytest.param(("dir1", "dir2"), None, None, "Dir2", id="nested directory in docs"),
        pytest.param(("the-dir-1",), None, None, "The Dir 1", id="directory in docs with -"),
        pytest.param((), "file1.md", None, "File1", id="file in docs empty"),
        pytest.param(("dir1",), "file1.md", None, "File1", id="file in subdirectory empty"),
        pytest.param((), "the-file-1.md", None, "The File 1", id="file including - in docs empty"),
        pytest.param((), "file1.md", "", "File1", id="file in docs empty string"),
        pytest.param((), "file1.md", "line 1", "line 1", id="file in docs single line no title"),
        pytest.param(
            (),
            "file1.md",
            "line 1\nline 2",
            "line 1",
            id="file in docs multiple line no title",
        ),
        pytest.param((), "file1.md", "# line 1", "line 1", id="file in docs title on first line"),
        pytest.param(
            (),
            "file1.md",
            "# line 1\nline 2",
            "line 1",
            id="file in docs title on first line with more lines",
        ),
        pytest.param(
            (),
            "file1.md",
            "line 1\n# line 2",
            "line 2",
            id="file in docs title on second line",
        ),
        pytest.param(
            (),
            "file1.md",
            "line 1\n# line 2\nline 3",
            "line 2",
            id="file in docs title on second line with more lines",
        ),
    ],
)
def test__calculate_navlink_title(
    directories: tuple[str, ...],
    file: str | None,
    content: str | None,
    expected_navlink_title: str,
    tmp_path: Path,
):
    """
    arrange: given directories and file to create and contents of the file
    act: when _calculate_navlink_title is called with the docs folder and the created directory and file
    assert: then the expected navlink title is returned.
    """
    path = create_directories_file(base_path=tmp_path, directories=directories, file=file)
    if file is not None and content is not None:
        path.write_text(content, encoding="utf-8")

    returned_navlink_title = docs_folder._calculate_navlink_title(path=path, docs_path=tmp_path)

    assert returned_navlink_title == expected_navlink_title
