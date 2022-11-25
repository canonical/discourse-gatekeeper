# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for run module."""

# Need access to protected functions for testing
# pylint: disable=protected-access

from pathlib import Path
from unittest import mock

import pytest

from src import discourse, index
from src.exceptions import DiscourseError, InputError, ServerError


def create_metadata_yaml(content: str, path: Path) -> None:
    """Create the metadata file.

    Args:
        content: The text to be written to the file.
        path: The directory to create the file in.

    """
    metadata_yaml = path / index.METADATA_FILENAME
    metadata_yaml.write_text(content, encoding="utf-8")


def assert_substrings_in_string(substrings: tuple[str, ...], string: str) -> None:
    """Assert that a string contains substrings.

    Args:
        string: The string to check.
        substrings: The sub strings that must be contained in the string.

    """
    for substring in substrings:
        assert substring in string


def test__get_metadata_metadata_yaml_missing(tmp_path: Path):
    """
    arrange: given empty directory
    act: when _get_metadata is called with that directory
    assert: then InputError is raised.
    """
    with pytest.raises(InputError) as exc_info:
        index._get_metadata(path=tmp_path)

    assert index.METADATA_FILENAME in str(exc_info.value).lower()


@pytest.mark.parametrize(
    "metadata_yaml_content, expected_error_msg_contents",
    [
        pytest.param("", ("empty", index.METADATA_FILENAME), id="malformed"),
        pytest.param("malformed: yaml:", ("malformed", index.METADATA_FILENAME), id="malformed"),
        pytest.param("value 1", ("not", "mapping", index.METADATA_FILENAME), id="not dict"),
    ],
)
def test__get_metadata_metadata_yaml_malformed(
    metadata_yaml_content: str, expected_error_msg_contents: tuple[str, ...], tmp_path: Path
):
    """
    arrange: given directory with metadata.yaml that is malformed
    act: when _get_metadata is called with the directory
    assert: then InputError is raised.
    """
    create_metadata_yaml(content=metadata_yaml_content, path=tmp_path)

    with pytest.raises(InputError) as exc_info:
        index._get_metadata(path=tmp_path)

    assert_substrings_in_string(expected_error_msg_contents, str(exc_info.value).lower())


def test__get_metadata_metadata(tmp_path: Path):
    """
    arrange: given directory with metadata.yaml with valid mapping yaml
    act: when _get_metadata is called with the directory
    assert: then file contents are returned as a dictionary.
    """
    create_metadata_yaml(content="key: value", path=tmp_path)

    metadata = index._get_metadata(path=tmp_path)

    assert metadata == {"key": "value"}


@pytest.mark.parametrize(
    "metadata, expected_error_msg_content",
    [
        pytest.param({}, "not defined", id="empty"),
        pytest.param({"key": "value"}, "not defined", id="docs not defined"),
        pytest.param({index.METADATA_DOCS_KEY: ""}, "empty", id="docs empty"),
        pytest.param({index.METADATA_DOCS_KEY: 5}, "not a string", id="not string"),
    ],
)
def test__get_key_docs_missing_malformed(metadata: dict, expected_error_msg_content: str):
    """
    arrange: given malformed metadata
    act: when _get_key is called with the metadata
    assert: then InputError is raised.
    """
    with pytest.raises(InputError) as exc_info:
        index._get_key(metadata=metadata, key=index.METADATA_DOCS_KEY)

    assert_substrings_in_string(
        (
            f"'{index.METADATA_DOCS_KEY}'",
            expected_error_msg_content,
            index.METADATA_FILENAME,
            f"{metadata=!r}",
        ),
        str(exc_info.value).lower(),
    )


def test__get_key():
    """
    arrange: given metadata with docs key
    act: when _get_key is called with the metadata
    assert: then the docs value is returned.
    """
    docs_key = index.METADATA_DOCS_KEY
    docs_value = "url 1"

    returned_value = index._get_key(metadata={docs_key: docs_value}, key=docs_key)

    assert returned_value == docs_value


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
    docs_directory = tmp_path / index.DOCUMENTATION_FOLDER_NAME
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
    create_metadata_yaml(
        content=f"{index.METADATA_DOCS_KEY}: http://server/index-page", path=tmp_path
    )
    mocked_server_client = mock.MagicMock(spec=discourse.Discourse)
    mocked_server_client.retrieve_topic.side_effect = DiscourseError

    with pytest.raises(ServerError) as exc_info:
        index.get(base_path=tmp_path, server_client=mocked_server_client)

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
    create_metadata_yaml(
        content=f"{index.METADATA_DOCS_KEY}: {url}\n{index.METADATA_NAME_KEY}: {name}",
        path=tmp_path,
    )
    mocked_server_client = mock.MagicMock(spec=discourse.Discourse)
    mocked_server_client.retrieve_topic.return_value = (content := "content 2")

    returned_index = index.get(base_path=tmp_path, server_client=mocked_server_client)

    assert returned_index.server.url == url
    assert returned_index.server.content == content
    assert returned_index.local.title == "Name 1 Documentation Overview"
    assert returned_index.local.content == index_file_content
    mocked_server_client.retrieve_topic.assert_called_once_with(url=url)


def test_get_metadata_yaml_retrieve_empty(tmp_path: Path):
    """
    arrange: given directory with metadata.yaml without docs defined and empty local documentation
    act: when get is called with that directory
    assert: then all information is None except the title.
    """
    name = "name 1"
    create_metadata_yaml(content=f"{index.METADATA_NAME_KEY}: {name}", path=tmp_path)
    mocked_server_client = mock.MagicMock(spec=discourse.Discourse)

    returned_index = index.get(base_path=tmp_path, server_client=mocked_server_client)

    assert returned_index.server is None
    assert returned_index.local.title == "Name 1 Documentation Overview"
    assert returned_index.local.content is None
