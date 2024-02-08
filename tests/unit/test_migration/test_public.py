# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for public functions in migration module."""

from collections.abc import Iterable
from pathlib import Path
from unittest import mock

import pytest

from src import discourse, exceptions, migration, types_

from ... import factories


def test_run_error(tmp_path: Path):
    """
    arrange: given table rows, index content, mocked discourse that throws an exception and a
        temporary docs path
    act: when run is called
    assert: table rows are successfully migrated
    """
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.retrieve_topic.side_effect = exceptions.DiscourseError
    table_rows = (factories.TableRowFactory(level=1),)

    with pytest.raises(exceptions.MigrationError):
        migration.run(
            table_rows=table_rows,
            index_content="content-1",
            discourse=mocked_discourse,
            docs_path=tmp_path,
        )


def _test_run_parameters():
    """Generate parameters for the test_run test.

    Returns:
        The tests.
    """
    return [
        pytest.param(
            (row_1 := factories.TableRowFactory(is_document=True, path=("doc-1",), level=1),),
            (index_content := "content-1"),
            (path_1 := Path(f"{row_1.path[0]}.md"),),
            f"{index_content}\n\n# Contents\n\n1. [{row_1.navlink.title}]({path_1})",
            id="single doc",
        ),
        pytest.param(
            (
                row_1 := factories.TableRowFactory(is_group=True, path=("group-1",), level=1),
                row_2 := factories.TableRowFactory(
                    is_document=True, path=("group-1", "doc-1"), level=2
                ),
            ),
            (index_content := "content-1"),
            (path_2 := Path(f"{row_2.path[0]}/{row_2.path[1]}.md"),),
            (
                f"{index_content}\n\n"
                "# Contents\n\n"
                f"1. [{row_1.navlink.title}]({row_1.path[0]})\n"
                f"  1. [{row_2.navlink.title}]({path_2})"
            ),
            id="nested doc",
        ),
        pytest.param(
            (
                row_1 := factories.TableRowFactory(is_group=True, path=("group-1",), level=1),
                row_2 := factories.TableRowFactory(
                    is_group=True, path=("group-1", "group-2"), level=2
                ),
            ),
            (index_content := "content-1"),
            (Path(f"{row_2.path[0]}/{row_2.path[1]}/.gitkeep"),),
            (
                f"{index_content}\n\n"
                "# Contents\n\n"
                f"1. [{row_1.navlink.title}]({row_1.path[0]})\n"
                f"  1. [{row_2.navlink.title}]({row_2.path[0]}/{row_2.path[1]})"
            ),
            id="nested group no docs",
        ),
    ]


@pytest.mark.parametrize(
    "table_rows, index_content, expected_files, expected_index_content",
    _test_run_parameters(),
)
def test_run(
    table_rows: tuple[types_.TableRow, ...],
    index_content: str,
    tmp_path: Path,
    expected_files: Iterable[Path],
    expected_index_content: str,
):
    """
    arrange: given table rows, index content, mocked discourse and a temporary docs path
    act: when run is called
    assert: table rows are successfully migrated
    """
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.retrieve_topic.return_value = "document-content"

    migration.run(
        table_rows=table_rows,
        index_content=index_content,
        discourse=mocked_discourse,
        docs_path=tmp_path,
    )

    assert (tmp_path / "index.md").read_text() == expected_index_content
    for path in expected_files:
        assert (tmp_path / path).is_file()
