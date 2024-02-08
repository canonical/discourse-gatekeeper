# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for private functions of migration module."""

# Need access to protected functions for testing
# pylint: disable=protected-access

from collections.abc import Iterable
from pathlib import Path
from typing import cast
from unittest import mock

import pytest

from src import discourse, exceptions, migration, types_

from ... import factories
from ..helpers import assert_substrings_in_string


@pytest.mark.parametrize(
    "table_rows, expected_message_contents",
    [
        pytest.param(
            (factories.TableRowFactory(level=2),),
            (
                "invalid starting row level",
                "a table row must start with level value 1",
                "please fix the upstream first and re-run",
            ),
            id="Invalid starting row",
        ),
        pytest.param(
            (
                factories.TableRowFactory(level=1),
                factories.TableRowFactory(level=0),
            ),
            ("invalid row level", "zero or negative level value is invalid."),
            id="Invalid level(0)",
        ),
        pytest.param(
            (
                factories.TableRowFactory(level=1),
                factories.TableRowFactory(level=-1),
            ),
            ("invalid row level", "zero or negative level value is invalid."),
            id="Invalid level(negative value)",
        ),
        pytest.param(
            (factories.TableRowFactory(level=1), factories.TableRowFactory(level=3)),
            (
                "invalid row level value sequence",
                "level sequence jumps of more than 1 is invalid.",
            ),
            id="Invalid level sequence jump",
        ),
        pytest.param(
            (
                factories.TableRowFactory(level=1, is_document=True),
                factories.TableRowFactory(level=2, is_document=True),
            ),
            (
                "invalid row level value sequence",
                "level sequence jumps of more than 1 is invalid.",
            ),
            id="document sequence level increase(no group)",
        ),
        pytest.param(
            (
                factories.TableRowFactory(level=1, is_document=True),
                factories.TableRowFactory(level=2, is_group=True),
            ),
            (
                "invalid row level value sequence",
                "level sequence jumps of more than 1 is invalid.",
            ),
            id="document group sequence level increase(no group)",
        ),
        pytest.param(
            (
                factories.TableRowFactory(level=1, is_group=True),
                factories.TableRowFactory(level=2, is_document=True),
                factories.TableRowFactory(level=3, is_group=True),
            ),
            (
                "invalid row level value sequence",
                "level sequence jumps of more than 1 is invalid.",
            ),
            id="document group sequence level increase(doc doesn't increase group level)",
        ),
    ],
)
def test__validate_table_rows_invalid_rows(
    table_rows: tuple[types_.TableRow, ...],
    expected_message_contents: Iterable[str],
    mocked_clients,
):
    """
    arrange: given invalid table_rows sequence
    act: when _validate_table_rows is called
    assert: InputError is raised with expected error message contents.
    """
    with pytest.raises(exceptions.InputError) as exc:
        tuple(
            row
            for row in migration._validate_table_rows(
                table_rows=table_rows, discourse=mocked_clients.discourse
            )
        )

    assert_substrings_in_string(expected_message_contents, str(exc.value).lower())


@pytest.mark.parametrize(
    "table_rows",
    [
        pytest.param(
            (factories.TableRowFactory(level=1),),
            id="Valid starting row",
        ),
        pytest.param(
            (
                factories.TableRowFactory(level=1, is_group=True),
                factories.TableRowFactory(level=2, is_group=True),
            ),
            id="Valid row sequence(increase)",
        ),
        pytest.param(
            (
                factories.TableRowFactory(level=1, is_group=True),
                factories.TableRowFactory(level=2, is_group=True),
                factories.TableRowFactory(level=1, is_group=True),
            ),
            id="Valid row sequence(decrease)",
        ),
        pytest.param(
            (
                factories.TableRowFactory(level=1, is_group=True),
                factories.TableRowFactory(level=2, is_group=True),
                factories.TableRowFactory(level=3, is_group=True),
                factories.TableRowFactory(level=1, is_group=True),
            ),
            id="Valid row sequence(decrease multi)",
        ),
    ],
)
def test__validate_table_rows(table_rows: tuple[types_.TableRow, ...], mocked_clients):
    """
    arrange: given table rows of valid sequence
    act: when _validate_table_rows is called
    assert: an iterable with original sequence preserved is returned.
    """
    assert tuple(
        row
        for row in migration._validate_table_rows(
            table_rows=table_rows, discourse=mocked_clients.discourse
        )
    ) == tuple(row for row in table_rows)


