# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for migration module."""

# Need access to protected functions for testing
# pylint: disable=protected-access

from pathlib import Path
from typing import Iterable, List

import pytest

from src import exceptions, migration, types_

from .helpers import path_to_markdown


# Pylint diesn't understand how the walrus operator works
# pylint: disable=undefined-variable,unused-variable
@pytest.mark.parametrize(
    "table_rows, expected_error_msg_contents",
    [
        pytest.param(
            [
                types_.TableRow(
                    level=-1,
                    path=(test_path := "path 1"),
                    navlink=(test_navlink := types_.Navlink(title="title 1", link=None)),
                )
            ],
            (invalid_msg := "invalid level"),
            id="negative table row level",
        ),
        pytest.param(
            [
                types_.TableRow(
                    level=0,
                    path=(test_path),
                    navlink=(test_navlink),
                )
            ],
            invalid_msg,
            id="zero table row level",
        ),
        pytest.param(
            [
                types_.TableRow(
                    level=2,
                    path=(test_path),
                    navlink=(test_navlink),
                )
            ],
            (level_difference_msg := "level difference"),
            id="invalid starting table row level",
        ),
        pytest.param(
            [
                types_.TableRow(
                    level=1,
                    path=(test_path),
                    navlink=(test_navlink),
                ),
                types_.TableRow(
                    level=3,
                    path=(test_path),
                    navlink=(test_navlink),
                ),
            ],
            level_difference_msg,
            id="invalid table row level change",
        ),
    ],
)
def test__validate_row_levels_invalid_rows(
    table_rows: Iterable[types_.TableRow], expected_error_msg_contents: str
):
    """
    arrange: given table rows with invalid levels
    act: when _validate_row_levels is called
    assert: InvalidRow exception is raised with excpected error message contents.
    """
    with pytest.raises(exceptions.InvalidTableRowLevelError) as exc_info:
        migration._validate_row_levels(table_rows=table_rows)

    exc_str = str(exc_info.value).lower()
    assert expected_error_msg_contents in exc_str


@pytest.mark.parametrize(
    "table_rows",
    [
        pytest.param(
            [
                types_.TableRow(
                    level=1,
                    path=("path 1"),
                    navlink=(types_.Navlink(title="title 1", link=None)),
                ),
            ],
            id="valid level",
        ),
        pytest.param(
            [
                types_.TableRow(
                    level=1,
                    path=("path 1"),
                    navlink=(types_.Navlink(title="title 1", link=None)),
                ),
                types_.TableRow(
                    level=2,
                    path=("path 2"),
                    navlink=(types_.Navlink(title="title 2", link="link")),
                ),
            ],
            id="increasing levels",
        ),
        pytest.param(
            [
                types_.TableRow(
                    level=1,
                    path=("path 1"),
                    navlink=(types_.Navlink(title="title 1", link=None)),
                ),
                types_.TableRow(
                    level=2,
                    path=("path 2"),
                    navlink=(types_.Navlink(title="title 2", link="link 1")),
                ),
                types_.TableRow(
                    level=1,
                    path=("path 3"),
                    navlink=(types_.Navlink(title="title 3", link="link 2")),
                ),
            ],
            id="descend one level",
        ),
        pytest.param(
            [
                types_.TableRow(
                    level=1,
                    path=("path 1"),
                    navlink=(types_.Navlink(title="title 1", link=None)),
                ),
                types_.TableRow(
                    level=2,
                    path=("path 2"),
                    navlink=(types_.Navlink(title="title 2", link="link 1")),
                ),
                types_.TableRow(
                    level=3,
                    path=("path 3"),
                    navlink=(types_.Navlink(title="title 3", link="link 2")),
                ),
                types_.TableRow(
                    level=1,
                    path=("path 4"),
                    navlink=(types_.Navlink(title="title 4", link="link 3")),
                ),
            ],
            id="descend multiple levels",
        ),
    ],
)
def test__validate_row_levels(table_rows: Iterable[types_.TableRow]):
    """
    arrange: given table rows with valid levels
    act: when __validate_row_levels is called
    assert: no exceptions are raised.
    """
    migration._validate_row_levels(table_rows=table_rows)


@pytest.mark.parametrize(
    "table_rows, expected_files",
    [
        pytest.param(
            [
                types_.TableRow(
                    level=1,
                    path=((path_str := "path 1")),
                    navlink=((dir_navlink := types_.Navlink(title="title 1", link=None))),
                ),
            ],
            [types_.GitkeepFile(path=Path(path_str) / (gitkeep_file := Path(".gitkeep")))],
            id="table row no navlink",
        ),
        pytest.param(
            [
                types_.TableRow(
                    level=1,
                    path=(path_str),
                    navlink=(dir_navlink),
                ),
                types_.TableRow(
                    level=1,
                    path=((path_str_2 := "path 2")),
                    navlink=(dir_navlink),
                ),
            ],
            [
                types_.GitkeepFile(path=Path(path_str) / gitkeep_file),
                types_.GitkeepFile(path=Path(path_str_2) / gitkeep_file),
            ],
            id="multiple empty directories",
        ),
        pytest.param(
            [
                types_.TableRow(
                    level=1,
                    path=(path_str),
                    navlink=(dir_navlink),
                ),
                types_.TableRow(
                    level=2,
                    path=(path_str_2),
                    navlink=(dir_navlink),
                ),
            ],
            [
                types_.GitkeepFile(path=Path(path_str) / Path(path_str_2) / gitkeep_file),
            ],
            id="nested empty directories",
        ),
    ],
)
def test_migrate_empty_directory(
    table_rows: Iterable[types_.TableRow],
    expected_files: List[types_.MigrationDocument],
):
    """
    arrange: given valid table rows with no navlink(only directories)
    act: when migrate is called
    assert: gitkeep files with respective directories are returned.
    """
    files = [file for file in migration.migrate(table_rows=table_rows)]
    assert files == expected_files


