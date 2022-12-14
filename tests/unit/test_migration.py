# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for migration module."""

# Need access to protected functions for testing
# pylint: disable=protected-access

from pathlib import Path
from typing import Iterable, List
from unittest import mock

import pytest

from src import discourse, exceptions, migration, types_

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
    with pytest.raises(exceptions.InvalidTableRowError) as exc_info:
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
                (
                    root_dir_row := types_.TableRow(
                        level=1,
                        path="root path 1",
                        navlink=(dir_navlink := types_.Navlink(title="title 1", link=None)),
                    )
                ),
            ],
            [
                types_.GitkeepMeta(
                    path=Path(root_dir_row.path) / (gitkeep_file := Path(".gitkeep")),
                    table_row=root_dir_row,
                )
            ],
            id="table row no navlink",
        ),
        pytest.param(
            [
                root_dir_row,
                (
                    root_dir_row_2 := types_.TableRow(
                        level=1,
                        path="root path 2",
                        navlink=dir_navlink,
                    )
                ),
            ],
            [
                types_.GitkeepMeta(
                    path=Path(root_dir_row.path) / gitkeep_file, table_row=root_dir_row
                ),
                types_.GitkeepMeta(
                    path=Path(root_dir_row_2.path) / gitkeep_file, table_row=root_dir_row_2
                ),
            ],
            id="multiple empty directories",
        ),
        pytest.param(
            [
                root_dir_row,
                sub_dir_row := types_.TableRow(
                    level=2,
                    path="sub path 1",
                    navlink=(dir_navlink),
                ),
            ],
            [
                types_.GitkeepMeta(
                    path=Path(root_dir_row.path) / Path(sub_dir_row.path) / gitkeep_file,
                    table_row=sub_dir_row,
                ),
            ],
            id="nested empty directories",
        ),
    ],
)
def test_extract_docs_empty_directory_rows(
    table_rows: Iterable[types_.TableRow],
    expected_files: List[types_.MigrationFileMeta],
):
    """
    arrange: given valid table rows with no navlink(only directories)
    act: when migrate is called
    assert: .gitkeep files with respective directories are returned.
    """
    files = [file for file in migration.extract_docs(table_rows=table_rows)]
    assert files == expected_files


@pytest.mark.parametrize(
    "table_rows, expected_files",
    [
        pytest.param(
            [
                root_file_row := types_.TableRow(
                    level=1,
                    path="root file 1",
                    navlink=(
                        file_navlink := types_.Navlink(
                            title="title 1", link=(link_str := "link 1")
                        )
                    ),
                )
            ],
            [
                types_.DocumentMeta(
                    path=path_to_markdown(Path(root_file_row.path)),
                    link=link_str,
                    table_row=root_file_row,
                )
            ],
            id="single file",
        ),
        pytest.param(
            [
                root_dir_row,
                sub_file_row := types_.TableRow(
                    level=2,
                    path="sub file 1",
                    navlink=file_navlink,
                ),
            ],
            [
                types_.DocumentMeta(
                    path=path_to_markdown(Path(root_dir_row.path) / Path(sub_file_row.path)),
                    link=link_str,
                    table_row=sub_file_row,
                )
            ],
            id="single file in directory",
        ),
        pytest.param(
            [
                root_file_row,
                root_file_row_2 := types_.TableRow(
                    level=1,
                    path="root file 2",
                    navlink=file_navlink,
                ),
            ],
            [
                types_.DocumentMeta(
                    path=path_to_markdown(Path(root_file_row.path)),
                    link=link_str,
                    table_row=root_file_row,
                ),
                types_.DocumentMeta(
                    path=path_to_markdown(Path(root_file_row_2.path)),
                    link=link_str,
                    table_row=root_file_row_2,
                ),
            ],
            id="multiple files",
        ),
        pytest.param(
            [
                root_dir_row,
                sub_file_row,
                sub_file_row_2 := types_.TableRow(
                    level=2,
                    path="sub file 2",
                    navlink=(file_navlink),
                ),
            ],
            [
                types_.DocumentMeta(
                    path=path_to_markdown(Path(root_dir_row.path) / Path(sub_file_row.path)),
                    link=link_str,
                    table_row=sub_file_row,
                ),
                types_.DocumentMeta(
                    path=path_to_markdown(Path(root_dir_row.path) / Path(sub_file_row_2.path)),
                    link=link_str,
                    table_row=sub_file_row_2,
                ),
            ],
            id="multiple files in directory",
        ),
        pytest.param(
            [
                root_dir_row,
                sub_file_row,
                sub_file_row_2,
                root_dir_row_2,
                sub_file_row,
                sub_file_row_2,
            ],
            [
                types_.DocumentMeta(
                    path=path_to_markdown(Path(root_dir_row.path) / Path(sub_file_row.path)),
                    link=link_str,
                    table_row=sub_file_row,
                ),
                types_.DocumentMeta(
                    path=path_to_markdown(Path(root_dir_row.path) / Path(sub_file_row_2.path)),
                    link=link_str,
                    table_row=sub_file_row_2,
                ),
                types_.DocumentMeta(
                    path=path_to_markdown(Path(root_dir_row_2.path) / Path(sub_file_row.path)),
                    link=link_str,
                    table_row=sub_file_row,
                ),
                types_.DocumentMeta(
                    path=path_to_markdown(Path(root_dir_row_2.path) / Path(sub_file_row_2.path)),
                    link=link_str,
                    table_row=sub_file_row_2,
                ),
            ],
            id="multiple files in multiple directory",
        ),
        pytest.param(
            [
                root_dir_row,
                sub_dir_row,
                (
                    nested_file_row := types_.TableRow(
                        level=3,
                        path="path 3",
                        navlink=(file_navlink),
                    )
                ),
            ],
            [
                types_.DocumentMeta(
                    path=path_to_markdown(
                        Path(root_dir_row.path)
                        / Path(sub_dir_row.path)
                        / Path(nested_file_row.path)
                    ),
                    link=link_str,
                    table_row=nested_file_row,
                ),
            ],
            id="nested directory file",
        ),
    ],
)
def test_extract_docs(
    table_rows: Iterable[types_.TableRow],
    expected_files: List[types_.MigrationFileMeta],
):
    """
    arrange: given valid table rows
    act: when migrate is called
    assert: document file with correct paths are returned.
    """
    files = [file for file in migration.extract_docs(table_rows=table_rows)]
    assert files == expected_files