# Pylint doesn't understand how the walrus operator works
# pylint: disable=undefined-variable,unused-variable
@pytest.mark.parametrize(
    "row, expected_meta",
    [
        pytest.param(
            doc_row := factories.TableRowFactory(is_document=True, path=("doc-1",)),
            types_.DocumentMeta(
                path=Path("doc-1.md"), link=cast(str, doc_row.navlink.link), table_row=doc_row
            ),
            id="single doc file",
        ),
        pytest.param(
            doc_row := factories.TableRowFactory(is_document=True, path=("group-1", "doc-1")),
            types_.DocumentMeta(
                path=Path("group-1/doc-1.md"),
                link=cast(str, doc_row.navlink.link),
                table_row=doc_row,
            ),
            id="nested doc file",
        ),
        pytest.param(
            doc_row := factories.TableRowFactory(
                is_document=True,
                path=(
                    "group-1",
                    "group-2-doc-1",
                ),
            ),
            types_.DocumentMeta(
                path=Path("group-1/group-2-doc-1.md"),
                link=cast(str, doc_row.navlink.link),
                table_row=doc_row,
            ),
            id="typo in nested doc file path",
        ),
    ],
)
def test__create_document_meta(row: types_.TableRow, expected_meta: types_.DocumentMeta):
    """
    arrange: given a document table row
    act: when _create_document_meta is called
    assert: document meta with path to file is returned.
    """
    assert migration._create_document_meta(row=row) == expected_meta


@pytest.mark.parametrize(
    "row, expected_meta",
    [
        pytest.param(
            group_row := factories.TableRowFactory(is_group=True, path=("group-1",)),
            types_.GitkeepMeta(path=Path("group-1/.gitkeep"), table_row=group_row),
            id="single group row",
        ),
        pytest.param(
            group_row := factories.TableRowFactory(is_group=True, path=("group-1", "group-2")),
            types_.GitkeepMeta(path=Path("group-1/group-2/.gitkeep"), table_row=group_row),
            id="nested group row with correct current path",
        ),
    ],
)
def test__create_gitkeep_meta(row: types_.TableRow, expected_meta: types_.GitkeepMeta):
    """
    arrange: given a empty group table row
    act: when _create_gitkeep_meta is called
    assert: gitkeep meta denoting empty group is returned.
    """
    assert migration._create_gitkeep_meta(row=row) == expected_meta


def test__index_file_from_content(mocked_clients):
    """
    arrange: given an index file content
    act: when _index_file_from_content is called
    assert: expected index document metadata is returned.
    """
    content = "content 1"
    table_row = factories.TableRowFactory(is_document=True)

    returned_index_file = migration._index_file_from_content(
        content, table_rows=(table_row,), discourse=mocked_clients.discourse
    )

    assert returned_index_file.path == Path("index.md")
    assert (
        returned_index_file.content
        == f"{content}\n\n# Contents\n\n1. [{table_row.navlink.title}]({table_row.path[0]}.md)"
    )


