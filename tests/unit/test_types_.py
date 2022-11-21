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
        ),
        pytest.param(
            types_.TableRow(
                level=1, path="path 1", navlink=types_.Navlink(title="title 1", link=None)
            ),
            True,
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
