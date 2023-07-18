# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for types module."""

import pytest

from src import types_

from .. import factories


@pytest.mark.parametrize(
    "table_row, expected_is_group",
    [
        pytest.param(
            types_.TableRow(
                level=1, path=("path 1",), navlink=types_.Navlink(title="title 1", link="link 1")
            ),
            False,
            id="not group",
        ),
        pytest.param(
            types_.TableRow(
                level=1, path=("path 1",), navlink=types_.Navlink(title="title 1", link=None)
            ),
            True,
            id="is group",
        ),
    ],
)
def test_table_row_is_group(table_row: types_.TableRow, expected_is_group: bool):
    """
    arrange: given TableRow
    act: when is_group is called
    assert: then expected result is returned.
    """
    assert table_row.is_group == expected_is_group


def _test_table_row_to_markdown_parameters():
    """Generate parameters for the test_table_row_to_markdown test.

    Returns:
        The tests.
    """
    return [
        pytest.param(
            factories.TableRowFactory(
                level=1, path=("path-1",), navlink=types_.Navlink(title="title 1", link="/link-1")
            ),
            "| 1 | path-1 | [title 1](/link-1) |",
            id="not group",
        ),
        pytest.param(
            factories.TableRowFactory(
                level=1,
                path=("path-1",),
                navlink=types_.Navlink(title="title 1", link="/link-1"),
                hidden=True,
            ),
            "| | path-1 | [title 1](/link-1) |",
            id="not group hidden",
        ),
        pytest.param(
            factories.TableRowFactory(
                level=1,
                path=("path-1",),
                navlink=types_.Navlink(title="title 1", link="http://host/link-1"),
            ),
            "| 1 | path-1 | [title 1](/link-1) |",
            id="url with protocol and host",
        ),
        pytest.param(
            factories.TableRowFactory(
                level=2, path=("path-2",), navlink=types_.Navlink(title="title 2", link=None)
            ),
            "| 2 | path-2 | [title 2]() |",
            id="is group",
        ),
        pytest.param(
            factories.TableRowFactory(
                level=2,
                path=("path-2",),
                navlink=types_.Navlink(title="title 2", link=None),
                hidden=True,
            ),
            "| | path-2 | [title 2]() |",
            id="is group hidden",
        ),
        pytest.param(
            factories.TableRowFactory(
                level=2,
                path=(
                    "path-1",
                    "path-2",
                ),
                navlink=types_.Navlink(title="title 2", link=None),
            ),
            "| 2 | path-1-path-2 | [title 2]() |",
            id="is group",
        ),
    ]


@pytest.mark.parametrize("table_row, expected_line", _test_table_row_to_markdown_parameters())
def test_table_row_to_markdown(table_row: types_.TableRow, expected_line: bool):
    """
    arrange: given TableRow
    act: when to_markdown is called
    assert: then expected result is returned.
    """
    assert table_row.to_markdown() == expected_line