@pytest.mark.parametrize(
    "table_rows, expected_metas",
    [
        pytest.param((), (), id="no table rows"),
        pytest.param(
            (doc_row_1 := factories.TableRowFactory(level=1, path=("doc-1",), is_document=True),),
            (
                types_.DocumentMeta(
                    path=Path("doc-1.md"),
                    link=cast(str, cast(str, doc_row_1.navlink.link)),
                    table_row=doc_row_1,
                ),
            ),
            id="single initial document",
        ),
        pytest.param(
            (group_row_1 := factories.TableRowFactory(level=1, path=("group-1",), is_group=True),),
            (types_.GitkeepMeta(path=Path("group-1/.gitkeep"), table_row=group_row_1),),
            id="single initial group",
        ),
        pytest.param(
            (
                group_row_1 := factories.TableRowFactory(
                    level=1, path=("group-1",), is_external=True
                ),
            ),
            (),
            id="single initial external ref",
        ),
        pytest.param(
            (
                doc_row_1 := factories.TableRowFactory(level=1, path=("doc-1",), is_document=True),
                doc_row_2 := factories.TableRowFactory(level=1, path=("doc-2",), is_document=True),
            ),
            (
                types_.DocumentMeta(
                    path=Path("doc-1.md"),
                    link=cast(str, doc_row_1.navlink.link),
                    table_row=doc_row_1,
                ),
                types_.DocumentMeta(
                    path=Path("doc-2.md"),
                    link=cast(str, doc_row_2.navlink.link),
                    table_row=doc_row_2,
                ),
            ),
            id="two documents",
        ),
        pytest.param(
            (
                group_row_1 := factories.TableRowFactory(
                    level=1, path=("group-1",), is_group=True
                ),
                group_row_2 := factories.TableRowFactory(
                    level=1, path=("group-2",), is_group=True
                ),
            ),
            (
                types_.GitkeepMeta(path=Path("group-1/.gitkeep"), table_row=group_row_1),
                types_.GitkeepMeta(path=Path("group-2/.gitkeep"), table_row=group_row_2),
            ),
            id="distinct two groups",
        ),
        pytest.param(
            (
                doc_row_1 := factories.TableRowFactory(level=1, path=("doc-1",), is_document=True),
                group_row_1 := factories.TableRowFactory(
                    level=1, path=("group-1",), is_group=True
                ),
            ),
            (
                types_.DocumentMeta(
                    path=Path("doc-1.md"),
                    link=cast(str, doc_row_1.navlink.link),
                    table_row=doc_row_1,
                ),
                types_.GitkeepMeta(path=Path("group-1/.gitkeep"), table_row=group_row_1),
            ),
            id="distinct document and group",
        ),
        pytest.param(
            (
                doc_row_1 := factories.TableRowFactory(level=1, path=("doc-1",), is_document=True),
                group_row_1 := factories.TableRowFactory(
                    level=1, path=("group-1",), is_external=True
                ),
            ),
            (
                types_.DocumentMeta(
                    path=Path("doc-1.md"),
                    link=cast(str, doc_row_1.navlink.link),
                    table_row=doc_row_1,
                ),
            ),
            id="distinct document and external ref",
        ),
        pytest.param(
            (
                group_row_1 := factories.TableRowFactory(
                    level=1, path=("group-1",), is_group=True
                ),
                doc_row_1 := factories.TableRowFactory(level=1, path=("doc-1",), is_document=True),
            ),
            (
                types_.GitkeepMeta(path=Path("group-1/.gitkeep"), table_row=group_row_1),
                types_.DocumentMeta(
                    path=Path("doc-1.md"),
                    link=cast(str, doc_row_1.navlink.link),
                    table_row=doc_row_1,
                ),
            ),
            id="distinct group and document",
        ),
        pytest.param(
            (
                factories.TableRowFactory(level=1, path=("external-1",), is_external=True),
                doc_row_1 := factories.TableRowFactory(level=1, path=("doc-1",), is_document=True),
            ),
            (
                types_.DocumentMeta(
                    path=Path("doc-1.md"),
                    link=cast(str, doc_row_1.navlink.link),
                    table_row=doc_row_1,
                ),
            ),
            id="distinct external ref and document",
        ),
        pytest.param(
            (
                group_row_1 := factories.TableRowFactory(
                    level=1, path=("group-1",), is_group=True
                ),
                doc_row_1 := factories.TableRowFactory(
                    level=2,
                    path=(
                        "group-1",
                        "doc-1",
                    ),
                    is_document=True,
                ),
            ),
            (
                types_.DocumentMeta(
                    path=Path("group-1/doc-1.md"),
                    link=cast(str, doc_row_1.navlink.link),
                    table_row=doc_row_1,
                ),
            ),
            id="nested document in group",
        ),
        pytest.param(
            (
                group_row_1 := factories.TableRowFactory(
                    level=1, path=("group-1",), is_group=True
                ),
                group_row_2 := factories.TableRowFactory(
                    level=2,
                    path=(
                        "group-1",
                        "group-2",
                    ),
                    is_group=True,
                ),
            ),
            (types_.GitkeepMeta(path=Path("group-1/group-2/.gitkeep"), table_row=group_row_2),),
            id="nested group in group",
        ),
        pytest.param(
            (
                group_row_1 := factories.TableRowFactory(
                    level=1, path=("group-1",), is_group=True
                ),
                group_row_2 := factories.TableRowFactory(
                    level=1, path=("group-2",), is_group=True
                ),
                group_row_3 := factories.TableRowFactory(
                    level=1, path=("group-3",), is_group=True
                ),
            ),
            (
                types_.GitkeepMeta(path=Path("group-1/.gitkeep"), table_row=group_row_1),
                types_.GitkeepMeta(path=Path("group-2/.gitkeep"), table_row=group_row_2),
                types_.GitkeepMeta(path=Path("group-3/.gitkeep"), table_row=group_row_3),
            ),
            id="distinct rows(group, group, group)",
        ),
        pytest.param(
            (
                group_row_1 := factories.TableRowFactory(
                    level=1, path=("group-1",), is_group=True
                ),
                doc_row_1 := factories.TableRowFactory(level=1, path=("doc-1",), is_document=True),
                group_row_2 := factories.TableRowFactory(
                    level=1, path=("group-2",), is_group=True
                ),
            ),
            (
                types_.GitkeepMeta(path=Path("group-1/.gitkeep"), table_row=group_row_1),
                types_.DocumentMeta(
                    path=Path("doc-1.md"),
                    link=cast(str, doc_row_1.navlink.link),
                    table_row=doc_row_1,
                ),
                types_.GitkeepMeta(path=Path("group-2/.gitkeep"), table_row=group_row_2),
            ),
            id="distinct rows(group, doc, group)",
        ),
        pytest.param(
            (
                group_row_1 := factories.TableRowFactory(
                    level=1, path=("group-1",), is_group=True
                ),
                nested_doc_row_1 := factories.TableRowFactory(
                    level=2, path=("group-1", "doc-1"), is_document=True
                ),
                group_row_2 := factories.TableRowFactory(
                    level=1, path=("group-2",), is_group=True
                ),
            ),
            (
                types_.DocumentMeta(
                    path=Path("group-1/doc-1.md"),
                    link=cast(str, nested_doc_row_1.navlink.link),
                    table_row=nested_doc_row_1,
                ),
                types_.GitkeepMeta(path=Path("group-2/.gitkeep"), table_row=group_row_2),
            ),
            id="multi rows 1 nested(group, nested-doc, group)",
        ),
        pytest.param(
            (
                group_row_1 := factories.TableRowFactory(
                    level=1, path=("group-1",), is_group=True
                ),
                nested_doc_row_1 := factories.TableRowFactory(
                    level=2, path=("group-1", "doc-1"), is_document=True
                ),
                nested_group_row_1 := factories.TableRowFactory(
                    level=2, path=("group-1", "group-2"), is_group=True
                ),
            ),
            (
                types_.DocumentMeta(
                    path=Path("group-1/doc-1.md"),
                    link=cast(str, nested_doc_row_1.navlink.link),
                    table_row=nested_doc_row_1,
                ),
                types_.GitkeepMeta(
                    path=Path("group-1/group-2/.gitkeep"), table_row=nested_group_row_1
                ),
            ),
            id="multi rows 2 separately nested(group, nested-group, nested-doc)",
        ),
        pytest.param(
            (
                group_row_1 := factories.TableRowFactory(
                    level=1, path=("group-1",), is_group=True
                ),
                nested_doc_row_1 := factories.TableRowFactory(
                    level=2, path=("group-1", "doc-1"), is_document=True
                ),
                nested_doc_row_2 := factories.TableRowFactory(
                    level=2, path=("group-1", "doc-2"), is_document=True
                ),
            ),
            (
                types_.DocumentMeta(
                    path=Path("group-1/doc-1.md"),
                    link=cast(str, nested_doc_row_1.navlink.link),
                    table_row=nested_doc_row_1,
                ),
                types_.DocumentMeta(
                    path=Path("group-1/doc-2.md"),
                    link=cast(str, nested_doc_row_2.navlink.link),
                    table_row=nested_doc_row_2,
                ),
            ),
            id="multi rows 2 nested in group(group, nested-doc, nested-doc)",
        ),
        pytest.param(
            (
                group_row_1 := factories.TableRowFactory(
                    level=1, path=("group-1",), is_group=True
                ),
                nested_group_row_1 := factories.TableRowFactory(
                    level=2, path=("group-1", "group-2"), is_group=True
                ),
                doc_row_1 := factories.TableRowFactory(level=1, path=("doc-1",), is_document=True),
            ),
            (
                types_.GitkeepMeta(
                    path=Path("group-1/group-2/.gitkeep"), table_row=nested_group_row_1
                ),
                types_.DocumentMeta(
                    path=Path("doc-1.md"),
                    link=cast(str, doc_row_1.navlink.link),
                    table_row=doc_row_1,
                ),
            ),
            id="multi rows 2 separately nested(group, nested-group, doc)",
        ),
        pytest.param(
            (
                group_row_1 := factories.TableRowFactory(
                    level=1, path=("group-1",), is_group=True
                ),
                nested_group_row_1 := factories.TableRowFactory(
                    level=2, path=("group-1", "group-2"), is_group=True
                ),
                nested_doc_row_1 := factories.TableRowFactory(
                    level=2, path=("group-1", "doc-1"), is_document=True
                ),
            ),
            (
                types_.GitkeepMeta(
                    path=Path("group-1/group-2/.gitkeep"), table_row=nested_group_row_1
                ),
                types_.DocumentMeta(
                    path=Path("group-1/doc-1.md"),
                    link=cast(str, nested_doc_row_1.navlink.link),
                    table_row=nested_doc_row_1,
                ),
            ),
            id="multi rows 2 separately nested(group, nested-group, nested-doc)",
        ),
        pytest.param(
            (
                group_row_1 := factories.TableRowFactory(
                    level=1, path=("group-1",), is_group=True
                ),
                nested_group_row_1 := factories.TableRowFactory(
                    level=2, path=("group-1", "group-2"), is_group=True
                ),
                nested_doc_row_1 := factories.TableRowFactory(
                    level=3, path=("group-1", "group-2", "doc-1"), is_document=True
                ),
            ),
            (
                types_.DocumentMeta(
                    path=Path("group-1/group-2/doc-1.md"),
                    link=cast(str, nested_doc_row_1.navlink.link),
                    table_row=nested_doc_row_1,
                ),
            ),
            id="multi rows nested(group, nested-group, nested-group-nested-doc)",
        ),
    ],
)
def test__extract_docs_from_table_rows(
    table_rows: tuple[types_.TableRow, ...],
    expected_metas: tuple[types_.DocumentMeta, ...],
    mocked_clients,
):
    """
    arrange: given an valid table row sequences
    act: when _extract_docs_from_table_rows is called
    assert: expected document metadatas are yielded.
    """
    assert (
        tuple(
            row
            for row in migration._extract_docs_from_table_rows(
                table_rows=table_rows, discourse=mocked_clients.discourse
            )
        )
        == expected_metas
    )


