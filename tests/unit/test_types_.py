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
            factories.TableRowFactory(navlink=factories.NavlinkFactory(link="link 1")),
            False,
            id="not group",
        ),
        pytest.param(
            factories.TableRowFactory(navlink=factories.NavlinkFactory(link=None)),
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
    "table_row, server_hostname, expected_is_external",
    [
        pytest.param(
            factories.TableRowFactory(navlink=factories.NavlinkFactory(link=None)),
            "https://discourse.com",
            False,
            id="group",
        ),
        pytest.param(
            factories.TableRowFactory(navlink=factories.NavlinkFactory(link="doc.md")),
            "https://discourse.com",
            False,
            id="local link",
        ),
        pytest.param(
            factories.TableRowFactory(
                navlink=factories.NavlinkFactory(link="https://discourse.com/1")
            ),
            "https://discourse.com",
            False,
            id="link matching server url",
        ),
        pytest.param(
            factories.TableRowFactory(
                navlink=factories.NavlinkFactory(link="https://discourse.com/1")
            ),
            "https://DISCOURSE.com",
            False,
            id="link matching server url different case",
        ),
        pytest.param(
            factories.TableRowFactory(
                navlink=factories.NavlinkFactory(link="https://canonical.com")
            ),
            "https://discourse.com",
            True,
            id="external link",
        ),
        pytest.param(
            factories.TableRowFactory(
                navlink=factories.NavlinkFactory(link="https://canonical.com?param=val")
            ),
            "https://discourse.com",
            True,
            id="external link query string",
        ),
        pytest.param(
            factories.TableRowFactory(
                navlink=factories.NavlinkFactory(link="https://canonical.com#anchor")
            ),
            "https://discourse.com",
            True,
            id="external link anchor",
        ),
        pytest.param(
            factories.TableRowFactory(
                navlink=factories.NavlinkFactory(link="HTTPS://canonical.com")
            ),
            "https://discourse.com",
            True,
            id="external link upper case",
        ),
        pytest.param(
            factories.TableRowFactory(
                navlink=factories.NavlinkFactory(link="http://canonical.com")
            ),
            "https://discourse.com",
            True,
            id="external link http",
        ),
    ],
)
def test_table_row_is_external(
    table_row: types_.TableRow, server_hostname: str, expected_is_external: bool
):
    """
    arrange: given TableRow
    act: when is_external is called
    assert: then expected result is returned.
    """
    assert table_row.is_external(server_hostname=server_hostname) == expected_is_external


def _test_table_row_to_markdown_parameters():
    """Generate parameters for the test_table_row_to_markdown test.

    Returns:
        The tests.
    """
    return [
        pytest.param(
            factories.TableRowFactory(
                level=1,
                path=("path-1",),
                navlink=factories.NavlinkFactory(title="title 1", link="/link-1"),
            ),
            "https://discourse.com",
            "| 1 | path-1 | [title 1](/link-1) |",
            id="not group",
        ),
        pytest.param(
            factories.TableRowFactory(
                level=1,
                path=("path-1",),
                navlink=factories.NavlinkFactory(title="title 1", link="/link-1", hidden=True),
            ),
            "https://discourse.com",
            "| | path-1 | [title 1](/link-1) |",
            id="not group hidden",
        ),
        pytest.param(
            factories.TableRowFactory(
                level=1,
                path=("path-1",),
                navlink=factories.NavlinkFactory(
                    title="title 1", link="https://discourse.com/link-1"
                ),
            ),
            "https://discourse.com",
            "| 1 | path-1 | [title 1](/link-1) |",
            id="url with protocol and host matching server hostname",
        ),
        pytest.param(
            factories.TableRowFactory(
                level=1,
                path=("path-1",),
                navlink=factories.NavlinkFactory(
                    title="title 1", link="https://discourse.com/link-1"
                ),
            ),
            "https://DISCOURSE.com",
            "| 1 | path-1 | [title 1](/link-1) |",
            id="url with protocol and host matching server hostname different case",
        ),
        pytest.param(
            factories.TableRowFactory(
                level=2,
                path=("path-2",),
                navlink=factories.NavlinkFactory(title="title 2", link=None),
            ),
            "https://discourse.com",
            "| 2 | path-2 | [title 2]() |",
            id="is group",
        ),
        pytest.param(
            factories.TableRowFactory(
                level=2,
                path=("path-2",),
                navlink=factories.NavlinkFactory(title="title 2", link=None, hidden=True),
            ),
            "https://discourse.com",
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
                navlink=factories.NavlinkFactory(title="title 2", link=None),
            ),
            "https://discourse.com",
            "| 2 | path-1-path-2 | [title 2]() |",
            id="is group",
        ),
        pytest.param(
            factories.TableRowFactory(
                level=1,
                path=("path-1",),
                navlink=factories.NavlinkFactory(title="title 1", link="https://canonical.com/"),
            ),
            "https://discourse.com",
            "| 1 | path-1 | [title 1](https://canonical.com/) |",
            id="is external",
        ),
        pytest.param(
            factories.TableRowFactory(
                level=1,
                path=("path-1",),
                navlink=factories.NavlinkFactory(
                    title="title 1", link="https://canonical.com/", hidden=True
                ),
            ),
            "https://discourse.com",
            "| | path-1 | [title 1](https://canonical.com/) |",
            id="is external hidden",
        ),
    ]


