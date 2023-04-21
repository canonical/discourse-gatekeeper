# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for run module."""

# Need access to protected functions for testing
# pylint: disable=protected-access

from pathlib import Path
from unittest import mock

import pytest

from src import constants, discourse, index, types_
from src.exceptions import DiscourseError, ServerError

from .helpers import assert_substrings_in_string


def test__read_docs_index_docs_directory_missing(tmp_path: Path):
    """
    arrange: given empty directory
    act: when _read_docs_index is called with the directory
    assert: then None is returned.
    """
    returned_content = index._read_docs_index(base_path=tmp_path)

    assert returned_content is None


def test__read_docs_index_index_file_missing(tmp_path: Path):
    """
    arrange: given directory with the docs folder
    act: when _read_docs_index is called with the directory
    assert: then None is returned.
    """
    docs_directory = tmp_path / constants.DOCUMENTATION_FOLDER_NAME
    docs_directory.mkdir()

    returned_content = index._read_docs_index(base_path=tmp_path)

    assert returned_content is None


def test__read_docs_index_index_file(index_file_content: str, tmp_path: Path):
    """
    arrange: given directory with the docs folder and index file
    act: when _read_docs_index is called with the directory
    assert: then the index file content is returned.
    """
    returned_content = index._read_docs_index(base_path=tmp_path)

    assert returned_content == index_file_content


def test_get_metadata_yaml_retrieve_discourse_error(tmp_path: Path):
    """
    arrange: given directory with metadata.yaml with docs defined and discourse client that
        raises DiscourseError
    act: when get is called with that directory
    assert: then ServerError is raised.
    """
    meta = types_.Metadata(name="name", docs="http://server/index-page")
    mocked_server_client = mock.MagicMock(spec=discourse.Discourse)
    mocked_server_client.retrieve_topic.side_effect = DiscourseError

    with pytest.raises(ServerError) as exc_info:
        index.get(metadata=meta, base_path=tmp_path, server_client=mocked_server_client)

    assert_substrings_in_string(("index page", "retrieval", "failed"), str(exc_info.value).lower())


def test_get_metadata_yaml_retrieve_local_and_server(tmp_path: Path, index_file_content: str):
    """
    arrange: given directory with metadata.yaml with docs defined and discourse client that
        returns the index page content and local index file
    act: when get is called with that directory
    assert: then retrieve topic is called with the docs key value and the content returned by the
        client, docs key and local file information is returned.
    """
    url = "http://server/index-page"
    name = "name 1"
    meta = types_.Metadata(name=name, docs=url)
    mocked_server_client = mock.MagicMock(spec=discourse.Discourse)
    mocked_server_client.retrieve_topic.return_value = (content := "content 2")

    returned_index = index.get(
        metadata=meta, base_path=tmp_path, server_client=mocked_server_client
    )

    assert returned_index.server is not None
    assert returned_index.server.url == url
    assert returned_index.server.content == content
    assert returned_index.local.title == "Name 1 Documentation Overview"
    assert returned_index.local.content == index_file_content
    assert returned_index.name == name
    mocked_server_client.retrieve_topic.assert_called_once_with(url=url)


def test_get_metadata_yaml_retrieve_empty(tmp_path: Path):
    """
    arrange: given directory with metadata.yaml without docs defined and empty local documentation
    act: when get is called with that directory
    assert: then all information is None except the title.
    """
    name = "name 1"
    meta = types_.Metadata(name=name, docs=None)
    mocked_server_client = mock.MagicMock(spec=discourse.Discourse)

    returned_index = index.get(
        metadata=meta, base_path=tmp_path, server_client=mocked_server_client
    )

    assert returned_index.server is None
    assert returned_index.local.title == "Name 1 Documentation Overview"
    assert returned_index.local.content is None
    assert returned_index.name == name


TABLE_ROWS = [
    types_.TableRow(level=1, path=("tutorial",), navlink=types_.Navlink("Title1", None)),
    types_.TableRow(level=2, path=("tutorial", "part-1"), navlink=types_.Navlink("Title2", None)),
    types_.TableRow(level=1, path=("how-to",), navlink=types_.Navlink("Title3", None)),
    types_.TableRow(level=1, path=("explanation",), navlink=types_.Navlink("Title4", None)),
]

TABLE_ROWS_TEXT = "\n".join([table.to_markdown() for table in TABLE_ROWS])


# Pylint doesn't understand how the walrus operator works
# pylint: disable=undefined-variable,unused-variable
@pytest.mark.parametrize(
    "page, expected_content, expected_rows",
    [
        pytest.param(
            f"{constants.NAVIGATION_TABLE_START}\n{TABLE_ROWS_TEXT}",
            "",
            TABLE_ROWS,
            id="navigation table only",
        ),
        pytest.param(
            f"{(content := 'Page content')}",
            content,
            [],
            id="content only",
        ),
        pytest.param(
            f"{(content := 'Page content')}{constants.NAVIGATION_TABLE_START}\n{TABLE_ROWS_TEXT}",
            content,
            TABLE_ROWS,
            id="content and navigation table",
        ),
        pytest.param(
            f"{(content := 'Page content')}"
            f"{constants.NAVIGATION_TABLE_START}\n{TABLE_ROWS_TEXT}\n"
            "content-afterwards",
            content,
            TABLE_ROWS,
            id="content and navigation table, content afterwards ignored",
        ),
        pytest.param(
            f"{(content := 'Page content')}"
            f"\n# Navigation\n|     Level |    Path  |Navlink|\n{TABLE_ROWS_TEXT}",
            content,
            TABLE_ROWS,
            id="content and unformatted navigation table",
        ),
        # pytest.param(
        #     (content := "Page content"),
        #     content,
        #     id="page content only",
        # ),
        # pytest.param(
        #     (multiline_content := "Page content\nWithMultiline"),
        #     multiline_content,
        #     id="multiline content only",
        # ),
        # pytest.param(
        #     f"{(content := 'Page content')}{constants.NAVIGATION_TABLE_START}",
        #     content,
        #     id="page with content and navigation table",
        # ),
        # pytest.param(
        #     f"{(content := 'page content')}{constants.NAVIGATION_TABLE_START}\ncontent-afterwards",
        #     content,
        #     id="page with content after the navigation table",
        # ),
    ],
)
# pylint: enable=undefined-variable,unused-variable
def test_get_contents_from_page(
        page: str, expected_content: str, expected_rows: list[types_.TableRow]
):
    """
    arrange: given an index page from server
    act: when contents_from_page is called
    assert: contents without navigation table is returned.
    """
    index_content = index.contents_from_index(index=page)
    assert index_content.content == expected_content
    assert list(index_content.navigation_table) == expected_rows