@pytest.mark.parametrize(
    "meta",
    [
        pytest.param(
            types_.GitkeepMeta(path=Path(".gitkeep"), table_row=factories.TableRowFactory()),
            id="single .gitkeep",
        ),
        pytest.param(
            types_.GitkeepMeta(
                path=Path("nested-dir/.gitkeep"), table_row=factories.TableRowFactory()
            ),
            id="nested .gitkeep",
        ),
    ],
)
def test__migrate_gitkeep(meta: types_.GitkeepMeta, tmp_path: Path):
    """
    arrange: given a gitkeep file metadata and a temporary path denoting docs directory
    act: when _migrate_gitkeep is called
    assert: Successful action report is returned and gitkeep file is created.
    """
    returned_report = migration._migrate_gitkeep(gitkeep_meta=meta, docs_path=tmp_path)
    assert returned_report.table_row == meta.table_row
    assert returned_report.result == types_.ActionResult.SUCCESS
    assert returned_report.location == tmp_path / meta.path
    assert returned_report.reason == migration.EMPTY_DIR_REASON
    assert (tmp_path / meta.path).is_file()


def _test__table_row_to_contents_index_line_parameters():
    """Generate parameters for the test__table_row_to_contents_index_line test.

    Returns:
        The tests.
    """
    return [
        pytest.param(
            row := factories.TableRowFactory(is_document=True),
            f"1. [{row.navlink.title}]({row.path[0]}.md)",
            id="page top level path",
        ),
        pytest.param(
            row := factories.TableRowFactory(is_document=True, path=("dir_1", "file")),
            f"  1. [{row.navlink.title}]({row.path[0]}/{row.path[1]}.md)",
            id="page nested path path",
        ),
        pytest.param(
            row := factories.TableRowFactory(is_document=True, path=("dir_1", "dir_2", "file")),
            f"    1. [{row.navlink.title}]({row.path[0]}/{row.path[1]}/{row.path[2]}.md)",
            id="page deeply nested path",
        ),
        pytest.param(
            row := factories.TableRowFactory(is_group=True),
            f"1. [{row.navlink.title}]({row.path[0]})",
            id="group top level path",
        ),
        pytest.param(
            row := factories.TableRowFactory(is_group=True, path=("dir_1", "dir_2")),
            f"  1. [{row.navlink.title}]({row.path[0]}/{row.path[1]})",
            id="group nested path path",
        ),
        pytest.param(
            row := factories.TableRowFactory(is_group=True, path=("dir_1", "dir_2", "dir_3")),
            f"    1. [{row.navlink.title}]({row.path[0]}/{row.path[1]}/{row.path[2]})",
            id="group deeply nested path",
        ),
        pytest.param(
            row := factories.TableRowFactory(is_external=True),
            f"1. [{row.navlink.title}]({row.navlink.link})",
            id="page top level path",
        ),
        pytest.param(
            row := factories.TableRowFactory(
                is_external=True, path=("dir_1", "https-canonical-com")
            ),
            f"  1. [{row.navlink.title}]({row.navlink.link})",
            id="page nested path path",
        ),
        pytest.param(
            row := factories.TableRowFactory(
                is_external=True, path=("dir_1", "dir_2", "https-canonical-com")
            ),
            f"    1. [{row.navlink.title}]({row.navlink.link})",
            id="page deeply nested path",
        ),
    ]