@pytest.mark.parametrize(
    "table_row, server_hostname, expected_line", _test_table_row_to_markdown_parameters()
)
def test_table_row_to_markdown(
    table_row: types_.TableRow, server_hostname: str, expected_line: bool
):
    """
    arrange: given TableRow
    act: when to_markdown is called
    assert: then expected result is returned.
    """
    assert table_row.to_markdown(server_hostname=server_hostname) == expected_line


@pytest.mark.parametrize(
    "index_contens_list_item, expected_table_path",
    [
        pytest.param(
            factories.IndexContentsListItemFactory(reference_value="dir"),
            ("dir",),
            id="top level dir",
        ),
        pytest.param(
            factories.IndexContentsListItemFactory(reference_value="file.md"),
            ("file",),
            id="top level file",
        ),
        pytest.param(
            factories.IndexContentsListItemFactory(reference_value="dir/nested-dir"),
            ("dir", "nested-dir"),
            id="dir in dir",
        ),
        pytest.param(
            factories.IndexContentsListItemFactory(reference_value="dir/file.md"),
            ("dir", "file"),
            id="file in dir",
        ),
        pytest.param(
            factories.IndexContentsListItemFactory(
                reference_value="dir/nested-dir/deeply-nested-dir"
            ),
            ("dir", "nested-dir", "deeply-nested-dir"),
            id="dir in dir in dir",
        ),
        pytest.param(
            factories.IndexContentsListItemFactory(reference_value="https://canonical.com"),
            ("https", "canonical", "com"),
            id="external",
        ),
        pytest.param(
            factories.IndexContentsListItemFactory(reference_value="https://canonical.com/page"),
            ("https", "canonical", "com", "page"),
            id="external with path",
        ),
        pytest.param(
            factories.IndexContentsListItemFactory(
                reference_value="https://canonical.com?key=value"
            ),
            ("https", "canonical", "com", "keyvalue"),
            id="external with query",
        ),
        pytest.param(
            factories.IndexContentsListItemFactory(reference_value="https://canonical.com#anchor"),
            ("https", "canonical", "com", "anchor"),
            id="external with anchor",
        ),
        pytest.param(
            factories.IndexContentsListItemFactory(reference_value="https://canonical.com%"),
            ("https", "canonical", "com"),
            id="external with single special characters",
        ),
        pytest.param(
            factories.IndexContentsListItemFactory(reference_value="https://canonical.com%$"),
            ("https", "canonical", "com"),
            id="external with multiple special characters",
        ),
        pytest.param(
            factories.IndexContentsListItemFactory(
                reference_value="https://canonical.com/page/nested-page"
            ),
            ("https", "canonical", "com", "page", "nested-page"),
            id="external with deep path",
        ),
    ],
)
def test_index_contens_list_item_table_path(
    index_contens_list_item: types_.IndexContentsListItem, expected_table_path: bool
):
    """
    arrange: given IndexContentsListItem
    act: when table_path is called
    assert: then expected result is returned.
    """
    assert index_contens_list_item.table_path == expected_table_path