def test__migrate_gitkeep(tmp_path: Path):
    """
    arrange: given valid gitkeep metadata
    act: when _migrate_gitkeep is called
    assert: migration report is created with responsible table row, written path \
        and reason.
    """
    path = Path("empty/docs/dir/.gitkeep")
    table_row = types_.TableRow(
        level=1, path="empty-directory", navlink=types_.Navlink(title="title 1", link=None)
    )
    gitkeep_meta = types_.GitkeepMeta(path=path, table_row=table_row)

    migration_report = migration._migrate_gitkeep(gitkeep_meta=gitkeep_meta, docs_path=tmp_path)

    assert (file_path := tmp_path / path).is_file()
    assert file_path.read_text(encoding="utf-8") == ""
    assert migration_report.table_row == table_row
    assert migration_report.result == types_.ActionResult.SUCCESS
    assert migration_report.reason is not None
    assert "created due to empty directory" in migration_report.reason


def test__migrate_document_fail(tmp_path: Path):
    """
    arrange: given valid document metadata and mocked discourse that raises an error
    act: when _migrate_document is called
    assert: failed migration report is returned.
    """
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.retrieve_topic.side_effect = (error := exceptions.DiscourseError("fail"))
    table_row = types_.TableRow(
        level=(level := 1),
        path=(path_str := "empty-directory"),
        navlink=types_.Navlink(title=(navlink_title := "title 1"), link=(link_str := "link 1")),
    )
    document_meta = types_.DocumentMeta(
        path=(path := Path(path_str)), table_row=table_row, link=link_str
    )

    returned_report = migration._migrate_document(
        document_meta=document_meta, discourse=mocked_discourse, docs_path=tmp_path
    )

    assert not (tmp_path / path).exists()
    mocked_discourse.retrieve_topic.assert_called_once_with(url=link_str)
    assert returned_report.table_row is not None
    assert returned_report.table_row.level == level
    assert returned_report.table_row.path == path_str
    assert returned_report.table_row.navlink.title == navlink_title
    assert returned_report.table_row.navlink.link == link_str
    assert returned_report.result == types_.ActionResult.FAIL
    assert returned_report.reason == str(error)


def test__migrate_document(tmp_path: Path):
    """
    arrange: given valid document metadata
    act: when _migrate_document is called
    assert: migration report is created with responsible table row, written path \
        and reason.
    """
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.retrieve_topic.return_value = (content := "content")
    table_row = types_.TableRow(
        level=(level := 1),
        path=(path_str := "empty-directory"),
        navlink=types_.Navlink(title=(navlink_title := "title 1"), link=(link_str := "link 1")),
    )
    document_meta = types_.DocumentMeta(
        path=(path := Path(path_str)), table_row=table_row, link=link_str
    )

    returned_report = migration._migrate_document(
        document_meta=document_meta, discourse=mocked_discourse, docs_path=tmp_path
    )

    assert (file_path := (tmp_path / path)).is_file()
    assert file_path.read_text(encoding="utf-8") == content
    mocked_discourse.retrieve_topic.assert_called_once_with(url=link_str)
    assert returned_report.table_row is not None
    assert returned_report.table_row.level == level
    assert returned_report.table_row.path == path_str
    assert returned_report.table_row.navlink.title == navlink_title
    assert returned_report.table_row.navlink.link == link_str
    assert returned_report.result == types_.ActionResult.SUCCESS