@pytest.mark.parametrize(
    "row, expected_line", _test__table_row_to_contents_index_line_parameters()
)
def test__table_row_to_contents_index_line(
    row: types_.TableRow, expected_line: str, mocked_clients
):
    """
    arrange: given table row
    act: when _table_row_to_contents_index_line is called with the row
    assert: then the expected contents index line is returned.
    """
    returned_line = migration._table_row_to_contents_index_line(
        row=row, discourse=mocked_clients.discourse
    )

    assert returned_line == expected_line


def _test__migrate_navigation_table_parameters():
    """Generate parameters for the test__migrate_navigation_table test.

    Returns:
        The tests.
    """
    return [
        pytest.param(
            (),
            "# Contents",
            id="empty rows",
        ),
        pytest.param(
            (row_1 := factories.TableRowFactory(is_document=True),),
            f"# Contents\n\n1. [{row_1.navlink.title}]({row_1.path[0]}.md)",
            id="single row",
        ),
        pytest.param(
            (
                row_1 := factories.TableRowFactory(is_document=True),
                row_2 := factories.TableRowFactory(is_document=True),
            ),
            (
                "# Contents\n\n"
                f"1. [{row_1.navlink.title}]({row_1.path[0]}.md)\n"
                f"1. [{row_2.navlink.title}]({row_2.path[0]}.md)"
            ),
            id="multiple rows",
        ),
    ]