@pytest.mark.parametrize(
    "table_rows, expected_files",
    [
        pytest.param(
            [
                types_.TableRow(
                    level=1,
                    path=(path_str),
                    navlink=(
                        (file_navlink := types_.Navlink(title="title 1", link=(link := "link 1")))
                    ),
                ),
            ],
            [types_.DocumentFile(path=path_to_markdown(Path(path_str)), link=link)],
            id="single file",
        ),
        pytest.param(
            [
                types_.TableRow(
                    level=1,
                    path=(path_str),
                    navlink=(dir_navlink),
                ),
                types_.TableRow(
                    level=2,
                    path=(path_str_2),
                    navlink=(file_navlink),
                ),
            ],
            [
                types_.DocumentFile(
                    path=path_to_markdown(Path(path_str) / Path(path_str_2)), link=link
                )
            ],
            id="single file in directory",
        ),
        pytest.param(
            [
                types_.TableRow(
                    level=1,
                    path=(path_str),
                    navlink=(file_navlink),
                ),
                types_.TableRow(
                    level=1,
                    path=(path_str_2),
                    navlink=(file_navlink),
                ),
            ],
            [
                types_.DocumentFile(path=path_to_markdown(Path(path_str)), link=link),
                types_.DocumentFile(path=path_to_markdown(Path(path_str_2)), link=link),
            ],
            id="multiple files",
        ),
        pytest.param(
            [
                types_.TableRow(
                    level=1,
                    path=((base_path_dir_str := "base")),
                    navlink=(dir_navlink),
                ),
                types_.TableRow(
                    level=2,
                    path=(path_str),
                    navlink=(file_navlink),
                ),
                types_.TableRow(
                    level=2,
                    path=(path_str_2),
                    navlink=(file_navlink),
                ),
            ],
            [
                types_.DocumentFile(
                    path=path_to_markdown(Path(base_path_dir_str) / Path(path_str)), link=link
                ),
                types_.DocumentFile(
                    path=path_to_markdown(Path(base_path_dir_str) / Path(path_str_2)), link=link
                ),
            ],
            id="multiple files in directory",
        ),
        pytest.param(
            [
                types_.TableRow(
                    level=1,
                    path=(base_path_dir_str),
                    navlink=(dir_navlink),
                ),
                types_.TableRow(
                    level=2,
                    path=(path_str),
                    navlink=(file_navlink),
                ),
                types_.TableRow(
                    level=2,
                    path=(path_str_2),
                    navlink=(file_navlink),
                ),
                types_.TableRow(
                    level=1,
                    path=((base_path_dir_str_2 := "base 2")),
                    navlink=(dir_navlink),
                ),
                types_.TableRow(
                    level=2,
                    path=(path_str),
                    navlink=(file_navlink),
                ),
                types_.TableRow(
                    level=2,
                    path=(path_str_2),
                    navlink=(file_navlink),
                ),
            ],
            [
                types_.DocumentFile(
                    path=path_to_markdown(Path(base_path_dir_str) / Path(path_str)), link=link
                ),
                types_.DocumentFile(
                    path=path_to_markdown(Path(base_path_dir_str) / Path(path_str_2)), link=link
                ),
                types_.DocumentFile(
                    path=path_to_markdown(Path(base_path_dir_str_2) / Path(path_str)), link=link
                ),
                types_.DocumentFile(
                    path=path_to_markdown(Path(base_path_dir_str_2) / Path(path_str_2)), link=link
                ),
            ],
            id="multiple files in multiple directory",
        ),
        pytest.param(
            [
                types_.TableRow(
                    level=1,
                    path=(base_path_dir_str),
                    navlink=(dir_navlink),
                ),
                types_.TableRow(
                    level=2,
                    path=(path_str),
                    navlink=(dir_navlink),
                ),
                types_.TableRow(
                    level=3,
                    path=(path_str_2),
                    navlink=(file_navlink),
                ),
            ],
            [
                types_.DocumentFile(
                    path=path_to_markdown(
                        Path(base_path_dir_str) / Path(path_str) / Path(path_str_2)
                    ),
                    link=link,
                ),
            ],
            id="nested directory file",
        ),
    ],
)
def test_migrate_directory(
    table_rows: Iterable[types_.TableRow],
    expected_files: List[types_.MigrationDocument],
):
    """
    arrange: given valid table rows
    act: when migrate is called
    assert: document file with correct paths are returned.
    """
    files = [file for file in migration.migrate(table_rows=table_rows)]
    assert files == expected_files
