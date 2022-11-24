# Copyright 2022 Canonical Ltd.
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
                level=1, path="path-1", navlink=types_.Navlink(title="title 1", link="/link-1")
            ),
            "| 1 | path-1 | [title 1](/link-1) |",
            id="not group",
        ),
        pytest.param(
            types_.TableRow(
                level=2, path="path-2", navlink=types_.Navlink(title="title 2", link=None)
            ),
            "| 2 | path-2 | [title 2]() |",
            id="is group",
        ),
    ],
)
def test_table_row_to_line(table_row: types_.TableRow, expected_line: bool):
    """
    arrange: given TableRow
    act: when to_line is called
    assert: then expected result is returned.
    """
    assert table_row.to_line() == expected_line