@pytest.mark.parametrize(
    "rows, expected_contents_index", _test__migrate_navigation_table_parameters()
)
def test__migrate_navigation_table(
    rows: tuple[types_.TableRow, ...], expected_contents_index: str, mocked_clients
):
    """
    arrange: given table rows
    act: when _migrate_navigation_table is called with the rows
    assert: then the expected contents index is returned.
    """
    returned_contents_index = migration._migrate_navigation_table(
        rows=rows, discourse=mocked_clients.discourse
    )

    assert returned_contents_index == expected_contents_index


def test__migrate_document_fail(tmp_path: Path, mocked_clients):
    """
    arrange: given valid document metadata and mocked discourse that raises an error
    act: when _migrate_document is called
    assert: failed migration report is returned.
    """
    mocked_discourse = mocked_clients.discourse
    mocked_discourse.retrieve_topic.side_effect = (error := exceptions.DiscourseError("fail"))
    table_row = types_.TableRow(
        level=(level := 1),
        path=(path_str := ("empty-group-path",)),
        navlink=factories.NavlinkFactory(
            title=(navlink_title := "title 1"), link=(link_str := "link 1")
        ),
    )
    document_meta = types_.DocumentMeta(
        path=(path := Path(*path_str)), table_row=table_row, link=link_str
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
        path=(path_str := ("empty-directory",)),
        navlink=factories.NavlinkFactory(
            title=(navlink_title := "title 1"), link=(link_str := "link 1")
        ),
    )
    document_meta = types_.DocumentMeta(
        path=(path := Path(*path_str)), table_row=table_row, link=link_str
    )

    returned_report = migration._migrate_document(
        document_meta=document_meta, discourse=mocked_discourse, docs_path=tmp_path
    )

    assert (file_path := tmp_path / path).is_file()
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

    assert (file_path := tmp_path / path).is_file()
    assert file_path.read_text(encoding="utf-8") == content
    assert returned_report.table_row is None
    assert returned_report.result == types_.ActionResult.SUCCESS
    assert returned_report.location == tmp_path / path
    assert returned_report.reason is None


