# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for types module."""

import pytest

from src import types_


@pytest.mark.parametrize(
    "table_row, expected_is_group",
    [
        pytest.param(
            types_.TableRow(
                level=1, path="path 1", navlink=types_.Navlink(title="title 1", link="link 1")
            ),
            False,
            id="not group",
        ),
        pytest.param(
            types_.TableRow(
                level=1, path="path 1", navlink=types_.Navlink(title="title 1", link=None)
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


@pytest.mark.parametrize(
    "table_row, expected_line",
    [
        pytest.param(
            types_.TableRow(
                level=1, path=("path-1",), navlink=types_.Navlink(title="title 1", link="/link-1")
            ),
            "| 1 | path-1 | [title 1](/link-1) |",
            id="not group",
        ),
        pytest.param(
            types_.TableRow(
                level=1,
                path=("path-1",),
                navlink=types_.Navlink(title="title 1", link="http://host/link-1"),
            ),
            "| 1 | path-1 | [title 1](/link-1) |",
            id="url with protocol and host",
        ),
        pytest.param(
            types_.TableRow(
                level=2, path=("path-2",), navlink=types_.Navlink(title="title 2", link=None)
            ),
            "| 2 | path-2 | [title 2]() |",
            id="is group",
        ),
    ],
)
def test_table_row_to_markdown(table_row: types_.TableRow, expected_line: bool):
    """
    arrange: given TableRow
    act: when to_markdown is called
    assert: then expected result is returned.
    """
    assert table_row.to_markdown() == expected_line


@pytest.mark.parametrize(
    "hrow, depth, expected_result",
    [
        pytest.param(
            types_.HierachicalTableRow(
                row1 := types_.TableRow(
                    level=1, path=("g1",), navlink=types_.Navlink("", None)
                ), []
            ),
            None,
            [row1]
        ),
        pytest.param(
            types_.HierachicalTableRow(
                row1,
                [types_.HierachicalTableRow(
                    row2 := types_.TableRow(
                        level=2, path=("g1","g2"), navlink=types_.Navlink("", None)
                    ), []
                )]
            ),
            None,
            [row1, row2]
        ),
        pytest.param(
            types_.HierachicalTableRow(
                row1,
                [types_.HierachicalTableRow(
                    row2 := types_.TableRow(
                        level=2, path=("g1", "g2"), navlink=types_.Navlink("", None)
                    ), []
                )]
            ),
            0,
            [row1]
        ),
        pytest.param(
            types_.HierachicalTableRow(
                row1,
                [types_.HierachicalTableRow(
                    row2 := types_.TableRow(
                        level=2, path=("g1", "g2"), navlink=types_.Navlink("", None)
                    ), []
                )]
            ),
            1,
            [row1, row2]
        ),
    ],
)
def test_hierarchical_row_get_rows(
        hrow: types_.HierachicalTableRow, depth: int | None, expected_result: list[types_.TableRow]
):
    """
    arrange: given HierarchicalTableRow
    act: when get_rows is called with various depth values
    assert: then expected result is returned.
    """
    assert list(hrow.get_rows(depth)) == expected_result



@pytest.mark.parametrize(
    "hrow, expected_result",
    [
        pytest.param(
            types_.HierachicalTableRow(
                row1 := types_.TableRow(
                    level=1, path=("my-file",), navlink=types_.Navlink("", None)
                ),
                []
            ),
            True
        ),
        pytest.param(
            hrow := types_.HierachicalTableRow(
                row1,
                [types_.HierachicalTableRow(
                    types_.TableRow(
                        level=2, path=("g1", "g2"), navlink=types_.Navlink("", None)
                    ), []
                )]
            ),
            False,
        ),
        pytest.param(hrow.children[0], True)
    ]
)
def test_hierarchical_row_is_leaf(hrow: types_.HierachicalTableRow, expected_result: bool):
    """
    arrange: given HierarchicalTableRow
    act: when is_leaf is called
    assert: then expected result is returned.
    """
    assert hrow.is_leaf == expected_result
