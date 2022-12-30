# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for migration module."""

# Need access to protected functions for testing
# pylint: disable=protected-access

from pathlib import Path
from typing import List
from collections.abc import Iterable
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
                    navlink=(directory_navlink := types_.Navlink(title="title 1", link=None)),
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
                    navlink=directory_navlink,
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
                    navlink=directory_navlink,
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
                    navlink=directory_navlink,
                ),
                types_.TableRow(
                    level=3,
                    path=(test_path),
                    navlink=directory_navlink,
                ),
            ],
            level_difference_msg,
            id="invalid table row level change",
        ),
        pytest.param(
            [
                types_.TableRow(
                    level=1,
                    path=(test_path),
                    navlink=(file_navlink := types_.Navlink(title="title 1", link="link 1")),
                ),
                types_.TableRow(
                    level=2,
                    path=(test_path),
                    navlink=(file_navlink := types_.Navlink(title="title 1", link="link 1")),
                ),
            ],
            "invalid parent row",
            id="invalid parent directory",
        ),
    ],
)
def test__validate_row_levels_invalid_rows(
    table_rows: list[types_.TableRow], expected_error_msg_contents: str
):
    """
    arrange: given table rows with invalid levels
    act: when _validate_row_levels is called
    assert: InvalidRow exception is raised with expected error message contents.
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
                    navlink=(types_.Navlink(title="title 2", link=None)),
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
def test__validate_row_levels(table_rows: list[types_.TableRow]):
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
                root_dir_row := types_.TableRow(
                    level=1,
                    path="root path 1",
                    navlink=(dir_navlink := types_.Navlink(title="title 1", link=None)),
                )
            ],
            [
                root_dir_gitkeep := types_.GitkeepMeta(
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
                root_dir_gitkeep,
                root_dir_2_gitkeep := types_.GitkeepMeta(
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
def test_extract_docs__from_table_rows_empty_directory_rows(
    table_rows: Iterable[types_.TableRow],
    expected_files: list[types_.MigrationFileMeta],
):
    """
    arrange: given valid table rows with no navlink(only directories)
    act: when migrate is called
    assert: .gitkeep files metadata with respective directories are returned.
    """
    assert list(migration._extract_docs_from_table_rows(table_rows=table_rows)) == expected_files


def test__index_file_from_content():
    """
    arrange: given content to write to index file
    act: when _index_file_from_content is called
    assert: index file metadata is returned.
    """
    content = "content 1"

    assert migration._index_file_from_content(content=content) == types_.IndexDocumentMeta(
        path=Path("index.md"), content=content
    )


@pytest.mark.parametrize(
    "table_rows, index_content, expected_migration_metadata",
    [
        pytest.param(
            [],
            content := "content 1",
            [index_meta := types_.IndexDocumentMeta(path=Path("index.md"), content=content)],
            id="no table rows",
        ),
        pytest.param(
            [root_dir_row, root_dir_row_2],
            content,
            [index_meta, root_dir_gitkeep, root_dir_2_gitkeep],
            id="multiple table_rows",
        ),
    ],
)
def test_get_docs_metadata(
    table_rows: list[types_.TableRow],
    index_content: str,
    expected_migration_metadata: list[types_.MigrationFileMeta],
):
    """
    arrange: given document table rows and index file content
    act: when get_docs_metadata is called
    assert: expected metadata are returned.
    """
    assert (
        list(migration.get_docs_metadata(table_rows=table_rows, index_content=index_content))
        == expected_migration_metadata
    )


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
    expected_files: list[types_.MigrationFileMeta],
):
    """
    arrange: given valid table rows
    act: when migrate is called
    assert: document file with correct paths are returned.
    """
    assert list(migration._extract_docs_from_table_rows(table_rows=table_rows)) == expected_files


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
    assert: document is created and migration report is returned.
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


def test__migrate_index(tmp_path: Path):
    """
    arrange: given valid index document metadata
    act: when _migrate_index is called
    assert: index file is created and migration report is returned.
    """
    document_meta = types_.IndexDocumentMeta(
        path=(path := Path("index.md")), content=(content := "content 1")
    )

    returned_report = migration._migrate_index(index_meta=document_meta, docs_path=tmp_path)

    assert (file_path := (tmp_path / path)).is_file()
    assert file_path.read_text(encoding="utf-8") == content
    assert returned_report.table_row is None
    assert returned_report.result == types_.ActionResult.SUCCESS
    assert returned_report.path == tmp_path / path
    assert returned_report.reason is None


@pytest.mark.parametrize(
    "file_meta, expected_report",
    [
        pytest.param(
            gitkeep_meta := types_.GitkeepMeta(
                path=(gitkeep_path := Path(".gitkeep")),
                table_row=(
                    table_row_sample := types_.TableRow(
                        level=1,
                        path="tablepath",
                        navlink=types_.Navlink(title="navlink", link=None),
                    )
                ),
            ),
            gitkeep_report := types_.MigrationReport(
                table_row=table_row_sample,
                path=gitkeep_path,
                result=types_.ActionResult.SUCCESS,
                reason=migration.EMPTY_DIR_REASON,
            ),
            id="gitkeep file",
        ),
        pytest.param(
            document_meta := types_.DocumentMeta(
                path=(document_path := Path("document.md")),
                table_row=table_row_sample,
                link="samplelink",
            ),
            document_report := types_.MigrationReport(
                table_row=table_row_sample,
                path=document_path,
                result=types_.ActionResult.SUCCESS,
                reason=None,
            ),
            id="document file",
        ),
        pytest.param(
            types_.IndexDocumentMeta(
                path=(index_path := Path("index.md")), content="index content"
            ),
            types_.MigrationReport(
                table_row=None,
                path=index_path,
                result=types_.ActionResult.SUCCESS,
                reason=None,
            ),
            id="index file",
        ),
    ],
)
def test__run_one(
    file_meta: types_.MigrationFileMeta, expected_report: types_.MigrationReport, tmp_path: Path
):
    """
    arrange: given a migration metadata and mocked discourse
    act: when _run_one is called
    assert: a valid migration report is returned and a file is created.
    """
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.retrieve_topic.side_effect = "content"

    returned_report = migration._run_one(
        file_meta=file_meta, discourse=mocked_discourse, docs_path=tmp_path
    )

    assert returned_report.path is not None
    assert returned_report.path.is_file()
    assert expected_report.path is not None
    assert returned_report.path == tmp_path / expected_report.path
    assert returned_report.result == expected_report.result
    assert returned_report.reason == expected_report.reason
    assert returned_report.table_row == expected_report.table_row


@pytest.mark.parametrize(
    "migration_metas, expected_results",
    [
        pytest.param([document_meta], [document_report], id="single"),
        pytest.param(
            [document_meta, gitkeep_meta], [document_report, gitkeep_report], id="multiple"
        ),
    ],
)
def test_run(
    migration_metas: list[types_.MigrationFileMeta],
    expected_results: list[types_.MigrationReport],
    tmp_path: Path,
):
    """
    arrange: given migration metadata and mocked discourse
    act: when run is called
    assert: migration reports are returned and files are created.
    """
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.retrieve_topic.side_effect = "content"

    returned_reports = migration.run(
        documents=migration_metas, discourse=mocked_discourse, docs_path=tmp_path
    )

    for returned, expected in zip(returned_reports, expected_results):
        assert returned.path is not None
        assert returned.path.is_file()
        assert expected.path is not None
        assert returned.path == tmp_path / expected.path
        assert returned.result == expected.result
        assert returned.reason == expected.reason
        assert returned.table_row == expected.table_row