@pytest.mark.parametrize(
    "file_meta, expected_report",
    [
        pytest.param(
            gitkeep_meta := types_.GitkeepMeta(
                path=(gitkeep_path := Path(".gitkeep")),
                table_row=(table_row_sample := factories.TableRowFactory()),
            ),
            gitkeep_report := types_.ActionReport(
                table_row=table_row_sample,
                location=gitkeep_path,
                result=types_.ActionResult.SUCCESS,
                reason=migration.EMPTY_DIR_REASON,
            ),
            id="gitkeep file",
        ),
        pytest.param(
            document_meta := types_.DocumentMeta(
                path=(document_path := Path("document.md")),
                table_row=(table_row_sample := factories.TableRowFactory()),
                link="samplelink",
            ),
            document_report := types_.ActionReport(
                table_row=table_row_sample,
                location=document_path,
                result=types_.ActionResult.SUCCESS,
                reason=None,
            ),
            id="document file",
        ),
        pytest.param(
            types_.IndexDocumentMeta(
                path=(index_path := Path("index.md")), content="index content"
            ),
            types_.ActionReport(
                table_row=None,
                location=index_path,
                result=types_.ActionResult.SUCCESS,
                reason=None,
            ),
            id="index file",
        ),
    ],
)
def test__run_one(
    file_meta: types_.MigrationFileMeta, expected_report: types_.ActionReport, tmp_path: Path
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

    assert isinstance(returned_report.location, Path)
    assert returned_report.location.is_file()
    assert isinstance(expected_report.location, Path)
    assert returned_report.location == tmp_path / expected_report.location
    assert returned_report.result == expected_report.result
    assert returned_report.reason == expected_report.reason
    assert returned_report.table_row == expected_report.table_row


def test__get_docs_metadata(mocked_clients):
    """
    arrange: given table rows from index table and the index_content from index file
    act: when _get_docs_metadata is called
    assert: an iterable starting with index migration metadata is returned.
    """
    table_rows = (factories.TableRowFactory(level=1),)
    index_content = "index-content-1"

    returned_docs_metadata = tuple(
        meta
        for meta in migration._get_docs_metadata(
            table_rows=table_rows, index_content=index_content, discourse=mocked_clients.discourse
        )
    )

    assert len(returned_docs_metadata) == 2
    assert isinstance(returned_docs_metadata[0], types_.IndexDocumentMeta)
    assert isinstance(returned_docs_metadata[1], types_.MigrationFileMeta)
